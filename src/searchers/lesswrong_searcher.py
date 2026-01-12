from .base import BaseSearcher
import requests
import os
import re
from datetime import datetime, timezone
from src.utils import sanitize_filename
from bs4 import BeautifulSoup

class LessWrongSearcher(BaseSearcher):
    def __init__(self, config):
        super().__init__(config)
        self.source_name = "lesswrong"
        self.download_dir = os.path.join(config.get("papers_dir", "data/papers"), self.source_name)
        os.makedirs(self.download_dir, exist_ok=True)
        self.api_url = "https://www.lesswrong.com/graphql"

    def search(self, query, start_date=None, max_results=10, stop_event=None):
        self.logger.info(f"Searching LessWrong (fetching recent posts to filter)...")
        
        # LessWrong API doesn't have a simple "search" query in GraphQL easily accessible without Algolia keys.
        # Strategy: Fetch 'new' or 'top' posts and let the Client-Side Filter do the work.
        # We fetch more than max_results to allow for filtering.
        fetch_limit = max_results * 5 
        
        query_ql = """
        query($limit: Int) {
            posts(input: { terms: { view: "new", limit: $limit } }) {
                results {
                    _id
                    title
                    pageUrl
                    postedAt
                    htmlBody
                    user {
                        displayName
                    }
                }
            }
        }
        """
        
        variables = {"limit": fetch_limit}
        
        try:
            if stop_event and stop_event.is_set():
                 return []

            response = requests.post(self.api_url, json={'query': query_ql, 'variables': variables}, timeout=10)
            if response.status_code != 200:
                self.logger.error(f"LessWrong API Error: {response.status_code}")
                return []
                
            data = response.json()
            if data is None:
                 self.logger.error("LessWrong API returned None/Null JSON")
                 return []
                 
            data_inner = data.get('data')
            if data_inner is None:
                 self.logger.error(f"LessWrong GraphQL Error (No 'data' field): {data}")
                 return []
            
            posts_wrapper = data_inner.get('posts') or {}
            posts = posts_wrapper.get('results', [])
            
        except Exception as e:
            self.logger.error(f"Error fetching LessWrong posts: {str(e)}")
            return []

        results = []
        for post in posts:
            if stop_event and stop_event.is_set():
                break

            if post is None:
                continue
            
            # Safe access with null checks
            html_body = post.get('htmlBody') if isinstance(post, dict) else None
            if not html_body:
                continue
            
            # Date Parsing
            posted_at = post.get('postedAt') if isinstance(post, dict) else None
            pub_date = None
            if posted_at:
                try:
                    pub_date = datetime.strptime(posted_at.split('T')[0], "%Y-%m-%d")
                    pub_date = pub_date.replace(tzinfo=timezone.utc)
                except:
                    pass
            
            # Date Filter
            if start_date:
                if start_date.tzinfo is None:
                    start_date = start_date.replace(tzinfo=timezone.utc)
                if pub_date and pub_date < start_date:
                    continue

            # Author - safe access
            user_obj = post.get('user') if isinstance(post, dict) else None
            author = "Unknown"
            if user_obj and isinstance(user_obj, dict):
                author = user_obj.get('displayName', 'Unknown')

            # Abstract (First 500 chars of body text)
            try:
                soup = BeautifulSoup(html_body, 'html.parser')
                abstract_text = soup.get_text()[:1000] + "..."
            except:
                abstract_text = "Content unavailable"

            # Safe field access
            post_id = post.get('_id', 'unknown')
            title = post.get('title', 'Untitled')
            page_url = post.get('pageUrl', '')

            paper_meta = {
                'id': post_id,
                'title': title,
                'published_date': (posted_at.split('T')[0] if posted_at else "Unknown") if isinstance(posted_at, str) else "Unknown",
                'authors': author,
                'abstract': abstract_text,
                'source_url': page_url,
                'pdf_url': None,
                'html_content': html_body,
                'source': self.source_name,
                'is_preprint': False
            }
            
            # Fix absolute URL
            if paper_meta['source_url'] and not paper_meta['source_url'].startswith('http'):
                paper_meta['source_url'] = f"https://www.lesswrong.com{paper_meta['source_url']}"
                
            results.append(paper_meta)
            
        self.logger.info(f"Fetched {len(results)} potential posts from LessWrong.")
        return results

    def download(self, paper_meta):
        # Generate Clean PDF
        html_content = paper_meta.get('html_content')
        if not html_content:
            return None
            
        # Clean title for filename - Title Case, no underscores, Windows safe
        filename = sanitize_filename(paper_meta['title'])
        filepath = os.path.join(self.download_dir, filename)
        
        if os.path.exists(filepath):
            self.logger.info(f"File already exists: {filepath}")
            return filepath
            
        # Clean HTML using BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Header Info
        retrieval_date = datetime.now().strftime("%Y-%m-%d")
        header_text = f"Retrieved from lesswrong.com on {retrieval_date} from URL {paper_meta['source_url']}"
        
        # Simple Styling for PDF
        style = """
        <style>
            @page {
                size: letter;
                margin: 1in;
            }
            body { font-family: Helvetica, sans-serif; line-height: 1.5; font-size: 11pt; }
            h1 { color: #2c3e50; font-size: 18pt; margin-bottom: 0.5em; }
            .meta { color: #666; font-size: 10pt; margin-bottom: 20px; border-bottom: 1px solid #ccc; padding-bottom: 10px; }
            a { color: #2980b9; text-decoration: none; }
            img { max-width: 100%; height: auto; }
            pre { background-color: #f5f5f5; padding: 10px; font-family: monospace; font-size: 10pt; white-space: pre-wrap; }
        </style>
        """
        
        clean_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{paper_meta['title']}</title>
            {style}
        </head>
        <body>
            <div style="font-size: 9pt; color: #555; font-style: italic; margin-bottom: 20px; text-align: center; border-bottom: 1px solid #ddd; padding-bottom: 5px;">
                {header_text}
            </div>
            <h1>{paper_meta['title']}</h1>
            <div class="meta">
                <strong>Author:</strong> {paper_meta['authors']} <br>
                <strong>Date:</strong> {paper_meta['published_date']} <br>
                <strong>Source:</strong> <a href="{paper_meta['source_url']}">{paper_meta['source_url']}</a>
            </div>
            <div class="content">
                {soup.prettify()}
            </div>
        </body>
        </html>
        """
        
        try:
            from xhtml2pdf import pisa
            
            with open(filepath, "wb") as pdf_file:
                pisa_status = pisa.CreatePDF(clean_html, dest=pdf_file)
                
            if pisa_status.err:
                self.logger.error(f"Error generating PDF: {pisa_status.err}")
                return None
                
            self.logger.info(f"Saved Clean PDF: {filename}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"Error saving PDF: {e}")
            return None
