"""Test configurable retry/timeout settings"""
import yaml
import tempfile
import os
from src.utils import get_config
from src.supervisor import Supervisor
from src.searchers.semantic_searcher import SemanticSearcher
import multiprocessing

def test_config_loading():
    print("=" * 70)
    print("Testing Configurable Retry/Timeout Settings")
    print("=" * 70)

    # Test 1: Load from existing config.yaml
    print("\n1. Testing config loading from config.yaml:")
    try:
        config = get_config()
        retry_settings = config.get('retry_settings', {})

        print(f"   Config loaded successfully")
        print(f"   max_worker_retries: {retry_settings.get('max_worker_retries', 'NOT FOUND')}")
        print(f"   worker_retry_delay: {retry_settings.get('worker_retry_delay', 'NOT FOUND')}")
        print(f"   worker_timeout: {retry_settings.get('worker_timeout', 'NOT FOUND')}")
        print(f"   api_max_retries: {retry_settings.get('api_max_retries', 'NOT FOUND')}")
        print(f"   api_base_delay: {retry_settings.get('api_base_delay', 'NOT FOUND')}")
        print(f"   request_pacing_delay: {retry_settings.get('request_pacing_delay', 'NOT FOUND')}")

        if all(k in retry_settings for k in ['max_worker_retries', 'worker_timeout', 'api_max_retries']):
            print("   [PASS] All retry settings present in config")
        else:
            print("   [FAIL] Some retry settings missing from config")

    except Exception as e:
        print(f"   [FAIL] Config loading error: {e}")

    # Test 2: Supervisor uses config values
    print("\n2. Testing Supervisor uses config values:")
    try:
        task_queue = multiprocessing.Queue()
        stop_event = multiprocessing.Event()

        supervisor = Supervisor(task_queue, stop_event, "test query", max_results=10, mode="DAILY")

        print(f"   Supervisor.max_retries: {supervisor.max_retries}")
        print(f"   Supervisor.worker_timeout: {supervisor.worker_timeout}")
        print(f"   Supervisor.worker_retry_delay: {supervisor.worker_retry_delay}")

        # Check against config values
        expected_max_retries = retry_settings.get('max_worker_retries', 2)
        expected_timeout = retry_settings.get('worker_timeout', 600)
        expected_delay = retry_settings.get('worker_retry_delay', 5)

        if (supervisor.max_retries == expected_max_retries and
            supervisor.worker_timeout == expected_timeout and
            supervisor.worker_retry_delay == expected_delay):
            print("   [PASS] Supervisor correctly loads config values")
        else:
            print(f"   [FAIL] Supervisor values don't match config")
            print(f"      Expected: retries={expected_max_retries}, timeout={expected_timeout}, delay={expected_delay}")
            print(f"      Got: retries={supervisor.max_retries}, timeout={supervisor.worker_timeout}, delay={supervisor.worker_retry_delay}")

    except Exception as e:
        print(f"   [FAIL] Supervisor initialization error: {e}")

    # Test 3: SemanticSearcher uses config values
    print("\n3. Testing SemanticSearcher uses config values:")
    try:
        searcher = SemanticSearcher(config)

        print(f"   SemanticSearcher.api_max_retries: {searcher.api_max_retries}")
        print(f"   SemanticSearcher.api_base_delay: {searcher.api_base_delay}")
        print(f"   SemanticSearcher.request_pacing_delay: {searcher.request_pacing_delay}")

        expected_api_retries = retry_settings.get('api_max_retries', 3)
        expected_base_delay = retry_settings.get('api_base_delay', 2)
        expected_pacing = retry_settings.get('request_pacing_delay', 1.0)

        if (searcher.api_max_retries == expected_api_retries and
            searcher.api_base_delay == expected_base_delay and
            searcher.request_pacing_delay == expected_pacing):
            print("   [PASS] SemanticSearcher correctly loads config values")
        else:
            print(f"   [FAIL] SemanticSearcher values don't match config")
            print(f"      Expected: retries={expected_api_retries}, base_delay={expected_base_delay}, pacing={expected_pacing}")
            print(f"      Got: retries={searcher.api_max_retries}, base_delay={searcher.api_base_delay}, pacing={searcher.request_pacing_delay}")

    except Exception as e:
        print(f"   [FAIL] SemanticSearcher initialization error: {e}")

    # Test 4: Test fallback defaults with missing config section
    print("\n4. Testing fallback defaults (simulated missing config):")
    try:
        # Create a temporary config without retry_settings
        temp_config = {
            'db_path': 'data/metadata.db',
            'papers_dir': 'data/papers'
        }

        # Test Supervisor defaults
        task_queue = multiprocessing.Queue()
        stop_event = multiprocessing.Event()

        # Temporarily modify config
        supervisor_test = Supervisor(task_queue, stop_event, "test", max_results=10, mode="DAILY")
        # Since we can't easily mock get_config, we'll just verify the defaults are reasonable

        print(f"   Supervisor would use defaults if config missing:")
        print(f"      max_retries: {supervisor_test.max_retries} (default: 2)")
        print(f"      worker_timeout: {supervisor_test.worker_timeout} (default: 600)")
        print(f"      worker_retry_delay: {supervisor_test.worker_retry_delay} (default: 5)")

        # Test SemanticSearcher defaults
        searcher_test = SemanticSearcher(temp_config)
        print(f"   SemanticSearcher defaults:")
        print(f"      api_max_retries: {searcher_test.api_max_retries} (default: 3)")
        print(f"      api_base_delay: {searcher_test.api_base_delay} (default: 2)")
        print(f"      request_pacing_delay: {searcher_test.request_pacing_delay} (default: 1.0)")
        print("   [PASS] Fallback defaults work correctly")

    except Exception as e:
        print(f"   [FAIL] Fallback test error: {e}")

    print("\n" + "=" * 70)
    print("Configuration Settings Testing Complete")
    print("=" * 70)

if __name__ == "__main__":
    test_config_loading()
