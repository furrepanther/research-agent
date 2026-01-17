"""
Validate and add Red Teaming PDFs to database.
"""
import os
from datetime import datetime
from pathlib import Path
import PyPDF2
from src.storage import StorageManager

db_path = r'R:\My Drive\03 Research Papers\metadata.db'
red_teaming_dir = r'R:\My Drive\03 Research Papers\Red Teaming'

storage = StorageManager(db_path)

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
    
    print(f"\nTesting: {filename[:70]}")
    
    try:
        # Try to read the PDF
        with open(filepath, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            pages = len(reader.pages)
            
        print(f"  ✓ Readable ({pages} pages)")
        readable += 1
        
        # Add to database using StorageManager
        title = Path(filepath).stem
        file_date = datetime.fromtimestamp(os.path.getmtime(filepath)).strftime("%Y-%m-%d")
        
        paper_data = {
            'title': title,
            'published_date': file_date,
            'authors': 'Unknown',
            'abstract': '',
            'pdf_path': filepath,
            'source_url': '',
            'downloaded_date': file_date,
            'source': 'arxiv'
        }
        
        new_id = storage.add_paper(paper_data)
        if new_id:
            storage.mark_synced([new_id])
            added += 1
            print(f"  ✓ Added to database -> ID: {new_id}")
        else:
            print("  ⊙ Already in DB or failed to add.")
        
    except Exception as e:
        errors += 1
        print(f"  ✗ Error: {str(e)[:60]}")

print(f"\n{'='*80}")
print("SUMMARY")
print("="*80)
print(f"Readable PDFs: {readable}")
print(f"Added to DB: {added}")
print(f"Errors: {errors}")
print(f"Total papers in database: {total}")
print("="*80)
