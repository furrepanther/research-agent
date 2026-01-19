import sys
import os
from datetime import datetime
sys.path.append(os.getcwd())

from src.searchers.openreview_searcher import OpenReviewSearcher
from src.utils import get_config

def test_openreview():
    config = get_config()
    searcher = OpenReviewSearcher(config)
    
    query = "AI Safety"
    print(f"Testing OpenReview Search with query: {query}")
    
    start_time = time.time()
    results = searcher.search(query, max_results=3)
    end_time = time.time()
    
    print(f"Search took {end_time - start_time:.2f} seconds")
    print(f"Found {len(results)} results")
    for p in results:
        print(f"- {p['title']} ({p['published_date']})")

if __name__ == "__main__":
    import time
    test_openreview()
