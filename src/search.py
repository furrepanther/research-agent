import arxiv
import requests
import os
import re
from datetime import datetime, timezone
from src.utils import logger

class ResearchAgent:
    def __init__(self, config):
        self.config = config
        self.download_dir = config.get("papers_dir", "data/papers")

    def search_arxiv(self, query, start_date=None, max_results=10):
        """
        Search Arxiv for papers.
        query: Search string from prompts/prompt.txt
        start_date: datetime object (UTC). If provided, filters results newer than this date.
        max_results: int
        """
        logger.info(f"Searching arXiv for: '{query}' (Max: {max_results})")
        
        # Construct client
        client = arxiv.Client()
        
        # Construct search
        # Note: Arxiv API sort by submittedDate is usually best for "newest"
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending
        )

        results = []
        for result in client.results(search):
            # Filter by date if necessary
            # result.published is a datetime object with timezone
            if start_date:
                # Ensure start_date is timezone aware for comparison
                if start_date.tzinfo is None:
                    start_date = start_date.replace(tzinfo=timezone.utc)
                
                if result.published < start_date:
                    # Since we sorted by descending date, once we hit a paper older than start_date, 
                    # we can usually stop if strictly sorted, but arXiv sorting can be fuzzy.
                    # We'll just skip this one. If many are skipped, we might stop. 
                    # For safety, let's just skip.
                    continue

            paper_meta = {
                'id': result.entry_id.split('/')[-1], # parsing ID from URL
                'title': result.title,
                'published_date': result.published.strftime("%Y-%m-%d"),
                'authors': ", ".join([a.name for a in result.authors]),
                'abstract': result.summary.replace("\n", " "),
                'source_url': result.entry_id,
                'pdf_url': result.pdf_url,
                'is_preprint': "arXiv" in result.entry_id # arXiv is prepints generally
            }
            results.append(paper_meta)
        
        logger.info(f"Found {len(results)} relevant papers.")
        return results

    def download_pdf(self, paper_meta):
        """
        Downloads PDF for a single paper.
        Returns: absolute path to PDF or None if failed.
        """
        pdf_url = paper_meta.get('pdf_url')
        if not pdf_url:
            return None

        # Clean title for filename
        safe_title = re.sub(r'[\\/*?:"<>|]', "", paper_meta['title'])[:150] # limit length
        filename = f"{paper_meta['id']}_{safe_title}.pdf"
        filepath = os.path.join(self.download_dir, filename)

        if os.path.exists(filepath):
            logger.info(f"PDF already exists: {filepath}")
            return filepath

        try:
            logger.info(f"Downloading PDF: {pdf_url}")
            response = requests.get(pdf_url, timeout=30)
            if response.status_code == 200:
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                return filepath
            else:
                logger.error(f"Failed to download PDF. Status: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error downloading PDF: {e}")
            return None
