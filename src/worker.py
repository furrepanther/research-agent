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

def run_worker(searcher_class, source_name, task_queue, stop_event, prompt, search_params, mode="DAILY", run_id=None):
    """
    Worker function to run a single searcher with enhanced monitoring.

    search_params: dict with keys:
        - max_papers_per_agent: int or float('inf') for unlimited
        - per_query_limit: int for batch size per API call
        - respect_date_range: bool
        - start_date: datetime object
    run_id: Optional run identifier from supervisor (for summary window)
    """
    # Use provided run_id or generate new one
    if run_id is None:
        start_time = datetime.now()
        run_id = start_time.strftime("%Y-%m-%d %H:%M:%S")
    else:
        start_time = datetime.now()

    try:
        # Initialize
        # Select prompt based on source
        # strict prompt for ArXiv, relaxed for blogs/labs
        if source_name == "ArXiv":
            prompt_file = "prompts/prompt.txt"
        else:
            prompt_file = "prompts/prompt_relaxed.txt"
            
        # Fallback if specific file doesn't exist
        if not os.path.exists(prompt_file):
            prompt_file = "prompts/prompt.txt" # Default back to main prompt
            
        if os.path.exists(prompt_file):
            with open(prompt_file, "r") as f:
                current_prompt = f.read().strip()
        else:
            current_prompt = prompt # Use the passed-in prompt as fallback
            
        config = get_config()
        searcher = searcher_class(config)
        filter_mgr = FilterManager(current_prompt)
        storage = StorageManager(config.get("db_path", "data/metadata.db"))

        # Extract search parameters
        max_papers_per_agent = search_params.get('max_papers_per_agent', float('inf'))
        per_query_limit = search_params.get('per_query_limit', 10)
        respect_date_range = search_params.get('respect_date_range', True)
        start_date = search_params.get('start_date', None)

        task_queue.put({
            "type": "UPDATE_ROW",
            "source": source_name,
            "status": "Running...",
            "run_id": run_id,
            "mode": mode
        })

        # SEARCH STRATEGY:
        # For BACKFILL: Fetch a LARGE batch to get many results in one call
        # For DAILY/TESTING: Use smaller configured batch size
        if mode == "BACKFILL":
            # Fetch 1000 results for backfill (ArXiv multiplies by 5 = up to 5000 papers!)
            # This should be enough to get substantial results on first run
            batch_size = 1000
            task_queue.put({
                "type": "LOG",
                "text": f"[{source_name}] BACKFILL mode: Fetching large batch ({batch_size} requested, searcher may fetch more)"
            })
        else:
            batch_size = per_query_limit

        task_queue.put({
            "type": "UPDATE_ROW",
            "source": source_name,
            "status": "Searching...",
            "details": f"Fetching papers..."
        })

        # Search phase
        task_queue.put({
            "type": "PROGRESS_UPDATE",
            "source": source_name,
            "status": "Searching",
            "found": 0,
            "downloaded": 0,
            "progress": 0,
            "details": "Searching for papers..."
        })

        results = searcher.search(
            prompt,
            max_results=batch_size,
            start_date=start_date if respect_date_range else None,
            stop_event=stop_event
        )

        if stop_event and stop_event.is_set():
            task_queue.put({
                "type": "LOG",
                "text": f"[{source_name}] Search cancelled by user"
            })
            return

        task_queue.put({
            "type": "LOG",
            "text": f"[{source_name}] Fetched {len(results)} papers from source"
        })

        task_queue.put({
            "type": "PROGRESS_UPDATE",
            "source": source_name,
            "status": "Searching",
            "found": len(results),
            "downloaded": 0,
            "progress": 0,
            "details": f"Found {len(results)} papers"
        })

        # Filtering phase
        task_queue.put({
            "type": "PROGRESS_UPDATE",
            "source": source_name,
            "status": "Filtering",
            "found": len(results),
            "downloaded": 0,
            "progress": 0,
            "details": f"Filtering {len(results)} papers..."
        })

        kept = []
        for p in results:
            if stop_event and stop_event.is_set():
                break
            if filter_mgr.is_relevant(p):
                kept.append(p)

        task_queue.put({
            "type": "LOG",
            "text": f"[{source_name}] {len(kept)} papers passed filter ({len(results) - len(kept)} filtered out)"
        })

        task_queue.put({
            "type": "PROGRESS_UPDATE",
            "source": source_name,
            "status": "Filtering",
            "found": len(kept),
            "downloaded": 0,
            "progress": 0,
            "details": f"{len(kept)} papers passed filter"
        })
        
        # TEST MODE: Skip downloads and database updates, just report counts
        if mode == "TEST":
            task_queue.put({
                "type": "LOG",
                "text": f"[{source_name}] TEST MODE: Found {len(kept)} papers (no downloads)"
            })
            task_queue.put({
                "type": "UPDATE_ROW",
                "source": source_name,
                "status": "Complete",
                "found": len(kept),
                "downloaded": 0,
                "details": f"✓ Test: {len(kept)} papers found"
            })
            return  # Exit early for TEST mode

        # Download & Store (respect max_papers_per_agent limit)
        downloaded_count = 0  # Actually downloaded (new papers)
        duplicate_count = 0   # Papers skipped because they already exist
        papers_to_download = kept[:int(max_papers_per_agent)] if max_papers_per_agent != float('inf') else kept

        for i, paper in enumerate(papers_to_download):
            if stop_event and stop_event.is_set():
                break

            # Stop if we've hit the per-agent limit
            if downloaded_count >= max_papers_per_agent:
                task_queue.put({
                    "type": "LOG",
                    "text": f"[{source_name}] Reached max_papers_per_agent limit ({int(max_papers_per_agent)})"
                })
                break

            # Check for duplicates before downloading
            paper_id = paper.get('id')
            
            # 1. Check cloud storage first (if enabled)
            from src.cloud_transfer import CloudTransferManager
            from src.utils import sanitize_filename
            
            cloud_mgr = CloudTransferManager(config)
            pdf_filename = sanitize_filename(paper.get('title', ''), extension=".pdf")
            
            if cloud_mgr.enabled and cloud_mgr.check_cloud_duplicate(paper.get('title', ''), pdf_filename):
                duplicate_count += 1
                task_queue.put({
                    "type": "LOG",
                    "text": f"[{source_name}] Skipping (in cloud storage): {paper['title'][:50]}..."
                })
                
                # Count toward progress in BACKFILL mode
                if mode == "BACKFILL":
                    processed = downloaded_count + duplicate_count
                    progress_pct = (processed / len(papers_to_download)) * 100
                    task_queue.put({
                        "type": "PROGRESS_UPDATE",
                        "source": source_name,
                        "status": "Downloading",
                        "found": len(papers_to_download),
                        "downloaded": downloaded_count,
                        "progress": progress_pct,
                        "details": f"New: {downloaded_count}, Duplicates: {duplicate_count}"
                    })
                continue
            
            # 2. Check database for duplicates
            if paper_id and storage.paper_exists(paper_id):
                duplicate_count += 1
                task_queue.put({
                    "type": "LOG",
                    "text": f"[{source_name}] Skipping (in database): {paper['title'][:50]}..."
                })
                
                if mode == "BACKFILL":
                    processed = downloaded_count + duplicate_count
                    progress_pct = (processed / len(papers_to_download)) * 100
                    task_queue.put({
                        "type": "PROGRESS_UPDATE",
                        "source": source_name,
                        "status": "Downloading",
                        "found": len(kept),
                        "downloaded": processed,
                        "progress": progress_pct,
                        "details": f"New: {downloaded_count}, Duplicates: {duplicate_count}"
                    })

                continue

            task_queue.put({
                "type": "UPDATE_ROW",
                "source": source_name,
                "status": "Downloading",
                "details": f"({i+1}/{len(papers_to_download)}) {paper['title'][:30]}..."
            })

            path = searcher.download(paper)
            if path:
                # Set metadata and store
                paper['pdf_path'] = path
                paper['downloaded_date'] = run_id
                storage.add_paper(paper)
                downloaded_count += 1

                # Send progress update with mode-appropriate details
                if mode == "BACKFILL":
                    # In BACKFILL: count both new and duplicates toward progress
                    processed = downloaded_count + duplicate_count
                    progress_pct = (processed / len(papers_to_download)) * 100
                    details_text = f"New: {downloaded_count}, Duplicates: {duplicate_count}"
                    display_count = processed
                else:
                    # In other modes: only count new papers
                    progress_pct = (downloaded_count / len(papers_to_download)) * 100
                    details_text = f"Downloading ({downloaded_count}/{len(papers_to_download)})"
                    display_count = downloaded_count

                task_queue.put({
                    "type": "PROGRESS_UPDATE",
                    "source": source_name,
                    "status": "Downloading",
                    "found": len(kept),
                    "downloaded": display_count,
                    "progress": progress_pct,
                    "details": details_text
                })

        # Check for empty results in BACKFILL mode
        if mode == "BACKFILL" and downloaded_count == 0 and duplicate_count == 0:
            error_msg = f"Zero documents returned from {source_name} during backfill run."
            task_queue.put({
                "type": "LOG",
                "text": f"[{source_name}] WARNING: {error_msg}"
            })
            task_queue.put({
                "type": "LOG",
                "text": f"[{source_name}] This could mean:"
            })
            task_queue.put({
                "type": "LOG",
                "text": f"[{source_name}]   1. No papers match the search query"
            })
            task_queue.put({
                "type": "LOG",
                "text": f"[{source_name}]   2. All papers were filtered by content filters"
            })
            task_queue.put({
                "type": "LOG",
                "text": f"[{source_name}]   3. API/network error prevented fetching"
            })
            raise RuntimeError(error_msg)

        # Complete
        status_text = "Complete" if downloaded_count > 0 else "No Results"

        # Prepare final messages based on mode
        if mode == "BACKFILL":
            processed = downloaded_count + duplicate_count
            final_details = f"✓ New: {downloaded_count}, Duplicates: {duplicate_count}"
            log_msg = f"[{source_name}] Finished successfully - {downloaded_count} new papers, {duplicate_count} duplicates"
            display_count = processed
        else:
            final_details = f"✓ Downloaded {downloaded_count} papers"
            log_msg = f"[{source_name}] Finished successfully - {downloaded_count} papers downloaded"
            display_count = downloaded_count

        # Send final progress update
        task_queue.put({
            "type": "PROGRESS_UPDATE",
            "source": source_name,
            "status": "Complete",
            "found": len(kept),
            "downloaded": display_count,
            "progress": 100,
            "details": final_details
        })

        task_queue.put({
            "type": "UPDATE_ROW",
            "source": source_name,
            "status": status_text,
            "count": str(downloaded_count),
            "details": final_details
        })

        task_queue.put({
            "type": "LOG",
            "text": log_msg
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
