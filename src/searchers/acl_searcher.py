from .base import BaseSearcher
import os
from datetime import datetime, timezone
import logging
from src.utils import sanitize_filename
from src.classifier import classify_paper

try:
    from acl_anthology import Anthology
except ImportError:
    Anthology = None

class AclSearcher(BaseSearcher):
    def __init__(self, config):
        super().__init__(config)
        self.source_name = "acl_anthology"
        
        # Determine download and metadata directories
        base_dir = config.get("staging_dir", config.get("papers_dir", "data/papers"))
        self.download_dir = base_dir
        os.makedirs(self.download_dir, exist_ok=True)
        
        # Metadata directory for ACL (cloned repository)
        self.metadata_dir = os.path.join("data", "acl_metadata")
        os.makedirs(self.metadata_dir, exist_ok=True)
        
        self.anthology = None
        
    def _ensure_anthology(self):
        if self.anthology:
            return True
            
        try:
            if Anthology:
                self.logger.info(f"Initializing ACL Anthology (fetching/updating repo in {self.metadata_dir})...")
                # from_repo will clone if it doesn't exist, or update if it does.
                self.anthology = Anthology.from_repo(path=self.metadata_dir)
                self.logger.info("ACL Anthology initialized successfully from repo.")
                return True
            else:
                self.logger.error("acl-anthology library not installed.")
                return False
        except Exception as e:
            self.logger.error(f"Failed to initialize ACL Anthology from repo: {e}")
            try:
                self.logger.info("Attempting local load fallback...")
                self.anthology = Anthology(datadir=self.metadata_dir)
                return True
            except Exception as e2:
                self.logger.error(f"Local fallback also failed: {e2}")
                return False

    def search(self, query, start_date=None, max_results=10, stop_event=None):
        if not self._ensure_anthology():
            return []
            
        self.logger.info(f"Searching ACL Anthology for: '{query}'")
        
        all_results = []
        limit = 100 if (max_results == float('inf') or max_results is None) else int(max_results)
        
        queries = query.lower().split()
        count = 0
        
        try:
            # The library allows iterating over all papers
            # For 0.5.x, Anthology.papers() or Anthology.collections etc.
            # We iterate collections -> volumes -> papers for exhaustive search
            # Optimization: Iterate volumes by year DESCENDING
            all_volumes = []
            for collection in self.anthology.collections.values():
                all_volumes.extend(list(collection.volumes()))

            
            # Sort volumes: newest first
            # volume.year is typically a string "2023"
            all_volumes.sort(key=lambda v: int(v.year) if v.year and v.year.isdigit() else 0, reverse=True)

            for volume in all_volumes:
                if stop_event and stop_event.is_set():
                    break
                if count >= limit:
                    break
                    
                # Year filtering
                if start_date:
                    try:
                        vol_year = int(volume.year)
                        if vol_year < start_date.year:
                            continue
                    except:
                        pass # Scan if year parsing fails
                
                for paper in volume.papers():
                    if stop_event and stop_event.is_set():
                        break
                    if count >= limit:
                        break
                        
                    title = paper.title.text if hasattr(paper.title, 'text') else str(paper.title)
                    title_lower = title.lower()
                    
                    # Abstract might be available
                    abstract = ""
                    if paper.abstract:
                        abstract = paper.abstract.text if hasattr(paper.abstract, 'text') else str(paper.abstract)
                    abstract_lower = abstract.lower()
                    
                    # Language tracking: Detect if paper is English
                    lang_code = 'en'
                    if hasattr(paper, 'language') and paper.language:
                        lang_code = paper.language.lower()
                    else:
                        try:
                            from langdetect import detect
                            lang_code = detect(title + " " + abstract)
                        except:
                            lang_code = 'en' # Default to english


                        # Keyword matching: Use extracted positive keywords and ANY match (Recall Strategy)
                        # The FilterManager will handle strict boolean logic (Precision Strategy)
                        from src.utils import extract_simple_keywords
                        simple_queries = extract_simple_keywords(query)
                        
                        if count < 5:
                            self.logger.info(f"DEBUG: simple_queries: {simple_queries}")
                            self.logger.info(f"DEBUG: Checking title: '{title_lower}'")
                        
                        # Match if ANY keyword is present (high recall)
                        # If no valid keywords extracted (e.g. only stopwords), we might skip or match all?
                        # Let's assume there's at least one term.
                        if not simple_queries or any(q in title_lower or q in abstract_lower for q in simple_queries):
                            if count < 5:
                                self.logger.info("DEBUG: MATCHED!")
                            # Map authors using as_first_last() for clean strings
                            authors = ", ".join([person.name.as_first_last() for person in paper.authors])
                            
                            # Published date
                            pub_year = volume.year
                            pub_date_str = f"{pub_year}-01-01"
                            
                            paper_meta = {
                                'id': paper.full_id,
                                'title': title,
                                'published_date': pub_date_str,
                                'authors': authors,
                                'abstract': abstract,
                                'source_url': f"https://aclanthology.org/{paper.full_id}",
                                'pdf_url': f"https://aclanthology.org/{paper.full_id}.pdf",
                                'source': self.source_name,
                                'is_preprint': False,
                                'language': lang_code
                            }
                            
                            all_results.append(paper_meta)
                            count += 1
                            
        except Exception as e:
            self.logger.error(f"Error during ACL search: {e}")
            
        self.logger.info(f"Found {len(all_results)} papers in ACL Anthology.")
        return all_results

    def download(self, paper_meta):
        pdf_url = paper_meta.get('pdf_url')
        if not pdf_url:
            return None

        import requests
        import time

        filename = sanitize_filename(paper_meta['title'], extension=".pdf")
        category = classify_paper(paper_meta['title'], paper_meta.get('abstract', ''), paper_meta.get('authors', ''))
        category_safe = sanitize_filename(category, extension="")
        
        save_dir = os.path.join(self.download_dir, category_safe)
        os.makedirs(save_dir, exist_ok=True)
        filepath = os.path.join(save_dir, filename)

        if os.path.exists(filepath):
            return filepath

        try:
            self.logger.info(f"Downloading ACL PDF: {pdf_url}")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            response = requests.get(pdf_url, headers=headers, stream=True, timeout=30)
            if response.status_code == 200:
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                return filepath
            else:
                self.logger.error(f"Failed to download ACL PDF. Status: {response.status_code}")
                return None
        except Exception as e:
            self.logger.error(f"Error downloading ACL PDF: {e}")
            return None
