import tkinter as tk
from tkinter import scrolledtext, ttk
import os
import time
import threading

# Path setup
import sys
sys.path.append(os.getcwd())

try:
    from src.utils import get_config
    config = get_config()
    cloud_path = config.get("cloud_storage", {}).get("path", ".")
    LOG_FILE = os.path.join(cloud_path, "reconstruction_log.txt")
except ImportError:
    LOG_FILE = "reconstruction_log.txt"

class LogViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("Reconstruction Log")
        self.root.geometry("800x600")
        
        # Text Area
        self.text_area = scrolledtext.ScrolledText(root, state='disabled', font=("Consolas", 10))
        self.text_area.pack(expand=True, fill='both', padx=10, pady=10)
        
        # Status Bar
        self.status = tk.StringVar()
        self.status.set(f"Looking for log at: {LOG_FILE}")
        lbl = ttk.Label(root, textvariable=self.status, relief=tk.SUNKEN, anchor=tk.W)
        lbl.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.last_pos = 0
        self.running = True
        
        # Start polling
        self.poll_log()
        
    def poll_log(self):
        if not self.running:
            return
            
        if os.path.exists(LOG_FILE):
            try:
                with open(LOG_FILE, "r", encoding='utf-8') as f:
                    # Seek to last read position
                    f.seek(self.last_pos)
                    new_data = f.read()
                    
                    if new_data:
                        self.last_pos = f.tell()
                        self.text_area.config(state='normal')
                        self.text_area.insert(tk.END, new_data)
                        self.text_area.see(tk.END)
                        self.text_area.config(state='disabled')
                        self.status.set(f"Reading {LOG_FILE} - Last updated: {time.strftime('%H:%M:%S')}")
                    else:
                        # Check if process is done? (Hard to know from file alone, unless we check for specific 'Completed' string)
                         self.status.set(f"Monitoring {LOG_FILE}...")
            except Exception as e:
                self.status.set(f"Error reading log: {e}")
        else:
             self.status.set(f"Log file not found yet at: {LOG_FILE}")
             
        # Poll every 1000ms
        self.root.after(1000, self.poll_log)

def main():
    root = tk.Tk()
    app = LogViewer(root)
    root.mainloop()

if __name__ == "__main__":
    main()
