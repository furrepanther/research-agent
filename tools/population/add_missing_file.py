```
"""
Manually add specific files that were missed during initial population.
"""
from datetime import datetime
from src.storage import StorageManager
from pathlib import Path
import PyPDF2 # This import is no longer used in the modified function, but kept as per instruction.

def add_file_to_db(filepath, db_path):
    """Add a single file to the database"""
    storage = StorageManager(db_path)
    
    if Path(filepath).exists(): # Changed os.path.exists to Path(filepath).exists() for consistency
        print(f"Adding: {Path(filepath).name}") # Changed os.path.basename to Path(filepath).name
        mtime = datetime.fromtimestamp(Path(filepath).stat().st_mtime).strftime('%Y-%m-%d') # Changed os.path.getmtime to Path(filepath).stat().st_mtime
        
        paper_data = {
            'title': Path(filepath).stem,
            'published_date': mtime,
            'authors': 'Unknown',
            'abstract': '',
            'pdf_path': filepath,
            'source_url': '',
            'downloaded_date': mtime,
            'source': 'arxiv'
        }
        
        new_id = storage.add_paper(paper_data)
        if new_id:
            storage.mark_synced([new_id])
            print(f"✓ Added: {paper_data['title']} -> ID: {new_id}")
            return True # Added return True here as the original function returned True on success
        else:
            print("- Paper already exists or failed to add.")
            return False # Added return False here for consistency
    else:
        print(f"MISSING ON DISK: {filepath}")
        return False # Added return False here for consistency

# Add KannsasJackson.pdf
db_path = r'R:\My Drive\03 Research Papers\metadata.db'
filepath = r'R:\My Drive\03 Research Papers\Consciousness\KannsasJackson.pdf'

print("Adding missing file to database...")
success = add_file_to_db(filepath, db_path)

if success:
    # Verify
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM papers")
    count = cursor.fetchone()[0]
    conn.close()
    print(f"\nTotal papers in database: {count}")
