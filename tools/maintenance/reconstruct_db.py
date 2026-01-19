import os
import sys
import sqlite3
import re
import logging
import time
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from pypdf import PdfReader
from urllib.parse import urlparse, parse_qs
import urllib.parse
import atexit
import signal

# Add project root to path
sys.path.append(os.getcwd())
try:
    from src.utils import get_config, to_title_case, generate_stable_hash
    from src.storage import StorageManager
except ImportError:
    # Standalone fallback
    def get_config(): return {"cloud_storage": {"path": "R:/My Drive/03 Research Papers"}, "db_path": "data/metadata.db"}
    def to_title_case(t): return t.title()
    def generate_stable_hash(t): return hash(t)

if sys.platform == 'win32' and sys.stdout:
    sys.stdout.reconfigure(encoding='utf-8')

def ask_wipe_mode():
    """Calculates if user wants to wipe the DB. Returns True for Wipe, False for Update."""
    import ctypes
    
    # 0x04 = MB_YESNO
    # 0x30 = MB_ICONWARNING
    # 0x1000 = MB_SYSTEMMODAL (Force on top)
    # Return: 6 = YES, 7 = NO
    
    result = ctypes.windll.user32.MessageBoxW(
        0, 
        "Do you want to WIPE the database and start fresh?\n\nYes = DELETE existing database and rescan.\nNo = UPDATE existing database (faster).", 
        "Database Reconstruction", 
        0x04 | 0x30 | 0x1000
    )
    
    return result == 6

def verify_database(cursor):
    """
    Returns a dict of error counts in the DB.
    """
    stats = {}
    try:
        # Total
        cursor.execute("SELECT COUNT(*) FROM papers")
        stats['total'] = cursor.fetchone()[0]
        
        # Missing Abstracts (Empty or very short)
        cursor.execute("SELECT COUNT(*) FROM papers WHERE abstract IS NULL OR length(abstract) < 50")
        stats['missing_abstracts'] = cursor.fetchone()[0]
        
        # Missing URLs
        cursor.execute("SELECT COUNT(*) FROM papers WHERE source_url IS NULL OR length(source_url) < 5")
        stats['missing_urls'] = cursor.fetchone()[0]
        
    except Exception as e:
        logging.error(f"Verification failed: {e}")
        return {'total': 0, 'missing_abstracts': 0, 'missing_urls': 0, 'error': str(e)}
        
    return stats

def validate_url(url):
    """Check if URL is reachable (HEAD request)."""
    try:
        if not url or not url.startswith('http'):
            return False
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.head(url, headers=headers, timeout=5, allow_redirects=True)
        return resp.status_code < 400
    except:
        return False

def fetch_online_abstract(url):
    """
    Attempts to fetch abstract from the URL page (Arxiv/OpenReview/General).
    """
    if not url: return None
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        
        # Arxiv API (Better than scraping)
        if 'arxiv.org' in url:
            # Extract ID: arxiv.org/abs/2305.11004 -> 2305.11004
            arxiv_id = re.search(r'(\d+\.\d+)', url)
            if arxiv_id:
                api_url = f"http://export.arxiv.org/api/query?id_list={arxiv_id.group(1)}"
                resp = requests.get(api_url, timeout=10)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, 'xml') # XML for API
                    summary = soup.find('summary')
                    if summary:
                        return summary.text.strip().replace('\n', ' ')

        # General Scraping (OpenReview, etc)
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Meta Description
            meta = soup.find('meta', property='og:description') or soup.find('meta', attrs={'name': 'description'})
            if meta and meta.get('content'):
                return meta['content'].strip()
                
            # OpenReview specific (often in specific div)
            if 'openreview.net' in url:
                note = soup.find('span', class_='note-content-value')
                if note: return note.text.strip()
                
    except Exception as e:
        print(f"  Example: Online fetch failed for {url}: {e}")
        
    return None

def extract_metadata_from_pdf(file_path):
    """
    Extracts Title (from filename/text), URL (from links), and Abstract (heuristic).
    """
    meta = {
        'title': None,
        'url': None,
        'abstract': None,
        'authors': None,
        'date': None
    }
    
    filename = os.path.basename(file_path)
    clean_filename = os.path.splitext(filename)[0]
    
    # 1. Title from Filename (Title Case it)
    meta['title'] = to_title_case(clean_filename)
    
    try:
        reader = PdfReader(file_path)
        if not reader.pages:
            return meta
            
        first_page = reader.pages[0]
        
        # Visitor to extract text without headers/footers (approx by y-pos?)
        # For now, standard extract
        text = first_page.extract_text()
        
        # CLEANUP: De-hyphenation (Requested by User)
        # Fixes: "hyphen- ation" -> "hyphenation" (and "hyphen-\nation")
        # Pattern: Word char + Hyphen + Whitespace + Word char
        if text:
             text = re.sub(r'(\w)-\s+(\w)', r'\1\2', text)
        
        # 2. URL from Annotations
        if first_page.annotations:
            for annot in first_page.annotations:
                try:
                    annot_obj = annot.get_object()
                    if '/A' in annot_obj and '/URI' in annot_obj['/A']:
                        uri = annot_obj['/A']['/URI']
                        if any(x in uri for x in ['arxiv.org', 'openreview.net', 'doi.org', 'aclweb.org']):
                            meta['url'] = uri
                            break
                        if not meta['url'] and uri.startswith('http'):
                            meta['url'] = uri
                except:
                    pass
        
        # 3. URL from Text
        if not meta['url']:
            urls = re.findall(r'(https?://(?:arxiv\.org/abs/|openreview\.net/forum|doi\.org/)[^\s]+)', text)
            if urls:
                meta['url'] = urls[0]

        # 4. Abstract extraction (Improved)
        # Strategy: Find "Abstract" keyword. Take text until "Introduction" or "1." or page break.
        # Normalize text first (compress spaces)
        clean_text = ' '.join(text.split())
        
        # Regex: Abstract [content] Introduction
        # Allow for "Abstract." or "ABSTRACT"
        # DOTALL is crucial.
        matches = re.search(r'\b(?:Abstract|ABSTRACT|abstract)[\.:\s]*(.*?)\b(?:Introduction|INTRODUCTION|1\.|Background|Method)', clean_text, re.IGNORECASE)
        
        if matches:
            found_abs = matches.group(1).strip()
            # Sanity check length
            if len(found_abs) > 50 and len(found_abs) < 3000:
                meta['abstract'] = found_abs
        
        # Fallback: If no "Introduction" found, take first 1500 chars after Abstract
        if not meta['abstract'] and 'abstract' in clean_text.lower():
            start_idx = clean_text.lower().find('abstract') + 8
            meta['abstract'] = clean_text[start_idx:start_idx+1500].strip()
            
        # Fallback 2: No "Abstract" header at all (e.g. Transcript/Essay)
        if not meta['abstract'] and len(text) > 100:
             # Take start of text
             clean_intro = ' '.join(text[:2000].split())
             meta['abstract'] = clean_intro[:1500] + "..."

        # 5. Year from text
        year_match = re.search(r'\b(20\d\d)\b', text)
        if year_match:
            meta['date'] = year_match.group(1)
        else:
            mtime = os.path.getmtime(file_path)
            meta['date'] = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')

    except Exception as e:
        print(f"Error reading PDF {filename}: {e}")
        
    return meta

def web_search_url_heuristic(title):
    """
    Search for Title + 'abstract' to get a valid URL.
    """
    try:
        if not title: return None
        time.sleep(2) 
        headers = {'User-Agent': 'Mozilla/5.0'}
        query = f"{title} abstract"
        url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            results = soup.find_all('a', class_='result__a')
            for res in results:
                link = res.get('href')
                # Decode DDG redirect if present
                if 'duckduckgo.com/l/' in link:
                    try:
                        parsed = urlparse(link)
                        qs = urllib.parse.parse_qs(parsed.query)
                        if 'uddg' in qs:
                            link = qs['uddg'][0]
                    except:
                        pass
                
                # Prioritize sources
                if any(x in link for x in ['arxiv.org', 'openreview.net', 'aclweb.org', 'ieee.org', 'springer.com', 'acm.org', 'alignmentforum.org', 'lesswrong.com']):
                    return link
    except Exception as e:
        print(f"Search failed for '{title}': {e}")
    return None

def reconstruct_db():
    config = get_config()
    cloud_path = config.get("cloud_storage", {}).get("path")
    if not cloud_path or not os.path.exists(cloud_path):
        logging.error(f"Cloud path not found: {cloud_path}")
        return

    # Target the Cloud Database specifically as requested
    db_path = os.path.join(cloud_path, "metadata.db")

    # SETUP LOGGING (First, so we capture the UI wait)
    log_file = os.path.join(cloud_path, "reconstruction_log.txt")
    handlers = [logging.FileHandler(log_file, mode='w', encoding='utf-8')]
    if sys.stdout:
        handlers.append(logging.StreamHandler(sys.stdout))
        
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=handlers,
        force=True
    )
    logging.info(f"Scanning Cloud Directory: {cloud_path}")
    logging.info(f"Target Database (Cloud): {db_path}")

    # --- SINGLETON LOCK CHECK ---
    lock_file = os.path.join(cloud_path, "reconstruct.lock")
    pid = os.getpid()
    
    if os.path.exists(lock_file):
        try:
            with open(lock_file, 'r') as f:
                old_pid = f.read().strip()
            
            # Ask user what to do
            import ctypes
            # MB_YESNO | MB_ICONWARNING | MB_SYSTEMMODAL
            msg = f"Lock file found (PID {old_pid}).\nThe script appears to be running already.\n\nDo you want to FORCE START (kill/ignore old instance)?\n\nYes = Force Start\nNo = Exit"
            r = ctypes.windll.user32.MessageBoxW(0, msg, "Already Running?", 0x04 | 0x30 | 0x1000)
            
            if r != 6: # 6 = Yes
                logging.info("User chose to exit due to lock file.")
                return
            else:
                logging.info(f"User chose to override lock (old pid: {old_pid}).")
        except Exception as e:
            logging.error(f"Error checking lock file: {e}")

    # Create Lock
    with open(lock_file, 'w') as f:
        f.write(str(pid))
    
    def cleanup_lock():
        try:
            if os.path.exists(lock_file):
                os.remove(lock_file)
        except:
            pass
    atexit.register(cleanup_lock)

    # ASK USER FOR MODE (Wipe vs Update)
    # Always ask if we are running interactively-ish (headless but user initiated)
    # Even if DB is missing, we ask to confirm they want to start the reconstruction.
    
    logging.info(f"Checking for existing database at: {db_path}")
    
    if os.path.exists(db_path):
        logging.info("Existing database found. Initiating Popup...")
        should_wipe = ask_wipe_mode()
    else:
        # DB Missing -> Ask if they want to start fresh (or if they ran by mistake)
        logging.info("Database not found. Asking user to confirm Fresh Start...")
        import ctypes
        # MB_OKCANCEL | MB_ICONINFORMATION | MB_SYSTEMMODAL
        msg = "No existing database found.\n\nStart a FRESH reconstruction from cloud files?"
        r = ctypes.windll.user32.MessageBoxW(0, msg, "Database Missing", 0x01 | 0x40 | 0x1000)
        
        if r != 1: # 1 = OK
            logging.info("User cancelled fresh start.")
            return
            
        should_wipe = True # Fresh start is effectively a wipe
        logging.info("User confirmed Fresh Start.")


    logging.info(f"User selection: {'WIPE/FRESH' if should_wipe else 'UPDATE'}")
    
    if should_wipe:
        try:
            if os.path.exists(db_path):
                logging.info(f"{datetime.now()} - Wipe run started.")
                logging.info("User requested WIPE. Deleting old database...")
                os.remove(db_path)
            else:
                logging.info(f"{datetime.now()} - Fresh run started.")
        except Exception as e:
            logging.error(f"Failed to delete database: {e}")
    else:
        logging.info(f"{datetime.now()} - Update run started.")

    # Initialize Schema if needed (Fresh or Wiped)
    if should_wipe:
        try:
             logging.info("Initializing fresh database schema...")
             # StorageManager will create tables in __init__
             sm = StorageManager(db_path)
             # We rely on it to setup tables. No need to keep it open.
             del sm 
        except Exception as e:
             logging.error(f"Failed to initialize schema: {e}")
             return
        
    # Connect
    try:
        conn = sqlite3.connect(db_path, timeout=60)
    except Exception as e:
        logging.error(f"Failed to connect to database: {e}")
        return
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. Verification Before
    logging.info("Verifying database state BEFORE correction...")
    pre_stats = verify_database(cursor)
    logging.info(f"Pre-Stats: {pre_stats}")
    
    # Ensure Schema is up to date (Cloud DB might be old)
    try:
        cursor.execute("SELECT language FROM papers LIMIT 1")
    except sqlite3.OperationalError:
        print("Schema update: Adding 'language' column...")
        cursor.execute("ALTER TABLE papers ADD COLUMN language TEXT DEFAULT 'en'")
        
    try:
        cursor.execute("SELECT synced_to_cloud FROM papers LIMIT 1")
    except sqlite3.OperationalError:
        print("Schema update: Adding 'synced_to_cloud' column...")
        cursor.execute("ALTER TABLE papers ADD COLUMN synced_to_cloud INTEGER DEFAULT 1")

    # Also check for paper_hash unique index
    try:
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_paper_hash ON papers(paper_hash)")
    except Exception as e:
        logging.warning(f"Index error (ignored): {e}")

    files_processed = 0
    updates_made = 0
    inserts_made = 0
    
    for root, dirs, files in os.walk(cloud_path):
        for file in files:
            try:
                if not file.lower().endswith('.pdf'):
                    continue
                    
                file_path = os.path.join(root, file)
                files_processed += 1
                
                # Use a safer print for potential unicode filenames
                try:
                    logging.info(f"[{files_processed}] Processing: {file}")
                except:
                    logging.info(f"[{files_processed}] Processing: (filename print error)")

                # Extract
                meta = extract_metadata_from_pdf(file_path)
                title = meta['title']
                
                # Lookup existing to check validity of URL/Abstract
                t_hash = generate_stable_hash(title)
                
                # RECURRENCE FIX: Check by Path first (Robust against hash drift)
                cursor.execute("SELECT id, title, abstract, source_url, pdf_path FROM papers WHERE pdf_path = ?", (file_path,))
                existing = cursor.fetchone()
                
                if not existing:
                    # Fallback: Check by Title Hash (e.g. file moved)
                    cursor.execute("SELECT id, title, abstract, source_url, pdf_path FROM papers WHERE title_hash = ?", (t_hash,))
                    existing = cursor.fetchone()
                
                # If no URL in PDF, and existing URL is missing or looks bad?
                if not meta['url']:
                    if existing and existing['source_url'] and validate_url(existing['source_url']):
                        meta['url'] = existing['source_url']
                    else:
                        logging.info(f"  - Missing/Bad URL. Searching web for '{title}'...")
                        found_url = web_search_url_heuristic(title)
                        if found_url:
                            meta['url'] = found_url
                            logging.info(f"  - Found URL: {found_url}")
                
                # Re-generate hash with final URL
                if meta['url']:
                    p_hash = generate_stable_hash(meta['url'])
                else:
                    p_hash = generate_stable_hash(f"local:{title}")
                
                # IMPROVEMENT: If abstract missing/short, fetch online
                if (not meta['abstract'] or len(meta['abstract']) < 100) and meta['url']:
                    logging.info(f"  - Abstract missing. Fetching online from {meta['url']}...")
                    online_abs = fetch_online_abstract(meta['url'])
                    if online_abs:
                        meta['abstract'] = online_abs
                        logging.info(f"  - Found online abstract ({len(online_abs)} chars).")

                current_time = datetime.now().strftime("%Y-%m-%d")
                
                if existing: # UPDATE
                    update_sql = []
                    update_vals = []
                    
                    # FIX 1: Path
                    if not existing['pdf_path'] or existing['pdf_path'] != file_path:
                        update_sql.append("pdf_path = ?")
                        update_vals.append(file_path)
                    
                    # FIX 2: Abstract (if missing in DB but found in PDF)
                    if (not existing['abstract'] or len(existing['abstract']) < 50) and meta['abstract']:
                        print(f"  - Filling missing abstract ({len(meta['abstract'])} chars)")
                        update_sql.append("abstract = ?")
                        update_vals.append(meta['abstract'])
                        
                    # FIX 3: URL (if missing in DB)
                    if (not existing['source_url']) and meta['url']:
                        print(f"  - Update URL: {meta['url']}")
                        update_sql.append("source_url = ?")
                        update_vals.append(meta['url'])
                        update_sql.append("paper_hash = ?")
                        update_vals.append(p_hash)
                    
                    # Always Sync
                    update_sql.append("synced_to_cloud = 1")
                    
                    if update_sql:
                        sql = f"UPDATE papers SET {', '.join(update_sql)} WHERE id = ?"
                        update_vals.append(existing['id'])
                        cursor.execute(sql, update_vals)
                        updates_made += 1
                        logging.info("  - Updated record.")
                else:
                    # INSERT
                    logging.info("  - Creating NEW record.")
                    cursor.execute("""
                        INSERT INTO papers (
                            paper_hash, title_hash, title, published_date, 
                            authors, abstract, pdf_path, source_url, 
                            downloaded_date, source, synced_to_cloud, language
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        p_hash, t_hash, title, 
                        meta['date'], 
                        meta['authors'] or "Unknown", 
                        meta['abstract'] or "", 
                        file_path, 
                        meta['url'] or "", 
                        current_time, 
                        "Reconstructed", 
                        1, 
                        "en"
                    ))
                    inserts_made += 1
            except Exception as e:
                logging.error(f"  ERROR processing file: {e}", exc_info=True)
                
        conn.commit()
    
    # 2. Verification After
    logging.info("Verifying database state AFTER correction...")
    post_stats = verify_database(cursor)
    
    conn.close()

    # SUMMARY
    logging.info("=============================================")
    logging.info(f"Errors in database before correction: Total {pre_stats['total']} entries. (Abs: {pre_stats['missing_abstracts']}, URL: {pre_stats['missing_urls']})")
    logging.info(f"Errors in database after correction:  Total {post_stats['total']} entries. (Abs: {post_stats['missing_abstracts']}, URL: {post_stats['missing_urls']})")
    
    logging.info(f"Total research documents found on disk: {files_processed}")
    logging.info(f"Summary of Changes: {updates_made} Updates, {inserts_made} New Records Created.")
    logging.info("Reconstruction Complete.")
    logging.info("=============================================")
    # Also print to console for visibility if not redirected
    # print(summary) 
    
    
    # Notify user (Windows)
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, f"Reconstruction Complete.\nProcessed: {files_processed}\nUpdates: {updates_made}", "Research Agent", 0x40)
    except:
        pass

if __name__ == "__main__":
    reconstruct_db()
