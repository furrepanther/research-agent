"""
Verify database population and create error report.
"""
import os
import sqlite3
from pathlib import Path

def verify_database():
    """Verify database contents against cloud storage"""
    cloud_dir = r'R:\My Drive\03 Research Papers'
    db_path = os.path.join(cloud_dir, 'metadata.db')
    
    print("="*80)
    print("DATABASE VERIFICATION REPORT")
    print("="*80)
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get database stats
    cursor.execute("SELECT COUNT(*) FROM papers")
    db_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT source, COUNT(*) FROM papers GROUP BY source")
    source_counts = cursor.fetchall()
    
    print(f"\nDatabase Statistics:")
    print(f"  Total papers in database: {db_count}")
    print(f"\n  Papers by source:")
    for source, count in source_counts:
        print(f"    {source}: {count}")
    
    # Count PDFs in cloud storage
    pdf_count = 0
    pdf_by_folder = {}
    
    for root, dirs, files in os.walk(cloud_dir):
        folder = os.path.relpath(root, cloud_dir)
        if folder == '.':
            continue
            
        pdf_files = [f for f in files if f.endswith('.pdf')]
        if pdf_files:
            pdf_by_folder[folder] = len(pdf_files)
            pdf_count += len(pdf_files)
    
    print(f"\n  Total PDFs in cloud storage: {pdf_count}")
    print(f"\n  PDFs by folder:")
    for folder, count in sorted(pdf_by_folder.items()):
        print(f"    {folder}: {count}")
    
    # Check for missing entries
    print(f"\n{'='*80}")
    print("VERIFICATION")
    print("="*80)
    
    missing_count = pdf_count - db_count
    if missing_count == 0:
        print(f"✓ All {pdf_count} PDFs are in the database")
    else:
        print(f"⚠ {missing_count} PDFs are missing from database")
        print(f"  (This is expected for files with EOF errors)")
    
    # Get list of files in database
    cursor.execute("SELECT pdf_path FROM papers")
    db_files = set(row[0] for row in cursor.fetchall())
    
    # Find PDFs not in database
    missing_files = []
    for root, dirs, files in os.walk(cloud_dir):
        for filename in files:
            if not filename.endswith('.pdf'):
                continue
            filepath = os.path.join(root, filename)
            if filepath not in db_files:
                missing_files.append(filepath)
    
    if missing_files:
        print(f"\n{'='*80}")
        print("FILES NOT IN DATABASE (Likely EOF/Read Errors)")
        print("="*80)
        for filepath in sorted(missing_files):
            rel_path = os.path.relpath(filepath, cloud_dir)
            print(f"  {rel_path}")
    
    conn.close()
    
    print(f"\n{'='*80}")
    print("SUMMARY")
    print("="*80)
    print(f"Database: {db_path}")
    print(f"Papers in DB: {db_count}")
    print(f"PDFs in cloud: {pdf_count}")
    print(f"Missing from DB: {len(missing_files)}")
    print("="*80)

if __name__ == "__main__":
    verify_database()
