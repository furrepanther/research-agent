import multiprocessing
import time
import os
import sqlite3
from src.supervisor import Supervisor
from src.searchers.base import BaseSearcher

# Mock Searcher that crashes
class CrashSearcher(BaseSearcher):
    def __init__(self, config):
        super().__init__(config)
        self.source_name = "crashtest"
        self.download_dir = "data/papers/crashtest"
        os.makedirs(self.download_dir, exist_ok=True)

    def search(self, query, start_date=None, max_results=10, stop_event=None):
        ts = int(time.time())
        return [
            {
                'id': f'test1_{ts}', 
                'title': f'Test Paper 1 {ts}', 
                'source_url': f'http://example.com/1/{ts}',
                'published_date': '2024-01-01',
                'authors': 'Test Author',
                'abstract': 'Test Abstract',
                'source': 'crashtest'
            },
            {
                'id': f'test2_{ts}', 
                'title': f'Test Paper 2 {ts}', 
                'source_url': f'http://example.com/2/{ts}',
                'published_date': '2024-01-01',
                'authors': 'Test Author',
                'abstract': 'Test Abstract',
                'source': 'crashtest'
            }
        ]

    def download(self, paper_meta):
        # Successfully "download" the first paper, then crash on the second
        if 'test1' in paper_meta['id']:
            path = os.path.join(self.download_dir, f"{paper_meta['id']}.pdf")
            with open(path, "w") as f: f.write("dummy content")
            return path
        else:
            raise RuntimeError("SIMULATED CRASH for testing self-healing!")

def test_self_healing():
    print("Starting Self-Healing Test...")
    q = multiprocessing.Queue()
    stop_event = multiprocessing.Event()
    
    # Initialize Supervisor
    supervisor = Supervisor(q, stop_event, "test prompt", 10)
    
    # Manually inject our crash searcher class
    # Normally Supervisor gets this from GUI, but we'll call start_worker directly
    supervisor.start_worker(CrashSearcher, "Crash Test")
    
    # Monitor queue
    start_time = time.time()
    errors_detected = 0
    retries_detected = 0
    rollback_detected = False
    
    while time.time() - start_time < 20: # 20 second timeout
        try:
            msg = q.get(timeout=1)
            msg_type = msg.get("type")
            
            if msg_type == "ERROR":
                print(f"Detected Error from {msg['source']}: {msg['error']}")
                errors_detected += 1
                supervisor.handle_error(msg)
            
            elif msg_type == "LOG":
                text = msg.get("text")
                print(f"LOG: {text}")
                if "Rolling back" in text: rollback_detected = True
                if "Self-healing attempt" in text: retries_detected += 1
            
            elif msg_type == "UPDATE_ROW":
                print(f"STATUS: {msg['source']} -> {msg.get('status')} ({msg.get('details')})")
                
            if retries_detected >= 1:
                # We saw it retry, let's stop the test
                print("\nSUCCESS: Self-healing retry loop verified!")
                break
                
        except Exception:
            # Continue waiting for the retry message even if queue times out
            pass

    # Final Verification of disk/DB
    db_path = "f:/Antigravity_Results/Research_Papers/data/metadata.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) FROM papers WHERE source = 'crashtest'")
    count = cursor.fetchone()[0]
    conn.close()
    
    print(f"\nFinal DB Count for 'crashtest': {count} (Should be 0 if rollback worked)")
    
    # Check if ANY files exist in the crashtest folder
    files = os.listdir("data/papers/crashtest") if os.path.exists("data/papers/crashtest") else []
    print(f"Files in data/papers/crashtest: {files} (Should be empty [])")
    
    supervisor.stop_all()
    
    if count == 0 and len(files) == 0 and retries_detected > 0:
        print("\n=== ALL TESTS PASSED ===")
    else:
        print("\n=== TEST FAILED ===")

if __name__ == "__main__":
    test_self_healing()
