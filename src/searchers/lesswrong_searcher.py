from .base import BaseSearcher
import requests
import os
import re
from datetime import datetime, timezone
from src.utils import sanitize_filename
from src.classifier import classify_paper
from bs4 import BeautifulSoup

class LessWrongSearcher(BaseSearcher):
    def __init__(self, config):
        super().__init__(config)
        self.source_name = "lesswrong"
        
        # Prefer staging dir if configured, otherwise use papers_dir
        base_dir = config.get("staging_dir", config.get("papers_dir", "data/papers"))
        self.download_dir = base_dir
        
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
        
        # Define strict taxonomy keywords (matching ArXiv query)
        required_keywords = [
            "agentic", "ai safety", "ai alignment", "consciousness", 
            "personhood", "persona", "future ai", "red team", "red teaming", 
            "taxonomy", "alignment", "safety"
        ]
        
        # Trusted authors/organizations (known for quality AI safety content)
        # This list focuses on established researchers, organizations, and recognized contributors
        trusted_authors = [
            # Organizations & Labs
            "Anthropic", "OpenAI", "DeepMind", "Alignment Research Center", 
            "MIRI", "Machine Intelligence Research Institute", "Redwood Research",
            "AI Safety Camp", "Center for AI Safety", "FAR AI",
            
            # Established Researchers & Authors
            "Eliezer Yudkowsky", "Paul Christiano", "Rohin Shah", "Buck Shlegeris",
            "Evan Hubinger", "Chris Olah", "Ajeya Cotra", "Holden Karnofsky",
            "Nate Soares", "Scott Alexander", "Zvi Mowshowitz", "Gwern",
            "Jacob Steinhardt", "Dan Hendrycks", "Ethan Perez", "Sam Bowman",
            "Owain Evans", "Stuart Russell", "Max Tegmark", "Nick Bostrom",
            "Katja Grace", "Daniel Kokotajlo", "Richard Ngo", "Victoria Krakovna",
            "Jan Leike", "John Wentworth", "Vanessa Kosoy", "Abram Demski",
            "Scott Garrabrant", "Alex Turner", "Quintin Pope", "Neel Nanda",
            "Steven Byrnes",
            
            # Emerging Authors (reputation built 2023-2026)
            "Lucius Bushnaq", "Marius Hobbhahn", "Fabien Roger", "Lawrence Chan",
            "Jérémy Scheurer", "Ethan Perez", "Nina Rimsky", "Cody Rushing",
            "Garrett Baker", "Mrinank Sharma", "Jared Kaplan", "Sam Marks",
            "Bilal Chughtai", "Adrià Garriga-Alonso", "Nora Belrose", "Curt Tigges",
            "Joseph Miller", "Evan Miyazono", "Akbir Khan", "Jared Quincy Davis",
            
            # Community Contributors (high karma/quality)
            "habryka", "Oliver Habryka", "Raemon", "Ben Pace", "Ruby",
            "Wei Dai", "Kaj Sotala", "Anna Salamon", "Andrew Critch"
        ]
        
        # Convert to lowercase for case-insensitive matching
        trusted_authors_lower = [author.lower() for author in trusted_authors]
        
        for post in posts:
            if stop_event and stop_event.is_set():
                break

            if post is None:
                continue
            
            # Safe access with null checks
            html_body = post.get('htmlBody') if isinstance(post, dict) else None
            if not html_body:
                continue
            
            # Get title for filtering
            title = post.get('title', '').lower() if isinstance(post, dict) else ''
            
            # STRICT FILTERING: Check if title or abstract contains taxonomy keywords
            try:
                soup = BeautifulSoup(html_body, 'html.parser')
                abstract_text = soup.get_text()[:2000].lower()  # First 2000 chars for filtering
            except:
                abstract_text = ""
            
            # Combined text for keyword matching
            combined_text = f"{title} {abstract_text}"
            
            # Must contain at least one taxonomy keyword
            if not any(keyword in combined_text for keyword in required_keywords):
                continue
            
            # Author - safe access (moved up for filtering)
            user_obj = post.get('user') if isinstance(post, dict) else None
            author = "Unknown"
            if user_obj and isinstance(user_obj, dict):
                author = user_obj.get('displayName', 'Unknown')
            
            # TRUSTED AUTHOR FILTER: Only include posts from trusted sources
            author_lower = author.lower()
            if not any(trusted_author in author_lower for trusted_author in trusted_authors_lower):
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

            # Full abstract for storage
            try:
                soup = BeautifulSoup(html_body, 'html.parser')
                abstract_text_full = soup.get_text()[:1000] + "..."
            except:
                abstract_text_full = "Content unavailable"

            # Safe field access
            post_id = post.get('_id', 'unknown')
            title_original = post.get('title', 'Untitled')
            page_url = post.get('pageUrl', '')

            paper_meta = {
                'id': post_id,
                'title': title_original,
                'published_date': (posted_at.split('T')[0] if posted_at else "Unknown") if isinstance(posted_at, str) else "Unknown",
                'authors': author,
                'abstract': abstract_text_full,
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
            
        self.logger.info(f"Fetched {len(results)} filtered posts from LessWrong (from {len(posts)} total).")
        return results

    def download(self, paper_meta):
        # Generate Clean PDF
        html_content = paper_meta.get('html_content')
        if not html_content:
            return None
            
        # Clean title for filename - Title Case, no underscores, Windows safe
        filename = sanitize_filename(paper_meta['title'], extension=".pdf")
        
        # CATEGORIZATION
        category = classify_paper(paper_meta['title'], paper_meta.get('abstract', ''), paper_meta.get('authors', 'Unknown'))
        category_safe = sanitize_filename(category, extension="")
        
        save_dir = os.path.join(self.download_dir, category_safe)
        os.makedirs(save_dir, exist_ok=True)
        
        filepath = os.path.join(save_dir, filename)
        
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
