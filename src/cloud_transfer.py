"""
Cloud Transfer Manager - Handles transfer from staging to cloud storage with conflict resolution.
"""
import os
import shutil
import hashlib
from pathlib import Path
from datetime import datetime
from src.utils import logger
import tkinter as tk
from tkinter import messagebox, filedialog

class Conflict:
    """Represents a file conflict between staging and cloud storage"""
    def __init__(self, filename, staging_path, cloud_path, category):
        self.filename = filename
        self.staging_path = staging_path
        self.cloud_path = cloud_path
        self.category = category
        self.staging_size = os.path.getsize(staging_path) if os.path.exists(staging_path) else 0
        self.cloud_size = os.path.getsize(cloud_path) if os.path.exists(cloud_path) else 0
        self.staging_modified = datetime.fromtimestamp(os.path.getmtime(staging_path)) if os.path.exists(staging_path) else None
        self.cloud_modified = datetime.fromtimestamp(os.path.getmtime(cloud_path)) if os.path.exists(cloud_path) else None

class CloudTransferManager:
    def __init__(self, config, working_db_path=None, prod_db_path=None):
        self.staging_dir = config.get("staging_dir", "F:/RESTMP")
        cloud_config = config.get("cloud_storage", {})
        self.cloud_dir = cloud_config.get("path", "R:/MyDrive/03 Research Papers")
        self.enabled = cloud_config.get("enabled", True)
        self.working_db_path = working_db_path
        self.prod_db_path = prod_db_path
        
    def scan_conflicts(self):
        """Scan for files that exist in both staging and cloud storage"""
        conflicts = []
        
        if not os.path.exists(self.staging_dir):
            logger.warning(f"Staging directory does not exist: {self.staging_dir}")
            return conflicts
            
        if not os.path.exists(self.cloud_dir):
            logger.warning(f"Cloud directory does not exist: {self.cloud_dir}")
            return conflicts
        
        # Walk through staging directory
        for root, dirs, files in os.walk(self.staging_dir):
            for filename in files:
                if not filename.endswith('.pdf'):
                    continue
                    
                staging_path = os.path.join(root, filename)
                
                # Get category from folder structure
                rel_path = os.path.relpath(root, self.staging_dir)
                category = rel_path if rel_path != '.' else 'Uncategorized'
                
                # Check if file exists in cloud storage (same category)
                cloud_category_path = os.path.join(self.cloud_dir, category)
                cloud_path = os.path.join(cloud_category_path, filename)
                
                if os.path.exists(cloud_path):
                    conflicts.append(Conflict(filename, staging_path, cloud_path, category))
                    
        logger.info(f"Found {len(conflicts)} potential conflicts")
        return conflicts
    
    def show_diff_dialog(self, conflict):
        """Show dialog with file differences and ask user to confirm overwrite"""
        root = tk.Tk()
        root.withdraw()
        
        message = f"""Conflict Detected: {conflict.filename}

Staging File (F:\\RESTMP\\{conflict.category}\\):
- Size: {conflict.staging_size / 1024 / 1024:.2f} MB
- Modified: {conflict.staging_modified.strftime('%Y-%m-%d %H:%M:%S') if conflict.staging_modified else 'Unknown'}
- Category: {conflict.category}

Cloud File (R:\\MyDrive\\03 Research Papers\\{conflict.category}\\):
- Size: {conflict.cloud_size / 1024 / 1024:.2f} MB
- Modified: {conflict.cloud_modified.strftime('%Y-%m-%d %H:%M:%S') if conflict.cloud_modified else 'Unknown'}
- Category: {conflict.category}

Overwrite the cloud file with the staging file?"""
        
        result = messagebox.askyesnocancel(
            "File Conflict",
            message,
            icon='warning'
        )
        
        root.destroy()
        return result  # True = overwrite, False = skip, None = cancel all
    
    def transfer_folders(self, conflicts_resolution=None):
        """Transfer folders from staging to cloud storage
        
        Args:
            conflicts_resolution: Dict mapping conflict filename to resolution (True=overwrite, False=skip)
        """
        if not self.enabled:
            logger.info("Cloud storage transfer disabled in config")
            return False
            
        conflicts = self.scan_conflicts()
        
        # Handle conflicts
        if conflicts:
            logger.info(f"Processing {len(conflicts)} conflicts...")
            
            for conflict in conflicts:
                # Ask user for each conflict
                result = self.show_diff_dialog(conflict)
                
                if result is None:  # Cancel all
                    logger.info("Transfer cancelled by user")
                    return False
                elif result is True:  # Overwrite
                    logger.info(f"Overwriting cloud file: {conflict.filename}")
                    shutil.copy2(conflict.staging_path, conflict.cloud_path)
                else:  # Skip
                    logger.info(f"Skipping conflict: {conflict.filename}")
        
        # Transfer non-conflicting files
        transferred_count = 0
        for root, dirs, files in os.walk(self.staging_dir):
            for filename in files:
                if not filename.endswith('.pdf'):
                    continue
                    
                staging_path = os.path.join(root, filename)
                
                # Get category
                rel_path = os.path.relpath(root, self.staging_dir)
                category = rel_path if rel_path != '.' else 'Uncategorized'
                
                # Build cloud path
                cloud_category_path = os.path.join(self.cloud_dir, category)
                cloud_path = os.path.join(cloud_category_path, filename)
                
                # Skip if already exists (conflict was handled above)
                if os.path.exists(cloud_path):
                    continue
                
                # Create category folder if needed
                os.makedirs(cloud_category_path, exist_ok=True)
                
                # Move file
                try:
                    shutil.move(staging_path, cloud_path)
                    transferred_count += 1
                    logger.info(f"Transferred: {filename} -> {category}")
                    
                    # --- DATABASE SYNC ---
                    self._sync_to_prod_db(filename, category, cloud_path)
                    
                except Exception as e:
                    logger.error(f"Error transferring {filename}: {e}")
        
        logger.info(f"Transfer complete: {transferred_count} files moved to cloud storage")
        return True
    
    def check_cloud_duplicate(self, title, pdf_filename):
        """Check if a paper already exists in cloud storage by filename
        
        Args:
            title: Paper title
            pdf_filename: Sanitized PDF filename
            
        Returns:
            True if duplicate found in cloud storage
        """
        if not self.enabled or not os.path.exists(self.cloud_dir):
            return False
        
        # Search all category folders for matching filename
        for root, dirs, files in os.walk(self.cloud_dir):
            if pdf_filename in files:
                logger.info(f"Found duplicate in cloud storage: {pdf_filename}")
                return True
                
        return False

    def _sync_to_prod_db(self, filename, category, cloud_path):
        """Syncs the metadata for a transferred file from Working DB to Production DB."""
        if not self.working_db_path or not self.prod_db_path:
            return

        try:
            from src.storage import StorageManager
            import sqlite3
            
            # Read from Working DB (direct query for speed/safety)
            conn = sqlite3.connect(self.working_db_path)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT * FROM papers WHERE pdf_path LIKE ?", (f"%{filename}",))
            row = c.fetchone()
            conn.close()
            
            if row:
                paper_data = dict(row)
                
                # Update path in memory before insert/update
                paper_data['pdf_path'] = cloud_path
                paper_data['synced_to_cloud'] = 1
                
                # Write to Production DB
                prod_store = StorageManager(self.prod_db_path)
                
                # 1. Add (or Merge)
                new_id = prod_store.add_paper(paper_data)
                
                # 2. Force Path Update (Ensure hash exists)
                if 'paper_hash' in paper_data and paper_data['paper_hash']:
                    prod_store.update_pdf_path(paper_data['paper_hash'], cloud_path)
                    logger.info(f"Synced metadata to Production DB: {filename}")
            else:
                pass 

        except Exception as e:
            logger.error(f"Failed to sync database for {filename}: {e}")
