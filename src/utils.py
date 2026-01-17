import yaml
import os
import logging
import re
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("research_agent.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def load_config(config_path="config.yaml"):
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found at {config_path}")
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

def ensure_directories(config):
    os.makedirs(config.get("papers_dir", "data/papers"), exist_ok=True)
    os.makedirs(os.path.dirname(config.get("db_path", "data/metadata.db")), exist_ok=True)

def get_config():
    config = load_config()
    ensure_directories(config)
    return config

def to_title_case(text):
    """Converts a string to Title Case based on standard rules."""
    minor_words = {
        'a', 'an', 'the', 'and', 'but', 'for', 'at', 'by', 'from', 'in', 'into', 
        'of', 'off', 'on', 'onto', 'out', 'over', 'up', 'with', 'as', 'to'
    }
    words = text.split()
    if not words:
        return ""
    
    title_words = []
    for i, word in enumerate(words):
        # Remove non-alphanumeric for comparison
        clean_word = re.sub(r'[^a-zA-Z]', '', word).lower()
        if i == 0 or i == len(words) - 1 or clean_word not in minor_words:
            # Capitalize word, preserving interior case (like AGI) if it's already mostly caps?
            # Actually, standard capitalize() lowercases the rest. 
            # Let's be careful with acronyms.
            if word.isupper() and len(word) > 1:
                title_words.append(word)
            else:
                title_words.append(word.capitalize())
        else:
            title_words.append(word.lower())
    return " ".join(title_words)

def normalize_url(url):
    """
    Normalize URL for comparison and deduplication.
    - Forces https (most academic sites use https)
    - Removes trailing slash
    - Removes common tracking params
    - Lowercases domain
    """
    if not url:
        return url

    from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

    # Parse URL
    parsed = urlparse(url)

    # Normalize scheme to https (most academic sites use https now)
    scheme = 'https'

    # Lowercase domain
    netloc = parsed.netloc.lower()

    # Remove trailing slash from path
    path = parsed.path.rstrip('/')

    # Remove tracking parameters
    tracking_params = {'utm_source', 'utm_medium', 'utm_campaign', 'ref', 'source', 'fbclid', 'gclid'}
    if parsed.query:
        query_dict = parse_qs(parsed.query)
        # Remove tracking params
        query_dict = {k: v for k, v in query_dict.items() if k not in tracking_params}
        # Rebuild query string
        query = urlencode(query_dict, doseq=True) if query_dict else ''
    else:
        query = ''

    # Reconstruct URL
    normalized = urlunparse((scheme, netloc, path, '', query, ''))
    return normalized

def sanitize_filename(title, extension=""):
    """Creates a Windows-safe filename using Title Case and removing 'garbage'."""
    # 1. Title Case
    clean_title = to_title_case(title)
    # 2. Windows Safe: No < > : " / \ | ? * and no underscores
    safe_title = re.sub(r'[<>:"/\\|?*_]', ' ', clean_title)
    # 3. No extra spaces
    safe_title = " ".join(safe_title.split())
    # 4. Length limit (under 150 for safety)
    safe_title = safe_title[:150].strip()
    if not safe_title:
        safe_title = "Untitled Paper"
    return f"{safe_title}{extension}"

def clear_directory(directory_path):
    """Safely delete ALL files and folders within a directory without deleting the directory itself."""
    import shutil
    if not os.path.exists(directory_path):
        return
    
    for filename in os.listdir(directory_path):
        file_path = os.path.join(directory_path, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            logger.error(f"Failed to delete {file_path}. Reason: {e}")
