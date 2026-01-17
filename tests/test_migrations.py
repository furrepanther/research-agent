"""Test database migration versioning system"""
import sqlite3
import os
import tempfile
from src.storage import StorageManager

def test_migrations():
    print("=" * 70)
    print("Testing Database Migration Versioning")
    print("=" * 70)

    # Test 1: Fresh database (no tables exist)
    print("\n1. Testing fresh database initialization:")
    try:
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db') as f:
            temp_db = f.name

        # Create fresh database
        storage = StorageManager(temp_db)

        # Check schema_version table exists
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'")
        version_table_exists = cursor.fetchone() is not None

        # Check current version
        cursor.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
        current_version = cursor.fetchone()

        # Check papers table has source column
        cursor.execute("PRAGMA table_info(papers)")
        columns = [info[1] for info in cursor.fetchall()]
        has_source_column = 'source' in columns

        conn.close()

        print(f"   schema_version table exists: {version_table_exists}")
        print(f"   Current version: {current_version[0] if current_version else 'None'}")
        print(f"   papers.source column exists: {has_source_column}")

        if version_table_exists and current_version and current_version[0] == 2 and has_source_column:
            print("   [PASS] Fresh database initialized to v2 correctly")
        else:
            print("   [FAIL] Fresh database not at expected state")

        os.unlink(temp_db)

    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        if os.path.exists(temp_db):
            os.unlink(temp_db)

    # Test 2: Old database without source column (v0)
    print("\n2. Testing migration from v0 (no source column):")
    try:
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db') as f:
            temp_db = f.name

        # Create old-style database (papers table but no source column)
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE papers (
                id TEXT PRIMARY KEY,
                title TEXT,
                published_date TEXT,
                authors TEXT,
                abstract TEXT,
                pdf_path TEXT,
                source_url TEXT,
                downloaded_date TEXT,
                synced_to_cloud BOOLEAN DEFAULT 0
            )
        """)
        conn.commit()
        conn.close()

        # Initialize storage (should trigger migrations)
        storage = StorageManager(temp_db)

        # Verify migration applied
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        # Check source column added
        cursor.execute("PRAGMA table_info(papers)")
        columns = [info[1] for info in cursor.fetchall()]
        has_source_column = 'source' in columns

        # Check version recorded
        cursor.execute("SELECT version FROM schema_version ORDER BY version DESC")
        versions = [row[0] for row in cursor.fetchall()]

        conn.close()

        print(f"   papers.source column added: {has_source_column}")
        print(f"   Versions in database: {versions}")

        if has_source_column and 1 in versions and 2 in versions:
            print("   [PASS] Migration from v0 to v2 successful")
        else:
            print("   [FAIL] Migration not applied correctly")

        os.unlink(temp_db)

    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        if os.path.exists(temp_db):
            os.unlink(temp_db)

    # Test 3: Database with source column but no version table (legacy)
    print("\n3. Testing migration from legacy (has source, no version table):")
    try:
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db') as f:
            temp_db = f.name

        # Create legacy database (has source column but no version tracking)
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE papers (
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
        conn.commit()
        conn.close()

        # Initialize storage (should add version table)
        storage = StorageManager(temp_db)

        # Verify version table created
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'")
        version_table_exists = cursor.fetchone() is not None

        cursor.execute("SELECT version FROM schema_version ORDER BY version DESC")
        versions = [row[0] for row in cursor.fetchall()]

        conn.close()

        print(f"   schema_version table created: {version_table_exists}")
        print(f"   Versions recorded: {versions}")

        if version_table_exists and versions == [2, 1]:
            print("   [PASS] Legacy database migrated to versioned system")
        else:
            print("   [FAIL] Legacy migration incomplete")

        os.unlink(temp_db)

    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        if os.path.exists(temp_db):
            os.unlink(temp_db)

    # Test 4: Up-to-date database (already at v2)
    print("\n4. Testing up-to-date database (no migrations needed):")
    try:
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db') as f:
            temp_db = f.name

        # Create database at current version
        storage1 = StorageManager(temp_db)

        # Get initial migration count
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM schema_version")
        initial_count = cursor.fetchone()[0]
        conn.close()

        # Re-initialize (should not apply migrations again)
        storage2 = StorageManager(temp_db)

        # Get final migration count
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM schema_version")
        final_count = cursor.fetchone()[0]
        conn.close()

        print(f"   Initial migration count: {initial_count}")
        print(f"   Final migration count: {final_count}")

        if initial_count == final_count == 2:
            print("   [PASS] Up-to-date database not re-migrated")
        else:
            print("   [FAIL] Migrations incorrectly re-applied")

        os.unlink(temp_db)

    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        if os.path.exists(temp_db):
            os.unlink(temp_db)

    # Test 5: Migration idempotency (safe to run multiple times)
    print("\n5. Testing migration idempotency:")
    try:
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db') as f:
            temp_db = f.name

        # Create v0 database
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE papers (
                id TEXT PRIMARY KEY,
                title TEXT,
                published_date TEXT,
                authors TEXT,
                abstract TEXT,
                pdf_path TEXT,
                source_url TEXT,
                downloaded_date TEXT,
                synced_to_cloud BOOLEAN DEFAULT 0
            )
        """)
        conn.commit()
        conn.close()

        # Run migrations 3 times
        for i in range(3):
            storage = StorageManager(temp_db)

        # Verify still correct
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        # Check column exists (and only once)
        cursor.execute("PRAGMA table_info(papers)")
        columns = [info[1] for info in cursor.fetchall()]
        source_count = columns.count('source')

        # Check version count (should be 2 entries: v1 and v2)
        cursor.execute("SELECT COUNT(*) FROM schema_version")
        version_count = cursor.fetchone()[0]

        conn.close()

        print(f"   'source' column appears {source_count} time(s)")
        print(f"   schema_version has {version_count} entries")

        if source_count == 1 and version_count == 2:
            print("   [PASS] Migrations are idempotent (safe to re-run)")
        else:
            print("   [FAIL] Migrations not idempotent")

        os.unlink(temp_db)

    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        if os.path.exists(temp_db):
            os.unlink(temp_db)

    # Test 6: Adding a new migration (simulate future v3)
    print("\n6. Testing future migration extensibility:")
    try:
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db') as f:
            temp_db = f.name

        # Create v2 database
        storage = StorageManager(temp_db)

        # Check current version
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(version) FROM schema_version")
        current = cursor.fetchone()[0]

        # Verify CURRENT_VERSION constant
        expected_version = StorageManager.CURRENT_VERSION

        conn.close()

        print(f"   Database version: {current}")
        print(f"   Code CURRENT_VERSION: {expected_version}")
        print(f"   Ready for v3: {current == expected_version}")

        if current == expected_version == 2:
            print("   [PASS] System ready to add future migrations")
        else:
            print("   [FAIL] Version mismatch")

        os.unlink(temp_db)

    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        if os.path.exists(temp_db):
            os.unlink(temp_db)

    print("\n" + "=" * 70)
    print("Migration Testing Complete")
    print("=" * 70)
    print("\nMigration System Features:")
    print("  - Tracks applied migrations in schema_version table")
    print("  - Applies migrations in order (v1, v2, ...)")
    print("  - Idempotent (safe to re-run)")
    print("  - Handles fresh, legacy, and up-to-date databases")
    print("  - Easy to extend with new migrations")
    print("=" * 70)

if __name__ == "__main__":
    test_migrations()
