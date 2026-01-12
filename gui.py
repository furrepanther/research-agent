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
        self.root.geometry("600x400")
        self.root.configure(bg="#f0f0f0")
        self.task_queue = task_queue
        self.stop_event = multiprocessing.Event()
        self.supervisor = None
        
        # Header
        header_frame = tk.Frame(root, bg="#2c3e50", pady=10)
        header_frame.pack(fill="x")
        lbl_title = tk.Label(header_frame, text="Antigravity Research Agent", font=("Helvetica", 16, "bold"), fg="white", bg="#2c3e50")
        lbl_title.pack()

        # Status Table
        columns = ("source", "status", "count", "details")
        self.tree = ttk.Treeview(root, columns=columns, show="headings", height=8)
        self.tree.heading("source", text="Source")
        self.tree.heading("status", text="Status")
        self.tree.heading("count", text="Papers")
        self.tree.heading("details", text="Details")
        
        self.tree.column("source", width=120)
        self.tree.column("status", width=100, anchor="center")
        self.tree.column("count", width=80, anchor="center")
        self.tree.column("details", width=280)
        
        self.tree.pack(pady=20, padx=20, fill="both", expand=True)
        
        # Init Rows
        self.sources = ["ArXiv", "Semantic Scholar", "LessWrong", "AI Labs"]
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
        self.log_area = scrolledtext.ScrolledText(log_frame, height=6, font=("Consolas", 9), state=tk.DISABLED, bg="#ffffff")
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

        self.root.after(100, self.process_queue)

    def start_agent(self):
        if any(p.is_alive() for p in self.worker_processes):
            return
            
        self.stop_event.clear()
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.is_running = True
        self.animate()
        
        # Reset Tree
        for src in self.sources:
            self.tree.item(self.row_ids[src], values=(src, "Waiting", "0", "-"))
        
        # Load prompt
        with open("prompt.txt", "r") as f:
            prompt = f.read().strip()
        
        # Import searchers and Supervisor
        from src.searchers.arxiv_searcher import ArxivSearcher
        from src.searchers.semantic_searcher import SemanticSearcher
        from src.searchers.lesswrong_searcher import LessWrongSearcher
        from src.searchers.lab_scraper import LabScraper
        from src.supervisor import Supervisor
        from src.storage import StorageManager
        
        # Determine Mode
        storage = StorageManager(get_config().get("db_path", "data/metadata.db"))
        mode = "DAILY" if storage.get_latest_date() else "BACKFILL"
        self.log_message(f"Detected search mode: {mode}")

        self.supervisor = Supervisor(self.task_queue, self.stop_event, prompt, 200, mode=mode)
        
        workers = [
            (ArxivSearcher, "ArXiv"),
            (SemanticSearcher, "Semantic Scholar"),
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
                        
                    self.btn_start.config(state=tk.NORMAL)
                    self.btn_stop.config(state=tk.DISABLED, text="Cancel Run")
                    
        except:
            pass
        finally:
            # Check if all workers are done
            if self.supervisor and not self.supervisor.is_any_alive():
                if self.is_running:  # Haven't sent DONE yet
                    self.task_queue.put({"type": "DONE"})
            
            self.root.after(100, self.process_queue)

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
