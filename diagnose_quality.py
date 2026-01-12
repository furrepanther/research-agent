from src.utils import get_config
from src.searchers.manager import SearchManager
import logging

# Setup logging to console
logging.basicConfig(level=logging.INFO)

def diagnose():
    config = get_config()
    manager = SearchManager(config)
    
    with open("prompt.txt", "r") as f:
        query = f.read().strip()
        
    print(f"DIAGNOSING QUERY: {query}")
    print("-" * 50)
    
    # search with a small limit
    results = manager.search_all(query, max_results=20)
    
    print(f"\nFound {len(results)} results.")
    print("-" * 50)
    
    for i, p in enumerate(results):
        print(f"[{i+1}] [{p.get('source', 'unknown')}] {p['title']}")
        # print first 200 chars of abstract
        print(f"    Abstract: {p['abstract'][:200]}...")
        print("-" * 20)

if __name__ == "__main__":
    diagnose()
