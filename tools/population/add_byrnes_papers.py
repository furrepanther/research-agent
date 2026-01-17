"""
Add the three corrected Byrnes papers to the database.
"""
import os
from datetime import datetime
from pathlib import Path
import PyPDF2
from src.storage import StorageManager

def add_byrnes_papers():
    """Add the three corrected Byrnes papers"""
    db_path = r'R:\My Drive\03 Research Papers\metadata.db'
    cloud_dir = r'R:\My Drive\03 Research Papers'
    
    byrnes_files = [
        r'R:\My Drive\03 Research Papers\Byrnes\6 reasons why "alignment-is-hard" discourse seems alien to human intuitions, and vice-versa.pdf',
        r'R:\My Drive\03 Research Papers\Byrnes\Foom & Doom 2 - Technical alignment is hard.pdf',
        r'R:\My Drive\03 Research Papers\Byrnes\"The Era of Experience" has an unsolved technical alignment problem.pdf'
    ]
    
    storage = StorageManager(db_path)
    
    added = 0
    errors = 0
    
    for filepath in byrnes_files:
        if not os.path.exists(filepath):
            print(f"✗ File not found: {os.path.basename(filepath)}")
            errors += 1
            continue
        
        try:
            # Try to read the PDF
            with open(filepath, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                pages = len(reader.pages)
            
            # Get title from filename
            title = Path(filepath).stem
            
            # Get file timestamp
            file_date = datetime.fromtimestamp(os.path.getmtime(filepath)).strftime("%Y-%m-%d")
            
            # Prepare data
            paper_data = {
                'title': title,
                'published_date': file_date,
                'authors': 'Steven Byrnes',
                'abstract': '',
                'pdf_path': filepath,
                'source_url': '',
                'downloaded_date': file_date,
                'source': 'lesswrong'
            }
            
            # Insert into database using StorageManager
            new_id = storage.add_paper(paper_data)
            if new_id:
                added += 1
                # Mark as synced since it's already in cloud storage
                storage.mark_synced([new_id])
                print(f"✓ Added: {title[:60]}... ({pages} pages) -> ID: {new_id}")
            else:
                print(f"- Skipped (Duplicate): {title[:60]}...")
            
        except Exception as e:
            errors += 1
            print(f"✗ Error with {os.path.basename(filepath)}: {e}")
    
    conn.commit()
    
    # Get final count
    cursor.execute("SELECT COUNT(*) FROM papers")
    total = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"\n{'='*80}")
    print(f"Byrnes Papers Added: {added}")
    print(f"Errors: {errors}")
    print(f"Total papers in database: {total}")
    print("="*80)

if __name__ == "__main__":
    add_byrnes_papers()
