"""
Test script for GUI DAILY mode summary window.

Uses actual papers from database to test the full paper display.
This is useful for testing the UI with real data.

Usage:
    python test_gui_daily.py

Requirements:
    - Database must exist with papers (run agent at least once)

Expected Output:
    - Wide window (1400x700) showing full paper details
    - NO stats section at top
    - Scrollable paper list with titles, authors, abstracts
    - Centered summary footer at bottom with fixed-width font
"""
import tkinter as tk
import sqlite3
import random
from collections import Counter
from src.summary_window import SummaryWindow
from src.utils import get_config


def load_papers_from_database(limit=100):
    """
    Load papers from database for testing.

    Args:
        limit: Maximum number of papers to load from database

    Returns:
        List of paper dictionaries

    Raises:
        SystemExit: If no papers found in database
    """
    config = get_config()
    db_path = config.get("db_path", "data/metadata.db")

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM papers LIMIT ?", (limit,))
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            print("ERROR: No papers found in database.")
            print("Please run the agent first to collect papers:")
            print("  python main.py --mode TESTING")
            exit(1)

        return [dict(row) for row in rows]

    except sqlite3.Error as e:
        print(f"ERROR: Failed to access database: {e}")
        print(f"Database path: {db_path}")
        exit(1)


def main():
    """Launch the DAILY summary window with test data from database."""
    # Load papers from database
    all_papers = load_papers_from_database(limit=100)

    # Randomly select papers to simulate a DAILY run (45 papers)
    num_papers = min(45, len(all_papers))
    selected_papers = random.sample(all_papers, num_papers)

    print(f"Selected {len(selected_papers)} random papers from database for DAILY mode test")

    # Count by source
    source_counts = Counter([p['source'] for p in selected_papers])
    print("\nBreakdown by source:")
    for source, count in sorted(source_counts.items()):
        print(f"  {source}: {count}")
    print(f"  TOTAL: {len(selected_papers)}")

    # Launch the summary window in DAILY mode
    root = tk.Tk()
    root.withdraw()  # Hide the main window

    print("\nLaunching summary window in DAILY mode...")
    print("Expected: Wide window with full paper details and centered summary footer\n")

    summary = SummaryWindow(selected_papers, run_id="daily_2024-01-11", mode="DAILY")

    root.mainloop()


if __name__ == "__main__":
    main()
