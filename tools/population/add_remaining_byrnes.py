"""
Add the remaining two corrected Byrnes papers.
"""
import os
import sqlite3
from datetime import datetime
from pathlib import Path
import PyPDF2

db_path = r'R:\My Drive\03 Research Papers\metadata.db'

byrnes_files = [
    (r'R:\My Drive\03 Research Papers\Byrnes\6 reasons why "alignment-is-hard" discourse seems alien to human intuitions, and vice-versa.pdf', '6_reasons_why_alignment-is-hard_discourse_seems'),
    (r'R:\My Drive\03 Research Papers\Byrnes\"The Era of Experience" has an unsolved technical alignment problem.pdf', 'the_era_of_experience_has_an_unsolved_technical')
]

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

for filepath, paper_id in byrnes_files:
    try:
        # Verify file exists and is readable
        with open(filepath, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            pages = len(reader.pages)
        
        title = Path(filepath).stem
        file_date = datetime.fromtimestamp(os.path.getmtime(filepath)).strftime("%Y-%m-%d")
        
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
            'lesswrong'
        ))
        
        print(f"✓ Added: {title[:60]}... ({pages} pages)")
        
    except Exception as e:
        print(f"✗ Error: {e}")

conn.commit()
cursor.execute("SELECT COUNT(*) FROM papers")
total = cursor.fetchone()[0]
conn.close()

print(f"\nTotal papers in database: {total}")
