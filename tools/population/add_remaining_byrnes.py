"""
Add the remaining two corrected Byrnes papers.
"""
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from src.storage import StorageManager

db_path = r'R:\My Drive\03 Research Papers\metadata.db'

byrnes_files = [
    r'R:\My Drive\03 Research Papers\Byrnes\6 reasons why "alignment-is-hard" discourse seems alien to human intuitions, and vice-versa.pdf',
    r'R:\My Drive\03 Research Papers\Byrnes\"The Era of Experience" has an unsolved technical alignment problem.pdf'
]

storage = StorageManager(db_path)

added = 0
for filepath in byrnes_files:
    try:
        if os.path.exists(filepath):
            title = Path(filepath).stem
            file_date = datetime.fromtimestamp(os.path.getmtime(filepath)).strftime("%Y-%m-%d")
            
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
            
            new_id = storage.add_paper(paper_data)
            if new_id:
                storage.mark_synced([new_id])
                added += 1
                print(f"✓ Added: {title[:60]}... -> ID: {new_id}")
    except Exception as e:
        print(f"✗ Error: {e}")

print(f"\nFinal sync successful. Added {added} papers.")
