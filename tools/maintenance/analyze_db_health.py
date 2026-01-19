import sqlite3
import os
import sys

# Add project root
sys.path.append(os.getcwd())

def analyze_db(db_path):
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print(f"Analyzing Database: {db_path}")
    print("="*50)

    # 1. Basic Counts
    cursor.execute("SELECT COUNT(*) FROM papers")
    total = cursor.fetchone()[0]
    print(f"Total Records: {total}")

    # 2. Missing URLs
    cursor.execute("SELECT COUNT(*), title FROM papers WHERE source_url IS NULL OR length(source_url) < 5")
    missing_url_count = cursor.fetchone()[0]
    print(f"Missing URLs:  {missing_url_count} ({missing_url_count/total*100:.1f}%)")

    # 3. Missing Abstracts
    cursor.execute("SELECT COUNT(*) FROM papers WHERE abstract IS NULL OR length(abstract) < 50")
    missing_abs_count = cursor.fetchone()[0]
    print(f"Missing Abs:   {missing_abs_count} ({missing_abs_count/total*100:.1f}%)")
    
    # 4. Both Missing
    cursor.execute("SELECT COUNT(*) FROM papers WHERE (source_url IS NULL OR length(source_url) < 5) AND (abstract IS NULL OR length(abstract) < 50)")
    both_missing = cursor.fetchone()[0]
    print(f"Stub Records (Both Missing): {both_missing}")

    print("-" * 30)
    print("SAMPLE FAILURES (Missing URL):")
    cursor.execute("SELECT title, pdf_path FROM papers WHERE source_url IS NULL OR length(source_url) < 5 LIMIT 10")
    for row in cursor.fetchall():
        print(f" - {row['title'][:60]}...")

    print("-" * 30)
    print("SAMPLE FAILURES (Short/Bad Abstract):")
    cursor.execute("SELECT title, abstract FROM papers WHERE abstract IS NULL OR length(abstract) < 50 LIMIT 5")
    for row in cursor.fetchall():
        abs_preview = row['abstract'] if row['abstract'] else "[NULL]"
        print(f" - {row['title'][:40]}... -> Abstract: {abs_preview}")

    conn.close()

if __name__ == "__main__":
    # Hardcoded cloud path based on context
    CLOUD_DB = r"R:\My Drive\03 Research Papers\metadata.db"
    analyze_db(CLOUD_DB)
