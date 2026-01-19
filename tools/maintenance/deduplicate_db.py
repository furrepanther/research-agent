import sqlite3
import os
import sys

def deduplicate_db(db_path):
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print(f"Deduplicating Database: {db_path}")
    print("="*50)

    # 1. Get all papers
    cursor.execute("SELECT id, pdf_path, source_url, abstract, title FROM papers")
    rows = cursor.fetchall()
    
    print(f"Total Records Scanned: {len(rows)}")
    
    # 2. Group by PDF Path
    by_path = {}
    for row in rows:
        path = row['pdf_path']
        if not path: continue
        if path not in by_path:
            by_path[path] = []
        by_path[path].append(row)

    duplicates_found = 0
    records_deleted = 0
    
    for path, group in by_path.items():
        if len(group) > 1:
            duplicates_found += 1
            # Sort by "quality": Length of URL + Length of Abstract
            # We want to keep the one with the MOST info.
            def quality_score(r):
                score = 0
                if r['source_url'] and len(r['source_url']) > 5: score += 1000
                if r['abstract'] and len(r['abstract']) > 50: score += len(r['abstract'])
                return score

            group.sort(key=quality_score, reverse=True)
            
            # Keep first (best), delete rest
            keep = group[0]
            to_delete = group[1:]
            
            # print(f"Duplicate: {keep['title'][:30]}...")
            # print(f"  Keeping ID {keep['id']} (Score: {quality_score(keep)})")
            
            ids_to_del = [r['id'] for r in to_delete]
            records_deleted += len(ids_to_del)
            
            placeholders = ', '.join('?' * len(ids_to_del))
            cursor.execute(f"DELETE FROM papers WHERE id IN ({placeholders})", ids_to_del)

    conn.commit()
    
    # 3. Final Count
    cursor.execute("SELECT COUNT(*) FROM papers")
    final_total = cursor.fetchone()[0]
    
    print("-" * 30)
    print(f"Duplicates Groups Found: {duplicates_found}")
    print(f"Records Deleted:         {records_deleted}")
    print(f"Final Count:             {final_total}")
    print("="*50)
    
    conn.close()

if __name__ == "__main__":
    CLOUD_DB = r"R:\My Drive\03 Research Papers\metadata.db"
    deduplicate_db(CLOUD_DB)
