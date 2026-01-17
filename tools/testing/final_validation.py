"""
Final database validation - show exactly which files are missing.
"""
import os
import sqlite3

cloud_dir = r'R:\My Drive\03 Research Papers'
db_path = os.path.join(cloud_dir, 'metadata.db')

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get all PDF paths in database
cursor.execute("SELECT pdf_path FROM papers")
db_files = set(row[0] for row in cursor.fetchall())

# Find all PDFs in cloud storage
all_pdfs = []
for root, dirs, files in os.walk(cloud_dir):
    for filename in files:
        if filename.endswith('.pdf'):
            filepath = os.path.join(root, filename)
            all_pdfs.append(filepath)

# Find missing files
missing = [f for f in all_pdfs if f not in db_files]

print("="*80)
print("FINAL DATABASE STATUS")
print("="*80)
print(f"\nTotal PDFs in cloud storage: {len(all_pdfs)}")
print(f"Papers in database: {len(db_files)}")
print(f"Missing from database: {len(missing)}")

if missing:
    print(f"\n{'='*80}")
    print("MISSING FILES")
    print("="*80)
    for filepath in sorted(missing):
        rel_path = os.path.relpath(filepath, cloud_dir)
        print(f"  {rel_path}")

conn.close()
