"""
Validate and add Red Teaming PDFs to database.
"""
import os
import sqlite3
from datetime import datetime
from pathlib import Path
import PyPDF2

db_path = r'R:\My Drive\03 Research Papers\metadata.db'
red_teaming_dir = r'R:\My Drive\03 Research Papers\Red Teaming'

# Get existing files in database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT pdf_path FROM papers")
existing_files = set(row[0] for row in cursor.fetchall())

print("="*80)
print("RED TEAMING PDF VALIDATION")
print("="*80)

added = 0
readable = 0
errors = 0

for filename in os.listdir(red_teaming_dir):
    if not filename.endswith('.pdf'):
        continue
    
    filepath = os.path.join(red_teaming_dir, filename)
    
    # Skip if already in database
    if filepath in existing_files:
        print(f"⊙ Already in DB: {filename[:60]}")
        continue
    
    print(f"\nTesting: {filename[:70]}")
    
    try:
        # Try to read the PDF
        with open(filepath, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            pages = len(reader.pages)
            
        print(f"  ✓ Readable ({pages} pages)")
        readable += 1
        
        # Add to database
        title = Path(filepath).stem
        file_date = datetime.fromtimestamp(os.path.getmtime(filepath)).strftime("%Y-%m-%d")
        paper_id = title.replace(' ', '_').replace('-', '_').lower()[:50]
        
        cursor.execute("""
            INSERT OR IGNORE INTO papers (
                id, title, published_date, authors, abstract,
                pdf_path, source_url, downloaded_date, synced_to_cloud, source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            paper_id,
            title,
            file_date,
            'Unknown',
            '',
            filepath,
            '',
            file_date,
            1,
            'arxiv'  # Red teaming papers
        ))
        
        added += 1
        print(f"  ✓ Added to database")
        
    except Exception as e:
        errors += 1
        print(f"  ✗ Error: {str(e)[:60]}")

conn.commit()
cursor.execute("SELECT COUNT(*) FROM papers")
total = cursor.fetchone()[0]
conn.close()

print(f"\n{'='*80}")
print("SUMMARY")
print("="*80)
print(f"Readable PDFs: {readable}")
print(f"Added to DB: {added}")
print(f"Errors: {errors}")
print(f"Total papers in database: {total}")
print("="*80)
