import sys
import os
import multiprocessing
import time
sys.path.append(os.getcwd())

from src.searchers.arxiv_searcher import ArxivSearcher
from src.worker import run_worker
from src.utils import logger

if __name__ == "__main__":
    print("Debug Worker: Starting...")
    queue = multiprocessing.Queue()
    stop = multiprocessing.Event()
    
    # Mock params
    params = {
        'max_papers_per_agent': 10,
        'per_query_limit': 5,
        'respect_date_range': True,
        'start_date': None 
    }
    
    p = multiprocessing.Process(
         target=run_worker,
         args=(ArxivSearcher, "ArXiv", queue, stop, "AI", params, "TEST"),
         kwargs={'run_id': "DEBUG_RUN"}
    )
    p.start()
    
    print("Debug Worker: Process launched. Listening to queue...")
    
    start = time.time()
    while time.time() - start < 10:
        if not queue.empty():
            msg = queue.get()
            print(f"Msg: {msg}")
        
        if not p.is_alive():
            print("Process died!")
            break
        time.sleep(0.5)
        
    if p.is_alive():
        print("Stopping process...")
        p.terminate()
