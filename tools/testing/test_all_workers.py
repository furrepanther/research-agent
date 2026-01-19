import sys
import os
import time
import logging
sys.path.append(os.getcwd())

from src.searchers.openreview_searcher import OpenReviewSearcher
from src.searchers.acl_searcher import AclSearcher
from src.searchers.aaai_searcher import AaaiSearcher
from src.utils import get_config

# Configure basic logging to console
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def test_worker(name, searcher_cls, query, max_results=3):
    print(f"\n{'='*20} Testing {name} {'='*20}")
    try:
        config = get_config()
        searcher = searcher_cls(config)
        
        start = time.time()
        print(f"Searching for '{query}'...")
        # Use a recent date for AAAI to avoid OAI-PMH time travel
        from datetime import datetime
        start_date = datetime(2023, 1, 1) if name == "AAAI" else None
        
        results = searcher.search(query, max_results=max_results, start_date=start_date)
        duration = time.time() - start
        
        print(f"\nResult: Found {len(results)} papers in {duration:.2f}s")
        for i, p in enumerate(results):
            print(f"{i+1}. {p['title']} ({p['published_date']})")
            
        if len(results) == 0:
            print("FAILURE: No results found.")
        else:
            print("SUCCESS")
            
    except Exception as e:
        print(f"\nCRASH: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Test with the complex query that was failing logically
    complex_query = '(("AI" OR "Artificial Intelligence") AND ("LLM" OR "Language Model"))'
    
    # AAAI uses OAI-PMH which is slow and doesn't support Boolean search.
    # Use a simpler query for faster, reliable testing.
    aaai_query = "Deep Learning"
    
    test_worker("OpenReview", OpenReviewSearcher, "AI Safety")
    test_worker("ACL Anthology", AclSearcher, complex_query)
    test_worker("AAAI", AaaiSearcher, aaai_query) 
