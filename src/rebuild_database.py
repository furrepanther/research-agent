"""
Database Rebuild Utility - Rebuild production database from cloud storage PDFs

This module provides functionality to scan cloud storage and rebuild the production
database from scratch. Useful for disaster recovery or re-syncing after manual changes.
"""

import os
import hashlib
from datetime import datetime
from pathlib import Path
from src.utils import logger
from src.storage import StorageManager


def generate_paper_hash(title):
    """Generate a stable hash for a paper based on its title"""
    if not title:
        return hashlib.sha256(b"").hexdigest()
    return hashlib.sha256(title.encode('utf-8')).hexdigest()


def extract_metadata_from_filename(filename):
    """
    Extract metadata from PDF filename.
    
    Args:
        filename: PDF filename (without path)
        
    Returns:
        dict with 'title' extracted from filename
    """
    # Remove .pdf extension
    title = filename
    if title.lower().endswith('.pdf'):
        title = title[:-4]
    
    # Title is already in Title Case format from sanitize_filename
    # Just clean up any remaining artifacts
    title = title.strip()
    
    return {'title': title}


def scan_cloud_storage(cloud_dir, progress_callback=None):
    """
    Recursively scan cloud storage directory for PDFs.
    
    Args:
        cloud_dir: Path to cloud storage root directory
        progress_callback: Optional function(message) to report progress
        
    Returns:
        List of dicts with paper metadata
    """
    papers = []
    
    if not os.path.exists(cloud_dir):
        logger.error(f"Cloud directory does not exist: {cloud_dir}")
        return papers
    
    # Walk through all subdirectories
    for root, dirs, files in os.walk(cloud_dir):
        for filename in files:
            if not filename.lower().endswith('.pdf'):
                continue
            
            # Skip special files
            if filename.startswith('.') or filename.startswith('~'):
                continue
            
            # Get full path
            pdf_path = os.path.join(root, filename)
            
            # Extract category from folder structure
            rel_path = os.path.relpath(root, cloud_dir)
            category = rel_path if rel_path != '.' else 'Uncategorized'
            
            # Extract metadata
            metadata = extract_metadata_from_filename(filename)
            title = metadata['title']
            
            # Get file modification time
            try:
                mtime = os.path.getmtime(pdf_path)
                downloaded_date = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
            except:
                downloaded_date = datetime.now().strftime("%Y-%m-%d")
            
            # Create paper entry
            paper = {
                'title': title,
                'paper_hash': generate_paper_hash(title),
                'title_hash': generate_paper_hash(title),  # Same as paper_hash for simplicity
                'published_date': downloaded_date,  # Use file date as published date
                'authors': 'Unknown',
                'abstract': '',
                'pdf_path': pdf_path,
                'source_url': '',
                'downloaded_date': downloaded_date,
                'source': 'cloud_rebuild',
                'synced_to_cloud': 1,
                'language': 'en',
                'category': category
            }
            
            papers.append(paper)
            
            if progress_callback:
                progress_callback(f"Scanned: {filename}")
    
    return papers


def rebuild_database(cloud_dir, db_path, progress_callback=None):
    """
    Rebuild production database from cloud storage.
    
    Args:
        cloud_dir: Path to cloud storage directory
        db_path: Path to production database
        progress_callback: Optional function(message) to report progress
        
    Returns:
        dict with statistics (files_scanned, entries_created, errors)
    """
    stats = {
        'files_scanned': 0,
        'entries_created': 0,
        'errors': 0
    }
    
    if progress_callback:
        progress_callback("Starting database rebuild...")
    
    # Create backup of existing database
    if os.path.exists(db_path):
        backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        try:
            import shutil
            shutil.copy2(db_path, backup_path)
            logger.info(f"Created backup: {backup_path}")
            if progress_callback:
                progress_callback(f"Backup created: {backup_path}")
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            stats['errors'] += 1
            return stats
    
    # Delete existing database
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
            logger.info(f"Deleted old database: {db_path}")
        except Exception as e:
            logger.error(f"Failed to delete old database: {e}")
            stats['errors'] += 1
            return stats
    
    # Initialize new database
    if progress_callback:
        progress_callback("Initializing new database...")
    
    storage = StorageManager(db_path)
    
    # Scan cloud storage
    if progress_callback:
        progress_callback(f"Scanning cloud storage: {cloud_dir}")
    
    papers = scan_cloud_storage(cloud_dir, progress_callback)
    stats['files_scanned'] = len(papers)
    
    logger.info(f"Found {len(papers)} PDFs in cloud storage")
    
    # Add papers to database
    if progress_callback:
        progress_callback(f"Adding {len(papers)} papers to database...")
    
    for i, paper in enumerate(papers):
        try:
            storage.add_paper(paper)
            stats['entries_created'] += 1
            
            if progress_callback and (i + 1) % 100 == 0:
                progress_callback(f"Added {i + 1}/{len(papers)} papers...")
        except Exception as e:
            logger.error(f"Failed to add paper '{paper['title']}': {e}")
            stats['errors'] += 1
    
    if progress_callback:
        progress_callback("Database rebuild complete!")
    
    logger.info(f"Rebuild complete: {stats['entries_created']} entries created, {stats['errors']} errors")
    
    return stats
