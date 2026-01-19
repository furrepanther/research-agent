from .base import BaseSearcher
import openreview
import requests
import os
import re
import time
from datetime import datetime, timezone
from src.utils import get_config, logger, sanitize_filename
from src.classifier import classify_paper

class OpenReviewSearcher(BaseSearcher):
    def __init__(self, config):
        super().__init__(config)
        self.source_name = "openreview"
        
        # Prefer staging dir if configured, otherwise use papers_dir
        base_dir = config.get("staging_dir", config.get("papers_dir", "data/papers"))
        self.download_dir = base_dir
        os.makedirs(self.download_dir, exist_ok=True)
        
        # Initialize OpenReview client (V2 API)
        try:
            # V2 API uses api2.openreview.net
            self.client = openreview.api.OpenReviewClient(baseurl='https://api2.openreview.net')
            self.logger.info("OpenReview client initialized (V2 API)")
        except Exception as e:
            self.logger.error(f"Failed to initialize OpenReview client: {e}")
            self.client = None

    def search(self, query, start_date=None, max_results=10, stop_event=None):
        if not self.client:
            return []
            
        if stop_event and stop_event.is_set():
            return []

        self.logger.info(f"Searching OpenReview (V2) with query: '{query}'")
        
        all_results = []
        limit = 100 if (max_results == float('inf') or max_results is None) else int(max_results)
        
        try:
            # V2 search_notes uses Elasticsearch for global keyword search
            # We filter by content='title' to avoid retrieving reviews/comments that lack titles
            notes = self.client.search_notes(
                term=query,
                content='title',
                limit=limit
            )
            
            count = 0
            for note in notes:
                if stop_event and stop_event.is_set():
                    break
                if count >= limit:
                    break
                    
                # V2 Note content is nested: note.content[field]['value']
                content = note.content
                title = content.get('title', {}).get('value')
                if not title:
                    continue
                    
                # Date filtering (cdate is creation date in ms)
                pub_date = datetime.fromtimestamp(note.cdate / 1000.0, tz=timezone.utc)
                if start_date:
                    if start_date.tzinfo is None:
                        start_date = start_date.replace(tzinfo=timezone.utc)
                    if pub_date < start_date:
                        continue

                authors_list = content.get('authors', {}).get('value', [])
                authors = ", ".join(authors_list)
                abstract = content.get('abstract', {}).get('value', '')
                
                # Language tracking: Detect if paper is English
                lang_code = 'en'
                try:
                    from langdetect import detect
                    lang_code = detect(title + " " + abstract)
                except:
                    lang_code = 'en'
                
                # PDF URL construction for V2
                pdf_url = f"https://api2.openreview.net/pdf?id={note.id}"
                
                # Some notes might have a custom PDF field
                if 'pdf' in content:
                    pdf_val = content['pdf'].get('value')
                    if pdf_val:
                        if pdf_val.startswith('/'):
                            pdf_url = f"https://api2.openreview.net{pdf_val}"
                        else:
                            pdf_url = pdf_val

                paper_meta = {
                    'id': note.id,
                    'title': title,
                    'published_date': pub_date.strftime("%Y-%m-%d"),
                    'authors': authors,
                    'abstract': abstract,
                    'source_url': f"https://openreview.net/forum?id={note.id}",
                    'pdf_url': pdf_url,
                    'source': self.source_name,
                    # V2 invitations are strings
                    'is_preprint': ('submission' in note.invitations[0].lower() if note.invitations else True),
                    'language': lang_code
                }
                
                all_results.append(paper_meta)
                count += 1
                
        except Exception as e:
            self.logger.error(f"Error in OpenReview V2 search: {e}")

        self.logger.info(f"Fetched {len(all_results)} valid papers from OpenReview V2.")
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
        
        # Update download path to include category
        save_dir = os.path.join(self.download_dir, category_safe)
        os.makedirs(save_dir, exist_ok=True)
        
        filepath = os.path.join(save_dir, filename)

        if os.path.exists(filepath):
            self.logger.info(f"PDF already exists: {filepath}")
            return filepath

        try:
            self.logger.info(f"Downloading PDF: {pdf_url} to {category}")
            
            # 1. If it's an OpenReview hosted link, use the official client for better reliability
            if "openreview.net" in pdf_url or "api2.openreview.net" in pdf_url:
                try:
                    pdf_content = self.client.get_pdf(id=paper_meta['id'])
                    if pdf_content and isinstance(pdf_content, bytes):
                        with open(filepath, 'wb') as f:
                            f.write(pdf_content)
                        return filepath
                    else:
                        self.logger.error(f"Client failed to retrieve PDF content for {paper_meta['id']}")
                        # Fall through to requests if client fails
                except Exception as client_err:
                    self.logger.warning(f"Client download failed: {client_err}. Falling back to requests.")

            # 2. Use requests with headers for external links (or fallback)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            # Simple retry logic for rate limits
            max_retries = 3
            for attempt in range(max_retries):
                response = requests.get(pdf_url, headers=headers, stream=True, timeout=30)
                
                if response.status_code == 200:
                    with open(filepath, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    return filepath
                elif response.status_code == 429:
                    wait_time = (attempt + 1) * 5
                    self.logger.warning(f"Rate limited (429). Waiting {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"Failed to download PDF. Status: {response.status_code}")
                    return None
            
            return None
        except Exception as e:
            self.logger.error(f"Error downloading PDF: {e}")
            return None
