"""
Test script for GUI BACKFILL mode summary window.

Creates fake paper data to visualize the BACKFILL summary display.
This is useful for testing the UI without running a full backfill operation.

Usage:
    python test_gui_backfill.py

Expected Output:
    - Compact window (450x300) showing vertical stats
    - Source counts in fixed-width font (Consolas)
    - Centered TOTAL at bottom
"""
import tkinter as tk
from src.summary_window import SummaryWindow


def create_fake_papers():
    """
    Generate fake paper data simulating a BACKFILL run.

    Returns typical counts from a successful backfill:
    - ArXiv: 523 papers
    - LessWrong: 187 papers
    - Anthropic: 42 papers
    - OpenAI: 35 papers
    - DeepMind: 28 papers
    - Meta AI: 18 papers
    Total: 833 papers
    """
    fake_papers = []

    # Define source configurations
    sources = [
        ('arxiv', 'ArXiv Paper', 523),
        ('lesswrong', 'LessWrong Post', 187),
        ('labs_anthropic', 'Anthropic Research', 42),
        ('labs_openai', 'OpenAI Research', 35),
        ('labs_deepmind', 'DeepMind Research', 28),
        ('labs_meta', 'Meta AI Research', 18)
    ]

    for source, title_prefix, count in sources:
        for i in range(count):
            fake_papers.append({
                'id': f'{source}_{i}',
                'title': f'{title_prefix} {i}',
                'authors': f'Author {i}',
                'abstract': 'Sample abstract for testing purposes',
                'source': source,
                'published_date': '2024-01-01',
                'pdf_path': f'/fake/path/{source}_{i}.pdf'
            })

    return fake_papers


def main():
    """Launch the BACKFILL summary window with test data."""
    fake_papers = create_fake_papers()

    print(f"Created {len(fake_papers)} fake papers for BACKFILL mode test")
    print("\nBreakdown by source:")
    print(f"  ArXiv: 523")
    print(f"  LessWrong: 187")
    print(f"  Anthropic: 42")
    print(f"  OpenAI: 35")
    print(f"  DeepMind: 28")
    print(f"  Meta AI: 18")
    print(f"  TOTAL: {len(fake_papers)}")

    # Launch the summary window in BACKFILL mode
    root = tk.Tk()
    root.withdraw()  # Hide the main window

    print("\nLaunching summary window in BACKFILL mode...")
    print("Expected: Compact stats-only window with vertical layout\n")

    summary = SummaryWindow(fake_papers, run_id="test_2024-01-11", mode="BACKFILL")

    root.mainloop()


if __name__ == "__main__":
    main()
