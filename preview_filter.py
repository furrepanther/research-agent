import sqlite3
import pandas as pd
from src.filter import FilterManager
from src.utils import get_config, logger
import os

def preview_filter():
    print("Loading config and prompt...")
    config = get_config()
    db_path = config.get("db_path", "data/metadata.db")
    
    with open("prompt.txt", "r") as f:
        prompt_text = f.read().strip()
        
    print(f"Initializing Filter with prompt: {prompt_text[:100]}...")
    filter_mgr = FilterManager(prompt_text)
    
    print(f"Connecting to DB: {db_path}")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM papers")
    rows = cursor.fetchall()
    papers = [dict(row) for row in rows]
    conn.close()
    
    print(f"Total papers in DB: {len(papers)}")
    
    kept_papers = []
    rejected_count = 0
    
    for p in papers:
        if filter_mgr.is_relevant(p):
            kept_papers.append(p)
        else:
            rejected_count += 1
            
    print("-" * 30)
    print(f"FILTER RESULTS:")
    print(f"Original Count: {len(papers)}")
    print(f"Kept:           {len(kept_papers)}")
    print(f"Rejected:       {rejected_count}")
    print("-" * 30)
    
    if kept_papers:
        # Export to Excel
        output_file = "research_log_filtered_preview.xlsx"
        export_path = os.path.join(config.get("export_dir", "."), output_file)
        
        df = pd.DataFrame(kept_papers)
        # Reorder columns slightly for readability if possible
        cols = ['id', 'title', 'published_date', 'source', 'authors', 'pdf_path', 'source_url', 'abstract']
        # Filter to only cols that exist
        cols = [c for c in cols if c in df.columns]
        df = df[cols]
        
        df.to_excel(export_path, index=False)
        print(f"\nPreview exported to: {export_path}")
    else:
        print("\nNo papers matched the strict filter.")

if __name__ == "__main__":
    preview_filter()
