import tkinter as tk
from tkinter import ttk
import multiprocessing
import time
import sys
from src.utils import get_config, logger

class AgentGUI:
    def __init__(self, root, task_queue):
        self.root = root
        self.root.title("Research Agent Status")
        self.root.configure(bg="#f0f0f0")
        self.task_queue = task_queue
        self.stop_event = multiprocessing.Event()
        self.supervisor = None

        # Set window size and constraints
        window_width = 800
        window_height = 600
        self.root.geometry(f"{window_width}x{window_height}")
        self.root.minsize(600, 400)  # Minimum size constraints
        self.root.resizable(True, True)  # Allow resizing

        # Center window on screen
        self._center_window(window_width, window_height)
        
        # Header
        header_frame = tk.Frame(root, bg="#2c3e50", pady=10)
        header_frame.pack(fill="x")
        lbl_title = tk.Label(header_frame, text="Antigravity Research Agent", font=("Helvetica", 16, "bold"), fg="white", bg="#2c3e50")
        lbl_title.pack()

        # Status Table
        columns = ("source", "status", "count", "details")
        self.tree = ttk.Treeview(root, columns=columns, show="headings", height=10)
        self.tree.heading("source", text="Source")
        self.tree.heading("status", text="Status")
        self.tree.heading("count", text="Papers")
        self.tree.heading("details", text="Details")

        self.tree.column("source", width=150)
        self.tree.column("status", width=120, anchor="center")
        self.tree.column("count", width=100, anchor="center")
        self.tree.column("details", width=400)
        
        self.tree.pack(pady=20, padx=20, fill="both", expand=True)
        
        # Init Rows
        self.sources = ["ArXiv", "LessWrong", "AI Labs"]  # Removed Semantic Scholar
        self.row_ids = {}
        for src in self.sources:
            item_id = self.tree.insert("", "end", values=(src, "Waiting", "0", "-"))
            self.row_ids[src] = item_id

        # Animation Canvas (Throbber)
        self.canvas = tk.Canvas(root, width=50, height=50, bg="#f0f0f0", highlightthickness=0)
        self.canvas.pack(pady=10)
        self.spinner_angle = 0
        self.is_running = True
        self.animate()
        
        # Log Area (Integrated scrollable text)
        log_frame = tk.LabelFrame(root, text="Agent Logs", bg="#f0f0f0", font=("Helvetica", 10, "bold"))
        log_frame.pack(pady=10, padx=20, fill="both", expand=True)
        
        from tkinter import scrolledtext
        self.log_area = scrolledtext.ScrolledText(log_frame, height=8, font=("Consolas", 9), state=tk.DISABLED, bg="#ffffff")
        self.log_area.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.lbl_status = tk.Label(root, text="Ready...", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.lbl_status.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Control Buttons
        btn_frame = tk.Frame(root, pady=10, bg="#f0f0f0")
        btn_frame.pack()
        
        self.btn_start = tk.Button(btn_frame, text="Start Agent", command=self.start_agent, bg="#27ae60", fg="white", font=("Helvetica", 10, "bold"), width=15)
        self.btn_start.pack(side=tk.LEFT, padx=10)
        
        self.btn_stop = tk.Button(btn_frame, text="Cancel Run", command=self.stop_agent, bg="#c0392b", fg="white", font=("Helvetica", 10, "bold"), state=tk.DISABLED, width=15)
        self.btn_stop.pack(side=tk.LEFT, padx=10)

        self.btn_settings = tk.Button(btn_frame, text="Settings", command=self.open_settings, bg="#34495e", fg="white", font=("Helvetica", 10, "bold"), width=15)
        self.btn_settings.pack(side=tk.LEFT, padx=10)

        # Keyboard shortcuts
        self.root.bind('<Return>', lambda e: self.start_agent() if self.btn_start['state'] == tk.NORMAL else None)
        self.root.bind('<Escape>', lambda e: self.stop_agent() if self.btn_stop['state'] == tk.NORMAL else self.root.quit())

        self.root.after(100, self.process_queue)

    def _center_window(self, width, height):
        """Center the window on the screen"""
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def start_agent(self):
        # Check if supervisor exists and has running workers
        if self.supervisor and self.supervisor.is_any_alive():
            self.log_message("Workers already running. Please wait for completion or cancel.")
            return

        self.stop_event.clear()
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.is_running = True
        self.root.config(cursor="watch")  # Busy cursor
        self.animate()
        
        # Reset Tree
        for src in self.sources:
            self.tree.item(self.row_ids[src], values=(src, "Waiting", "0", "-"))
        
        # Load prompt
        with open("prompt.txt", "r") as f:
            prompt = f.read().strip()
        
        # Import searchers and Supervisor
        from src.searchers.arxiv_searcher import ArxivSearcher
        # from src.searchers.semantic_searcher import SemanticSearcher  # DISABLED
        from src.searchers.lesswrong_searcher import LessWrongSearcher
        from src.searchers.lab_scraper import LabScraper
        from src.supervisor import Supervisor
        from src.storage import StorageManager
        
        # Determine Mode
        config = get_config()
        storage = StorageManager(config.get("db_path", "data/metadata.db"))
        latest_date_str = storage.get_latest_date()
        mode = "DAILY" if latest_date_str else "BACKFILL"
        self.mode = mode  # Store mode for later reference (summary window)
        self.root.title(f"Research Agent Status - {mode} Mode")
        self.log_message(f"Detected search mode: {mode}")

        # Get mode-specific settings
        from datetime import datetime
        mode_key = mode.lower()
        mode_settings = config.get("mode_settings", {}).get(mode_key, {})

        # Build search parameters
        max_papers_per_agent = mode_settings.get("max_papers_per_agent")
        if max_papers_per_agent is None:  # None means unlimited for backfill
            max_papers_per_agent = float('inf')

        per_query_limit = mode_settings.get("per_query_limit", 10)
        respect_date_range = mode_settings.get("respect_date_range", True)

        # Set start_date based on mode
        if mode == "DAILY" and latest_date_str:
            start_date = datetime.strptime(latest_date_str, "%Y-%m-%d")
        else:
            start_date = datetime(2003, 1, 1)

        search_params = {
            'max_papers_per_agent': max_papers_per_agent,
            'per_query_limit': per_query_limit,
            'respect_date_range': respect_date_range,
            'start_date': start_date
        }

        self.log_message(f"Limits: {int(max_papers_per_agent) if max_papers_per_agent != float('inf') else 'UNLIMITED'} total, {per_query_limit} per query")

        self.supervisor = Supervisor(self.task_queue, self.stop_event, prompt, search_params, mode=mode)

        workers = [
            (ArxivSearcher, "ArXiv"),
            # (SemanticSearcher, "Semantic Scholar"),  # DISABLED: Low success rate (~8%) due to missing PDF URLs
            (LessWrongSearcher, "LessWrong"),
            (LabScraper, "AI Labs")
        ]

        for searcher_class, display_name in workers:
            self.supervisor.start_worker(searcher_class, display_name)

    def stop_agent(self):
        if self.stop_event.is_set():
            return
        self.stop_event.set()
        if self.supervisor:
            self.supervisor.stop_all()
        self.root.config(cursor="")  # Restore normal cursor
        self.lbl_status.config(text="Stopping...")
        self.btn_stop.config(state=tk.DISABLED, text="Stopping...")

    def animate(self):
        if not self.is_running:
            return
        self.canvas.delete("all")
        # Draw spinner
        x, y, r = 25, 25, 15
        end_angle = self.spinner_angle + 90
        # Check if actually running to show distinct state or just idle
        active = self.supervisor.is_any_alive() if self.supervisor else False
        color = "#3498db" if active else "#bdc3c7"
        
        self.canvas.create_arc(x-r, y-r, x+r, y+r, start=self.spinner_angle, extent=90, style=tk.ARC, outline=color, width=4)
        self.spinner_angle = (self.spinner_angle + 10) % 360
        self.root.after(50, self.animate)

    def process_queue(self):
        try:
            while True:
                msg = self.task_queue.get_nowait()
                msg_type = msg.get("type")
                
                if msg_type == "UPDATE_ROW":
                    src = msg.get("source")
                    status = msg.get("status")
                    count = msg.get("count")
                    details = msg.get("details")

                    if src in self.row_ids:
                        current_vals = self.tree.item(self.row_ids[src])['values']
                        # Update only provided values
                        new_vals = list(current_vals)
                        if status: new_vals[1] = status
                        if count is not None: new_vals[2] = count
                        if details: new_vals[3] = details
                        self.tree.item(self.row_ids[src], values=new_vals)

                    # Update heartbeat
                    if self.supervisor and src in self.supervisor.workers:
                        import time
                        self.supervisor.workers[src]['last_heartbeat'] = time.time()
                        
                elif msg_type == "LOG":
                    self.log_message(msg.get("text"))
                    
                elif msg_type == "STATUS_BAR":
                    self.lbl_status.config(text=msg.get("text"))
                    self.log_message(f"STATUS: {msg.get('text')}")
                    
                elif msg_type == "ERROR":
                    if self.supervisor:
                        self.supervisor.handle_error(msg)

                elif msg_type == "DONE":
                    self.is_running = False
                    self.root.config(cursor="")  # Restore normal cursor
                    self.canvas.delete("all")
                    # Check if stopped or finished
                    if self.stop_event.is_set():
                        self.canvas.create_text(25, 25, text="⛔", font=("Helvetica", 24), fill="red")
                        self.lbl_status.config(text="Cancelled by user.")
                        self.log_message("RUN CANCELLED.")
                    else:
                        self.canvas.create_text(25, 25, text="✔", font=("Helvetica", 24), fill="green")
                        self.lbl_status.config(text="Finished.")
                        self.log_message("RUN COMPLETE.")

                        # Always open summary window after completion
                        self._show_summary_window()

                    self.btn_start.config(state=tk.NORMAL)
                    self.btn_stop.config(state=tk.DISABLED, text="Cancel Run")
                    
        except:
            pass
        finally:
            # Check for timeouts
            if self.supervisor:
                self.supervisor.check_timeouts()

            # Check if all workers are done
            if self.supervisor and not self.supervisor.is_any_alive():
                if self.is_running:  # Haven't sent DONE yet
                    self.task_queue.put({"type": "DONE"})

            self.root.after(100, self.process_queue)

    def _show_summary_window(self):
        """Open summary window with newly downloaded papers"""
        try:
            from src.summary_window import SummaryWindow
            from src.storage import StorageManager
            from src.utils import get_config

            config = get_config()
            storage = StorageManager(config.get("db_path", "data/metadata.db"))

            # Get papers from current run
            if hasattr(self, 'supervisor') and hasattr(self.supervisor, 'run_id'):
                papers = storage.get_papers_by_run_id(self.supervisor.run_id)
            else:
                # Fallback: get all unsynced papers
                papers = storage.get_unsynced_papers()

            # Get current mode
            mode = getattr(self, 'mode', 'UNKNOWN')

            if papers or mode == "BACKFILL":
                # Pass mode to summary window
                SummaryWindow(
                    papers if papers else [],
                    getattr(self.supervisor, 'run_id', 'unknown') if hasattr(self, 'supervisor') else 'unknown',
                    mode=mode
                )
                self.log_message(f"Summary window opened with {len(papers)} papers.")
            else:
                self.log_message("No new papers to display.")
        except Exception as e:
            self.log_message(f"Error opening summary window: {e}")

    def open_settings(self):
        """Open settings dialog"""
        from tkinter import messagebox
        import yaml

        settings_window = tk.Toplevel(self.root)
        settings_window.title("Research Agent Settings")
        settings_window.geometry("600x500")
        settings_window.resizable(False, False)

        # Center the settings window
        settings_window.update_idletasks()
        x = (settings_window.winfo_screenwidth() - 600) // 2
        y = (settings_window.winfo_screenheight() - 500) // 2
        settings_window.geometry(f"600x500+{x}+{y}")

        # Load current config
        config = get_config()

        # Create notebook for tabs
        notebook = ttk.Notebook(settings_window)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Tab 1: Mode Settings
        mode_frame = ttk.Frame(notebook, padding=20)
        notebook.add(mode_frame, text="Mode Settings")

        # TESTING Mode
        ttk.Label(mode_frame, text="TESTING Mode", font=("Helvetica", 11, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))
        ttk.Label(mode_frame, text="Max Papers Per Agent:").grid(row=1, column=0, sticky="w", pady=5)
        testing_max = tk.Entry(mode_frame, width=20)
        testing_max.insert(0, str(config.get("mode_settings", {}).get("testing", {}).get("max_papers_per_agent", 10)))
        testing_max.grid(row=1, column=1, sticky="w", pady=5)

        ttk.Label(mode_frame, text="Per Query Limit:").grid(row=2, column=0, sticky="w", pady=5)
        testing_limit = tk.Entry(mode_frame, width=20)
        testing_limit.insert(0, str(config.get("mode_settings", {}).get("testing", {}).get("per_query_limit", 5)))
        testing_limit.grid(row=2, column=1, sticky="w", pady=5)

        # DAILY Mode
        ttk.Label(mode_frame, text="DAILY Mode", font=("Helvetica", 11, "bold")).grid(row=3, column=0, columnspan=2, sticky="w", pady=(20, 10))
        ttk.Label(mode_frame, text="Max Papers Per Agent:").grid(row=4, column=0, sticky="w", pady=5)
        daily_max = tk.Entry(mode_frame, width=20)
        daily_max.insert(0, str(config.get("mode_settings", {}).get("daily", {}).get("max_papers_per_agent", 50)))
        daily_max.grid(row=4, column=1, sticky="w", pady=5)

        ttk.Label(mode_frame, text="Per Query Limit:").grid(row=5, column=0, sticky="w", pady=5)
        daily_limit = tk.Entry(mode_frame, width=20)
        daily_limit.insert(0, str(config.get("mode_settings", {}).get("daily", {}).get("per_query_limit", 20)))
        daily_limit.grid(row=5, column=1, sticky="w", pady=5)

        # BACKFILL Mode
        ttk.Label(mode_frame, text="BACKFILL Mode", font=("Helvetica", 11, "bold")).grid(row=6, column=0, columnspan=2, sticky="w", pady=(20, 10))
        ttk.Label(mode_frame, text="Max Papers Per Agent:").grid(row=7, column=0, sticky="w", pady=5)
        backfill_max = tk.Entry(mode_frame, width=20)
        backfill_val = config.get("mode_settings", {}).get("backfill", {}).get("max_papers_per_agent")
        backfill_max.insert(0, "unlimited" if backfill_val is None else str(backfill_val))
        backfill_max.grid(row=7, column=1, sticky="w", pady=5)

        ttk.Label(mode_frame, text="Per Query Limit:").grid(row=8, column=0, sticky="w", pady=5)
        backfill_limit = tk.Entry(mode_frame, width=20)
        backfill_limit.insert(0, str(config.get("mode_settings", {}).get("backfill", {}).get("per_query_limit", 10)))
        backfill_limit.grid(row=8, column=1, sticky="w", pady=5)

        # Tab 2: Paths
        path_frame = ttk.Frame(notebook, padding=20)
        notebook.add(path_frame, text="Paths")

        ttk.Label(path_frame, text="Storage Path:").grid(row=0, column=0, sticky="w", pady=5)
        storage_path = tk.Entry(path_frame, width=50)
        storage_path.insert(0, config.get("storage_path", "data"))
        storage_path.grid(row=0, column=1, sticky="w", pady=5)

        ttk.Label(path_frame, text="Papers Directory:").grid(row=1, column=0, sticky="w", pady=5)
        papers_dir = tk.Entry(path_frame, width=50)
        papers_dir.insert(0, config.get("papers_dir", "data/papers"))
        papers_dir.grid(row=1, column=1, sticky="w", pady=5)

        ttk.Label(path_frame, text="Database Path:").grid(row=2, column=0, sticky="w", pady=5)
        db_path = tk.Entry(path_frame, width=50)
        db_path.insert(0, config.get("db_path", "data/metadata.db"))
        db_path.grid(row=2, column=1, sticky="w", pady=5)

        # Tab 3: Retry Settings
        retry_frame = ttk.Frame(notebook, padding=20)
        notebook.add(retry_frame, text="Retry Settings")

        ttk.Label(retry_frame, text="Max Worker Retries:").grid(row=0, column=0, sticky="w", pady=5)
        max_retries = tk.Entry(retry_frame, width=20)
        max_retries.insert(0, str(config.get("retry_settings", {}).get("max_worker_retries", 2)))
        max_retries.grid(row=0, column=1, sticky="w", pady=5)

        ttk.Label(retry_frame, text="Worker Timeout (seconds):").grid(row=1, column=0, sticky="w", pady=5)
        worker_timeout = tk.Entry(retry_frame, width=20)
        worker_timeout.insert(0, str(config.get("retry_settings", {}).get("worker_timeout", 600)))
        worker_timeout.grid(row=1, column=1, sticky="w", pady=5)

        ttk.Label(retry_frame, text="API Max Retries:").grid(row=2, column=0, sticky="w", pady=5)
        api_retries = tk.Entry(retry_frame, width=20)
        api_retries.insert(0, str(config.get("retry_settings", {}).get("api_max_retries", 3)))
        api_retries.grid(row=2, column=1, sticky="w", pady=5)

        # Save button
        def save_settings():
            try:
                # Update config
                config["mode_settings"]["testing"]["max_papers_per_agent"] = int(testing_max.get())
                config["mode_settings"]["testing"]["per_query_limit"] = int(testing_limit.get())
                config["mode_settings"]["daily"]["max_papers_per_agent"] = int(daily_max.get())
                config["mode_settings"]["daily"]["per_query_limit"] = int(daily_limit.get())

                backfill_max_val = backfill_max.get().strip().lower()
                if backfill_max_val == "unlimited" or backfill_max_val == "null":
                    config["mode_settings"]["backfill"]["max_papers_per_agent"] = None
                else:
                    config["mode_settings"]["backfill"]["max_papers_per_agent"] = int(backfill_max_val)

                config["mode_settings"]["backfill"]["per_query_limit"] = int(backfill_limit.get())
                config["storage_path"] = storage_path.get()
                config["papers_dir"] = papers_dir.get()
                config["db_path"] = db_path.get()
                config["retry_settings"]["max_worker_retries"] = int(max_retries.get())
                config["retry_settings"]["worker_timeout"] = int(worker_timeout.get())
                config["retry_settings"]["api_max_retries"] = int(api_retries.get())

                # Save to file
                with open("config.yaml", "w") as f:
                    yaml.dump(config, f, default_flow_style=False, sort_keys=False)

                messagebox.showinfo("Success", "Settings saved successfully!")
                settings_window.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save settings: {e}")

        btn_frame = ttk.Frame(settings_window)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Save", command=save_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=settings_window.destroy).pack(side=tk.LEFT, padx=5)

    def log_message(self, message):
        self.log_area.config(state=tk.NORMAL)
        timestamp = time.strftime("%H:%M:%S")
        self.log_area.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_area.see(tk.END)
        self.log_area.config(state=tk.DISABLED)

def run_gui():
    root = tk.Tk()
    q = multiprocessing.Queue()
    gui = AgentGUI(root, q)
    root.mainloop()


if __name__ == "__main__":
    # Required for multiprocessing on Windows
    multiprocessing.freeze_support()
    run_gui()
