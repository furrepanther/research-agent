"""
Final robust verification script.
"""
import os
import sqlite3
import pathlib

db_path = r'R:\My Drive\03 Research Papers\metadata.db'
cloud_dir = pathlib.Path(r'R:\My Drive\03 Research Papers')

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get DB count
cursor.execute("SELECT COUNT(*) FROM papers")
db_count = cursor.fetchone()[0]

# Get Disk count
all_pdfs = [p for p in cloud_dir.rglob("*.pdf")]
disk_count = len(all_pdfs)

# Find missing
cursor.execute("SELECT pdf_path FROM papers")
db_paths = set(row[0] for row in cursor.fetchall())

missing = []
for p in all_pdfs:
    if str(p) not in db_paths:
        missing.append(str(p))

print("="*60)
print("FINAL CLOUD DATABASE AUDIT")
print("="*60)
print(f"Papers in Database: {db_count}")
print(f"PDFs on Cloud Disk: {disk_count}")
print(f"Match Integrity: {'100%' if db_count == disk_count else 'INCOMPLETE'}")
print("="*60)

if missing:
    print("\nStill Missing:")
    for m in missing:
        print(f"  - {m}")

conn.close()
