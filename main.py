import os
import sys
import multiprocessing
import time
from datetime import datetime, timedelta, timezone
from src.utils import get_config, logger
from src.storage import StorageManager
from src.filter import FilterManager
from src.supervisor import Supervisor
from src.searchers.arxiv_searcher import ArxivSearcher
from src.searchers.lesswrong_searcher import LessWrongSearcher
from src.searchers.lab_scraper import LabScraper

import argparse

def main():
    parser = argparse.ArgumentParser(description="Research Agent CLI")
    parser.add_argument("--mode", type=str, choices=["BACKFILL", "DAILY", "TESTING"], help="Force search mode")
    parser.add_argument("--prompt", type=str, help="Override prompt text")
    parser.add_argument("--max-results", type=int, help="Override max results per agent (deprecated, use mode_settings)")
    args = parser.parse_args()

    logger.info("Starting Research Agent...")
    
    # 1. Setup
    try:
        config = get_config()
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return

    storage = StorageManager(config.get("db_path", "data/metadata.db"))
    export_mgr = ExportManager(config)

    # 2. Get User Prompt
    prompt_text = args.prompt
    if not prompt_text:
        prompt_path = "prompts/prompt.txt" if os.path.exists("prompts/prompt.txt") else "prompt.txt"
        if not os.path.exists(prompt_path):
            logger.error(f"Prompt file not found: prompts/prompt.txt or prompt.txt")
            return
        with open(prompt_path, "r") as f:
            prompt_text = f.read().strip()
    
    if not prompt_text:
        logger.error("No prompt provided.")
        return

    # Validate and parse prompt
    try:
        filter_mgr = FilterManager(prompt_text)
    except ValueError as e:
        logger.error(f"Invalid prompt syntax:\n{e}")
        logger.info("\nExample valid prompt:")
        logger.info('  ("AI" OR "machine learning") AND ("safety" OR "alignment") ANDNOT ("automotive")')
        logger.info("\nPrompt format rules:")
        logger.info('  - Use quotes around search terms: "term"')
        logger.info('  - Group terms with parentheses: ("term1" OR "term2")')
        logger.info('  - Connect groups with AND')
        logger.info('  - Exclude terms with ANDNOT at the end')
        return

    # 3. Determine Mode (Backfill vs Daily vs Testing)
    latest_date_str = storage.get_latest_date()

    # Priority: Command line arg > Database State
    if args.mode:
        mode = args.mode.upper()
        if mode == "DAILY" and latest_date_str:
            start_date = datetime.strptime(latest_date_str, "%Y-%m-%d")
        elif mode == "TESTING":
            start_date = datetime(2003, 1, 1)  # Testing uses arbitrary start date
        else:
            start_date = datetime(2003, 1, 1)  # Default for backfill or if no db date
    elif latest_date_str:
        logger.info(f"Database contains papers. Latest published date: {latest_date_str}")
        start_date = datetime.strptime(latest_date_str, "%Y-%m-%d")
        mode = "DAILY"
    else:
        logger.info("Database is empty. Starting Backfill Mode.")
        start_date = datetime(2003, 1, 1)
        mode = "BACKFILL"

    # Get mode-specific settings
    mode_key = mode.lower()
    mode_settings = config.get("mode_settings", {}).get(mode_key, {})

    # Legacy support: if --max-results specified, use it; otherwise use mode_settings
    if args.max_results:
        max_papers_per_agent = args.max_results
        logger.warning("Using deprecated --max-results flag. Consider using mode_settings in config.yaml")
    else:
        max_papers_per_agent = mode_settings.get("max_papers_per_agent")
        if max_papers_per_agent is None:  # None means unlimited for backfill
            max_papers_per_agent = float('inf')

    per_query_limit = mode_settings.get("per_query_limit", 10)  # Default to 10 if not specified
    respect_date_range = mode_settings.get("respect_date_range", True)

    logger.info(f"Mode: {mode} | Query: '{prompt_text[:50]}...' | Start Date: {start_date.strftime('%Y-%m-%d')}")
    logger.info(f"Limits: {max_papers_per_agent if max_papers_per_agent != float('inf') else 'UNLIMITED'} total, {per_query_limit} per query | Date Range: {'Respected' if respect_date_range else 'Ignored'}")

    # 4. Search & Download - USE SUPERVISOR FOR PARALLEL EXECUTION
    task_queue = multiprocessing.Queue()
    stop_event = multiprocessing.Event()

    # Pass mode settings to supervisor
    search_params = {
        'max_papers_per_agent': max_papers_per_agent,
        'per_query_limit': per_query_limit,
        'respect_date_range': respect_date_range,
        'start_date': start_date
    }

    supervisor = Supervisor(task_queue, stop_event, prompt_text, search_params, mode)

    # Start all workers
    workers = [
        (ArxivSearcher, "ArXiv"),
        (LessWrongSearcher, "LessWrong"),
        (LabScraper, "AI Labs")
    ]

    logger.info("Starting parallel search workers...")
    for searcher_class, display_name in workers:
        supervisor.start_worker(searcher_class, display_name)

    # Process messages until all workers complete
    while supervisor.is_any_alive():
        try:
            msg = task_queue.get(timeout=1)
            msg_type = msg.get("type")

            if msg_type == "UPDATE_ROW":
                status = msg.get("status", "")
                details = msg.get("details", "")
                logger.info(f"[{msg['source']}] {status}: {details}")

                # Update heartbeat
                src = msg.get("source")
                if src in supervisor.workers:
                    supervisor.workers[src]['last_heartbeat'] = time.time()

            elif msg_type == "LOG":
                logger.info(msg.get("text"))

            elif msg_type == "ERROR":
                supervisor.handle_error(msg)

        except:
            # Timeout (queue empty)
            pass
        
        # Always check timeouts/concurrency periodically
        supervisor.check_timeouts()

    logger.info("All workers completed.")

    # Check for backfill mode failure
    # Note: With the new architecture, workers handle their own storage,
    # so we check if any papers were added across all sources
    if mode == "BACKFILL":
        # Count recent papers added (within last minute)
        recent_papers = storage.get_unsynced_papers()
        if len(recent_papers) == 0:
            logger.error("Zero documents returned during backfill run. This is treated as a failure.")
            sys.exit(1)


    logger.info("Research Agent Finished.")

if __name__ == "__main__":
    main()
