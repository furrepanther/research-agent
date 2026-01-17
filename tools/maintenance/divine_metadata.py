
import sqlite3
import os
import re
import PyPDF2
from src.utils import get_config, logger

def extract_text_from_pdf(pdf_path, max_pages=1):
    text = ""
    try:
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            num_pages = min(len(reader.pages), max_pages)
            for i in range(num_pages):
                text += reader.pages[i].extract_text()
    except Exception as e:
        logger.error(f"Error reading {pdf_path}: {e}")
    return text

def divine_metadata():
    db_path = "R:/My Drive/03 Research Papers/metadata.db"
    if not os.path.exists(db_path):
        print("Production DB not found.")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, title, pdf_path FROM papers")
    rows = cursor.fetchall()
    
    # regex patterns
    arxiv_pattern = re.compile(r'arXiv:([0-9]{4}\.[0-9]{4,5})', re.IGNORECASE)
    doi_pattern = re.compile(r'10\.[0-9]{4,}/[-._;()/:A-Za-z0-9]+', re.IGNORECASE)
    
    results = []
    
    print(f"Analyzing {len(rows)} files...")
    
    for row in rows:
        pdf_path = row['pdf_path']
        if not pdf_path or not os.path.exists(pdf_path):
            continue
            
        text = extract_text_from_pdf(pdf_path)
        
        found_arxiv = arxiv_pattern.search(text)
        found_doi = doi_pattern.search(text)
        
        meta = {
            'id': row['id'],
            'title': row['title'],
            'arxiv': found_arxiv.group(1) if found_arxiv else None,
            'doi': found_doi.group(0) if found_doi else None,
        }
        
        if meta['arxiv'] or meta['doi']:
            results.append(meta)
            print(f"Found for [{row['id']}]: ArXiv={meta['arxiv']}, DOI={meta['doi']}")
        else:
            # Maybe try searching for some keywords to help manual research later
            pass

    print(f"\nSummary: Found metadata for {len(results)} out of {len(rows)} papers.")
    
    # Save findings to a temp file for next step
    import json
    with open("metadata_findings.json", "w") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    divine_metadata()
