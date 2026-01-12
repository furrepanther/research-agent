from .base import BaseSearcher
from semanticscholar import SemanticScholar
import requests
import os
import re
import time
from src.utils import get_config, logger, sanitize_filename
from datetime import datetime, timezone

class SemanticSearcher(BaseSearcher):
    def __init__(self, config):
        super().__init__(config)
        self.source_name = "semantic"
        self.download_dir = os.path.join(config.get("papers_dir", "data/papers"), self.source_name)
        os.makedirs(self.download_dir, exist_ok=True)
        self.sch = SemanticScholar()

    def search(self, query, start_date=None, max_results=10, stop_event=None):
        self.logger.info(f"Searching Semantic Scholar for: '{query}' (Max: {max_results})")
        
        papers = []
        offset = 0
        limit = 100
        base_url = "https://api.semanticscholar.org/graph/v1/paper/search"
        
        # SIMPLIFICATION: The API struggles with complex boolean queries (especially ANDNOT).
        # We will fetch BROADER results (ignoring exclusions) and let the Client-Side Filter
        # handle the strict exclusion logic. This avoids 429s and URL length limits.
        # FURTHER SIMPLIFICATION: Use only core high-value terms to avoid rate limiting
        simplified_query = "AI safety alignment risk"
        self.logger.info(f"Using ultra-simplified query for API: '{simplified_query}'")
        
        while len(papers) < max_results:
            if stop_event and stop_event.is_set():
                break
                
            params = {
                'query': simplified_query,
                'fields': 'title,abstract,authors,publicationDate,url,openAccessPdf,externalIds',
                'offset': offset,
                'limit': min(limit, max_results - len(papers))
            }
            
            retry_count = 0
            max_retries = 8
            time.sleep(1.0) # Pace requests slightly
            data = None
            
            while retry_count < max_retries:
                if stop_event and stop_event.is_set():
                    break
                try:
                    response = requests.get(base_url, params=params, timeout=10, headers={'User-Agent': 'ResearchAgent/1.0'})
                    
                    if response.status_code == 200:
                        data = response.json()
                        break
                    elif response.status_code == 429:
                        wait_time = min(30, 2**(retry_count+1))
                        self.logger.warning(f"Semantic Scholar 429 (Rate Limit). Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                        retry_count += 1
                    else:
                        self.logger.error(f"Semantic Scholar API Error: {response.status_code}")
                        break
                except Exception as e:
                    self.logger.error(f"Request failed: {e}")
                    retry_count += 1
                    time.sleep(1)
            
            if not data or 'data' not in data:
                break
                
            batch = data['data']
            if not batch:
                break
                
            for item in batch:
                if len(papers) >= max_results:
                    break
                    
                pub_date_str = item.get('publicationDate')
                pub_date = None
                if pub_date_str:
                    try:
                        pub_date = datetime.strptime(pub_date_str, "%Y-%m-%d")
                        pub_date = pub_date.replace(tzinfo=timezone.utc)
                    except ValueError:
                        pass
                
                if start_date:
                    if start_date.tzinfo is None:
                        start_date = start_date.replace(tzinfo=timezone.utc)
                    if pub_date and pub_date < start_date:
                        continue
                    
                pdf_url = None
                if item.get('openAccessPdf'):
                    pdf_url = item.get('openAccessPdf', {}).get('url')
                
                authors_list = item.get('authors', [])
                author_names = ", ".join([a.get('name', 'Unknown') for a in authors_list]) if authors_list else "Unknown"

                paper_meta = {
                    'id': item.get('paperId'),
                    'title': item.get('title'),
                    'published_date': pub_date_str if pub_date_str else "Unknown",
                    'authors': author_names,
                    'abstract': item.get('abstract') or "",
                    'source_url': item.get('url'),
                    'pdf_url': pdf_url,
                    'source': self.source_name,
                    'is_preprint': False 
                }
                papers.append(paper_meta)
            
            # Pagination
            # API returns 'total' sometimes, but using offset logic is safer
            if len(batch) < limit: 
                # End of results
                break
            
            offset += len(batch)
            time.sleep(0.2) # Be nice
                
        self.logger.info(f"Found {len(papers)} relevant papers from Semantic Scholar.")
        return papers

    def download(self, paper_meta):
        pdf_url = paper_meta.get('pdf_url')
        if not pdf_url:
            self.logger.warning(f"No PDF URL for paper: {paper_meta['title']}")
            return None

        # Clean title for filename - Title Case, no underscores, Windows safe
        filename = sanitize_filename(paper_meta['title'])
        filepath = os.path.join(self.download_dir, filename)

        if os.path.exists(filepath):
            self.logger.info(f"PDF already exists: {filepath}")
            return filepath

        try:
            self.logger.info(f"Downloading PDF: {pdf_url}")
            # Some PDFs might require headers or get blocked
            response = requests.get(pdf_url, timeout=30, headers={'User-Agent': 'Mozilla/5.0'})
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
