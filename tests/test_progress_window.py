"""
Test script for the progress tracking window.

This script demonstrates the ProgressWindow with simulated BACKFILL operations.
Run this to test the progress window independently before integration.

Usage:
    python test_progress_window.py
"""
import time
import random
from src.progress_window import ProgressWindow


def simulate_backfill_realistic():
    """
    Simulate a realistic BACKFILL operation with varying speeds per source.

    Simulates:
    - ArXiv: Fast, many papers
    - LessWrong: Medium speed, moderate papers
    - AI Labs: Slower, fewer papers
    """
    sources = ["ArXiv", "LessWrong", "AI Labs"]
    progress_win = ProgressWindow(sources, title="Backfill Progress - Realistic Test")

    # Source configurations (simulate different speeds)
    source_configs = {
        "ArXiv": {
            "target": 500,  # Total papers to download
            "search_speed": 50,  # Papers found per iteration
            "download_speed": 10  # Papers downloaded per iteration
        },
        "LessWrong": {
            "target": 150,
            "search_speed": 20,
            "download_speed": 5
        },
        "AI Labs": {
            "target": 50,
            "search_speed": 5,
            "download_speed": 2
        }
    }

    # Initialize tracking
    current_state = {}
    for source in sources:
        current_state[source] = {
            "found": 0,
            "downloaded": 0,
            "phase": "searching"
        }

    print("Starting realistic BACKFILL simulation...")
    print("Watch the progress window for live updates\n")

    # Simulate until all sources complete
    iteration = 0
    all_complete = False

    while not all_complete:
        iteration += 1
        all_complete = True

        for source in sources:
            config = source_configs[source]
            state = current_state[source]

            # Skip if already complete
            if state["downloaded"] >= config["target"]:
                if state["phase"] != "complete":
                    progress_win.update_source(
                        source,
                        status="Complete",
                        found=state["found"],
                        downloaded=state["downloaded"],
                        progress=100,
                        details=f"✓ Downloaded {state['downloaded']} papers"
                    )
                    state["phase"] = "complete"
                    print(f"[{source}] Complete - {state['downloaded']} papers downloaded")
                continue

            all_complete = False

            # Searching phase
            if state["phase"] == "searching":
                state["found"] += config["search_speed"]

                # Cap at target
                if state["found"] >= config["target"]:
                    state["found"] = config["target"]
                    state["phase"] = "filtering"

                progress_win.update_source(
                    source,
                    status="Searching",
                    found=state["found"],
                    downloaded=state["downloaded"],
                    progress=0,
                    details=f"Found {state['found']} papers..."
                )

            # Filtering phase
            elif state["phase"] == "filtering":
                # Simulate filtering taking a moment
                state["phase"] = "downloading"
                progress_win.update_source(
                    source,
                    status="Filtering",
                    found=state["found"],
                    downloaded=state["downloaded"],
                    progress=0,
                    details=f"Filtering {state['found']} papers..."
                )

            # Downloading phase
            elif state["phase"] == "downloading":
                state["downloaded"] += config["download_speed"]

                # Cap at found
                if state["downloaded"] > state["found"]:
                    state["downloaded"] = state["found"]

                progress_pct = (state["downloaded"] / state["found"]) * 100 if state["found"] > 0 else 0

                progress_win.update_source(
                    source,
                    status="Downloading",
                    found=state["found"],
                    downloaded=state["downloaded"],
                    progress=progress_pct,
                    details=f"Downloading ({state['downloaded']}/{state['found']})"
                )

        # Update status bar
        total_downloaded = sum(s["downloaded"] for s in current_state.values())
        total_target = sum(config["target"] for config in source_configs.values())
        progress_win.set_status(
            f"Iteration {iteration} - Total: {total_downloaded}/{total_target} papers downloaded"
        )

        # Update GUI
        progress_win.window.update()

        # Delay between iterations
        time.sleep(0.2)

    # Mark overall completion
    progress_win.mark_complete()
    print("\nBackfill simulation complete!")
    print(f"Total papers downloaded: {sum(s['downloaded'] for s in current_state.values())}")

    # Keep window open
    print("\nClose the window to exit...")
    progress_win.run()


def simulate_backfill_fast():
    """Quick test with fast random updates."""
    sources = ["ArXiv", "Semantic Scholar", "LessWrong", "AI Labs"]
    progress_win = ProgressWindow(sources, title="Backfill Progress - Fast Test")

    print("Starting fast random simulation...")
    print("This will update rapidly to test UI responsiveness\n")

    for step in range(50):
        for source in sources:
            found = random.randint(100, 1000)
            downloaded = random.randint(0, found)
            progress = (downloaded / found * 100) if found > 0 else 0
            status = random.choice(["Searching", "Filtering", "Downloading"])

            progress_win.update_source(
                source,
                status=status,
                found=found,
                downloaded=downloaded,
                progress=progress,
                details=f"Batch {step + 1}/50"
            )

        progress_win.set_status(f"Processing batch {step + 1} of 50...")
        progress_win.window.update()
        time.sleep(0.05)

    # Complete
    for source in sources:
        progress_win.update_source(source, status="Complete", progress=100)
    progress_win.mark_complete()

    print("\nFast test complete!")
    print("Close the window to exit...")
    progress_win.run()


def main():
    """Run progress window tests."""
    import sys

    print("=" * 60)
    print("Progress Window Test")
    print("=" * 60)
    print()

    # Check for command line argument
    if len(sys.argv) > 1:
        mode = sys.argv[1]
    else:
        print("Choose test mode:")
        print("  1. Realistic simulation (recommended)")
        print("  2. Fast random updates (stress test)")
        print()
        print("Usage: python test_progress_window.py [1|2]")
        print("Defaulting to realistic simulation...")
        print()
        mode = "1"

    if mode == "2":
        simulate_backfill_fast()
    else:
        simulate_backfill_realistic()


if __name__ == "__main__":
    main()
