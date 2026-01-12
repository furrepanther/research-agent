import multiprocessing
import time
import os
from src.utils import logger, get_config
from src.storage import StorageManager
from src.worker import run_worker

class Supervisor:
    def __init__(self, task_queue, stop_event, prompt, max_results=200, mode="DAILY"):
        self.task_queue = task_queue
        self.stop_event = stop_event
        self.prompt = prompt
        self.max_results = max_results
        self.mode = mode
        self.config = get_config()
        self.storage = StorageManager(self.config.get("db_path", "data/metadata.db"))
        
        self.workers = {}  # display_name -> {'process': p, 'class': c, 'retries': 0, 'run_id': None}
        self.max_retries = 5

    def start_worker(self, searcher_class, display_name):
        if display_name in self.workers and self.workers[display_name]['process'].is_alive():
            logger.warning(f"Worker {display_name} already running.")
            return

        p = multiprocessing.Process(
            target=run_worker,
            args=(searcher_class, display_name, self.task_queue, self.stop_event, self.prompt, self.max_results, self.mode),
            daemon=True
        )
        p.start()
        
        if display_name not in self.workers:
            self.workers[display_name] = {
                'class': searcher_class,
                'retries': 0,
                'run_id': None
            }
        
        self.workers[display_name]['process'] = p
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
            paths_to_delete = self.storage.rollback_source(source.lower().replace(" ", ""), run_id)
            for path in paths_to_delete:
                if os.path.exists(path):
                    os.remove(path)
                    self.task_queue.put({"type": "LOG", "text": f"[{source}] Deleted file: {os.path.basename(path)}"})
            self.task_queue.put({"type": "LOG", "text": f"[{source}] Rollback complete. Database and files reverted."})
        except Exception as re:
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
                "status": f"Retrying ({retry_count}/5)",
                "details": "Restarting after rollback"
            })
            
            # Restart after a short delay
            time.sleep(2) 
            self.start_worker(worker_info['class'], source)
        else:
            self.task_queue.put({"type": "LOG", "text": f"[{source}] Max retries reached. Halting agent."})
            self.task_queue.put({
                "type": "UPDATE_ROW",
                "source": source,
                "status": "HALTED",
                "details": "Exceeded 5 retries"
            })

    def is_any_alive(self):
        return any(w['process'].is_alive() for w in self.workers.values())

    def stop_all(self):
        self.stop_event.set()
        for w in self.workers.values():
            if w['process'].is_alive():
                w['process'].terminate()
