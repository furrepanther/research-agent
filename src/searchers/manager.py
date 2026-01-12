from src.utils import logger
from .arxiv_searcher import ArxivSearcher
from .semantic_searcher import SemanticSearcher
from .lesswrong_searcher import LessWrongSearcher
from .lab_scraper import LabScraper

class SearchManager:
    def __init__(self, config):
        self.config = config
        self.searchers = [
            ArxivSearcher(config),
            SemanticSearcher(config),
            LessWrongSearcher(config),
            LabScraper(config)
        ]

    def search_all(self, query, start_date=None, max_results=10):
        all_results = []
        for searcher in self.searchers:
            try:
                results = searcher.search(query, start_date, max_results)
                logger.info(f"{searcher.__class__.__name__} returned {len(results)} results.")
                all_results.extend(results)
            except Exception as e:
                logger.error(f"Error in {searcher.__class__.__name__}: {e}")
        return all_results

    def download_paper(self, paper_meta):
        # Dispatch download to the correct searcher based on source
        source = paper_meta.get('source', 'arxiv')
        
        # Simple lookup
        searcher = next((s for s in self.searchers if s.source_name == source), None)
        
        # Fallback for labs_*
        if not searcher and source.startswith("labs_"):
            searcher = next((s for s in self.searchers if s.source_name == "labs"), None)
        
        if searcher:
            return searcher.download(paper_meta)
        else:
            logger.error(f"No searcher found for source: {source}")
            return None
