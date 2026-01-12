from src.searchers.lab_scraper import LabScraper
from src.utils import logger
import logging
import os

# Setup basic logging to console
logging.basicConfig(level=logging.INFO)

config = {"papers_dir": "data/test_papers"}
scraper = LabScraper(config)

# Specifically test Mistral/Scrape
print("Testing Mistral Scraper...")
labs = [s for s in scraper.lab_sources if s['name'] == 'Mistral']
if labs:
    results = scraper._process_scrape(labs[0], None)
    print(f"Found {len(results)} Mistral articles.")
else:
    print("Mistral source not found!")

print("\nTesting Google Research RSS...")
g_labs = [s for s in scraper.lab_sources if s['name'] == 'Google Research']
if g_labs:
    results = scraper._process_rss(g_labs[0], None)
    print(f"Found {len(results)} Google Research articles.")
    for r in results[:3]:
        print(f"- {r['title']} ({r['source_url']})")
    
    if results:
        print("\nTesting PDF Download (Browser Extraction)...")
        filepath = scraper.download(results[0])
        if filepath and os.path.exists(filepath):
            print(f"SUCCESS: PDF saved to {filepath}")
        else:
            print("FAILED: PDF not saved.")

