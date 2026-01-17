import os
import sys
import multiprocessing
import time
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

# --- ENVIRONMENT VALIDATION ---
def check_environment():
    """Ensure the script is running in the project virtual environment"""
    executable = sys.executable.lower()
    expected_venv = os.path.join(os.getcwd(), "venv")
    
    if "venv" not in executable and os.path.exists(expected_venv):
        try:
            # We use a temporary root just for the error box
            temp_root = tk.Tk()
            temp_root.withdraw()
            messagebox.showerror("Wrong Environment Detected", 
                        f"You are running the agent with the wrong Python interpreter:\n{sys.executable}\n\n"
                        "Please launch the agent using 'run_gui.bat' to ensure the virtual environment is used.")
            temp_root.destroy()
        except:
            print(f"\n[ERROR] WRONG ENVIRONMENT: Please run with 'run_gui.bat' or activate the venv first.")
        sys.exit(1)

# Run check before other imports
check_environment()

from src.utils import get_config, logger
import threading
from src.searchers.arxiv_searcher import ArxivSearcher
from src.searchers.lesswrong_searcher import LessWrongSearcher
from src.searchers.lab_scraper import LabScraper
from src.supervisor import Supervisor
from src.storage import StorageManager
from src.cloud_transfer import CloudTransferManager
from src.backup import BackupManager
from src.summary_window import SummaryWindow
import yaml

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


        # Log Area (Integrated scrollable text)
        log_frame = tk.LabelFrame(root, text="Agent Logs", bg="#f0f0f0", font=("Helvetica", 10, "bold"))
        log_frame.pack(pady=10, padx=20, fill="both", expand=True)
        
        self.log_area = scrolledtext.ScrolledText(log_frame, height=8, font=("Consolas", 9), state=tk.DISABLED, bg="#ffffff")
        self.log_area.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Mode Selector
        mode_frame = tk.Frame(root, bg="#f0f0f0", pady=5)
        mode_frame.pack()
        
        tk.Label(mode_frame, text="Run Mode:", bg="#f0f0f0", font=("Helvetica", 10, "bold")).pack(side=tk.LEFT, padx=(20, 5))
        
        self.mode_var = tk.StringVar(value="Automatic")
        mode_dropdown = ttk.Combobox(mode_frame, textvariable=self.mode_var, 
                                     values=["Automatic", "Test", "Backfill"],
                                     state="readonly", width=15, font=("Helvetica", 10))
        mode_dropdown.pack(side=tk.LEFT, padx=5)
        
        # Mode descriptions
        mode_help = tk.Label(mode_frame, 
                            text="Automatic: Uses latest DB date | Test: Count only, no downloads | Backfill: Full historical",
                            bg="#f0f0f0", font=("Helvetica", 8), fg="gray")
        mode_help.pack(side=tk.LEFT, padx=10)
        
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
        
        self.btn_backup = tk.Button(btn_frame, text="Backup", command=self.create_backup, bg="#16a085", fg="white", font=("Helvetica", 10, "bold"), width=15)
        self.btn_backup.pack(side=tk.LEFT, padx=10)
        
        self.btn_quit = tk.Button(btn_frame, text="Quit", command=self.quit_app, bg="#7f8c8d", fg="white", font=("Helvetica", 10, "bold"), width=15)
        self.btn_quit.pack(side=tk.LEFT, padx=10)

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
        
        # Reset Tree
        for src in self.sources:
            self.tree.item(self.row_ids[src], values=(src, "Waiting", "0", "-"))
        
        # Load prompt
        with open("prompts/prompt.txt", "r") as f:
            prompt = f.read().strip()
        
        # Import searchers and Supervisor (Now moved to top)
        
        # Determine Mode from dropdown
        config = get_config()
        storage = StorageManager(config.get("db_path", "data/metadata.db"))
        
        selected_mode = self.mode_var.get()
        
        if selected_mode == "Automatic":
            # Automatic: detect based on database
            latest_date_str = storage.get_latest_date()
            mode = "DAILY" if latest_date_str else "BACKFILL"
            self.log_message(f"Automatic mode: Detected {mode} (latest date: {latest_date_str or 'None'})")
        elif selected_mode == "Test":
            mode = "TEST"
            self.log_message("Test mode: Count only, no downloads or database updates")
        else:  # Backfill
            mode = "BACKFILL"
            self.log_message("Backfill mode: Full historical retrieval")
            
            # STAGING CLEANUP PROMPT (Bypass for TEST mode)
            from src.utils import clear_directory
            staging_dir = config.get("staging_dir", "F:/RESTMP")
            if mode != "TEST" and os.path.exists(staging_dir) and os.listdir(staging_dir):
                from tkinter import messagebox
                if messagebox.askyesno("Clear Staging Area?", 
                                      f"Backfill mode detected.\n\nWould you like to delete temporary files in '{staging_dir}' before starting?"):
                    self.log_message(f"Clearing staging directory: {staging_dir}")
                    clear_directory(staging_dir)
                    self.log_message("Staging area cleared.")
        
        self.mode = mode  # Store mode for later reference (summary window)
        self.root.title(f"Research Agent Status - {mode} Mode")

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

    def quit_app(self):
        """Quit application with comprehensive cleanup"""
        from tkinter import messagebox
        
        # Confirm quit
        is_running = hasattr(self, 'is_running') and self.is_running
        if is_running:
            if not messagebox.askyesno("Quit?", "Agent is running. Stop and quit?"):
                return
        else:
            if not messagebox.askyesno("Quit", "Are you sure you want to quit?"):
                return
        
        # Stop agent if running
        if is_running:
            self.stop_agent()
            # Give processes a moment to stop
            self.root.after(500, self._finish_quit)
        else:
            self._finish_quit()
    
    def _finish_quit(self):
        """Complete the quit process after stopping workers"""
        import sys
        import os
        
        # Close progress window if it exists
        if hasattr(self, 'progress_window') and self.progress_window:
            try:
                self.progress_window.destroy()
            except:
                pass
        
        # Terminate supervisor processes
        if hasattr(self, 'supervisor') and self.supervisor:
            try:
                for worker_name, worker_info in self.supervisor.workers.items():
                    proc = worker_info.get('process')
                    if proc and proc.is_alive():
                        proc.terminate()
            except:
                pass
        
        # Destroy window
        try:
            self.root.destroy()
        except:
            pass
        
        # Force exit
        os._exit(0)

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
                        
                        # BACKFILL MODE: Ask to transfer to cloud storage
                        if hasattr(self, 'mode') and self.mode == "BACKFILL":
                            self._show_transfer_dialog()

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
                    self.is_running = False # Mark as stopped
                    self.btn_start.config(state=tk.NORMAL)
                    self.btn_stop.config(state=tk.DISABLED)
                    self.root.config(cursor="")
                    
                    self.task_queue.put({"type": "DONE"})
                    
                    # TRIGGER FINAL WORKFLOW
                    self.root.after(500, self._show_summary_window)
                    if self.mode == "BACKFILL":
                        self.root.after(1000, self._show_transfer_dialog)

            self.root.after(100, self.process_queue)

    def _show_summary_window(self):
        """Open summary window with newly downloaded papers"""
        try:
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
    
    def _show_transfer_dialog(self):
        """Ask user if they want to transfer files to cloud storage"""
        
        try:
            result = messagebox.askyesno(
                "Commit Changes?",
                "Commit files and database changes? (this cannot be undone)\n\n"
                "This will move papers from F:\\RESTMP to R:\\MyDrive\\03 Research Papers.",
                icon='warning'
            )
            
            if result:
                self.log_message("Starting cloud transfer...")
                config = get_config()
                transfer_mgr = CloudTransferManager(config)
                
                success = transfer_mgr.transfer_folders()
                
                if success:
                    self.log_message("Cloud transfer complete!")
                else:
                    self.log_message("Cloud transfer cancelled or failed")
            else:
                self.log_message("Cloud transfer skipped")
                
        except Exception as e:
            self.log_message(f"Error during transfer: {e}")
    
    def create_backup(self):
        """Create a backup of cloud storage"""
        
        try:
            self.log_message("Creating backup...")
            config = get_config()
            backup_mgr = BackupManager(config)
            
            backup_path = backup_mgr.create_backup()
            
            if backup_path:
                self.log_message(f"Backup created: {backup_path}")
            else:
                self.log_message("Backup cancelled")
                
        except Exception as e:
            self.log_message(f"Error during backup: {e}")


    def open_settings(self):
        """Open settings dialog"""

        settings_window = tk.Toplevel(self.root)
        settings_window.title("Research Agent Settings")
        settings_window.geometry("600x650")
        settings_window.resizable(False, False)

        # Center the settings window
        settings_window.update_idletasks()
        x = (settings_window.winfo_screenwidth() - 600) // 2
        y = (settings_window.winfo_screenheight() - 650) // 2
        settings_window.geometry(f"600x650+{x}+{y}")

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

        # Cloud & Staging (Primary)
        ttk.Label(path_frame, text="Primary Library (Cloud Storage)", font=("Helvetica", 10, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 5))
        
        ttk.Label(path_frame, text="Cloud Storage Path:").grid(row=1, column=0, sticky="w", pady=5)
        cloud_path = tk.Entry(path_frame, width=50)
        cloud_path.insert(0, config.get("cloud_storage", {}).get("path", "R:/My Drive/03 Research Papers"))
        cloud_path.grid(row=1, column=1, sticky="w", pady=5)

        ttk.Label(path_frame, text="Temporary Staging (F: Drive):").grid(row=2, column=0, sticky="w", pady=5)
        staging_path = tk.Entry(path_frame, width=50)
        staging_path.insert(0, config.get("staging_dir", "F:/RESTMP"))
        staging_path.grid(row=2, column=1, sticky="w", pady=5)

        # Internal Data Paths
        ttk.Label(path_frame, text="Internal Agent Data", font=("Helvetica", 10, "bold")).grid(row=3, column=0, columnspan=2, sticky="w", pady=(15, 5))
        
        ttk.Label(path_frame, text="Data Root (Local Meta):").grid(row=4, column=0, sticky="w", pady=5)
        storage_path = tk.Entry(path_frame, width=50)
        storage_path.insert(0, config.get("storage_path", "data"))
        storage_path.grid(row=4, column=1, sticky="w", pady=5)

        ttk.Label(path_frame, text="Local PDF Cache:").grid(row=5, column=0, sticky="w", pady=5)
        papers_dir = tk.Entry(path_frame, width=50)
        papers_dir.insert(0, config.get("papers_dir", "data/papers"))
        papers_dir.grid(row=5, column=1, sticky="w", pady=5)

        ttk.Label(path_frame, text="Metadata Database:").grid(row=6, column=0, sticky="w", pady=5)
        db_path = tk.Entry(path_frame, width=50)
        db_path.insert(0, config.get("db_path", "data/metadata.db"))
        db_path.grid(row=6, column=1, sticky="w", pady=5)

        # Cloud Options
        ttk.Label(path_frame, text="Cloud Settings", font=("Helvetica", 10, "bold")).grid(row=7, column=0, columnspan=2, sticky="w", pady=(15, 5))
        
        cloud_enabled = tk.BooleanVar(value=config.get("cloud_storage", {}).get("enabled", True))
        ttk.Checkbutton(path_frame, text="Enable Cloud Protection", variable=cloud_enabled).grid(row=8, column=0, sticky="w")

        cloud_check_dupes = tk.BooleanVar(value=config.get("cloud_storage", {}).get("check_duplicates", True))
        ttk.Checkbutton(path_frame, text="Check Cloud for Duplicates", variable=cloud_check_dupes).grid(row=8, column=1, sticky="w")
        
        # Backup Directory
        ttk.Label(path_frame, text="Backup Settings", font=("Helvetica", 10, "bold")).grid(row=9, column=0, columnspan=2, sticky="w", pady=(15, 5))
        ttk.Label(path_frame, text="Backup Target:").grid(row=10, column=0, sticky="w", pady=5)
        backup_path = tk.Entry(path_frame, width=50)
        backup_path.insert(0, config.get("cloud_storage", {}).get("backup_path", ""))
        backup_path.grid(row=10, column=1, sticky="w", pady=5)
        
        # Help text
        help_text = tk.Label(path_frame, text="Note: Paths will be created automatically if they don't exist.\nRestart the application after changing paths.", 
                            font=("Helvetica", 8), fg="gray", justify="left")
        help_text.grid(row=11, column=0, columnspan=2, sticky="w", pady=(15, 0))

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
                # Update mode settings
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
                
                # Update general path settings
                config["storage_path"] = storage_path.get()
                config["papers_dir"] = papers_dir.get()
                config["db_path"] = db_path.get()
                config["staging_dir"] = staging_path.get()
                
                # Update cloud storage settings
                if "cloud_storage" not in config:
                    config["cloud_storage"] = {}
                config["cloud_storage"]["path"] = cloud_path.get()
                config["cloud_storage"]["enabled"] = cloud_enabled.get()
                config["cloud_storage"]["check_duplicates"] = cloud_check_dupes.get()
                config["cloud_storage"]["backup_path"] = backup_path.get()
                
                # Update retry settings
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
