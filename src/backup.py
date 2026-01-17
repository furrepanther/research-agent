"""
Backup Manager - Creates compressed backups of cloud storage.
"""
import os
import zipfile
from datetime import datetime
from pathlib import Path
from src.utils import logger
import tkinter as tk
from tkinter import filedialog, messagebox

class BackupManager:
    def __init__(self, config):
        self.config = config
        cloud_config = config.get("cloud_storage", {})
        self.cloud_dir = cloud_config.get("path", "R:/MyDrive/03 Research Papers")
        self.enabled = cloud_config.get("backup_enabled", True)
        
    def select_backup_directory(self):
        """Ask user to select backup directory"""
        root = tk.Tk()
        root.withdraw()
        
        # Use configured backup path as initial directory if available
        cloud_config = self.config.get("cloud_storage", {})
        initial_dir = cloud_config.get("backup_path", os.path.expanduser("~"))
        
        backup_dir = filedialog.askdirectory(
            title="Select Backup Directory",
            initialdir=initial_dir if initial_dir else os.path.expanduser("~")
        )
        
        root.destroy()
        return backup_dir
    
    def create_backup(self, backup_dir=None, progress_callback=None):
        """Create compressed ZIP backup of cloud storage
        
        Args:
            backup_dir: Directory to save backup (asks user if None)
            progress_callback: Function to call with progress updates (filename, current, total)
            
        Returns:
            Path to backup file or None if failed
        """
        if not self.enabled:
            logger.info("Backup disabled in config")
            return None
            
        if not os.path.exists(self.cloud_dir):
            logger.error(f"Cloud directory does not exist: {self.cloud_dir}")
            return None
        
        # Ask for backup directory if not provided
        if not backup_dir:
            backup_dir = self.select_backup_directory()
            if not backup_dir:
                logger.info("Backup cancelled by user")
                return None
        
        # Create backup filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"research_papers_backup_{timestamp}.zip"
        backup_path = os.path.join(backup_dir, backup_filename)
        
        logger.info(f"Creating backup: {backup_path}")
        
        try:
            # Count total files for progress
            total_files = sum(1 for _, _, files in os.walk(self.cloud_dir) for f in files if f.endswith('.pdf'))
            current_file = 0
            
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(self.cloud_dir):
                    for file in files:
                        if not file.endswith('.pdf'):
                            continue
                            
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, self.cloud_dir)
                        
                        zipf.write(file_path, arcname)
                        current_file += 1
                        
                        if progress_callback:
                            progress_callback(file, current_file, total_files)
                        
                        if current_file % 100 == 0:
                            logger.info(f"Backed up {current_file}/{total_files} files...")
            
            backup_size = os.path.getsize(backup_path) / 1024 / 1024  # MB
            logger.info(f"Backup complete: {backup_path} ({backup_size:.2f} MB)")
            
            # Show success message
            root = tk.Tk()
            root.withdraw()
            messagebox.showinfo(
                "Backup Complete",
                f"Backup created successfully!\n\nLocation: {backup_path}\nSize: {backup_size:.2f} MB\nFiles: {total_files}"
            )
            root.destroy()
            
            return backup_path
            
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            
            # Show error message
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Backup Failed", f"Failed to create backup:\n{str(e)}")
            root.destroy()
            
            return None
