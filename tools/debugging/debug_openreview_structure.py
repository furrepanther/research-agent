import sys
import os
import openreview
sys.path.append(os.getcwd())

def debug_structure():
    try:
        client = openreview.api.OpenReviewClient(baseurl='https://api2.openreview.net')
        print("Client initialized.")
        
        query = "AI Safety"
        # Try searching specifically in title to avoid reviews
        print(f"Searching for '{query}' with content='title'...")
        
        notes = client.search_notes(term=query, content='title', limit=5)
        print(f"Found {len(notes)} notes.")
        
        for i, note in enumerate(notes):
            print(f"\n--- Note {i+1} ---")
            print(f"ID: {note.id}")
            print(f"Forum: {getattr(note, 'forum', 'N/A')}")
            print(f"ReplyTo: {getattr(note, 'replyto', 'N/A')}")
            
            is_top_level = (note.id == getattr(note, 'forum', None))
            print(f"Is Top Level? {is_top_level}")

            if 'title' in note.content:
                print(f"Title raw: {note.content['title']}")
            else:
                print("No 'title' key in content")
                # Look for other potential title keys
                for k in note.content.keys():
                    if 'title' in k.lower():
                        print(f"Found partial match key '{k}': {note.content[k]}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_structure()
