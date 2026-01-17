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
        
        # Determine backup directory
        cloud_config = self.config.get("cloud_storage", {})
        backup_dir = cloud_config.get("backup_path", "")
        
        # If no path configured, default to Documents
        if not backup_dir:
            backup_dir = os.path.join(os.path.expanduser("~"), "Documents")
            
        # Confirm with user
        root = tk.Tk()
        root.withdraw()
        if not messagebox.askyesno("Start Backup", f"Create backup of Research Library and Database?\n\nTarget: {backup_dir}"):
            root.destroy()
            return None
        root.destroy()
        
        # Ensure backup directory exists
        try:
            os.makedirs(backup_dir, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create backup directory: {e}")
            messagebox.showerror("Error", f"Could not create backup directory:\n{backup_dir}\n\nError: {e}")
            return None

        # Create backup filename with timestamp (MMDDYY.ss)
        timestamp = datetime.now().strftime("%m%d%y.%S")
        backup_filename = f"Research_Backup_{timestamp}.zip"
        backup_path = os.path.join(backup_dir, backup_filename)
        
        logger.info(f"Creating backup: {backup_path}")
        
        try:
            # Count total files for progress (Cloud Dir + Database)
            file_count = sum(1 for _, _, files in os.walk(self.cloud_dir) for f in files)
            db_path = self.config.get("db_path")
            if db_path and os.path.exists(db_path):
                file_count += 1
            
            current_file = 0
            
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # 1. Backup Cloud Directory (Recursive)
                for root, dirs, files in os.walk(self.cloud_dir):
                    for file in files:
                        # Skip temporary or system files if needed, but generally keep everything
                        if file.startswith('~$') or file == 'Thumbs.db':
                            continue
                            
                        file_path = os.path.join(root, file)
                        # Create relative path for zip (preserve folder structure)
                        arcname = os.path.join("Library", os.path.relpath(file_path, self.cloud_dir))
                        
                        try:
                            zipf.write(file_path, arcname)
                            current_file += 1
                            
                            if progress_callback:
                                progress_callback(file, current_file, file_count)
                            
                            if current_file % 100 == 0:
                                logger.info(f"Backed up {current_file}/{file_count} files...")
                        except Exception as fw_err:
                            logger.warn(f"Failed to add file {file}: {fw_err}")

                # 2. Backup Database
                if db_path and os.path.exists(db_path):
                    logger.info(f"Backing up database: {db_path}")
                    try:
                        # Add to root of zip
                        zipf.write(db_path, os.path.basename(db_path))
                        current_file += 1
                        if progress_callback:
                            progress_callback("database", current_file, file_count)
                    except Exception as db_err:
                        logger.error(f"Failed to backup database: {db_err}")
            
            backup_size = os.path.getsize(backup_path) / 1024 / 1024  # MB
            logger.info(f"Backup complete: {backup_path} ({backup_size:.2f} MB)")
            
            # Show success message
            root = tk.Tk()
            root.withdraw()
            messagebox.showinfo(
                "Backup Complete",
                f"Backup created successfully!\n\nLocation: {backup_path}\nSize: {backup_size:.2f} MB\nFiles: {current_file}"
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
