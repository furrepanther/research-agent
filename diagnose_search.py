import arxiv
import logging

# Setup basic logging to console
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_search():
    with open("prompt.txt", "r") as f:
        query = f.read().strip()
    
    print(f"Testing Query: {query}")
    
    client = arxiv.Client()
    search = arxiv.Search(
        query=query,
        max_results=20,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending
    )
    
    count = 0
    try:
        for result in client.results(search):
            count += 1
            print(f"[{count}] {result.title} ({result.published.strftime('%Y-%m-%d')})")
    except Exception as e:
        print(f"Error during search: {e}")
        
    print(f"Total results found in this batch: {count}")

if __name__ == "__main__":
    test_search()
