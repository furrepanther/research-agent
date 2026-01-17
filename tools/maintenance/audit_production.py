
import sqlite3
import os
import sys

# Add project root to path
sys.path.append("f:/Github/research-agent")

from src.utils import get_config, logger
import logging

def audit_production():
    config = get_config()
    db_path = "R:/My Drive/03 Research Papers/metadata.db"
    
    if not os.path.exists(db_path):
        print(f"Production DB not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print(f"--- Production Database Audit: {db_path} ---")
    
    # 1. Count records
    cursor.execute("SELECT COUNT(*) FROM papers")
    total = cursor.fetchone()[0]
    print(f"Total Records: {total}")
    
    # 2. Check for missing titles
    cursor.execute("SELECT id FROM papers WHERE title IS NULL OR title = ''")
    missing_titles = cursor.fetchall()
    print(f"Records with missing titles: {len(missing_titles)}")
    
    # 3. Check for broken file links
    cursor.execute("SELECT id, pdf_path, title FROM papers")
    rows = cursor.fetchall()
    broken_links = 0
    for row in rows:
        path = row['pdf_path']
        if not path:
            broken_links += 1
            continue
        
        # Check if actual file exists
        if not os.path.exists(path):
            # Try to see if it's just a relative path issue or drive mapping
            broken_links += 1
            if broken_links <= 5:
                print(f"  Broken link [ID {row['id']}]: {path} (Title: {row['title'][:30]})")
    
    print(f"Total broken/missing file links: {broken_links}")
    
    # 4. Check for potentially duplicate titles that aren't merged (Fuzzy check)
    cursor.execute("SELECT title, COUNT(*) as c FROM papers GROUP BY lower(title) HAVING c > 1")
    dup_titles = cursor.fetchall()
    print(f"Potential title duplicates (not merged by URL): {len(dup_titles)}")
    for d in dup_titles[:5]:
        print(f"  - '{d['title']}' appeared {d['c']} times")

    # 5. Check for papers with no source_url
    cursor.execute("SELECT COUNT(*) FROM papers WHERE source_url IS NULL OR source_url = ''")
    no_url = cursor.fetchone()[0]
    print(f"Papers with no source_url: {no_url}")

    conn.close()

if __name__ == "__main__":
    audit_production()
