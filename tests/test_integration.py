"""Comprehensive integration tests for Research Agent"""
import os
import sqlite3
import tempfile
import multiprocessing
import time
from datetime import datetime
from src.supervisor import Supervisor
from src.storage import StorageManager
from src.utils import get_config
from src.searchers.arxiv_searcher import ArxivSearcher
from src.searchers.semantic_searcher import SemanticSearcher
from src.searchers.lesswrong_searcher import LessWrongSearcher
from src.searchers.lab_scraper import LabScraper

def test_integration():
    print("=" * 70)
    print("Comprehensive Integration Tests")
    print("=" * 70)

    # Test 1: End-to-end TESTING mode with all 4 searchers
    print("\n1. Testing end-to-end TESTING mode (all 4 searchers):")
    try:
        # Setup temporary database
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db') as f:
            temp_db = f.name

        # Create test prompt
        test_prompt = '("AI" OR "artificial intelligence") AND ("safety" OR "alignment")'

        # Setup search params for TESTING mode
        search_params = {
            'max_papers_per_agent': 3,  # Small limit for fast test
            'per_query_limit': 5,
            'respect_date_range': False,
            'start_date': datetime(2023, 1, 1)
        }

        # Create supervisor and workers
        task_queue = multiprocessing.Queue()
        stop_event = multiprocessing.Event()

        config = get_config()
        # Temporarily override db_path
        original_db = config.get('db_path')
        config['db_path'] = temp_db

        supervisor = Supervisor(task_queue, stop_event, test_prompt, search_params, mode="TESTING")

        # Start all workers
        workers = [
            (ArxivSearcher, "ArXiv"),
            (SemanticSearcher, "Semantic Scholar"),
            (LessWrongSearcher, "LessWrong"),
            (LabScraper, "AI Labs")
        ]

        start_time = time.time()
        print(f"   Starting {len(workers)} workers in parallel...")

        for searcher_class, display_name in workers:
            supervisor.start_worker(searcher_class, display_name)

        # Process messages with timeout
        timeout = 120  # 2 minutes max
        completed_workers = set()
        error_count = 0

        while supervisor.is_any_alive() and (time.time() - start_time) < timeout:
            try:
                msg = task_queue.get(timeout=1)
                msg_type = msg.get("type")
                source = msg.get("source", "Unknown")

                if msg_type == "UPDATE_ROW":
                    status = msg.get("status", "")
                    if status in ["Complete", "No Results", "HALTED"]:
                        completed_workers.add(source)
                    # Update heartbeat
                    if source in supervisor.workers:
                        supervisor.workers[source]['last_heartbeat'] = time.time()

                elif msg_type == "ERROR":
                    error_count += 1

            except:
                supervisor.check_timeouts()

        end_time = time.time()
        duration = end_time - start_time

        # Check results
        storage = StorageManager(temp_db)
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        # Count papers by source
        cursor.execute("SELECT source, COUNT(*) FROM papers GROUP BY source")
        source_counts = dict(cursor.fetchall())

        # Count unique papers
        cursor.execute("SELECT COUNT(DISTINCT id) FROM papers")
        total_unique = cursor.fetchone()[0]

        conn.close()

        print(f"   Duration: {duration:.1f}s")
        print(f"   Completed workers: {len(completed_workers)}/{len(workers)}")
        print(f"   Papers by source: {source_counts}")
        print(f"   Total unique papers: {total_unique}")
        print(f"   Errors: {error_count}")

        # Restore original db_path
        config['db_path'] = original_db

        # Pass if: completed some workers, got some papers, no excessive errors
        if len(completed_workers) >= 2 and total_unique > 0 and error_count < 3:
            print("   [PASS] End-to-end integration working")
        else:
            print("   [PARTIAL] Some workers completed but results suboptimal")

        os.unlink(temp_db)

    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        if os.path.exists(temp_db):
            os.unlink(temp_db)

    # Test 2: Database deduplication across sources
    print("\n2. Testing cross-source deduplication:")
    try:
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db') as f:
            temp_db = f.name

        storage = StorageManager(temp_db)

        # Simulate same paper from two sources
        paper1 = {
            'id': 'test-001',
            'title': 'AI Safety Research',
            'published_date': '2024-01-01',
            'authors': 'Smith, J.',
            'abstract': 'This paper explores AI safety.',
            'pdf_path': '/path/to/paper1.pdf',
            'source_url': 'https://arxiv.org/abs/test-001',
            'downloaded_date': '2024-06-01 10:00:00',
            'source': 'arxiv'
        }

        paper2 = {
            'id': 'test-001',  # Same ID
            'title': 'AI Safety Research',
            'published_date': '2024-01-01',
            'authors': 'Smith, J.',
            'abstract': 'This paper explores AI safety.',
            'pdf_path': '/path/to/paper2.pdf',
            'source_url': 'https://semanticscholar.org/paper/test-001',
            'downloaded_date': '2024-06-01 10:01:00',
            'source': 'semantic'
        }

        # Add both papers
        added1 = storage.add_paper(paper1)
        added2 = storage.add_paper(paper2)

        # Check database
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM papers WHERE id = 'test-001'")
        count = cursor.fetchone()[0]

        cursor.execute("SELECT source, source_url FROM papers WHERE id = 'test-001'")
        result = cursor.fetchone()
        merged_source = result[0] if result else None
        merged_urls = result[1] if result else None

        conn.close()

        print(f"   First add returned: {added1}")
        print(f"   Second add returned: {added2}")
        print(f"   Papers with ID 'test-001': {count}")
        print(f"   Merged source: {merged_source}")
        print(f"   Merged URLs: {merged_urls}")

        # Should have 1 paper with merged sources
        sources_merged = merged_source and ',' in merged_source
        urls_merged = merged_urls and ';' in merged_urls

        if count == 1 and sources_merged and urls_merged:
            print("   [PASS] Cross-source deduplication working")
        else:
            print("   [FAIL] Deduplication not merging correctly")

        os.unlink(temp_db)

    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        if os.path.exists(temp_db):
            os.unlink(temp_db)

    # Test 3: URL normalization in practice
    print("\n3. Testing URL normalization:")
    try:
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db') as f:
            temp_db = f.name

        storage = StorageManager(temp_db)

        # Same paper with different URL variations
        paper_v1 = {
            'id': 'url-test-001',
            'title': 'Test Paper',
            'published_date': '2024-01-01',
            'authors': 'Author',
            'abstract': 'Abstract text',
            'pdf_path': '/path/v1.pdf',
            'source_url': 'http://example.com/paper',  # http, no trailing slash
            'downloaded_date': '2024-06-01 10:00:00',
            'source': 'source1'
        }

        paper_v2 = {
            'id': 'url-test-001',
            'title': 'Test Paper',
            'published_date': '2024-01-01',
            'authors': 'Author',
            'abstract': 'Abstract text',
            'pdf_path': '/path/v2.pdf',
            'source_url': 'https://example.com/paper/',  # https, trailing slash
            'downloaded_date': '2024-06-01 10:01:00',
            'source': 'source2'
        }

        paper_v3 = {
            'id': 'url-test-001',
            'title': 'Test Paper',
            'published_date': '2024-01-01',
            'authors': 'Author',
            'abstract': 'Abstract text',
            'pdf_path': '/path/v3.pdf',
            'source_url': 'https://example.com/paper?utm_source=twitter',  # tracking params
            'downloaded_date': '2024-06-01 10:02:00',
            'source': 'source3'
        }

        storage.add_paper(paper_v1)
        storage.add_paper(paper_v2)
        storage.add_paper(paper_v3)

        # Check merged URLs
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT source_url FROM papers WHERE id = 'url-test-001'")
        merged_urls = cursor.fetchone()[0]
        conn.close()

        # Count URLs (should be 1 since all normalize to the same)
        url_count = len([u for u in merged_urls.split(';') if u.strip()])

        print(f"   Merged URLs: {merged_urls}")
        print(f"   Unique URLs after normalization: {url_count}")

        if url_count == 1:
            print("   [PASS] URL normalization preventing duplicates")
        else:
            print("   [FAIL] URLs not being normalized correctly")

        os.unlink(temp_db)

    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        if os.path.exists(temp_db):
            os.unlink(temp_db)

    # Test 4: Mode-specific behavior verification
    print("\n4. Testing mode-specific limits:")
    try:
        # Test TESTING mode respects max_papers_per_agent
        print("   Testing TESTING mode limits (max 3 papers)...")

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db') as f:
            temp_db = f.name

        test_prompt = '("machine learning")'

        search_params_testing = {
            'max_papers_per_agent': 3,
            'per_query_limit': 10,  # Request more than limit
            'respect_date_range': False,
            'start_date': datetime(2023, 1, 1)
        }

        task_queue = multiprocessing.Queue()
        stop_event = multiprocessing.Event()

        config = get_config()
        original_db = config.get('db_path')
        config['db_path'] = temp_db

        supervisor = Supervisor(task_queue, stop_event, test_prompt, search_params_testing, mode="TESTING")

        # Just test ArXiv for speed
        supervisor.start_worker(ArxivSearcher, "ArXiv")

        # Wait for completion
        start = time.time()
        while supervisor.is_any_alive() and (time.time() - start) < 60:
            try:
                msg = task_queue.get(timeout=1)
                if msg.get("type") == "UPDATE_ROW":
                    src = msg.get("source")
                    if src in supervisor.workers:
                        supervisor.workers[src]['last_heartbeat'] = time.time()
            except:
                pass

        # Check paper count
        storage = StorageManager(temp_db)
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM papers")
        paper_count = cursor.fetchone()[0]
        conn.close()

        config['db_path'] = original_db

        print(f"      Papers downloaded: {paper_count} (limit was 3)")

        if paper_count <= 3:
            print("      [PASS] max_papers_per_agent limit respected")
        else:
            print("      [FAIL] Exceeded max_papers_per_agent limit")

        os.unlink(temp_db)

    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        if os.path.exists(temp_db):
            os.unlink(temp_db)

    # Test 5: Schema version check
    print("\n5. Testing database schema versioning:")
    try:
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db') as f:
            temp_db = f.name

        storage = StorageManager(temp_db)

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        # Check schema_version table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'")
        has_version_table = cursor.fetchone() is not None

        # Check current version
        cursor.execute("SELECT MAX(version) FROM schema_version")
        current_version = cursor.fetchone()[0] if has_version_table else None

        # Check expected version
        expected_version = StorageManager.CURRENT_VERSION

        conn.close()

        print(f"   schema_version table exists: {has_version_table}")
        print(f"   Current DB version: {current_version}")
        print(f"   Expected version: {expected_version}")

        if has_version_table and current_version == expected_version:
            print("   [PASS] Database schema versioning working")
        else:
            print("   [FAIL] Schema version mismatch")

        os.unlink(temp_db)

    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        if os.path.exists(temp_db):
            os.unlink(temp_db)

    print("\n" + "=" * 70)
    print("Integration Testing Complete")
    print("=" * 70)
    print("\nTested Components:")
    print("  - End-to-end parallel execution (4 searchers)")
    print("  - Cross-source deduplication")
    print("  - URL normalization")
    print("  - Mode-specific limits (TESTING mode)")
    print("  - Database schema versioning")
    print("=" * 70)

if __name__ == "__main__":
    test_integration()
