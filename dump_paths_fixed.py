import sqlite3
import os

db_path = 'R:/My Drive/03 Research Papers/metadata.db'
if not os.path.exists(db_path):
    db_path = 'data/metadata.db'

output_file = 'f:/Github/research-agent/path_dump.txt'

with open(output_file, 'w', encoding='utf-8') as f:
    f.write(f"Checking DB: {db_path}\n")
    if not os.path.exists(db_path):
        f.write("DB NOT FOUND\n")
    else:
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT id, title, pdf_path FROM papers LIMIT 20")
            rows = cursor.fetchall()
            for row in rows:
                p = row['pdf_path']
                exists = os.path.exists(p) if p else False
                f.write(f"ID {row['id']} | EX: {exists} | PATH: {p}\n")
            conn.close()
        except Exception as e:
            f.write(f"ERROR: {e}\n")
