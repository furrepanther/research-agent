import sys
import os
import multiprocessing
import time
sys.path.append(os.getcwd())

from src.supervisor import Supervisor
from src.searchers.arxiv_searcher import ArxivSearcher

if __name__ == "__main__":
    print("Debug Supervisor: Starting...")
    queue = multiprocessing.Queue()
    stop = multiprocessing.Event()
    
    # Mock params
    params = {
        'max_papers_per_agent': 10,
        'per_query_limit': 5,
        'respect_date_range': True,
        'start_date': None 
    }
    
    # Create Supervisor
    sup = Supervisor(queue, stop, "AI", params, "TEST")
    
    # Start Worker via Supervisor
    print("Debug Supervisor: Launching Worker...")
    sup.start_worker(ArxivSearcher, "ArXiv")
    
    print("Debug Supervisor: Listening to queue...")
    start = time.time()
    while time.time() - start < 10:
        if not queue.empty():
            msg = queue.get()
            print(f"Msg: {msg}")
            if msg.get('status') == 'Searching':
                print("SUCCESS: Worker reached Searching state")
                break
        
        # Check supervisor Monitoring
        sup.check_timeouts()
        
        if not sup.is_any_alive():
             # Give it a second to start
             if time.time() - start > 2:
                 print("FAILURE: Worker died or failed to start")
                 break
                 
        time.sleep(0.5)
        
    sup.stop_all()
    print("Debug Supervisor: Done.")
