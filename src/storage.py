import sqlite3
import os
from src.utils import logger

class StorageManager:
    # Database schema version - increment when adding new migrations
    CURRENT_VERSION = 2

    def __init__(self, db_path):
        self.db_path = db_path
        self._init_db()

    def _get_schema_version(self, cursor):
        """Get current database schema version."""
        try:
            cursor.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
            result = cursor.fetchone()
            return result[0] if result else 0
        except sqlite3.OperationalError:
            # schema_version table doesn't exist yet
            return 0

    def _set_schema_version(self, cursor, version):
        """Record that a migration version has been applied."""
        cursor.execute("INSERT INTO schema_version (version, applied_at) VALUES (?, datetime('now'))", (version,))

    def _migration_v1_add_source_column(self, cursor):
        """Migration v1: Add 'source' column to papers table."""
        logger.info("Applying migration v1: Adding 'source' column")
        cursor.execute("PRAGMA table_info(papers)")
        columns = [info[1] for info in cursor.fetchall()]
        if 'source' not in columns:
            cursor.execute("ALTER TABLE papers ADD COLUMN source TEXT DEFAULT 'arxiv'")
            logger.info("  - Added 'source' column with default 'arxiv'")
        else:
            logger.info("  - 'source' column already exists, skipping")

    def _migration_v2_create_version_table(self, cursor):
        """Migration v2: Create schema_version tracking table."""
        logger.info("Applying migration v2: Creating schema_version table")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL
            )
        """)
        logger.info("  - Created schema_version table")

    def _run_migrations(self, conn, cursor):
        """Run all pending migrations in order."""
        current_version = self._get_schema_version(cursor)

        # If starting fresh (version 0), create schema_version table first
        if current_version == 0:
            self._migration_v2_create_version_table(cursor)
            # Don't record v2 yet, we'll do that after v1

        # Migration registry: version -> function
        migrations = {
            1: self._migration_v1_add_source_column,
            2: self._migration_v2_create_version_table,
        }

        # Apply migrations in order
        for version in sorted(migrations.keys()):
            if version > current_version:
                logger.info(f"Database schema at v{current_version}, applying v{version}...")
                migrations[version](cursor)
                self._set_schema_version(cursor, version)
                current_version = version

        if current_version < self.CURRENT_VERSION:
            logger.warning(f"Database at v{current_version} but code expects v{self.CURRENT_VERSION}")
        elif current_version == self.CURRENT_VERSION:
            logger.debug(f"Database schema up to date (v{current_version})")

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create base tables
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

        # Run versioned migrations
        self._run_migrations(conn, cursor)

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
        Helper to merge source and source_url fields with URL normalization.
        """
        from src.utils import normalize_url

        current_sources = existing_row['source'].split(',') if existing_row['source'] else []
        current_sources = [s.strip() for s in current_sources]

        new_source = new_data.get('source')
        updated = False

        if new_source and new_source not in current_sources:
            current_sources.append(new_source)
            new_source_str = ", ".join(current_sources)

            # Merge URLs with normalization to avoid duplicates
            current_urls = existing_row['source_url'] if existing_row['source_url'] else ""
            new_url = new_data['source_url']

            # Parse existing URLs
            existing_url_list = [u.strip() for u in current_urls.split(';') if u.strip()]

            # Normalize all URLs for comparison
            normalized_existing = {normalize_url(u): u for u in existing_url_list}
            normalized_new = normalize_url(new_url)

            # Add only if normalized version not present
            if normalized_new not in normalized_existing:
                existing_url_list.append(new_url)
                new_urls = " ; ".join(existing_url_list)
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

    def get_papers_by_run_id(self, run_id):
        """
        Retrieve all papers added during a specific run.

        Args:
            run_id: Run timestamp string (format: "YYYY-MM-DD HH:MM:SS")

        Returns:
            List of paper dictionaries from the current run, sorted by source and date
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM papers
            WHERE downloaded_date = ?
            ORDER BY source, published_date DESC
        """, (run_id,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def rollback_source(self, source, start_time_str):
        """
        Deletes papers added for a specific source after a given time.
        Handles papers with multiple sources by merging strings.
        Returns a dict with 'db_paths' and 'directory_path' for comprehensive cleanup.
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
        paper_ids = []

        for row in rows:
            paper_id = row['id']
            current_source_str = row['source']
            sources = [s.strip() for s in current_source_str.split(',')]

            if source in sources:
                if len(sources) == 1:
                    # Only source, delete the whole paper entry and the file
                    paths_to_delete.append(row['pdf_path'])
                    paper_ids.append(paper_id)
                    cursor.execute("DELETE FROM papers WHERE id = ?", (paper_id,))
                else:
                    # Multiple sources, just remove THIS source from the list
                    sources.remove(source)
                    new_source_str = ", ".join(sources)
                    cursor.execute("UPDATE papers SET source = ? WHERE id = ?", (new_source_str, paper_id))

        conn.commit()
        conn.close()

        # Return both paths and paper IDs for comprehensive cleanup
        result = {
            'paths': [p for p in paths_to_delete if p],
            'paper_ids': paper_ids,
            'source': source
        }
        return result

