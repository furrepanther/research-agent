from sickle import Sickle
import requests

def test_aaai_oai():
    # AAAI OJS OAI-PMH endpoint
    url = "https://ojs.aaai.org/index.php/AAAI/oai"
    
    print(f"Testing AAAI OAI-PMH at: {url}")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        sickle = Sickle(url, headers=headers)
        
        # 1. Identify
        identity = sickle.Identify()
        print(f"Repository Name: {identity.repositoryName}")
        print(f"Protocol Version: {identity.protocolVersion}")
        
        # 2. List Sets (to find AAAI conference sets)
        print("\nFetching sets...")
        sets = sickle.ListSets()
        for i, s in enumerate(sets):
            print(f"- {s.setName} ({s.setSpec})")
            if i > 10: 
                print("... truncated")
                break
                
        # 3. List Records (get a few samples)
        print("\nFetching recent records...")
        records = sickle.ListRecords(metadataPrefix='oai_dc', ignore_deleted=True)
        for i, record in enumerate(records):
            metadata = record.metadata
            print(f"\nRecord {i+1}:")
            print(f"Title: {metadata.get('title', ['No Title'])[0]}")
            print(f"Creator: {', '.join(metadata.get('creator', []))}")
            print(f"Date: {metadata.get('date', ['No Date'])[0]}")
            print(f"Language: {metadata.get('language', ['No Lang'])[0]}")
            print(f"Identifiers: {metadata.get('identifier', [])}")
            print(f"Abstract (truncated): {metadata.get('description', ['No Abstract'])[0][:200]}...")
            
            # Try to find landing page URL
            landing_url = None
            for idx in metadata.get('identifier', []):
                if 'article/view/' in idx:
                    landing_url = idx
                    break
            
            if landing_url:
                print(f"Landing Page: {landing_url}")
                # Test PDF pattern guessing
                article_id = landing_url.split('/')[-1]
                pdf_url = landing_url.replace('/view/', '/download/') + f"/{article_id}"
                print(f"Guessed PDF URL: {pdf_url}")
                
            if i >= 4: break
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_aaai_oai()
