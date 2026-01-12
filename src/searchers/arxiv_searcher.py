from .base import BaseSearcher
import arxiv
import requests
import os
import re
from datetime import datetime, timezone
from src.utils import get_config, logger, sanitize_filename

class ArxivSearcher(BaseSearcher):
    def __init__(self, config):
        super().__init__(config)
        self.source_name = "arxiv"
        self.download_dir = os.path.join(config.get("papers_dir", "data/papers"), self.source_name)
        os.makedirs(self.download_dir, exist_ok=True)

    def search(self, query, start_date=None, max_results=10, stop_event=None):
        # SIMPLIFICATION: arXiv API can be picky with complex boolean logic (like ANDNOT).
        # We'll use a broader query and let FilterManager handle the strict logic.
        simplified_query = "AI safety alignment risk"
        self.logger.info(f"Searching arXiv for simplified query: '{simplified_query}' (Filtering locally...)")
        
        client = arxiv.Client()
        search = arxiv.Search(
            query=simplified_query,
            max_results=max_results * 5, # Fetch more to allow for local filtering
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending
        )

        results = []
        for result in client.results(search):
            if stop_event and stop_event.is_set():
                self.logger.info("ArXiv search cancelled.")
                break
                
            if start_date:
                if start_date.tzinfo is None:
                    start_date = start_date.replace(tzinfo=timezone.utc)
                if result.published < start_date:
                    continue

            paper_meta = {
                'id': result.entry_id.split('/')[-1],
                'title': result.title,
                'published_date': result.published.strftime("%Y-%m-%d"),
                'authors': ", ".join([a.name for a in result.authors]),
                'abstract': result.summary.replace("\n", " "),
                'source_url': result.entry_id,
                'pdf_url': result.pdf_url,
                'source': self.source_name,
                'is_preprint': True
            }
            results.append(paper_meta)
        
        self.logger.info(f"Found {len(results)} relevant papers from arXiv.")
        return results

    def download(self, paper_meta):
        pdf_url = paper_meta.get('pdf_url')
        if not pdf_url:
            return None

        # Clean title for filename - Title Case, no underscores, Windows safe
        filename = sanitize_filename(paper_meta['title'])
        filepath = os.path.join(self.download_dir, filename)

        if os.path.exists(filepath):
            self.logger.info(f"PDF already exists: {filepath}")
            return filepath

        try:
            self.logger.info(f"Downloading PDF: {pdf_url}")
            response = requests.get(pdf_url, timeout=30)
            if response.status_code == 200:
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                return filepath
            else:
                self.logger.error(f"Failed to download PDF. Status: {response.status_code}")
                return None
        except Exception as e:
            self.logger.error(f"Error downloading PDF: {e}")
            return None
