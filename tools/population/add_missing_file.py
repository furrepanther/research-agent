"""
Manually add specific files that were missed during initial population.
"""
import os
import sqlite3
from datetime import datetime
from pathlib import Path
import PyPDF2

def add_file_to_db(filepath, db_path):
    """Add a single file to the database"""
    try:
        # Extract metadata
        with open(filepath, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            
            # Get title from filename
            title = Path(filepath).stem
            
            # Get file timestamp
            file_date = datetime.fromtimestamp(os.path.getmtime(filepath)).strftime("%Y-%m-%d")
            
            # Determine category and source
            cloud_dir = r'R:\My Drive\03 Research Papers'
            rel_path = os.path.relpath(os.path.dirname(filepath), cloud_dir)
            category = rel_path if rel_path != '.' else 'Uncategorized'
            
            # Determine source from category
            if 'consciousness' in category.lower():
                source = 'arxiv'
            else:
                source = 'arxiv'
            
            # Generate ID
            paper_id = Path(filepath).stem.replace(' ', '_').lower()[:50]
            
            # Insert into database
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
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
                source
            ))
            
            conn.commit()
            conn.close()
            
            print(f"✓ Added: {title}")
            return True
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

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
