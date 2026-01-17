"""
Add the three corrected Byrnes papers to the database.
"""
import os
import sqlite3
from datetime import datetime
from pathlib import Path
import PyPDF2

def add_byrnes_papers():
    """Add the three corrected Byrnes papers"""
    db_path = r'R:\My Drive\03 Research Papers\metadata.db'
    cloud_dir = r'R:\My Drive\03 Research Papers'
    
    byrnes_files = [
        r'R:\My Drive\03 Research Papers\Byrnes\6 reasons why "alignment-is-hard" discourse seems alien to human intuitions, and vice-versa.pdf',
        r'R:\My Drive\03 Research Papers\Byrnes\Foom & Doom 2 - Technical alignment is hard.pdf',
        r'R:\My Drive\03 Research Papers\Byrnes\"The Era of Experience" has an unsolved technical alignment problem.pdf'
    ]
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
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
            
            # Generate ID
            paper_id = title.replace(' ', '_').replace('"', '').replace('&', 'and').lower()[:50]
            
            # Insert into database
            cursor.execute("""
                INSERT OR IGNORE INTO papers (
                    id, title, published_date, authors, abstract,
                    pdf_path, source_url, downloaded_date, synced_to_cloud, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                paper_id,
                title,
                file_date,
                'Steven Byrnes',
                '',
                filepath,
                '',
                file_date,
                1,
                'lesswrong'  # Byrnes papers are from LessWrong
            ))
            
            added += 1
            print(f"✓ Added: {title[:60]}... ({pages} pages)")
            
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
