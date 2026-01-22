from .base import BaseSearcher
import requests
import os
import re
import time
from datetime import datetime, timezone
from sickle import Sickle
from src.utils import get_config, logger, sanitize_filename
from src.classifier import classify_paper

class AaaiSearcher(BaseSearcher):
    def __init__(self, config):
        super().__init__(config)
        self.source_name = "aaai"
        self.endpoint = "https://ojs.aaai.org/index.php/AAAI/oai"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        # Prefer staging dir if configured, otherwise use papers_dir
        base_dir = config.get("staging_dir", config.get("papers_dir", "data/papers"))
        self.download_dir = base_dir
        os.makedirs(self.download_dir, exist_ok=True)

    def search(self, query, start_date=None, max_results=10, stop_event=None):
        if stop_event and stop_event.is_set():
            return []

        self.logger.info(f"Searching AAAI (OAI-PMH) with keywords: '{query}'")
        
        sickle = Sickle(self.endpoint, headers=self.headers)
        all_results = []
        limit = 100 if (max_results == float('inf') or max_results is None) else int(max_results)
        
        # OAI-PMH 'from' parameter format: YYYY-MM-DD
        from_str = None
        if start_date:
            from_str = start_date.strftime("%Y-%m-%d")
        else:
            # Default to 2 years ago to avoid exhausting OAI-PMH
            from datetime import timedelta
            default_date = datetime.now() - timedelta(days=365*2)
            from_str = default_date.strftime("%Y-%m-%d")
            self.logger.warning(f"No start_date provided. Defaulting AAAI search to {from_str} to avoid OAI exhaustion.")

        try:
            # Note: ListRecords can be slow. We harvest and filter locally for keywords.
            # Use extracted positive keywords and ANY match (Recall Strategy)
            from src.utils import extract_simple_keywords
            simple_queries = extract_simple_keywords(query)
            
            # Harvest records
            params = {'metadataPrefix': 'oai_dc', 'ignore_deleted': True}
            if from_str:
                params['from'] = from_str
                self.logger.info(f"AAAI OAI-PMH Filter: fetching records from {from_str}")
                
            # Set timeout to prevent indefinite hangs (60s)
            sickle = Sickle(self.endpoint, headers=self.headers, timeout=60)
            records = sickle.ListRecords(**params)
            
            count = 0
            scanned = 0
            MAX_SCAN_LIMIT = 2000 # Safety brake
            
            for record in records:
                scanned += 1
                if scanned % 20 == 0:
                    self.logger.info(f"Scanned {scanned} AAAI records...")
                    
                if scanned > MAX_SCAN_LIMIT:
                    self.logger.info(f"Reached MAX_SCAN_LIMIT ({MAX_SCAN_LIMIT}). Stopping AAAI scan.")
                    break

                if stop_event and stop_event.is_set():
                    break
                if count >= limit:
                    break
                
                metadata = record.metadata
                if not metadata:
                    continue
                    
                title = metadata.get('title', [''])[0]
                abstract = metadata.get('description', ['No Abstract'])[0]
                
                if not title:
                    continue
                
                title_lower = title.lower()
                abstract_lower = abstract.lower()
                
                # Keyword matching (Broad Recall)
                if not simple_queries or any(q in title_lower or q in abstract_lower for q in simple_queries):
                    # Identify Language
                    lang_raw = metadata.get('language', ['eng'])[0].lower()
                    lang_code = 'en'
                    if 'eng' in lang_raw or 'en' == lang_raw:
                        lang_code = 'en'
                    else:
                        # Use fallback detection if needed
                        from src.utils import is_english
                        if not is_english(title + " " + abstract):
                            lang_code = lang_raw[:2] # Best effort
                    
                    # Identify Landing Page & PDF
                    landing_url = None
                    for idx in metadata.get('identifier', []):
                        if 'article/view/' in idx:
                            landing_url = idx
                            break
                    
                    if not landing_url:
                        continue
                        
                    # Guess PDF URL (landing page /article/view/ID -> /article/download/ID/ID)
                    article_id = landing_url.split('/')[-1]
                    pdf_url = landing_url.replace('/view/', '/download/') + f"/{article_id}"
                    
                    pub_date = metadata.get('date', [''])[0]
                    # OJS dates are often YYYY-MM-DD
                    if len(pub_date) == 4: # Just year
                        pub_date = f"{pub_date}-01-01"
                        
                    authors = ", ".join(metadata.get('creator', []))

                    paper_meta = {
                        'id': f"aaai_{article_id}",
                        'title': title,
                        'published_date': pub_date,
                        'authors': authors,
                        'abstract': abstract,
                        'source_url': landing_url,
                        'pdf_url': pdf_url,
                        'source': self.source_name,
                        'is_preprint': False,
                        'language': lang_code
                    }
                    
                    all_results.append(paper_meta)
                    count += 1
                    
        except Exception as e:
            self.logger.error(f"Error in AAAI OAI-PMH harvesting: {e}")

        self.logger.info(f"Fetched {len(all_results)} valid papers from AAAI.")
        return all_results

    def download(self, paper_meta):
        pdf_url = paper_meta.get('pdf_url')
        if not pdf_url:
            return None

        # Clean title for filename
        filename = sanitize_filename(paper_meta['title'], extension=".pdf")
        
        # CATEGORIZATION LOGIC
        category = classify_paper(paper_meta['title'], paper_meta.get('abstract', ''), paper_meta.get('authors', ''))
        category_safe = sanitize_filename(category, extension="")
        
        # Update download path
        save_dir = os.path.join(self.download_dir, category_safe)
        os.makedirs(save_dir, exist_ok=True)
        
        filepath = os.path.join(save_dir, filename)

        if os.path.exists(filepath):
            return filepath

        try:
            self.logger.info(f"Downloading AAAI PDF: {pdf_url}")
            response = requests.get(pdf_url, headers=self.headers, timeout=30, stream=True)
            
            # If the guessed URL fails (e.g. 404), try scraping the landing page
            if response.status_code != 200:
                self.logger.warning(f"Guessed PDF URL failed ({response.status_code}). Scraping landing page...")
                landing_url = paper_meta.get('source_url')
                if landing_url:
                    scrape_resp = requests.get(landing_url, headers=self.headers, timeout=20)
                    if scrape_resp.status_code == 200:
                        # Look for 'article/download/ID/Gid'
                        pdf_match = re.search(r'href="([^"]+article/download/[^"]+)"', scrape_resp.text)
                        if pdf_match:
                            pdf_url = pdf_match.group(1).replace("&amp;", "&")
                            self.logger.info(f"Found scraped PDF URL: {pdf_url}")
                            response = requests.get(pdf_url, headers=self.headers, timeout=30, stream=True)

            if response.status_code == 200:
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                return filepath
            else:
                self.logger.error(f"Failed to download AAAI PDF. Status: {response.status_code}")
                return None
        except Exception as e:
            self.logger.error(f"Error downloading AAAI PDF: {e}")
            return None
