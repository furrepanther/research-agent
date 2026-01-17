
import multiprocessing
import time
from src.utils import get_config, logger
from src.supervisor import Supervisor
from src.searchers.arxiv_searcher import ArxivSearcher
from src.storage import StorageManager
from datetime import datetime

def run_count_test():
    # 1. Setup
    config = get_config()
    task_queue = multiprocessing.Queue()
    stop_event = multiprocessing.Event()
    
    # 2. Get User Prompt
    with open("prompts/prompt.txt", "r") as f:
        prompt_text = f.read().strip()
        
    # Build search parameters for a "Full Backfill Count"
    search_params = {
        'max_papers_per_agent': 500, # Limit to 500 for a quick count test
        'per_query_limit': 500,
        'respect_date_range': False, # Check the whole database
        'start_date': datetime(2003, 1, 1)
    }

    # Use TEST mode (count only)
    mode = "TEST"
    
    print("\n" + "="*50)
    print(f"RUNNING ARCHIVE COUNT TEST (NEW LOGIC)")
    print("="*50)
    print(f"Mode: {mode}")
    print(f"Batch Size: {search_params['per_query_limit']}")
    print("="*50 + "\n")

    supervisor = Supervisor(task_queue, stop_event, prompt_text, search_params, mode)
    
    # Start ONLY ArXiv worker
    supervisor.start_worker(ArxivSearcher, "ArXiv")

    # Process messages until all workers complete
    while supervisor.is_any_alive():
        try:
            msg = task_queue.get(timeout=1)
            msg_type = msg.get("type")

            if msg_type == "UPDATE_ROW":
                status = msg.get("status", "")
                details = msg.get("details", "")
                print(f"[ArXiv Status] {status}: {details}")

            elif msg_type == "LOG":
                print(f"[Log] {msg.get('text')}")

            elif msg_type == "ERROR":
                print(f"[ERROR] {msg.get('error')}")

        except:
            pass

    print("\n" + "="*50)
    print("COUNT TEST COMPLETE")
    print("="*50)

if __name__ == "__main__":
    run_count_test()
