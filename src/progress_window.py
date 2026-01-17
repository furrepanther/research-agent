"""
Real-time progress tracking window for BACKFILL operations.

Displays live updates of paper collection progress across multiple sources.
Can be used standalone for testing or integrated into the main application.
"""
import tkinter as tk
from tkinter import ttk
import time
from datetime import datetime


class ProgressWindow:
    """
    Progress tracking window for BACKFILL mode operations.

    Shows real-time progress for each source including:
    - Current status (Searching, Downloading, Filtering, etc.)
    - Papers found
    - Papers downloaded
    - Progress percentage
    - Elapsed time
    """

    def __init__(self, sources, title="Backfill Progress"):
        """
        Initialize the progress window.

        Args:
            sources: List of source names to track (e.g., ["ArXiv", "LessWrong", "AI Labs"])
            title: Window title
        """
        self.sources = sources
        self.start_time = time.time()

        # Create main window
        self.window = tk.Tk()
        self.window.title(title)
        self.window.geometry("800x400")
        self.window.resizable(False, False)

        # Center window
        self._center_window(800, 400)

        # Track source data
        self.source_data = {}
        for source in sources:
            self.source_data[source] = {
                'status': 'Waiting',
                'found': 0,
                'downloaded': 0,
                'progress': 0,
                'details': ''
            }

        self._create_ui()

    def _center_window(self, width, height):
        """Center the window on the screen."""
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.window.geometry(f"{width}x{height}+{x}+{y}")

    def _create_ui(self):
        """Create the user interface."""
        # Header
        header_frame = tk.Frame(self.window, bg="#2c3e50", pady=10)
        header_frame.pack(fill="x")

        title_label = tk.Label(
            header_frame,
            text="Backfill Progress Tracker",
            font=("Consolas", 16, "bold"),
            fg="white",
            bg="#2c3e50"
        )
        title_label.pack()

        # Elapsed time label
        self.time_label = tk.Label(
            header_frame,
            text="Elapsed: 00:00:00",
            font=("Consolas", 10),
            fg="white",
            bg="#2c3e50"
        )
        self.time_label.pack()

        # Progress table
        table_frame = ttk.Frame(self.window, padding=20)
        table_frame.pack(fill="both", expand=True)

        # Create treeview with columns
        columns = ("source", "status", "found", "downloaded", "progress", "details")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=len(self.sources))

        # Configure columns
        self.tree.heading("source", text="Source")
        self.tree.heading("status", text="Status")
        self.tree.heading("found", text="Found")
        self.tree.heading("downloaded", text="Downloaded")
        self.tree.heading("progress", text="Progress")
        self.tree.heading("details", text="Details")

        self.tree.column("source", width=120, anchor="w")
        self.tree.column("status", width=100, anchor="center")
        self.tree.column("found", width=80, anchor="center")
        self.tree.column("downloaded", width=100, anchor="center")
        self.tree.column("progress", width=100, anchor="center")
        self.tree.column("details", width=280, anchor="w")

        self.tree.pack(fill="both", expand=True, pady=10)

        # Initialize rows for each source
        self.row_ids = {}
        for source in self.sources:
            item_id = self.tree.insert("", "end", values=(
                source,
                "Waiting",
                "0",
                "0",
                "0%",
                "-"
            ))
            self.row_ids[source] = item_id

        # Overall progress bar
        progress_frame = ttk.Frame(self.window, padding=(20, 0, 20, 10))
        progress_frame.pack(fill="x")

        overall_label = ttk.Label(progress_frame, text="Overall Progress:", font=("Consolas", 10, "bold"))
        overall_label.pack(anchor="w")

        self.overall_progress = ttk.Progressbar(
            progress_frame,
            mode='determinate',
            length=760
        )
        self.overall_progress.pack(fill="x", pady=5)

        self.overall_label = ttk.Label(
            progress_frame,
            text="0 / 0 papers downloaded (0%)",
            font=("Consolas", 9)
        )
        self.overall_label.pack(anchor="w")

        # Status bar at bottom
        self.status_bar = tk.Label(
            self.window,
            text="Ready to start...",
            bd=1,
            relief=tk.SUNKEN,
            anchor=tk.W,
            font=("Consolas", 9)
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # Start updating elapsed time
        self._update_elapsed_time()

    def _update_elapsed_time(self):
        """Update elapsed time display."""
        elapsed = int(time.time() - self.start_time)
        hours = elapsed // 3600
        minutes = (elapsed % 3600) // 60
        seconds = elapsed % 60
        self.time_label.config(text=f"Elapsed: {hours:02d}:{minutes:02d}:{seconds:02d}")
        self.window.after(1000, self._update_elapsed_time)

    def update_source(self, source, status=None, found=None, downloaded=None, progress=None, details=None):
        """
        Update progress for a specific source.

        Args:
            source: Source name to update
            status: Status text (e.g., "Searching", "Downloading", "Complete")
            found: Number of papers found
            downloaded: Number of papers downloaded
            progress: Progress percentage (0-100)
            details: Additional details text
        """
        if source not in self.source_data:
            return

        # Update stored data
        data = self.source_data[source]
        if status is not None:
            data['status'] = status
        if found is not None:
            data['found'] = found
        if downloaded is not None:
            data['downloaded'] = downloaded
        if progress is not None:
            data['progress'] = progress
        if details is not None:
            data['details'] = details

        # Update tree view
        self.tree.item(self.row_ids[source], values=(
            source,
            data['status'],
            str(data['found']),
            str(data['downloaded']),
            f"{data['progress']:.0f}%",
            data['details']
        ))

        # Update overall progress
        self._update_overall_progress()

    def _update_overall_progress(self):
        """Update overall progress bar and label."""
        total_found = sum(data['found'] for data in self.source_data.values())
        total_downloaded = sum(data['downloaded'] for data in self.source_data.values())

        if total_found > 0:
            overall_pct = (total_downloaded / total_found) * 100
        else:
            overall_pct = 0

        self.overall_progress['value'] = overall_pct
        self.overall_label.config(
            text=f"{total_downloaded} / {total_found} papers downloaded ({overall_pct:.1f}%)"
        )

    def set_status(self, message):
        """
        Update status bar message.

        Args:
            message: Status message to display
        """
        self.status_bar.config(text=message)

    def mark_complete(self):
        """Mark all operations as complete."""
        self.set_status("Backfill complete!")

        # Mark any pending sources as complete
        for source, data in self.source_data.items():
            if data['status'] not in ['Complete', 'Error']:
                self.update_source(source, status='Complete', progress=100)

    def run(self):
        """Start the GUI event loop."""
        self.window.mainloop()

    def destroy(self):
        """Close the window."""
        self.window.destroy()


# Standalone test function
if __name__ == "__main__":
    # Test the progress window
    import random

    sources = ["ArXiv", "LessWrong", "AI Labs"]
    progress_win = ProgressWindow(sources, title="Backfill Progress Test")

    # Simulate progress updates
    def simulate_progress():
        """Simulate a backfill operation with random progress."""
        states = ["Searching", "Filtering", "Downloading"]

        for step in range(100):
            for source in sources:
                state = random.choice(states)
                found = random.randint(0, 1000)
                downloaded = random.randint(0, found)
                progress = (downloaded / found * 100) if found > 0 else 0

                progress_win.update_source(
                    source,
                    status=state,
                    found=found,
                    downloaded=downloaded,
                    progress=progress,
                    details=f"Processing batch {step + 1}"
                )
                progress_win.set_status(f"Processing step {step + 1} of 100...")

            progress_win.window.update()
            time.sleep(0.1)

        # Mark complete
        for source in sources:
            progress_win.update_source(
                source,
                status="Complete",
                progress=100
            )
        progress_win.mark_complete()

    # Run simulation in background
    progress_win.window.after(1000, simulate_progress)
    progress_win.run()
