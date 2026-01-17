"""Test mode-specific parameter settings"""
import yaml
from src.utils import get_config
from datetime import datetime
import multiprocessing
from src.supervisor import Supervisor

def test_mode_settings():
    print("=" * 70)
    print("Testing Mode-Specific Parameter Settings")
    print("=" * 70)

    # Test 1: Load mode_settings from config
    print("\n1. Testing config structure:")
    try:
        config = get_config()
        mode_settings = config.get('mode_settings', {})

        print(f"   mode_settings section found: {bool(mode_settings)}")

        # Check all three modes exist
        testing_mode = mode_settings.get('testing', {})
        daily_mode = mode_settings.get('daily', {})
        backfill_mode = mode_settings.get('backfill', {})

        print(f"   testing mode: {bool(testing_mode)}")
        print(f"   daily mode: {bool(daily_mode)}")
        print(f"   backfill mode: {bool(backfill_mode)}")

        if all([testing_mode, daily_mode, backfill_mode]):
            print("   [PASS] All three modes present in config")
        else:
            print("   [FAIL] Some modes missing")

    except Exception as e:
        print(f"   [FAIL] Config loading error: {e}")

    # Test 2: Verify TESTING mode parameters
    print("\n2. Testing TESTING mode parameters:")
    try:
        testing = mode_settings.get('testing', {})
        print(f"   max_papers_per_agent: {testing.get('max_papers_per_agent')} (expected: 10)")
        print(f"   per_query_limit: {testing.get('per_query_limit')} (expected: 5)")
        print(f"   respect_date_range: {testing.get('respect_date_range')} (expected: False)")

        if (testing.get('max_papers_per_agent') == 10 and
            testing.get('per_query_limit') == 5 and
            testing.get('respect_date_range') == False):
            print("   [PASS] TESTING mode configured correctly")
        else:
            print("   [FAIL] TESTING mode configuration mismatch")

    except Exception as e:
        print(f"   [FAIL] Error: {e}")

    # Test 3: Verify DAILY mode parameters
    print("\n3. Testing DAILY mode parameters:")
    try:
        daily = mode_settings.get('daily', {})
        print(f"   max_papers_per_agent: {daily.get('max_papers_per_agent')} (expected: 50)")
        print(f"   per_query_limit: {daily.get('per_query_limit')} (expected: 20)")
        print(f"   respect_date_range: {daily.get('respect_date_range')} (expected: True)")

        if (daily.get('max_papers_per_agent') == 50 and
            daily.get('per_query_limit') == 20 and
            daily.get('respect_date_range') == True):
            print("   [PASS] DAILY mode configured correctly")
        else:
            print("   [FAIL] DAILY mode configuration mismatch")

    except Exception as e:
        print(f"   [FAIL] Error: {e}")

    # Test 4: Verify BACKFILL mode parameters
    print("\n4. Testing BACKFILL mode parameters:")
    try:
        backfill = mode_settings.get('backfill', {})
        max_papers = backfill.get('max_papers_per_agent')
        print(f"   max_papers_per_agent: {max_papers} (expected: null/None for unlimited)")
        print(f"   per_query_limit: {backfill.get('per_query_limit')} (expected: 10)")
        print(f"   respect_date_range: {backfill.get('respect_date_range')} (expected: True)")

        if (max_papers is None and
            backfill.get('per_query_limit') == 10 and
            backfill.get('respect_date_range') == True):
            print("   [PASS] BACKFILL mode configured correctly (unlimited)")
        else:
            print("   [FAIL] BACKFILL mode configuration mismatch")

    except Exception as e:
        print(f"   [FAIL] Error: {e}")

    # Test 5: Test Supervisor accepts search_params
    print("\n5. Testing Supervisor with search_params:")
    try:
        task_queue = multiprocessing.Queue()
        stop_event = multiprocessing.Event()

        # Build search params (testing mode)
        search_params = {
            'max_papers_per_agent': 10,
            'per_query_limit': 5,
            'respect_date_range': False,
            'start_date': datetime(2023, 1, 1)
        }

        supervisor = Supervisor(task_queue, stop_event, "test query", search_params, mode="TESTING")

        print(f"   Supervisor created successfully")
        print(f"   search_params stored: {supervisor.search_params}")

        if (supervisor.search_params['max_papers_per_agent'] == 10 and
            supervisor.search_params['per_query_limit'] == 5):
            print("   [PASS] Supervisor stores search_params correctly")
        else:
            print("   [FAIL] Supervisor search_params mismatch")

    except Exception as e:
        print(f"   [FAIL] Supervisor initialization error: {e}")

    # Test 6: Test parameter extraction logic (DAILY mode example)
    print("\n6. Testing parameter extraction for DAILY mode:")
    try:
        mode_key = "daily"
        mode_settings_daily = mode_settings.get(mode_key, {})

        max_papers = mode_settings_daily.get("max_papers_per_agent")
        if max_papers is None:
            max_papers = float('inf')

        per_query = mode_settings_daily.get("per_query_limit", 10)
        respect_dates = mode_settings_daily.get("respect_date_range", True)

        print(f"   Extracted max_papers_per_agent: {max_papers}")
        print(f"   Extracted per_query_limit: {per_query}")
        print(f"   Extracted respect_date_range: {respect_dates}")

        if max_papers == 50 and per_query == 20 and respect_dates == True:
            print("   [PASS] Parameter extraction works correctly")
        else:
            print("   [FAIL] Parameter extraction failed")

    except Exception as e:
        print(f"   [FAIL] Error: {e}")

    # Test 7: Test unlimited (infinity) handling for BACKFILL
    print("\n7. Testing unlimited handling for BACKFILL mode:")
    try:
        mode_key = "backfill"
        mode_settings_backfill = mode_settings.get(mode_key, {})

        max_papers = mode_settings_backfill.get("max_papers_per_agent")
        if max_papers is None:
            max_papers = float('inf')

        print(f"   max_papers_per_agent (after conversion): {max_papers}")
        print(f"   Is infinity: {max_papers == float('inf')}")
        print(f"   Can compare: 100 < max_papers = {100 < max_papers}")

        if max_papers == float('inf') and 100 < max_papers:
            print("   [PASS] Infinity handling works correctly")
        else:
            print("   [FAIL] Infinity handling failed")

    except Exception as e:
        print(f"   [FAIL] Error: {e}")

    # Test 8: Verify legacy settings still present (backward compatibility)
    print("\n8. Testing backward compatibility (legacy settings):")
    try:
        legacy_daily = config.get("max_results_daily")
        legacy_backfill = config.get("max_results_backfill")

        print(f"   max_results_daily (legacy): {legacy_daily}")
        print(f"   max_results_backfill (legacy): {legacy_backfill}")

        if legacy_daily is not None and legacy_backfill is not None:
            print("   [PASS] Legacy settings preserved for backward compatibility")
        else:
            print("   [WARN] Legacy settings not present (may break old code)")

    except Exception as e:
        print(f"   [FAIL] Error: {e}")

    print("\n" + "=" * 70)
    print("Mode Settings Testing Complete")
    print("=" * 70)
    print("\nSummary:")
    print("  - TESTING: 10 papers max, 5 per query, ignore dates")
    print("  - DAILY: 50 papers max, 20 per query, respect dates")
    print("  - BACKFILL: UNLIMITED papers, 10 per query, respect dates")
    print("=" * 70)

if __name__ == "__main__":
    test_mode_settings()
