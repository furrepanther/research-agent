import yaml
import os
import logging
import re
import sys
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("research_agent.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def load_config(config_path="config.yaml"):
    # Target path priority:
    # 1. Current Working Directory (for dev/custom runs)
    # 2. Directory of the executable (for standalone installations)
    # 3. Environment variable (optional, not implemented)
    
    final_path = config_path
    if not os.path.exists(final_path):
        # Check near the executable if frozen
        if getattr(sys, 'frozen', False):
            exe_dir = os.path.dirname(sys.executable)
            alt_path = os.path.join(exe_dir, config_path)
            if os.path.exists(alt_path):
                final_path = alt_path
        
    if not os.path.exists(final_path):
        raise FileNotFoundError(f"Config file not found at {final_path}")
    
    with open(final_path, "r") as f:
        return yaml.safe_load(f)

def ensure_directories(config):
    os.makedirs(config.get("papers_dir", "data/papers"), exist_ok=True)
    os.makedirs(os.path.dirname(config.get("db_path", "data/metadata.db")), exist_ok=True)

def get_config():
    config = load_config()
    ensure_directories(config)
    return config

def save_config(config, config_path="config.yaml"):
    """Saves the configuration dict to the file."""
    # Try to find where it was loaded from if we want to be persistent
    final_path = config_path
    if not os.path.exists(final_path) and getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        alt_path = os.path.join(exe_dir, config_path)
        final_path = alt_path

    with open(final_path, "w") as f:
        yaml.dump(config, f, sort_keys=False, default_flow_style=False)

def extract_simple_keywords(query):
    """
    Extracts meaningful keywords from a complex boolean query string.
    Removes operators (AND, OR, NOT) and punctuation.
    Returns a list of unique lowercase terms.
    """
    if not query:
        return []
    
    # Remove parens and quotes (both single and double)
    cleaned = query.replace('(', ' ').replace(')', ' ').replace('"', ' ').replace("'", ' ')
    
    # Split by whitespace
    tokens = cleaned.split()
    
    # Filter out operators and short/common words
    stop_words = {'and', 'or', 'not', 'andnot', 'to', 'in', 'of', 'the', 'a', 'an'}
    keywords = set()
    
    for token in tokens:
        t = token.lower().strip()
        if t and t not in stop_words and len(t) > 1:
            keywords.add(t)
            
    return list(keywords)

def clean_latex(text):
    """
    Removes common LaTeX formatting commands from text, keeping the content.
    Handles nested commands by looping.
    """
    if not text:
        return ""
        
    # Standard commands to strip wrapper from: \textbf{text} -> text
    # Loop to handle nesting like \underline{\textbf{...}}
    prev_text = None
    while prev_text != text:
        prev_text = text
        # Remove formatting wrappers
        text = re.sub(r'\\(textbf|textit|underline|emph|textsc)\{(.*?)\}', r'\2', text)
        # Remove simple no-arg commands
        text = re.sub(r'\\(bf|it|tt)\s+', '', text)
        
    # Handle escaped characters
    text = text.replace(r'\%', '%').replace(r'\&', '&').replace(r'\$', '$').replace(r'\#', '#')
    text = text.replace(r'\{', '{').replace(r'\}', '}')
    
    # Remove math mode delimiters (simple case)
    text = text.replace('$', '')
    
    return text.strip()

def to_title_case(text):
    """Converts a string to Title Case based on standard rules, preserving acronyms."""
    if not text:
        return ""
    
    # 0. Initial Clean
    # Remove common junk seen in samples
    text = text.replace("â•ﬂ", " - ").replace("â•Ž26", "'26").replace("â•Ž", "'")
    text = re.sub(r' \| .*$', '', text) # Remove source suffixes like "| LessWrong"
    text = text.replace("Microsoft Word - ", "")
    
    # Remove specific date patterns often found in titles
    # e.g., (2023), [2022], 2023-12-01
    text = re.sub(r'\(\d{4}\)', '', text)
    text = re.sub(r'\[\d{4}\]', '', text)
    text = re.sub(r'\d{4}-\d{2}-\d{2}', '', text)
    
    # Remove junk characters (pipes, asterisks, tildes)
    # Keep colons, hyphens, question marks, exclamation marks, quotes, parens
    text = re.sub(r'[\|\*\~]', ' ', text)
    
    # Replace underscores with spaces (always)
    text = text.replace("_", " ")
    
    # Only replace hyphens if they are likely separators (surrounded by spaces)
    # or between words where no specialized term is expected.
    # For now, let's keep hyphens inside words but replace ' - ' with ' : ' or ' - '
    # Wait, the user said "replace technical separators (_ , -) with clean spaces".
    # Let's stick to spaces but be careful with acronyms.
    text = text.replace("-", " ") 
    
    minor_words = {
        'a', 'an', 'the', 'and', 'but', 'for', 'at', 'by', 'from', 'in', 'into', 
        'of', 'off', 'on', 'onto', 'out', 'over', 'up', 'with', 'as', 'to'
    }
    
    # List of acronyms to preserve in EXACT casing if possible, or force Upper
    acronyms = {
        "AI": "AI", "AGI": "AGI", "LLM": "LLM", "LLMS": "LLMs", "NLP": "NLP", 
        "RL": "RL", "RLHF": "RLHF", "ML": "ML", "GPT": "GPT", "GAN": "GAN",
        "KBQA": "KBQA", "SQL": "SQL", "GUI": "GUI", "API": "API", "RAG": "RAG"
    }
    
    words = text.split()
    if not words:
        return ""
    
    title_words = []
    for i, word in enumerate(words):
        # Handle punctuation inside/around word (like "LLMs:")
        clean_word = re.sub(r'[^\w]', '', word).upper()
        
        # Preserve common research acronyms
        if clean_word in acronyms:
            # Preserve the punctuation if any
            prefix = re.match(r'^[^\w]*', word).group()
            suffix = re.search(r'[^\w]*$', word).group()
            title_words.append(f"{prefix}{acronyms[clean_word]}{suffix}")
            continue
            
        # Capitalize if first/last or not a minor word
        word_for_case = re.sub(r'[^\w]', '', word).lower()
        if i == 0 or i == len(words) - 1 or word_for_case not in minor_words:
            # If word is mostly uppercase, keep it uppercase (assume acronym)
            if sum(1 for c in word if c.isupper()) > 1 and len(word) > 1:
                title_words.append(word)
            else:
                title_words.append(word.capitalize())
        else:
            title_words.append(word.lower())
            
    return " ".join(title_words)

def normalize_url(url):
    """
    Normalize URL for comparison and deduplication.
    - Forces https (most academic sites use https)
    - Removes trailing slash
    - Removes common tracking params
    - Lowercases domain
    """
    if not url:
        return url

    from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

    # Parse URL
    parsed = urlparse(url)

    # Normalize scheme to https (most academic sites use https now)
    scheme = 'https'

    # Lowercase domain
    netloc = parsed.netloc.lower()

    # Remove trailing slash from path
    path = parsed.path.rstrip('/')

    # Remove tracking parameters
    tracking_params = {'utm_source', 'utm_medium', 'utm_campaign', 'ref', 'source', 'fbclid', 'gclid'}
    if parsed.query:
        query_dict = parse_qs(parsed.query)
        # Remove tracking params
        query_dict = {k: v for k, v in query_dict.items() if k not in tracking_params}
        # Rebuild query string
        query = urlencode(query_dict, doseq=True) if query_dict else ''
    else:
        query = ''

    # Reconstruct URL
    normalized = urlunparse((scheme, netloc, path, '', query, ''))
    return normalized

def sanitize_filename(title, extension=""):
    """Creates a Windows-safe filename using Title Case and removing 'garbage'."""
    # 1. Title Case
    clean_title = to_title_case(title)
    # 2. Windows Safe: No < > : " / \ | ? * and no underscores
    safe_title = re.sub(r'[<>:"/\\|?*_]', ' ', clean_title)
    # 3. No extra spaces
    safe_title = " ".join(safe_title.split())
    # 4. Length limit (under 150 for safety)
    safe_title = safe_title[:150].strip()
    if not safe_title:
        safe_title = "Untitled Paper"
    return f"{safe_title}{extension}"

def clear_directory(directory_path):
    """Safely delete ALL files and folders within a directory without deleting the directory itself."""
    import shutil
    if not os.path.exists(directory_path):
        return
    
    for filename in os.listdir(directory_path):
        file_path = os.path.join(directory_path, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            logger.error(f"Failed to delete {file_path}. Reason: {e}")

def run_beautification(dry_run=True, progress_callback=None, db_path=None):
    """
    Renames physical files to Title Case and updates the database.
    Used by CLI maintenance tools and the GUI.
    """
    import sqlite3
    import shutil
    
    config = get_config()
    if not db_path:
        db_path = config.get("db_path", "data/metadata.db")
    
    if not os.path.exists(db_path):
        logger.error(f"Database not found at {db_path}")
        return 0, 0

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, title, pdf_path FROM papers")
    papers = cursor.fetchall()
    
    logger.info(f"Analyzing {len(papers)} papers for beautification...")
    if progress_callback:
        progress_callback(f"Analyzing {len(papers)} papers...")
    
    changes_made = 0
    errors = 0
    
    for row in papers:
        internal_id = row['id']
        old_title = row['title']
        old_path = row['pdf_path']
        
        if not old_path or not os.path.exists(old_path):
            continue
            
        new_title = to_title_case(old_title)
        new_filename = sanitize_filename(new_title, extension=".pdf")
        dir_name = os.path.dirname(old_path)
        new_path = os.path.join(dir_name, new_filename)
        
        if old_path == new_path and old_title == new_title:
            continue
            
        if dry_run:
            logger.info(f"Dry-run: '{old_title}' -> '{new_title}'")
            changes_made += 1
            continue
            
        try:
            # Physical Rename
            if old_path != new_path:
                if os.path.exists(new_path):
                    logger.warning(f"Collision: {new_path} exists. Skipping physical rename.")
                else:
                    os.rename(old_path, new_path)
            
            # Database Update
            cursor.execute(
                "UPDATE papers SET title = ?, pdf_path = ? WHERE id = ?",
                (new_title, new_path, internal_id)
            )
            changes_made += 1
            if progress_callback:
                progress_callback(f"Beautified: {new_title}")
            
        except Exception as e:
            logger.error(f"Error processing {old_title}: {e}")
            errors += 1
            
    if not dry_run:
        conn.commit()
        logger.info(f"Beautification complete. {changes_made} updated. {errors} errors.")
    else:
        logger.info(f"Dry-run complete. {changes_made} would be updated.")
        
    conn.close()
    return changes_made, errors

def generate_stable_hash(text):
    """
    Generates a 64-bit signed integer hash from a string using SHA-256.
    Ensures hashes are consistent across different Python runs and platforms.
    """
    import hashlib
    if not text:
        return 0
    
    # Use SHA-256 for a robust, stable hash
    hash_bytes = hashlib.sha256(text.encode('utf-8')).digest()
    
    # Take the first 8 bytes (64 bits) and convert to a signed integer
    # SQLite INTEGER can store up to 8-byte signed integers.
# ... (at end of file)
def is_english(text, threshold=0.5):
    """
    Detects if the text is in English using langdetect.
    Returns True if 'en' is the most probable language or above threshold.
    If detection fails, defaults to True for academic context.
    """
    if not text or len(text) < 10:
        return True
    
    try:
        from langdetect import detect_langs
        langs = detect_langs(text)
        if not langs:
            return True
        # Check if 'en' is the top language or has decent probability
        main_lang = langs[0]
        if main_lang.lang == 'en':
            return True
        # If 'en' is in the list with high enough probability
        for l in langs:
            if l.lang == 'en' and l.prob > threshold:
                return True
        return False
    except:
        return True

def clean_text(text):
    """
    Beautifies text for database storage.
    - Remove newlines
    - Compress spaces
    - Fix hyphenation (e.g. 'hyphen- ation' -> 'hyphenation')
    """
    if not text:
        return ""
    
    import re
    
    # 1. De-hyphenation (Word + Hyphen + Whitespace + Word)
    # Fixes splits like "algorithm- ic" -> "algorithmic"
    text = re.sub(r'(\w)-\s+(\w)', r'\1\2', text)
    
    # 2. Whitespace normalization (also handles newlines)
    return ' '.join(text.split())

def clear_directory(directory_path):
    """
    Recursively deletes all contents of a directory but keeps the directory itself.
    Used for cleaning up staging areas after successful transfers.
    """
    import os
    import shutil
    
    if not os.path.exists(directory_path):
        logger.warning(f"Directory does not exist: {directory_path}")
        return
    
    try:
        for item in os.listdir(directory_path):
            item_path = os.path.join(directory_path, item)
            try:
                if os.path.isfile(item_path) or os.path.islink(item_path):
                    os.unlink(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
            except Exception as e:
                logger.error(f"Failed to delete {item_path}: {e}")
        logger.info(f"Cleared directory: {directory_path}")
    except Exception as e:
        logger.error(f"Error clearing directory {directory_path}: {e}")
