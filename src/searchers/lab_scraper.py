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
from src.classifier import classify_paper

class LabScraper(BaseSearcher):
    def __init__(self, config):
        super().__init__(config)
        self.source_name = "labs"
        
        # Prefer staging dir if configured, otherwise use papers_dir
        base_dir = config.get("staging_dir", config.get("papers_dir", "data/papers"))
        
        self.download_dir = base_dir
        os.makedirs(self.download_dir, exist_ok=True)

        self.browser = None
        self.playwright = None
        self.monitor_page = None
        self.index_path = os.path.abspath("index.html")
        self.active_pages = []  # Track active pages for cleanup

        # Research page indicators
        self.research_url_patterns = [
            '/research', '/publications', '/papers', '/blog/research',
            '/science', '/technical', '/ai-research', '/publication'
        ]
        
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
        self.browser = self.playwright.chromium.launch(
            headless=True
        )
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
            # Close all active pages first
            for page in self.active_pages:
                try:
                    if not page.is_closed():
                        page.close()
                except Exception:
                    pass
            self.active_pages = []

            # Close browser
            self.browser.close()
            self.playwright.stop()
            self.browser = None
            self.playwright = None

    def _cleanup_stale_pages(self):
        """Close any pages that should have been closed"""
        for page in self.active_pages[:]:
            try:
                if page.is_closed():
                    self.active_pages.remove(page)
            except Exception:
                self.active_pages.remove(page)

    def _apply_stealth(self, page):
        """Applies stealth to the page, handling various library versions."""
        try:
            # Fixed stealth import
            from playwright_stealth import stealth
            stealth(page)
        except Exception as e:
            self.logger.warning(f"Stealth could not be applied: {e}")

    def _find_research_page_url(self, base_url, html_content):
        """
        Find research/publications page URL from the homepage.
        Returns the research page URL or None if not found.
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # Look for navigation links containing research keywords
            nav_links = soup.find_all('a', href=True)

            for link in nav_links:
                href = link.get('href', '')
                text = link.get_text(strip=True).lower()

                # Check if URL or link text indicates a research page
                for pattern in self.research_url_patterns:
                    if pattern in href.lower() or any(
                        keyword in text for keyword in ['research', 'publications', 'papers']
                    ):
                        # Build full URL
                        if href.startswith('http'):
                            return href
                        else:
                            from urllib.parse import urljoin
                            return urljoin(base_url, href)

            return None
        except Exception as e:
            self.logger.warning(f"Error finding research page: {e}")
            return None

    def _find_paper_pdf_link(self, page_url, html_content):
        """
        Find direct PDF link or "Read the Paper" button on a page.
        Returns (pdf_url, method) tuple where method is 'direct' or 'button'.
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # 1. Look for direct PDF links
            pdf_links = soup.find_all('a', href=re.compile(r'\.pdf$', re.I))
            if pdf_links:
                pdf_url = pdf_links[0].get('href')
                if not pdf_url.startswith('http'):
                    from urllib.parse import urljoin
                    pdf_url = urljoin(page_url, pdf_url)
                return (pdf_url, 'direct')

            # 2. Look for "Read the Paper" or "View Paper" buttons/links
            paper_buttons = soup.find_all(
                ['a', 'button'],
                text=re.compile(r'read (the )?paper|view paper|download paper', re.I)
            )

            if not paper_buttons:
                # Also check for links with these phrases in aria-label or title
                paper_buttons = soup.find_all(
                    'a',
                    attrs={'aria-label': re.compile(r'paper|pdf', re.I)}
                )

            if paper_buttons:
                # Return the URL or indication that we need to click
                button_url = paper_buttons[0].get('href')
                if button_url:
                    if not button_url.startswith('http'):
                        from urllib.parse import urljoin
                        button_url = urljoin(page_url, button_url)
                    return (button_url, 'button')

            return (None, None)
        except Exception as e:
            self.logger.warning(f"Error finding PDF link: {e}")
            return (None, None)

    def _click_and_get_paper(self, page_url):
        """
        Navigate to a page, click "Read the Paper" button if present,
        and try to extract the PDF URL or content.
        """
        self._init_browser()
        page = self.context.new_page()
        self._apply_stealth(page)

        try:
            self.logger.info(f"Navigating to {page_url}")
            page.goto(page_url, timeout=60000, wait_until="domcontentloaded")
            time.sleep(2)

            # Look for "Read the Paper" button
            button_selectors = [
                'a:has-text("Read the Paper")',
                'a:has-text("View Paper")',
                'a:has-text("Download Paper")',
                'button:has-text("Read the Paper")',
                'a[href*=".pdf"]'
            ]

            pdf_url = None
            for selector in button_selectors:
                try:
                    element = page.locator(selector).first
                    if element.count() > 0:
                        # Check if it's a link with href
                        href = element.get_attribute('href')
                        if href:
                            if href.endswith('.pdf'):
                                pdf_url = href if href.startswith('http') else page.url + href
                                break
                            else:
                                # Click and see if we get redirected to PDF
                                element.click(timeout=5000)
                                time.sleep(2)

                                # Check if URL changed to PDF
                                current_url = page.url
                                if current_url.endswith('.pdf'):
                                    pdf_url = current_url
                                    break
                except Exception as e:
                    self.logger.debug(f"Selector {selector} not found or failed: {e}")
                    continue

            if not pdf_url:
                # Fallback: check page content for PDF links
                content = page.content()
                pdf_url, _ = self._find_paper_pdf_link(page.url, content)

            return pdf_url

        except Exception as e:
            self.logger.error(f"Error clicking paper button: {e}")
            return None
        finally:
            page.close()

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
                    lab_papers = self._process_rss(lab, start_date, stop_event)
                elif lab["type"] == "scrape":
                    lab_papers = self._process_scrape(lab, start_date, stop_event)
                
                all_papers.extend(lab_papers)
        finally:
            # Explicitly close browser after search phase to free up resources
            self._close_browser()
            
        self.logger.info(f"Found {len(all_papers)} total papers from AI Labs.")
        return all_papers[:max_results]

    def _process_rss(self, lab, start_date=None, stop_event=None):
        papers = []
        try:
            feed = feedparser.parse(lab["url"])
            for entry in feed.entries:
                if stop_event and stop_event.is_set():
                    break
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
                    'abstract': self._clean_lab_abstract(BeautifulSoup(summary, 'html.parser').get_text(separator=' ', strip=True), title)[:1000] + "...",
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

    def _clean_lab_abstract(self, text, title=""):
        """Cleans up RSS abstracts/summaries that contain metadata garbage."""
        if not text: return ""
        
        # 1. Strip Date (e.g. Jan 9, 2026) - Common in Anthropic/OpenAI feeds
        text = re.sub(r'^[A-Z][a-z]{2}\s\d{1,2},\s\d{4}\s*', '', text)
        
        # 2. Strip common lab categories
        categories = ["Alignment", "Interpretability", "Societal Impacts", "Economic Research", "Research", "Safety", "Product", "Announcements"]
        for cat in categories:
            if text.startswith(cat):
                # Replace "CategoryCategory" or "Category "
                text = re.sub(f'^{cat}\s*', '', text)
        
        # 3. Strip Title repetition (case insensitive check)
        # Often the abstract starts with the Title
        if title and len(title) > 5:
            # Normalize for comparison
            if text.lower().startswith(title.lower()):
                text = text[len(title):].strip()
                # Remove leading colons or hyphens left over ": Situating..."
                text = re.sub(r'^[:\-\s]+', '', text)
                
        return text.strip()

    def _process_scrape(self, lab, start_date=None, stop_event=None):
        self.logger.info(f"Scraping {lab['name']} with browser...")

        # Check stop event before long operation
        if stop_event and stop_event.is_set():
            return []

        # Fetch homepage
        html = self._fetch_page_content(lab['url'])
        if not html:
            return []

        # Try to find research-specific page
        research_url = self._find_research_page_url(lab['url'], html)
        if research_url and research_url != lab['url']:
            self.logger.info(f"Found research page for {lab['name']}: {research_url}")
            research_html = self._fetch_page_content(research_url)
            if research_html:
                html = research_html  # Use research page content instead
                lab['url'] = research_url  # Update base URL for link resolution

        papers = []
        try:
            soup = BeautifulSoup(html, 'html.parser')
            articles = soup.select(lab.get("selector", "article"))
            if not articles:
                articles = soup.find_all('a', href=re.compile(r'/news/|/blog/|/research/|/publication'))

            for art in articles:
                if stop_event and stop_event.is_set():
                    break
                title_tag = art.find(['h1', 'h2', 'h3', 'a', 'span'], class_=re.compile(r'title|heading|text-xl', re.I)) or \
                            art.find(['h1', 'h2', 'h3', 'a']) or \
                            (art if art.name in ['h1', 'h2', 'h3'] else None)

                if not title_tag:
                    if art.name == 'a':
                        title = art.get_text(separator=' ', strip=True)
                    else:
                        continue
                else:
                    title = title_tag.get_text(separator=' ', strip=True)

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

                # Try to find PDF link directly
                pdf_url = None
                try:
                    # Check if the article element itself contains a PDF link
                    pdf_link = art.find('a', href=re.compile(r'\.pdf$', re.I))
                    if pdf_link:
                        pdf_url = pdf_link.get('href')
                        if not pdf_url.startswith('http'):
                            from urllib.parse import urljoin
                            pdf_url = urljoin(lab['url'], pdf_url)
                except Exception as e:
                    self.logger.debug(f"No direct PDF link found: {e}")

                paper_meta = {
                    'id': link,
                    'title': title,
                    'published_date': datetime.now().strftime("%Y-%m-%d"),
                    'authors': lab['name'],
                    'abstract': "",
                    'source_url': link,
                    'pdf_url': pdf_url,  # May be None, will be resolved during download
                    'source': f"labs_{lab['name'].lower()}",
                    'is_preprint': False,
                    'html_content': None
                }
                papers.append(paper_meta)
        except Exception as e:
            self.logger.error(f"Error scraping {lab['name']}: {e}")
        return papers

    def download(self, paper_meta):
        # Clean title for filename - Title Case, no underscores, Windows safe
        filename = sanitize_filename(paper_meta['title'], extension=".pdf")
        
        # CATEGORIZATION
        category = classify_paper(paper_meta['title'], paper_meta.get('abstract', ''), paper_meta.get('authors', ''))
        category_safe = sanitize_filename(category, extension="")
        
        save_dir = os.path.join(self.download_dir, category_safe)
        os.makedirs(save_dir, exist_ok=True)
        
        filepath = os.path.join(save_dir, filename)

        if os.path.exists(filepath):
            return filepath

        # Strategy 1: Direct PDF URL (already found during scraping)
        pdf_url = paper_meta.get('pdf_url')
        if pdf_url:
            try:
                self.logger.info(f"Downloading direct PDF from {pdf_url}")
                response = requests.get(pdf_url, timeout=30, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                if response.status_code == 200 and response.headers.get('content-type', '').startswith('application/pdf'):
                    with open(filepath, 'wb') as f:
                        f.write(response.content)
                    self.logger.info(f"Successfully downloaded PDF: {filepath}")
                    return filepath
            except Exception as e:
                self.logger.warning(f"Failed to download direct PDF: {e}")

        # Strategy 2: Try to click "Read the Paper" button and get PDF
        try:
            pdf_url = self._click_and_get_paper(paper_meta['source_url'])
            if pdf_url:
                self.logger.info(f"Found PDF via button click: {pdf_url}")
                response = requests.get(pdf_url, timeout=30, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                if response.status_code == 200:
                    with open(filepath, 'wb') as f:
                        f.write(response.content)
                    self.logger.info(f"Successfully downloaded PDF from button: {filepath}")
                    return filepath
        except Exception as e:
            self.logger.warning(f"Failed to get PDF via button click: {e}")

        # Strategy 3: Fallback to HTML-to-PDF conversion
        try:
            self.logger.info(f"Falling back to HTML-to-PDF conversion for {paper_meta['title'][:50]}...")
            html_content = paper_meta.get('html_content')
            if not html_content:
                html_content = self._fetch_page_content(paper_meta['source_url'])
                if not html_content:
                    return None

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
            self.logger.info(f"Successfully created HTML-to-PDF: {filepath}")
            return filepath
        except Exception as e:
            self.logger.error(f"Error saving lab PDF: {e}")
            return None
        finally:
            # Always close the browser process to prevent stray headless instances
            self._close_browser()
