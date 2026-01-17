import os
import shutil
import time
from src.utils import get_config, logger

def get_staging_path():
    """Get the configured staging path."""
    config = get_config()
    return config.get("staging_dir", None)

def prepare_staging():
    """
    Ensures the staging directory exists and is empty properly.
    Returns the path if successful, None otherwise.
    """
    path = get_staging_path()
    if not path:
        return None

    logger.info(f"Preparing staging directory: {path}")

    try:
        if os.path.exists(path):
            # Try to remove contents
            shutil.rmtree(path)
            time.sleep(0.5) # Give OS a moment to release locks
        
        os.makedirs(path, exist_ok=True)
        return path
    except Exception as e:
        logger.error(f"Failed to prepare staging directory {path}: {e}")
        return None

def cleanup_staging():
    """
    Removes the staging directory and its contents.
    """
    path = get_staging_path()
    if not path:
        return

    logger.info(f"Cleaning up staging directory: {path}")
    
    try:
        if os.path.exists(path):
            shutil.rmtree(path)
    except Exception as e:
        logger.error(f"Failed to cleanup staging directory {path}: {e}")
