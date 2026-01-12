import sqlite3
import os
from src.utils import logger

class StorageManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS papers (
                id TEXT PRIMARY KEY,
                title TEXT,
                published_date TEXT,
                authors TEXT,
                abstract TEXT,
                pdf_path TEXT,
                source_url TEXT,
                downloaded_date TEXT,
                synced_to_cloud BOOLEAN DEFAULT 0,
                source TEXT
            )
        """)
        
        # Migration: Check if source column exists
        cursor.execute("PRAGMA table_info(papers)")
        columns = [info[1] for info in cursor.fetchall()]
        if 'source' not in columns:
            logger.info("Migrating database: Adding 'source' column")
            cursor.execute("ALTER TABLE papers ADD COLUMN source TEXT DEFAULT 'arxiv'")
            
        conn.commit()
        conn.close()

    def paper_exists(self, paper_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM papers WHERE id = ?", (paper_id,))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists

    def normalize_text(self, text):
        import re
        if not text: return ""
        return re.sub(r'[^a-z0-9]', '', text.lower())

    def is_content_similar(self, text1, text2):
        if not text1 or not text2: return False
        # Normalize
        n1 = self.normalize_text(text1)[:500] # Compare first ~500 chars (approx 5 sentences)
        n2 = self.normalize_text(text2)[:500]
        return n1 == n2

    def add_paper(self, paper_data):
        """
        paper_data: dict containing keys matching table columns
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            # 1. Check for Exact ID Match (Primary Key)
            cursor.execute("SELECT id, source, source_url FROM papers WHERE id = ?", (paper_data['id'],))
            existing = cursor.fetchone()
            
            if existing:
                logger.info(f"Paper ID exists: {paper_data['title']}")
                # Determine if we need to update source
                return self._merge_sources(conn, cursor, existing, paper_data)

            # 2. Check for Content Duplicate (Title + Abstract)
            # We search for exact title match (case-insensitive) first to minimize comparisons
            cursor.execute("SELECT id, title, abstract, source, source_url FROM papers WHERE lower(title) = ?", (paper_data['title'].lower(),))
            candidates = cursor.fetchall()
            
            for candidate in candidates:
                # Check abstract similarity
                if self.is_content_similar(paper_data['abstract'], candidate['abstract']):
                    logger.info(f"Duplicate found by content: '{paper_data['title']}' matches '{candidate['title']}'")
                    return self._merge_sources(conn, cursor, candidate, paper_data)

            # 3. If no duplicates, Insert New
            cursor.execute("""
                INSERT OR IGNORE INTO papers (
                    id, title, published_date, authors, abstract, 
                    pdf_path, source_url, downloaded_date, source, synced_to_cloud
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                paper_data['id'],
                paper_data['title'],
                paper_data['published_date'],
                paper_data['authors'],
                paper_data['abstract'],
                paper_data['pdf_path'],
                paper_data['source_url'],
                paper_data['downloaded_date'],
                paper_data.get('source', 'arxiv'),
                0 # Not synced yet
            ))
            conn.commit()
            if cursor.rowcount > 0:
                logger.info(f"Added paper: {paper_data['title']}")
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"Error adding paper: {e}")
            return False
        finally:
            conn.close()

    def _merge_sources(self, conn, cursor, existing_row, new_data):
        """
        Helper to merge source and source_url fields.
        """
        current_sources = existing_row['source'].split(',') if existing_row['source'] else []
        current_sources = [s.strip() for s in current_sources]
        
        new_source = new_data.get('source')
        updated = False
        
        if new_source and new_source not in current_sources:
            current_sources.append(new_source)
            new_source_str = ", ".join(current_sources)
            
            # Also merge URLs
            current_urls = existing_row['source_url'] if existing_row['source_url'] else ""
            if new_data['source_url'] not in current_urls:
                 new_urls = current_urls + " ; " + new_data['source_url']
            else:
                 new_urls = current_urls
            
            cursor.execute("UPDATE papers SET source = ?, source_url = ? WHERE id = ?", 
                           (new_source_str, new_urls, existing_row['id']))
            conn.commit()
            logger.info(f"Merged source '{new_source}' into existing paper {existing_row['id']}")
            updated = True
            
        return False # Return False because we didn't add a NEW paper, just updated an existing one

    def get_unsynced_papers(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM papers WHERE synced_to_cloud = 0")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def mark_synced(self, paper_ids):
        if not paper_ids:
            return
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        placeholders = ','.join(['?'] * len(paper_ids))
        cursor.execute(f"UPDATE papers SET synced_to_cloud = 1 WHERE id IN ({placeholders})", paper_ids)
        conn.commit()
        conn.close()

    def get_latest_date(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(published_date) FROM papers")
        result = cursor.fetchone()[0]
        conn.close()
        return result

    def rollback_source(self, source, start_time_str):
        """
        Deletes papers added for a specific source after a given time.
        Handles papers with multiple sources by merging strings.
        Returns a list of pdf_paths to be deleted from disk.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 1. Find papers that have THIS source and were added AFTER start_time
        # We use LIKE to catch merged sources
        cursor.execute("SELECT id, source, pdf_path FROM papers WHERE (source = ? OR source LIKE ? OR source LIKE ? OR source LIKE ?) AND downloaded_date >= ?", 
                       (source, f"{source}, %", f"%, {source}", f"%, {source}, %", start_time_str))
        rows = cursor.fetchall()
        
        paths_to_delete = []
        
        for row in rows:
            paper_id = row['id']
            current_source_str = row['source']
            sources = [s.strip() for s in current_source_str.split(',')]
            
            if source in sources:
                if len(sources) == 1:
                    # Only source, delete the whole paper entry and the file
                    paths_to_delete.append(row['pdf_path'])
                    cursor.execute("DELETE FROM papers WHERE id = ?", (paper_id,))
                else:
                    # Multiple sources, just remove THIS source from the list
                    sources.remove(source)
                    new_source_str = ", ".join(sources)
                    cursor.execute("UPDATE papers SET source = ? WHERE id = ?", (new_source_str, paper_id))
        
        conn.commit()
        conn.close()
        # Filter None paths
        return [p for p in paths_to_delete if p]
