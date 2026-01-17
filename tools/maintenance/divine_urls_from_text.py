
import sqlite3
import os
import re
import PyPDF2
from src.utils import get_config, logger
import logging

logging.basicConfig(level=logging.INFO)

def extract_urls_from_pdf(pdf_path, max_pages=3):
    text = ""
    urls = []
    try:
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            num_pages = min(len(reader.pages), max_pages)
            for i in range(num_pages):
                page = reader.pages[i]
                text += page.extract_text() or ""
                
                # Try to extract annotations (links)
                if "/Annots" in page:
                    for annot in page["/Annots"]:
                        obj = annot.get_object()
                        if "/A" in obj and "/URI" in obj["/A"]:
                            uri = obj["/A"]["/URI"]
                            urls.append(uri)
                            
    except Exception as e:
        logger.error(f"Error reading {pdf_path}: {e}")
        
    # Also find URLs in text using regex
    # Pattern for alignmentforum, lesswrong, arxiv, anthropic, openai, doi, etc.
    # We prioritize these specific domains as "canonical" sources
    text_urls = re.findall(r'(https?://(?:www\.)?(?:alignmentforum\.org|lesswrong\.com|arxiv\.org|anthropic\.com|openai\.com|deepmind\.com|openreview\.net|aclanthology\.org|ojs\.aaai\.org|nature\.com|science\.org|springer\.com)\S+)', text)
    urls.extend(text_urls)
    
    return list(set(urls))

def divine_urls():
    db_path = "R:/My Drive/03 Research Papers/metadata.db"
    if not os.path.exists(db_path):
        print("Production DB not found.")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get papers without source_url
    cursor.execute("SELECT id, title, pdf_path FROM papers WHERE source_url IS NULL OR source_url = ''")
    rows = cursor.fetchall()
    
    results = {}
    
    print(f"Scanning {len(rows)} papers for embedded URLs...")
    
    for row in rows:
        pdf_path = row['pdf_path']
        if not pdf_path or not os.path.exists(pdf_path):
            continue
            
        found_urls = extract_urls_from_pdf(pdf_path)
        
        # Simple heuristic: look for a URL that looks like the paper's home
        # For this pass, we just list what we find, or pick the best candidate
        candidate = None
        for url in found_urls:
            # Clean up trailing punctuation
            url = url.rstrip(').,;]')
            
            # Prioritize exact matches (simple heuristic)
            if "alignmentforum.org/posts/" in url or "lesswrong.com/posts/" in url:
                candidate = url
                break
            if "arxiv.org/abs/" in url:
                candidate = url
                break
            if "anthropic.com/research/" in url:
                candidate = url
                break
                
        if candidate:
            results[row['id']] = candidate
            print(f"Found candidate for [{row['id']}]: {candidate}")
            
    print(f"\nSummary: Found URL candidates for {len(results)} out of {len(rows)} papers.")
    
    import json
    with open("metadata_findings_text.json", "w") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    divine_urls()
