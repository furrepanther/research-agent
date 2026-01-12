"""
Worker module for running searchers in isolated processes.

This module provides the `run_worker` function that wraps a Searcher class
and runs it in a separate process, communicating status updates via a Queue.
"""

import multiprocessing
import traceback
import os
from datetime import datetime
from src.utils import get_config, logger
from src.filter import FilterManager
from src.storage import StorageManager

def run_worker(searcher_class, source_name, task_queue, stop_event, prompt, max_results=200, mode="DAILY"):
    """
    Worker function to run a single searcher with enhanced monitoring.
    """
    start_time = datetime.now()
    run_id = start_time.strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        # Initialize
        config = get_config()
        searcher = searcher_class(config)
        filter_mgr = FilterManager(prompt)
        storage = StorageManager(config.get("db_path", "data/metadata.db"))
        
        task_queue.put({
            "type": "UPDATE_ROW",
            "source": source_name,
            "status": "Running...",
            "run_id": run_id,
            "mode": mode
        })
        
        # Search phase
        results = searcher.search(prompt, max_results=max_results, start_date=None, stop_event=stop_event)
        
        # ... (rest of search/filter logic same but with error handling) ...
        # Simplified for brevity in this step, but focusing on the error catch
        
        if stop_event.is_set():
            return

        # Filtering
        kept = []
        for p in results:
            if stop_event.is_set(): break
            if filter_mgr.is_relevant(p):
                kept.append(p)
        
        # Download & Store
        downloaded_count = 0
        for i, paper in enumerate(kept):
            if stop_event.is_set(): break
            
            task_queue.put({
                "type": "UPDATE_ROW",
                "source": source_name,
                "status": "Downloading",
                "details": f"({i+1}/{len(kept)}) {paper['title'][:30]}..."
            })
            
            path = searcher.download(paper)
            if path:
                # Set metadata and store
                paper['pdf_path'] = path
                paper['downloaded_date'] = run_id
                storage.add_paper(paper)
                downloaded_count += 1
        
        if mode == "BACKFILL" and downloaded_count == 0:
            raise RuntimeError("Zero documents returned during backfill run.")

        # Complete
        status_text = "Complete" if downloaded_count > 0 else "No Results"
        task_queue.put({
            "type": "UPDATE_ROW",
            "source": source_name,
            "status": status_text,
            "count": str(downloaded_count),
            "details": "Finished successfully"
        })
        
    except Exception as e:
        error_stack = traceback.format_exc()
        task_queue.put({
            "type": "ERROR",
            "source": source_name,
            "run_id": run_id,
            "error": str(e),
            "stack": error_stack
        })
        logger.error(f"Worker {source_name} failed: {e}")
