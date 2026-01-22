from .base import BaseSearcher
import arxiv
import requests
import os
import re
from datetime import datetime, timezone
from src.utils import get_config, logger, sanitize_filename
from src.classifier import classify_paper

class ArxivSearcher(BaseSearcher):
    def __init__(self, config):
        super().__init__(config)
        self.source_name = "arxiv"
        
        # Prefer staging dir if configured, otherwise use papers_dir
        base_dir = config.get("staging_dir", config.get("papers_dir", "data/papers"))
        self.download_dir = base_dir
        os.makedirs(self.download_dir, exist_ok=True)

    def search(self, query, start_date=None, max_results=10, stop_event=None):
        # Early exit check
        if stop_event and stop_event.is_set():
            return []

        # STRATEGY: Use the full structured query from the prompt
        # We respect the boolean logic defined in the prompt (e.g. (AI AND LLM) AND Safety)
        
        # 1. Basic cleanup: remove newlines and extra spaces
        # Convert ANDNOT to ArXiv's preferred AND NOT
        arxiv_query = query.replace("\n", " ").replace("ANDNOT", "AND NOT").strip()
        while "  " in arxiv_query:
            arxiv_query = arxiv_query.replace("  ", " ")

        # 2. Handle infinity and set a production safety cap
        # If backfill is unlimited, we still cap a single search at 2000 
        # to avoid ArXiv rate-limiting/stalling.
        safe_limit = 200
        if max_results == float('inf') or max_results is None:
            safe_limit = 2000
        else:
            safe_limit = min(int(max_results) * 10, 2000)

        self.logger.info(f"Searching arXiv with query: '{arxiv_query}'")

        client = arxiv.Client(
            page_size=100,
            delay_seconds=5.0,
            num_retries=5
        )

        all_results = []
        
        # Determine total results goal
        total_goal = 2000
        if max_results != float('inf') and max_results is not None:
            total_goal = int(max_results)

        # Create a single search object
        # The library version 2.x handles pagination automatically via client.results()
        search = arxiv.Search(
            query=arxiv_query,
            max_results=total_goal,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending
        )

        try:
            count = 0
            reached_date_limit = False
            
            for result in client.results(search):
                if stop_event and stop_event.is_set():
                    break
                
                # Progress logging
                count += 1
                if count % 100 == 0:
                    self.logger.info(f"[{self.source_name}] Fetched {count} candidates...")
                
                # Date verification
                if start_date:
                    if start_date.tzinfo is None:
                        start_date = start_date.replace(tzinfo=timezone.utc)
                    
                    if result.published < start_date:
                        self.logger.info(f"[{self.source_name}] Date Cutoff Reached: Paper {result.published.strftime('%Y-%m-%d')} is older than {start_date.strftime('%Y-%m-%d')}")
                        reached_date_limit = True
                        break 

                # Language tracking: Detect if paper is English
                lang_code = 'en'
                try:
                    from langdetect import detect
                    lang_code = detect(result.title + " " + result.summary)
                except:
                    lang_code = 'en'

                paper_meta = {
                    'id': result.entry_id.split('/')[-1],
                    'title': result.title,
                    'published_date': result.published.strftime("%Y-%m-%d"),
                    'authors': ", ".join([a.name for a in result.authors]),
                    'abstract': result.summary.replace("\n", " "),
                    'source_url': result.entry_id,
                    'pdf_url': result.pdf_url,
                    'source': self.source_name,
                    'is_preprint': True,
                    'language': lang_code
                }
                all_results.append(paper_meta)
                
            if reached_date_limit:
                self.logger.info(f"[{self.source_name}] Reached date limit ({start_date.strftime('%Y-%m-%d')}).")

        except Exception as e:
            self.logger.error(f"Error in ArXiv retrieval: {e}")

        self.logger.info(f"Fetched {len(all_results)} total relevant papers from arXiv.")
        return all_results

    def download(self, paper_meta):
        pdf_url = paper_meta.get('pdf_url')
        if not pdf_url:
            return None

        # Clean title for filename - Title Case, no underscores, Windows safe
        filename = sanitize_filename(paper_meta['title'], extension=".pdf")
        
        # CATEGORIZATION LOGIC
        category = classify_paper(paper_meta['title'], paper_meta.get('abstract', ''), paper_meta.get('authors', ''))
        category_safe = sanitize_filename(category, extension="") # Ensure safe folder name
        
        # Update download path to include category
        save_dir = os.path.join(self.download_dir, category_safe)
        os.makedirs(save_dir, exist_ok=True)
        
        filepath = os.path.join(save_dir, filename)

        if os.path.exists(filepath):
            self.logger.info(f"PDF already exists: {filepath}")
            return filepath

        try:
            self.logger.info(f"Downloading PDF: {pdf_url} to {category}")
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
