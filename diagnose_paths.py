import sqlite3
import os
import sys

def check_db(db_path):
    print(f"\n--- Checking DB: {db_path} ---")
    if not os.path.exists(db_path):
        print("Database not found.")
        return

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check papers table
        try:
            cursor.execute("SELECT id, title, pdf_path FROM papers LIMIT 10")
        except sqlite3.OperationalError:
            try:
                cursor.execute("SELECT id, title, pdf_path FROM papers_new LIMIT 10")
            except Exception as e:
                print(f"Error querying papers table: {e}")
                return

        rows = cursor.fetchall()
        print(f"Found {len(rows)} rows sample.")
        
        for row in rows:
            path = row['pdf_path']
            exists = os.path.exists(path) if path else False
            status = "EXISTS" if exists else "MISSING"
            print(f"[{status}] ID: {row['id']} | Path: {path}")
            
            if not exists and path:
                 # Try to see if it works relative to CWD
                 abs_path = os.path.abspath(path)
                 if os.path.exists(abs_path):
                     print(f"  -> Found at absolute: {abs_path}")
                 else:
                     # Check if it's in a probable subfolder
                     basename = os.path.basename(path)
                     possible_locs = [
                         os.path.join("data", "papers", basename),
                         os.path.join("papers", basename),
                         os.path.join("F:/RESTMP", basename) # Check staging
                     ]
                     for loc in possible_locs:
                         if os.path.exists(loc):
                             print(f"  -> FOUND at alternate: {loc}")

        conn.close()
    except Exception as e:
        print(f"Error reading DB: {e}")

if __name__ == "__main__":
    print(f"CWD: {os.getcwd()}")
    
    # Check local DB
    check_db("data/metadata.db")
    
    # Check cloud DB if possible (guessing path)
    # You might want to pull this from config.yaml if needed, but let's start here.
