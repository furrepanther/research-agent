"""
Test script for the Summary Window feature.
This script opens a summary window with 10 random papers from the database.
"""
import tkinter as tk
import random
from src.summary_window import SummaryWindow
from src.storage import StorageManager
from src.utils import get_config

def test_summary_window():
    # Create root window (required for Toplevel)
    root = tk.Tk()
    root.withdraw()  # Hide root window

    # Get configuration
    config = get_config()
    storage = StorageManager(config.get("db_path", "data/metadata.db"))

    # Get all papers from database
    import sqlite3
    conn = sqlite3.connect(config.get("db_path", "data/metadata.db"))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM papers ORDER BY RANDOM() LIMIT 10")
    rows = cursor.fetchall()
    conn.close()

    papers = [dict(row) for row in rows]

    if not papers:
        print("No papers found in database!")
        print("Run a BACKFILL or DAILY mode first to populate the database.")
        return

    print(f"Opening summary window with {len(papers)} random papers...")

    # Create summary window
    summary = SummaryWindow(papers, "test-run-2024-01-15 14:30:00")

    # Keep window open
    root.mainloop()

if __name__ == "__main__":
    test_summary_window()
