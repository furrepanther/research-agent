"""
Test individual searcher agents in isolation.

Usage:
    python test_agent.py arxiv
    python test_agent.py semantic
    python test_agent.py lesswrong
"""

import sys
import multiprocessing
from src.worker import run_worker
from src.searchers.arxiv_searcher import ArxivSearcher
from src.searchers.semantic_searcher import SemanticSearcher
from src.searchers.lesswrong_searcher import LessWrongSearcher
from src.searchers.lab_scraper import LabScraper


def monitor_queue(q, stop_event, worker):
    """Monitor and print status updates from the worker."""
    while worker.is_alive() or not q.empty():
        try:
            msg = q.get(timeout=0.5)
            if msg.get("type") == "UPDATE_ROW":
                print(f"[{msg['source']}] {msg['status']} - {msg.get('details', '')} (Count: {msg.get('count', '0')})")
            elif msg.get("type") == "DONE":
                break
        except:
            if stop_event.is_set():
                break
            continue


if __name__ == "__main__":
    multiprocessing.freeze_support()
    
    if len(sys.argv) < 2:
        print("Usage: python test_agent.py [arxiv|semantic|lesswrong]")
        sys.exit(1)
    
    agent_name = sys.argv[1].lower()
    
    # Map agent names to classes
    agents = {
        "arxiv": (ArxivSearcher, "ArXiv"),
        "semantic": (SemanticSearcher, "Semantic Scholar"),
        "lesswrong": (LessWrongSearcher, "LessWrong"),
        "labs": (LabScraper, "AI Labs")
    }
    
    if agent_name not in agents:
        print(f"Unknown agent: {agent_name}")
        print("Available agents: arxiv, semantic, lesswrong")
        sys.exit(1)
    
    searcher_class, display_name = agents[agent_name]
    
    # Load prompt
    with open("prompt.txt", "r") as f:
        prompt = f.read().strip()
    
    print(f"Testing {display_name} agent...")
    print(f"Query: {prompt[:100]}...")
    print("-" * 60)
    
    # Create queue and event
    q = multiprocessing.Queue()
    stop_event = multiprocessing.Event()
    
    # Start worker
    worker = multiprocessing.Process(
        target=run_worker,
        args=(searcher_class, display_name, q, stop_event, prompt, 20)  # Limit to 20 for testing
    )
    worker.start()
    
    # Monitor output
    try:
        monitor_queue(q, stop_event, worker)
    except KeyboardInterrupt:
        print("\n\nCancelling...")
        stop_event.set()
    
    worker.join(timeout=5)
    if worker.is_alive():
        worker.terminate()
        worker.join()
    
    print("\nTest complete.")
