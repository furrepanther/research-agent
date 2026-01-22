"""
Document Ingestion System - Process user-provided PDFs

This module handles automatic ingestion of PDFs from a designated folder,
extracting metadata, discovering source URLs, and adding them to the database.
"""

import os
import re
import hashlib
import shutil
from datetime import datetime
from src.utils import logger, sanitize_filename
from langdetect import detect, LangDetectException

try:
    import PyPDF2
except ImportError:
    logger.error("PyPDF2 not installed. Run: pip install PyPDF2")
    raise

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    logger.error("requests or beautifulsoup4 not installed. Run: pip install requests beautifulsoup4")
    raise

try:
    from dateutil import parser as date_parser
except ImportError:
    logger.warning("python-dateutil not installed. Published date extraction from text will be limited.")
    date_parser = None


def scan_ingest_folder(ingest_path):
    """
    Scan ingest folder for PDFs.
    
    Args:
        ingest_path: Path to ingest folder
        
    Returns:
        List of PDF file paths
    """
    if not os.path.exists(ingest_path):
        return []
    
    pdf_files = []
    try:
        for filename in os.listdir(ingest_path):
            if filename.lower().endswith('.pdf'):
                # Skip hidden/temp files
                if filename.startswith('.') or filename.startswith('~'):
                    continue
                pdf_files.append(os.path.join(ingest_path, filename))
    except Exception as e:
        logger.error(f"Error scanning ingest folder: {e}")
    
    return pdf_files


def extract_pdf_metadata(pdf_path):
    """
    Extract metadata from PDF file.
    
    Priority order:
    1. PDF metadata fields
    2. Text extraction from first page
    3. Filename as fallback
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        dict with title, authors, abstract, url, published_date
    """
    metadata = {
        'title': '',
        'authors': 'Unknown',
        'abstract': '',
        'url': '',
        'published_date': None
    }
    
    try:
        with open(pdf_path, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            
            # Try PDF metadata first
            if pdf_reader.metadata:
                if '/Title' in pdf_reader.metadata and pdf_reader.metadata['/Title']:
                    metadata['title'] = pdf_reader.metadata['/Title'].strip()
                if '/Author' in pdf_reader.metadata and pdf_reader.metadata['/Author']:
                    metadata['authors'] = pdf_reader.metadata['/Author'].strip()
                if '/Subject' in pdf_reader.metadata and pdf_reader.metadata['/Subject']:
                    metadata['abstract'] = pdf_reader.metadata['/Subject'].strip()
                # Try to extract creation date as published date
                if '/CreationDate' in pdf_reader.metadata and pdf_reader.metadata['/CreationDate']:
                    try:
                        # PDF dates are in format: D:YYYYMMDDHHmmSS
                        date_str = str(pdf_reader.metadata['/CreationDate'])
                        if date_str.startswith('D:'):
                            date_str = date_str[2:10]  # Extract YYYYMMDD
                            metadata['published_date'] = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                    except Exception as e:
                        logger.debug(f"Could not parse PDF creation date: {e}")
            
            # Extract text from first page for additional metadata
            if len(pdf_reader.pages) > 0:
                first_page_text = pdf_reader.pages[0].extract_text()
                
                # If no title from metadata, try to extract from first page
                if not metadata['title'] and first_page_text:
                    # Look for title (usually first large text block)
                    lines = first_page_text.split('\n')
                    for line in lines[:10]:  # Check first 10 lines
                        line = line.strip()
                        if len(line) > 10 and len(line) < 200:  # Reasonable title length
                            metadata['title'] = line
                            break
                
                # Try to extract abstract
                if not metadata['abstract'] and first_page_text:
                    abstract_match = re.search(
                        r'(?:Abstract|ABSTRACT)[:\s]+(.*?)(?:\n\n|Introduction|INTRODUCTION|1\.|Keywords)',
                        first_page_text,
                        re.DOTALL | re.IGNORECASE
                    )
                    if abstract_match:
                        abstract = abstract_match.group(1).strip()
                        # Limit to ~500 words
                        words = abstract.split()[:500]
                        metadata['abstract'] = ' '.join(words)
                
                # Try to find URL in text
                if first_page_text:
                    url_patterns = [
                        r'https?://arxiv\.org/(?:abs|pdf)/[\w\.]+',
                        r'https?://doi\.org/[\w\./\-]+',
                        r'https?://(?:www\.)?(?:acm|ieee|springer)[\w\./\-]+'
                    ]
                    for pattern in url_patterns:
                        url_match = re.search(pattern, first_page_text)
                        if url_match:
                            metadata['url'] = url_match.group(0)
                            break
                
                # Try to extract published date from text if not in metadata
                if not metadata['published_date'] and first_page_text and date_parser:
                    # Look for common date patterns
                    date_patterns = [
                        r'(?:Published|Submitted|Accepted)[:\s]+([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
                        r'(\d{1,2}\s+[A-Za-z]+\s+\d{4})',
                        r'(\d{4}-\d{2}-\d{2})'
                    ]
                    for pattern in date_patterns:
                        date_match = re.search(pattern, first_page_text[:2000])  # Search first 2000 chars
                        if date_match:
                            try:
                                parsed_date = date_parser.parse(date_match.group(1))
                                metadata['published_date'] = parsed_date.strftime('%Y-%m-%d')
                                break
                            except:
                                continue
    
    except Exception as e:
        logger.error(f"Error extracting PDF metadata from {pdf_path}: {e}")
    
    # Fallback to filename for title
    if not metadata['title']:
        filename = os.path.basename(pdf_path)
        # Case-insensitive PDF extension removal
        metadata['title'] = re.sub(r'\.pdf$', '', filename, flags=re.IGNORECASE).replace('_', ' ').strip()
    
    return metadata


def discover_url_via_search(title, authors):
    """
    Use web search to find source URL for paper.
    
    Args:
        title: Paper title
        authors: Author names
        
    Returns:
        URL string or empty string if not found
    """
    try:
        
        # Construct search query
        query = f'"{title}"'
        if authors and authors != 'Unknown':
            # Add first author name
            first_author = authors.split(',')[0].strip()
            query += f' "{first_author}"'
        query += ' pdf'
        
        # Use DuckDuckGo (no API key needed)
        search_url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(search_url, headers=headers, timeout=10)
        if response.status_code != 200:
            return ''
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for links in search results
        priority_domains = [
            'arxiv.org',
            'dl.acm.org',
            'ieeexplore.ieee.org',
            'scholar.google.com',
            'researchgate.net',
            'academia.edu'
        ]
        
        # Find all result links
        for link in soup.find_all('a', class_='result__a'):
            href = link.get('href', '')
            # Check if it's a priority domain
            for domain in priority_domains:
                if domain in href:
                    logger.info(f"Found URL via search: {href}")
                    return href
        
        # If no priority domain found, return first result
        first_link = soup.find('a', class_='result__a')
        if first_link:
            href = first_link.get('href', '')
            if href:
                logger.info(f"Found URL via search (non-priority): {href}")
                return href
    
    except Exception as e:
        logger.error(f"Error discovering URL via search: {e}")
    
    return ''


def detect_language(text):
    """
    Detect language of text.
    
    Args:
        text: Text to analyze
        
    Returns:
        Language code (e.g., 'en', 'fr') or 'unknown'
    """
    if not text or len(text.strip()) < 50:
        return 'unknown'
    
    try:
        lang = detect(text)
        return lang
    except LangDetectException:
        return 'unknown'


def process_ingested_document(pdf_path, mode, run_id, staging_dir):
    """
    Process a single ingested document.
    
    Args:
        pdf_path: Path to PDF file
        mode: Run mode (TEST, AUTOMATIC, BACKFILL, etc.)
        run_id: Current run ID
        staging_dir: Staging directory for PDFs
        
    Returns:
        dict with paper metadata or None on error
    """
    try:
        # Extract metadata
        metadata = extract_pdf_metadata(pdf_path)
        
        # Discover URL if missing
        if not metadata['url']:
            metadata['url'] = discover_url_via_search(metadata['title'], metadata['authors'])
        
        # Detect language
        text_for_lang = metadata['title'] + ' ' + metadata['abstract']
        language = detect_language(text_for_lang)
        
        # Generate hash
        paper_hash = hashlib.sha256(metadata['title'].encode('utf-8')).hexdigest()
        
        # Determine category based on content (simple heuristic)
        category = 'User Ingested'
        if any(term in metadata['title'].lower() or term in metadata['abstract'].lower() 
               for term in ['alignment', 'safety', 'ethical']):
            category = 'Alignment Research'
        elif any(term in metadata['title'].lower() or term in metadata['abstract'].lower()
                 for term in ['agent', 'agentic', 'multi-agent']):
            category = 'Agentic AI'
        elif any(term in metadata['title'].lower() or term in metadata['abstract'].lower()
                 for term in ['red team', 'jailbreak', 'adversarial']):
            category = 'Red Teaming'
        
        # Copy PDF to staging directory
        filename = sanitize_filename(metadata['title'], extension='.pdf')
        category_dir = os.path.join(staging_dir, category)
        os.makedirs(category_dir, exist_ok=True)
        dest_path = os.path.join(category_dir, filename)
        
        # Check if file already exists in staging
        if os.path.exists(dest_path):
            # File exists but wasn't caught by database check - possible DB inconsistency
            logger.warning(f"File already exists in staging but not in database: {dest_path}")
            logger.warning("This may indicate database is out of sync. Consider running 'Rebuild DB'.")
            # Add timestamp to make filename unique
            base, ext = os.path.splitext(filename)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{base}_{timestamp}{ext}"
            dest_path = os.path.join(category_dir, filename)
        
        try:
            shutil.copy2(pdf_path, dest_path)
        except Exception as e:
            logger.error(f"Failed to copy PDF to staging: {e}")
            raise
        
        # Use extracted published date or default to current date
        current_date = datetime.now().strftime("%Y-%m-%d")
        published_date = metadata.get('published_date') or current_date
        
        # Create paper entry
        paper = {
            'title': metadata['title'],
            'paper_hash': paper_hash,
            'title_hash': paper_hash,
            'published_date': published_date,
            'authors': metadata['authors'],
            'abstract': metadata['abstract'],
            'pdf_path': dest_path,
            'source_url': metadata['url'],
            'downloaded_date': current_date,
            'source': 'user_ingest',
            'synced_to_cloud': 0,
            'language': language,
            'category': category,
            'run_id': run_id
        }
        
        logger.info(f"Processed ingested document: {metadata['title']}")
        return paper
        
    except Exception as e:
        logger.error(f"Error processing ingested document {pdf_path}: {e}")
        return None


def process_ingest_folder(ingest_path, mode, run_id, staging_dir, progress_callback=None):
    """
    Process all documents in ingest folder.
    
    Args:
        ingest_path: Path to ingest folder
        mode: Run mode
        run_id: Current run ID
        staging_dir: Staging directory
        progress_callback: Optional callback for progress updates
        
    Returns:
        dict with stats: {papers, processed, non_english, errors}
    """
    stats = {
        'papers': [],
        'processed': 0,
        'non_english': 0,
        'errors': 0
    }
    
    # Scan for PDFs
    pdf_files = scan_ingest_folder(ingest_path)
    
    if not pdf_files:
        return stats
    
    logger.info(f"Found {len(pdf_files)} documents in ingest folder")
    
    if progress_callback:
        progress_callback({
            'type': 'LOG',
            'text': f"[Ingest] Found {len(pdf_files)} documents to process"
        })
    
    # In TEST mode, just count
    if mode == 'TEST':
        stats['processed'] = len(pdf_files)
        if progress_callback:
            progress_callback({
                'type': 'LOG',
                'text': f"[Ingest] TEST MODE: {len(pdf_files)} documents found (not processed)"
            })
        return stats
    
    # Process each document
    for i, pdf_path in enumerate(pdf_files):
        paper = process_ingested_document(pdf_path, mode, run_id, staging_dir)
        
        if paper:
            stats['papers'].append(paper)
            stats['processed'] += 1
            
            if paper['language'] != 'en':
                stats['non_english'] += 1
            
            if progress_callback:
                progress_callback({
                    'type': 'LOG',
                    'text': f"[Ingest] Processed ({i+1}/{len(pdf_files)}): {paper['title'][:50]}..."
                })
            
            # Move processed file to "processed" subfolder
            try:
                processed_dir = os.path.join(ingest_path, 'processed')
                os.makedirs(processed_dir, exist_ok=True)
                processed_path = os.path.join(processed_dir, os.path.basename(pdf_path))
                shutil.move(pdf_path, processed_path)
                logger.debug(f"Moved processed file to: {processed_path}")
            except Exception as e:
                logger.warning(f"Could not move processed file {pdf_path}: {e}")
                # Continue anyway - file was successfully processed
        else:
            stats['errors'] += 1
    
    logger.info(f"Ingest complete: {stats['processed']} processed, {stats['non_english']} non-English, {stats['errors']} errors")
    
    return stats
