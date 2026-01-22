import sqlite3
import os

# db_path = r'R:\My Drive\03 Research Papers\metadata.db'
db_path = r'F:\TMPRES\metadata.db' # Targeting the STALE local copy to be safe

if not os.path.exists(db_path):
    print("DB not found")
    exit()

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
c = conn.cursor()

# 1. Find the culprit
print("Checking for future dates...")
c.execute("SELECT id, title, published_date FROM papers WHERE published_date > '2026-01-01'")
rows = c.fetchall()

if not rows:
    print("No future dates found! (Maybe logic error in get_latest_date?)")
else:
    print(f"Found {len(rows)} records with future dates:")
    for r in rows:
        print(f"[{r['id']}] {r['published_date']} - {r['title']}")
        
        # FIX: Reset to NULL or 2024
        # Since we don't know the real date easily without rescraping, 
        # let's set it to NULL so it doesn't block the "Latest Date" logic.
        print(f"  -> Fixing ID {r['id']}...")
        c.execute("UPDATE papers SET published_date = NULL WHERE id = ?", (r['id'],))

    conn.commit()
    print("Fix applied.")

# Verify new max date
c.execute("SELECT MAX(published_date) FROM papers")
new_max = c.fetchone()[0]
print(f"New Database Max Date: {new_max}")

conn.close()
