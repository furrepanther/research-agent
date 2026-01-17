
import arxiv
from src.filter import FilterManager
from src.utils import get_config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_diagnostic():
    # 1. Load the prompt
    try:
        with open("prompts/prompt.txt", "r") as f:
            prompt = f.read().strip()
    except FileNotFoundError:
        # fallback for running from tools/testing or root
        with open("../../prompts/prompt.txt", "r") as f:
            prompt = f.read().strip()
    
    # ArXiv prefers "AND NOT" over "ANDNOT"
    arxiv_query = prompt.replace("\n", " ").replace("ANDNOT", "AND NOT").strip()
    
    logger.info(f"Full Query: {arxiv_query[:100]}...")
    
    client = arxiv.Client(page_size=100)
    
    filter_mgr = FilterManager(prompt)
    
    # Test 1: Full Query (Total found vs total passed)
    search_full = arxiv.Search(
        query=arxiv_query,
        max_results=200,
        sort_by=arxiv.SortCriterion.SubmittedDate
    )
    
    full_results = []
    try:
        full_results = list(client.results(search_full))
        logger.info(f"Full Query Results Found: {len(full_results)}")
    except Exception as e:
        logger.error(f"Full Query Failed: {e}")

    passed_filter = 0
    for r in full_results:
        meta = {
            'title': r.title,
            'abstract': r.summary,
            'authors': ", ".join([a.name for a in r.authors])
        }
        if filter_mgr.is_relevant(meta):
            passed_filter += 1
            
    logger.info(f"Full Query Passed Filtering: {passed_filter}/{len(full_results)}")

    # Test 2: Simplified Query (Drop the ANDNOT exclusions)
    parts = prompt.split("ANDNOT")
    simple_query = parts[0].replace("ANDNOT", "").strip()
    arxiv_simple = simple_query.replace("\n", " ").strip()
    
    logger.info(f"Simple Query: {arxiv_simple[:100]}...")
    
    search_simple = arxiv.Search(
        query=arxiv_simple,
        max_results=200,
        sort_by=arxiv.SortCriterion.SubmittedDate
    )
    
    simple_results = []
    try:
        simple_results = list(client.results(search_simple))
        logger.info(f"Simple Query Results Found: {len(simple_results)}")
    except Exception as e:
        logger.error(f"Simple Query Failed: {e}")

    passed_simple = 0
    for r in simple_results:
        meta = {
            'title': r.title,
            'abstract': r.summary,
            'authors': ", ".join([a.name for a in r.authors])
        }
        if filter_mgr.is_relevant(meta):
            passed_simple += 1
            
    logger.info(f"Simple Query Passed Filtering: {passed_simple}/{len(simple_results)}")

if __name__ == "__main__":
    run_diagnostic()
