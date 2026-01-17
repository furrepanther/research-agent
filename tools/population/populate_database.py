"""
Populate database by scanning existing PDFs in cloud storage.
Extracts metadata from PDFs and populates the database.
"""
import os
import sqlite3
from datetime import datetime
from pathlib import Path
import PyPDF2
import re

def extract_pdf_metadata(pdf_path):
    """Extract metadata from PDF file"""
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            
            # Get PDF metadata
            metadata = reader.metadata
            
            # Try to extract title from metadata or first page
            title = None
            if metadata and metadata.title:
                title = metadata.title
            else:
                # Fallback: use filename without extension
                title = Path(pdf_path).stem
            
            # Try to extract publication date from metadata
            pub_date = None
            if metadata and metadata.creation_date:
                pub_date = metadata.creation_date.strftime("%Y-%m-%d")
            
            # Try to extract authors from metadata
            authors = "Unknown"
            if metadata and metadata.author:
                authors = metadata.author
            
            # Try to extract abstract from first page
            abstract = ""
            if len(reader.pages) > 0:
                first_page = reader.pages[0].extract_text()
                # Look for abstract section (simple heuristic)
                abstract_match = re.search(r'Abstract[:\s]+(.*?)(?:\n\n|\nIntroduction|\n1\.)', 
                                          first_page, re.IGNORECASE | re.DOTALL)
                if abstract_match:
                    abstract = abstract_match.group(1).strip()[:1000]  # First 1000 chars
            
            return {
                'title': title,
                'pub_date': pub_date,
                'authors': authors,
                'abstract': abstract
            }
    except Exception as e:
        print(f"Error extracting metadata from {pdf_path}: {e}")
        return None

def get_file_timestamp(filepath):
    """Get file modification timestamp as date string"""
    timestamp = os.path.getmtime(filepath)
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")

def determine_source(category, filename):
    """Determine source based on category folder"""
    category_lower = category.lower()
    
    # Check for specific lab sources
    if 'anthropic' in category_lower:
        return 'labs_anthropic'
    elif 'openai' in category_lower:
        return 'labs_openai'
    elif 'deepmind' in category_lower:
        return 'labs_deepmind'
    elif 'meta' in category_lower:
        return 'labs_meta'
    elif 'google' in category_lower:
        return 'labs_google'
    elif 'microsoft' in category_lower:
        return 'labs_microsoft'
    elif 'mistral' in category_lower:
        return 'labs_mistral'
    elif 'nvidia' in category_lower:
        return 'labs_nvidia'
    elif 'lesswrong' in category_lower or 'less wrong' in category_lower:
        return 'lesswrong'
    else:
        # Default to arxiv for research categories
        return 'arxiv'

def populate_database():
    """Scan cloud storage and populate database"""
    cloud_dir = r'R:\My Drive\03 Research Papers'
    db_path = os.path.join(cloud_dir, 'metadata.db')
    
    print(f"Scanning: {cloud_dir}")
    print(f"Database: {db_path}\n")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    added_count = 0
    error_count = 0
    
    # Walk through all subdirectories
    for root, dirs, files in os.walk(cloud_dir):
        for filename in files:
            if not filename.endswith('.pdf'):
                continue
            
            filepath = os.path.join(root, filename)
            
            # Get category from folder structure
            rel_path = os.path.relpath(root, cloud_dir)
            category = rel_path if rel_path != '.' else 'Uncategorized'
            
            print(f"Processing: {category}/{filename}")
            
            # Extract metadata from PDF
            metadata = extract_pdf_metadata(filepath)
            
            if not metadata:
                error_count += 1
                continue
            
            # Generate unique ID from filename
            paper_id = Path(filename).stem.replace(' ', '_').lower()
            
            # Determine publication date (use metadata or file timestamp)
            pub_date = metadata['pub_date'] or get_file_timestamp(filepath)
            
            # Use publication date as downloaded_date
            downloaded_date = pub_date
            
            # Determine source
            source = determine_source(category, filename)
            
            # Insert into database
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO papers (
                        id, title, published_date, authors, abstract,
                        pdf_path, source_url, downloaded_date, synced_to_cloud, source
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    paper_id,
                    metadata['title'],
                    pub_date,
                    metadata['authors'],
                    metadata['abstract'],
                    filepath,
                    '',  # No source URL for existing files
                    downloaded_date,
                    1,  # Already in cloud storage
                    source
                ))
                
                added_count += 1
                print(f"  ✓ Added: {metadata['title'][:50]}...")
                
            except Exception as e:
                error_count += 1
                print(f"  ✗ Error: {e}")
    
    conn.commit()
    conn.close()
    
    print(f"\n{'='*80}")
    print(f"Database Population Complete")
    print(f"{'='*80}")
    print(f"Papers added: {added_count}")
    print(f"Errors: {error_count}")
    print(f"Database: {db_path}")

if __name__ == "__main__":
    populate_database()
