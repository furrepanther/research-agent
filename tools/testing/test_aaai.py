import sys
import os
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

from src.searchers.aaai_searcher import AaaiSearcher
from src.utils import get_config

def test_aaai_searcher():
    config = get_config()
    # Use a test staging dir
    config['staging_dir'] = "data/test_staging_aaai"
    os.makedirs(config['staging_dir'], exist_ok=True)
    
    searcher = AaaiSearcher(config)
    
    # Test Search (using a specific recent query and date)
    query = "AI Safety AND Ethics"
    from datetime import datetime, timedelta
    start_date = datetime.now() - timedelta(days=365) # Last year
    print(f"Testing AAAI Search with query: {query} since {start_date.strftime('%Y-%m-%d')}")
    
    results = searcher.search(query, start_date=start_date, max_results=3)
    
    print(f"Found {len(results)} results:")
    for res in results:
        print(f"- {res['title']} ({res['published_date']})")
        print(f"  Authors: {res['authors']}")
        print(f"  Language: {res['language']}")
        print(f"  PDF URL: {res['pdf_url']}")
        
        # Test Download for the first result
        print(f"\nAttempting to download first result...")
        path = searcher.download(res)
        if path:
            print(f"SUCCESS: Downloaded to {path}")
        else:
            print("FAILED: Could not download PDF.")
        break

if __name__ == "__main__":
    test_aaai_searcher()
