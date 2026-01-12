from .base import BaseSearcher
import feedparser
import requests
import os
import re
import time
from datetime import datetime, timezone
from src.utils import sanitize_filename
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

class LabScraper(BaseSearcher):
    def __init__(self, config):
        super().__init__(config)
        self.source_name = "labs"
        self.download_dir = os.path.join(config.get("papers_dir", "data/papers"), self.source_name)
        os.makedirs(self.download_dir, exist_ok=True)
        
        self.browser = None
        self.playwright = None
        self.monitor_page = None
        self.index_path = os.path.abspath("index.html")
        
        self.lab_sources = [
            {
                "name": "Anthropic",
                "url": "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_research.xml",
                "type": "rss"
            },
            {
                "name": "OpenAI",
                "url": "https://openai.com/news/rss.xml",
                "type": "rss",
                "filter_keywords": ["research", "model", "gpt", "o1", "sora"]
            },
            {
                "name": "DeepMind",
                "url": "https://deepmind.google/blog/rss.xml",
                "type": "rss",
                "filter_keywords": ["research", "science", "alpha"]
            },
            {
                "name": "Meta AI",
                "url": "https://ai.meta.com/blog/rss/",
                "type": "rss",
                "filter_keywords": ["research", "llama", "fair"]
            },
            {
                "name": "Google Research",
                "url": "https://blog.google/technology/ai/rss/",
                "type": "rss"
            },
            {
                "name": "Microsoft Research",
                "url": "https://www.microsoft.com/en-us/research/feed/",
                "type": "rss",
                "filter_keywords": ["AI", "Machine Learning", "LLM"]
            },
            {
                "name": "Mistral",
                "url": "https://mistral.ai/news/",
                "type": "scrape",
                "selector": "div.news-card, article, section div a h3",
                "filter_keywords": ["research", "model", "mistral"]
            },
            {
                "name": "NVIDIA",
                "url": "https://blogs.nvidia.com/blog/category/deep-learning/feed/",
                "type": "rss"
            }
        ]

    def _init_browser(self):
        """Initializes the browser and opens the monitor window."""
        if self.browser:
            return
            
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=False)
        self.context = self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        # Open Monitor Window
        self.monitor_page = self.context.new_page()
        file_url = f"file:///{self.index_path.replace('\\', '/')}"
        self.monitor_page.goto(file_url)
        self.logger.info(f"Browser monitor initialized at {file_url}")

    def _close_browser(self):
        if self.browser:
            self.browser.close()
            self.playwright.stop()
            self.browser = None
            self.playwright = None

    def _apply_stealth(self, page):
        """Applies stealth to the page, handling various library versions."""
        try:
            import playwright_stealth
            # Try as a function first
            if callable(getattr(playwright_stealth, "stealth", None)):
                playwright_stealth.stealth(page)
            else:
                # Try importing from sub-module
                from playwright_stealth.stealth import stealth
                stealth(page)
        except Exception as e:
            self.logger.warning(f"Stealth could not be applied: {e}")

    def _fetch_page_content(self, url):
        """Fetch content using a temporary browser window."""
        self._init_browser()
        page = self.context.new_page()
        self._apply_stealth(page)
        
        content = None
        try:
            self.logger.info(f"Opening browser window for: {url}")
            # Use longer timeout for Cloudflare/verification
            page.goto(url, timeout=60000, wait_until="domcontentloaded")
            
            # Wait a few seconds for potential JS rendering or verification
            time.sleep(3) 
            
            content = page.content()
        except Exception as e:
            self.logger.error(f"Error fetching {url} with browser: {e}")
        finally:
            self.logger.info(f"Closing browser window for: {url}")
            page.close()
            
        return content

    def search(self, query, start_date=None, max_results=50, stop_event=None):
        self.logger.info(f"Searching AI Labs for: '{query}'")
        all_papers = []
        
        try:
            for lab in self.lab_sources:
                if stop_event and stop_event.is_set():
                    break
                    
                self.logger.info(f"Checking {lab['name']}...")
                lab_papers = []
                
                if lab["type"] == "rss":
                    lab_papers = self._process_rss(lab, start_date)
                elif lab["type"] == "scrape":
                    lab_papers = self._process_scrape(lab, start_date)
                
                all_papers.extend(lab_papers)
        finally:
            # We DONT close browser here because we might need it for downloads
            pass
            
        self.logger.info(f"Found {len(all_papers)} total papers from AI Labs.")
        return all_papers[:max_results]

    def _process_rss(self, lab, start_date):
        papers = []
        try:
            feed = feedparser.parse(lab["url"])
            for entry in feed.entries:
                title = self._clean_lab_title(entry.get('title', ''))
                summary = entry.get('summary', '') or entry.get('description', '')
                
                if 'filter_keywords' in lab:
                    if not any(k.lower() in (title + summary).lower() for k in lab['filter_keywords']):
                        continue
                
                pub_date = None
                if 'published_parsed' in entry:
                    pub_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                
                # Ensure start_date is timezone aware for comparison
                if start_date and start_date.tzinfo is None:
                    start_date = start_date.replace(tzinfo=timezone.utc)

                if start_date and pub_date and pub_date < start_date:
                    continue
                
                paper_meta = {
                    'id': entry.get('id') or entry.get('link'),
                    'title': title,
                    'published_date': pub_date.strftime("%Y-%m-%d") if pub_date else "Unknown",
                    'authors': lab['name'],
                    'abstract': BeautifulSoup(summary, 'html.parser').get_text()[:1000] + "...",
                    'source_url': entry.get('link'),
                    'pdf_url': None,
                    'source': f"labs_{lab['name'].lower()}",
                    'is_preprint': False,
                    'html_content': None # Will fetch during download if needed
                }
                papers.append(paper_meta)
        except Exception as e:
            self.logger.error(f"Error processing RSS for {lab['name']}: {e}")
        return papers

    def _clean_lab_title(self, title):
        """Cleans up concatenated RSS titles (e.g., Anthropic feeds)."""
        if not title: return ""
        # 1. Strip Date (e.g. Jan 9, 2026)
        title = re.sub(r'^[A-Z][a-z]{2}\s\d{1,2},\s\d{4}', '', title)
        # 2. Strip common lab categories that get glued to the start
        categories = ["Alignment", "Interpretability", "Societal Impacts", "Economic Research", "Research"]
        for cat in categories:
            if title.startswith(cat):
                # Check for double-trigger like "AlignmentAlignment"
                title = re.sub(f'^{cat}+', '', title)
        
        # 3. Strip trailing summary info if it's glued (often starts with 'This paper' or 'We ')
        # This is harder, but we can try to find where a new sentence starts without a space if glued
        # For now, just clean up extra spaces and Title Case it later
        return title.strip()

    def _process_scrape(self, lab, start_date):
        self.logger.info(f"Scraping {lab['name']} with browser...")
        html = self._fetch_page_content(lab['url'])
        if not html:
            return []
            
        papers = []
        try:
            soup = BeautifulSoup(html, 'html.parser')
            articles = soup.select(lab.get("selector", "article"))
            if not articles:
                articles = soup.find_all('a', href=re.compile(r'/news/|/blog/'))
            
            for art in articles:
                title_tag = art.find(['h1', 'h2', 'h3', 'a', 'span'], class_=re.compile(r'title|heading|text-xl', re.I)) or \
                            art.find(['h1', 'h2', 'h3', 'a']) or \
                            (art if art.name in ['h1', 'h2', 'h3'] else None)
                
                if not title_tag:
                    if art.name == 'a':
                        title = art.get_text(strip=True)
                    else:
                        continue
                else:
                    title = title_tag.get_text(strip=True)
                
                if not title or len(title) < 5: continue

                link_tag = art.find('a', href=True) or (art if art.name == 'a' and art.has_attr('href') else None)
                if not link_tag: continue
                
                link = link_tag['href']
                if not link.startswith('http'):
                    from urllib.parse import urljoin
                    link = urljoin(lab['url'], link)
                
                if 'filter_keywords' in lab:
                    if not any(k.lower() in title.lower() for k in lab['filter_keywords']):
                        continue
                
                paper_meta = {
                    'id': link,
                    'title': title,
                    'published_date': datetime.now().strftime("%Y-%m-%d"),
                    'authors': lab['name'],
                    'abstract': "",
                    'source_url': link,
                    'pdf_url': None,
                    'source': f"labs_{lab['name'].lower()}",
                    'is_preprint': False,
                    'html_content': None
                }
                papers.append(paper_meta)
        except Exception as e:
            self.logger.error(f"Error scraping {lab['name']}: {e}")
        return papers

    def download(self, paper_meta):
        html_content = paper_meta.get('html_content')
        if not html_content:
            html_content = self._fetch_page_content(paper_meta['source_url'])
            if not html_content:
                return None
        
        # Clean title for filename - Title Case, no underscores, Windows safe
        filename = sanitize_filename(paper_meta['title'])
        filepath = os.path.join(self.download_dir, filename)
        
        if os.path.exists(filepath):
            return filepath
            
        try:
            from xhtml2pdf import pisa
            soup = BeautifulSoup(html_content, 'html.parser')
            article = soup.find('article') or soup.find('div', class_=re.compile(r'content|post|body')) or soup
            
            retrieval_date = datetime.now().strftime("%Y-%m-%d")
            header_text = f"Retrieved from {paper_meta['source']} on {retrieval_date} from {paper_meta['source_url']}"
            
            clean_html = f"""
            <html>
            <head><style>body {{ font-family: Helvetica; line-height: 1.5; }}</style></head>
            <body>
                <div style="font-size: 8pt; color: gray; border-bottom: 1px solid silver; margin-bottom: 10px;">{header_text}</div>
                <h1>{paper_meta['title']}</h1>
                <div>{article.prettify()}</div>
            </body>
            </html>
            """
            
            with open(filepath, "wb") as f:
                pisa.CreatePDF(clean_html, dest=f)
            return filepath
        except Exception as e:
            self.logger.error(f"Error saving lab PDF: {e}")
            return None
        finally:
            # Optionally close browser if this is the last download, 
            # but workers might call this multiple times.
            pass
