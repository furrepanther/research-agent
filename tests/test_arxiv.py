import sys
import os
from datetime import datetime
sys.path.append(os.getcwd())

from src.searchers.arxiv_searcher import ArxivSearcher
from src.utils import get_config

def test():
    config = get_config()
    searcher = ArxivSearcher(config)
    print("Starting search...")
    try:
        results = searcher.search("AI safety alignment risk", max_results=200)
        print(f"Search finished count: {len(results)}")
    except Exception as e:
        print(f"CRASH: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test()
