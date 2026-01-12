from src.utils import get_config, logger
from src.searchers.manager import SearchManager
from src.filter import FilterManager
import os
from datetime import datetime
import time

def run_test():
    print("Starting 20-Document Retrieval Test...")
    config = get_config()
    manager = SearchManager(config)
    
    with open("prompt.txt", "r") as f:
        prompt_text = f.read().strip()
    filter_mgr = FilterManager(prompt_text)

    # We want to test each searcher individually to ensure diversity
    sources = ['arxiv', 'semantic', 'lesswrong']
    
    for source_name in sources:
        print(f"\nTesting Source: {source_name.upper()}")
        print("-" * 30)
        
        # Find the specific searcher instance
        searcher = next((s for s in manager.searchers if s.source_name == source_name), None)
        if not searcher:
            print(f"Error: Searcher {source_name} not found.")
            continue
            
        # Search (Requesting 50 to allow for filtering)
        # Note: Semantic/Arxiv allow date filtering, LessWrong we filter manually
        try:
            start_date = datetime(2023, 1, 1) if source_name != 'lesswrong' else None
            results = searcher.search(prompt_text, max_results=50, start_date=start_date)
            
            # Filter
            kept = []
            for p in results:
                if filter_mgr.is_relevant(p):
                    kept.append(p)
                if len(kept) >= 20:
                    break
            
            print(f"Found {len(results)} raw results.")
            print(f"After Filter: {len(kept)} relevant papers.")
            
            # Download first 3 for verification (saving bandwidth/time)
            print("Downloading sample (first 3)...")
            for i, paper in enumerate(kept[:3]):
                print(f"Downloading [{i+1}]: {paper['title'][:60]}...")
                path = searcher.download(paper)
                if path and os.path.exists(path):
                    print(f"  SUCCESS: {path}")
                else:
                    print(f"  FAILURE.")
                    
        except Exception as e:
            print(f"Error testing {source_name}: {e}")

if __name__ == "__main__":
    run_test()
