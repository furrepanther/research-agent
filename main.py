import os
import sys
from datetime import datetime, timedelta, timezone
from src.utils import get_config, logger
from src.storage import StorageManager
from src.searchers.manager import SearchManager
from src.export import ExportManager

from src.filter import FilterManager

import argparse

def main():
    parser = argparse.ArgumentParser(description="Research Agent CLI")
    parser.add_argument("--mode", type=str, choices=["BACKFILL", "DAILY"], help="Force search mode")
    parser.add_argument("--prompt", type=str, help="Override prompt text")
    parser.add_argument("--max-results", type=int, help="Override max results")
    args = parser.parse_args()

    logger.info("Starting Research Agent...")
    
    # 1. Setup
    try:
        config = get_config()
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return

    storage = StorageManager(config.get("db_path", "data/metadata.db"))
    search_manager = SearchManager(config)
    export_mgr = ExportManager(config)

    # 2. Get User Prompt
    prompt_text = args.prompt
    if not prompt_text:
        prompt_path = "prompt.txt"
        if not os.path.exists(prompt_path):
            logger.error(f"Prompt file not found: {prompt_path}")
            return
        with open(prompt_path, "r") as f:
            prompt_text = f.read().strip()
    
    if not prompt_text:
        logger.error("No prompt provided.")
        return
        
    filter_mgr = FilterManager(prompt_text)

    # 3. Determine Mode (Backfill vs Daily)
    latest_date_str = storage.get_latest_date()
    
    # Priority: Command line arg > Database State
    if args.mode:
        mode = args.mode.upper()
        if mode == "DAILY" and latest_date_str:
            start_date = datetime.strptime(latest_date_str, "%Y-%m-%d")
        else:
            start_date = datetime(2023, 1, 1) # Default for backfill or if no db date
    elif latest_date_str:
        logger.info(f"Database contains papers. Latest published date: {latest_date_str}")
        start_date = datetime.strptime(latest_date_str, "%Y-%m-%d")
        mode = "DAILY"
    else:
        logger.info("Database is empty. Starting Backfill Mode.")
        start_date = datetime(2023, 1, 1)
        mode = "BACKFILL"
    
    # Max Results logic
    if args.max_results:
        max_results = args.max_results
    else:
        max_results = config.get("max_results_backfill", 200) if mode == "BACKFILL" else config.get("max_results_daily", 10)
    
    logger.info(f"Mode: {mode} | Query: '{prompt_text[:50]}...' | Start Date: {start_date.strftime('%Y-%m-%d')} | Max Results: {max_results}")

    # 4. Search & Download
    # For API Search, we pass the full prompt. The API might do a loose match.
    results = search_manager.search_all(prompt_text, start_date=start_date, max_results=max_results)
    
    import random
    random.shuffle(results)
    
    new_count = 0
    filtered_count = 0
    
    for paper in results:
        # Client-Side Filter
        if not filter_mgr.is_relevant(paper):
            filtered_count += 1
            continue

        # Check if exists (Quick ID check to avoid download if possible)
        # Note: We still probably want to call add_paper to handle merging sources even if it exists.
        # But to save download bandwidth, we can check basic existence.
        # If ID exists, we just call add_paper to merge sources.
        # If ID doesn't exist, we check Title/Content in add_paper. 
        # But we need PDF to add new paper.
        # Strategy: 
        # 1. If ID exists -> Call add_paper (merges), Skip Download.
        # 2. If ID NOT exists -> Download -> Call add_paper (checks duplicate content -> merges OR adds).
        
        if storage.paper_exists(paper['id']):
             # Just try to merge source
             storage.add_paper(paper)
             continue
        
        # Download
        pdf_path = search_manager.download_paper(paper)
        if pdf_path:
            paper['pdf_path'] = pdf_path
            paper['downloaded_date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Store (handles content deduplication)
            if storage.add_paper(paper):
                new_count += 1
        else:
            logger.warning(f"Skipping storage for {paper['id']} due to download failure.")

    logger.info(f"Search Results: {len(results)} | Filtered Out: {filtered_count} | Added New: {new_count}")

    if mode == "BACKFILL" and new_count == 0:
        logger.error("Zero documents returned during backfill run. This is treated as a failure.")
        sys.exit(1)

    # 5. Export to Excel
    logger.info("Starting Excel Export...")
    unsynced = storage.get_unsynced_papers()
    if unsynced:
        exported_ids = export_mgr.export_papers(unsynced)
        storage.mark_synced(exported_ids)
        logger.info(f"Exported and marked {len(exported_ids)} papers.")
    else:
        logger.info("No unsynced papers found.")

    logger.info("Research Agent Finished.")

if __name__ == "__main__":
    main()
