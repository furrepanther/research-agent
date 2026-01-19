import sqlite3
conn = sqlite3.connect(r'R:\My Drive\03 Research Papers\metadata.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()
c.execute("SELECT title, pdf_path, abstract, source_url FROM papers WHERE title LIKE '%Cameron Berg%'")
r = c.fetchone()
if r:
    print(f"Title: '{r['title']}'")
    print(f"Path:  '{r['pdf_path']}'")
    print(f"URL:   '{r['source_url']}'")
    print(f"Abs:   '{r['abstract']}'")
else:
    print("Not Found")
