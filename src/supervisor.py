import multiprocessing
import time
import os
from src.utils import logger, get_config
from src.storage import StorageManager
from src.worker import run_worker

class Supervisor:
    def __init__(self, task_queue, stop_event, prompt, search_params, mode="DAILY"):
        self.task_queue = task_queue
        self.stop_event = stop_event
        self.prompt = prompt
        self.search_params = search_params  # Dict with max_papers_per_agent, per_query_limit, respect_date_range, start_date
        self.mode = mode
        self.config = get_config()
        self.storage = StorageManager(self.config.get("db_path", "data/metadata.db"))

        self.workers = {}  # display_name -> {'process': p, 'class': c, 'retries': 0, 'run_id': None, 'last_heartbeat': timestamp}

        # Store run_id for later reference (for summary window)
        from datetime import datetime
        self.run_id = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Load retry/timeout settings from config with defaults
        retry_settings = self.config.get('retry_settings', {})
        self.max_retries = retry_settings.get('max_worker_retries', 2)
        self.worker_timeout = retry_settings.get('worker_timeout', 600)
        self.worker_retry_delay = retry_settings.get('worker_retry_delay', 5)

    def start_worker(self, searcher_class, display_name):
        if display_name in self.workers and self.workers[display_name]['process'].is_alive():
            logger.warning(f"Worker {display_name} already running.")
            return

        p = multiprocessing.Process(
            target=run_worker,
            args=(searcher_class, display_name, self.task_queue, self.stop_event, self.prompt, self.search_params, self.mode),
            kwargs={'run_id': self.run_id},  # Pass run_id to worker
            daemon=True
        )
        p.start()

        if display_name not in self.workers:
            self.workers[display_name] = {
                'class': searcher_class,
                'retries': 0,
                'run_id': None,
                'last_heartbeat': time.time()
            }

        self.workers[display_name]['process'] = p
        self.workers[display_name]['last_heartbeat'] = time.time()  # Reset heartbeat on start
        logger.info(f"Supervisor started worker: {display_name}")

    def handle_error(self, msg):
        source = msg.get("source")
        run_id = msg.get("run_id")
        error_msg = msg.get("error")
        stack = msg.get("stack")
        
        if source not in self.workers:
            return

        worker_info = self.workers[source]
        
        # 1. Report Error
        self.task_queue.put({
            "type": "UPDATE_ROW",
            "source": source,
            "status": "FAILED",
            "details": f"Error: {error_msg}"
        })
        self.task_queue.put({"type": "LOG", "text": f"CRITICAL: {source} errored! Starting recovery..."})

        # 2. Rollback
        self.task_queue.put({"type": "LOG", "text": f"[{source}] Rolling back work from run {run_id}..."})
        try:
            rollback_result = self.storage.rollback_source(source.lower().replace(" ", ""), run_id)
            db_paths = rollback_result['paths']
            paper_ids = rollback_result['paper_ids']

            # Delete files tracked in database (PROTECTED: Never delete from cloud storage)
            deleted_count = 0
            cloud_dir = self.config.get("cloud_storage", {}).get("path", "R:/MyDrive/03 Research Papers")
            
            for path in db_paths:
                if path and os.path.exists(path):
                    # CRITICAL PROTECTION: Never delete files from cloud storage
                    if cloud_dir and os.path.abspath(path).startswith(os.path.abspath(cloud_dir)):
                        logger.warning(f"[{source}] PROTECTED: Skipping cloud storage file: {os.path.basename(path)}")
                        self.task_queue.put({"type": "LOG", "text": f"[{source}] PROTECTED: Cloud storage file not deleted: {os.path.basename(path)}"})
                        continue
                    
                    os.remove(path)
                    deleted_count += 1
                    self.task_queue.put({"type": "LOG", "text": f"[{source}] Deleted DB-tracked file: {os.path.basename(path)}"})
                elif path:
                    logger.warning(f"[{source}] DB path not found: {path}")

            # Additional cleanup: Scan source directory for orphaned files
            # This catches files created but not yet in DB when error occurred
            source_dir = os.path.join(self.config.get("papers_dir", "data/papers"), rollback_result['source'])
            if os.path.exists(source_dir):
                # Parse run_id to get timestamp for file comparison
                from datetime import datetime
                try:
                    run_time = datetime.strptime(run_id, "%Y-%m-%d %H:%M:%S")
                    run_timestamp = run_time.timestamp()

                    # Scan directory for files created after run started
                    for filename in os.listdir(source_dir):
                        filepath = os.path.join(source_dir, filename)
                        if os.path.isfile(filepath):
                            # CRITICAL PROTECTION: Never delete from cloud storage
                            if cloud_dir and os.path.abspath(filepath).startswith(os.path.abspath(cloud_dir)):
                                logger.warning(f"[{source}] PROTECTED: Skipping cloud storage orphan: {filename}")
                                continue
                            
                            file_mtime = os.path.getmtime(filepath)
                            # Delete files created after run started (with 1 second buffer)
                            if file_mtime >= (run_timestamp - 1):
                                os.remove(filepath)
                                deleted_count += 1
                                self.task_queue.put({"type": "LOG", "text": f"[{source}] Deleted orphaned file: {filename}"})
                except Exception as e:
                    logger.warning(f"[{source}] Directory cleanup failed: {e}")

            self.task_queue.put({"type": "LOG", "text": f"[{source}] Rollback complete. Deleted {len(paper_ids)} DB entries, {deleted_count} files."})
        except Exception as re:
            logger.error(f"[{source}] Rollback exception: {re}")
            self.task_queue.put({"type": "LOG", "text": f"[{source}] Rollback FAILED: {re}"})

        # 3. Corrective Action (Self-Healing Placeholder)
        # In a real scenario, this might trigger a LLM patch.
        # For now, we report the attempt and increment retry.
        self.task_queue.put({"type": "LOG", "text": f"[{source}] Analyzing error for self-healing..."})
        
        # Logic to "Fix" common patterns could go here
        # Example: if "429" in error_msg: wait longer
        
        if worker_info['retries'] < self.max_retries:
            worker_info['retries'] += 1
            retry_count = worker_info['retries']
            self.task_queue.put({"type": "LOG", "text": f"[{source}] Self-healing attempt {retry_count}/{self.max_retries}..."})
            self.task_queue.put({
                "type": "UPDATE_ROW",
                "source": source,
                "status": f"Retrying ({retry_count}/{self.max_retries})",
                "details": "Restarting after rollback"
            })

            # Restart after configured delay
            time.sleep(self.worker_retry_delay)
            self.start_worker(worker_info['class'], source)
        else:
            self.task_queue.put({"type": "LOG", "text": f"[{source}] Max retries reached. Halting agent."})
            self.task_queue.put({
                "type": "UPDATE_ROW",
                "source": source,
                "status": "HALTED",
                "details": f"Exceeded {self.max_retries} retries"
            })

    def is_any_alive(self):
        return any(w['process'].is_alive() for w in self.workers.values())

    def check_timeouts(self):
        """Check for workers that have been running too long without updates."""
        current_time = time.time()
        for display_name, worker_info in list(self.workers.items()):
            if not worker_info['process'].is_alive():
                continue  # Already dead

            elapsed = current_time - worker_info['last_heartbeat']
            if elapsed > self.worker_timeout:
                logger.warning(f"Worker {display_name} timeout after {elapsed:.0f}s")

                # Send timeout error message
                self.task_queue.put({
                    "type": "ERROR",
                    "source": display_name,
                    "run_id": worker_info.get('run_id', 'unknown'),
                    "error": f"Worker timeout after {self.worker_timeout}s",
                    "stack": "Timeout - no response"
                })

                # Terminate the stuck process
                worker_info['process'].terminate()
                worker_info['process'].join(timeout=5)
                if worker_info['process'].is_alive():
                    worker_info['process'].kill()  # Force kill if terminate doesn't work

    def stop_all(self):
        self.stop_event.set()
        for w in self.workers.values():
            if w['process'].is_alive():
                w['process'].terminate()
