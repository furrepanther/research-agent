import os
import sys
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import webbrowser
from datetime import datetime
import threading
import glob

# Add project root to path for imports if needed, though this is standalone
sys.path.append(os.getcwd())
from src.utils import get_config, save_config
from src.kindle_sender import KindleSender

try:
    import keyring
except ImportError:
    keyring = None

class ResearchViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("Research Document Viewer")
        self.root.geometry("1400x900")
        
        # Configure Styles
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("Treeview", rowheight=25)
        self.style.configure("Treeview.Heading", font=('Segoe UI', 9, 'bold'))
        
        # Data
        self.config = get_config()
        
        # Use Cloud DB as requested
        cloud_path = self.config.get("cloud_storage", {}).get("path")
        if cloud_path and os.path.exists(cloud_path):
            self.db_path = os.path.join(cloud_path, "metadata.db")
        else:
            # Fallback to local if cloud not configured/found
            print("WARNING: Cloud path not found, falling back to local DB setting.")
            raw_db_path = self.config.get("db_path", "data/metadata.db")
            self.db_path = os.path.abspath(raw_db_path)
            
        print(f"DEBUG: Research Viewer using Database: {self.db_path}")
        self.all_papers = [] # List of tuples/dicts
        self.current_sort_col = "downloaded_date"
        self.current_sort_desc = True
        
        # Layout
        self._create_widgets()
        
        # Load Data
        self.refresh_data()

    def _create_widgets(self):
        # 1. Top Bar (Search & Refresh)
        top_frame = ttk.Frame(self.root, padding="10")
        top_frame.pack(fill=tk.X)
        
        ttk.Label(top_frame, text="Search:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._on_search_change)
        search_entry = ttk.Entry(top_frame, textvariable=self.search_var, width=40)
        search_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(top_frame, text="Refresh", command=self.refresh_data).pack(side=tk.LEFT)
        ttk.Button(top_frame, text="⚙ Settings", command=self._open_settings_dialog).pack(side=tk.LEFT, padx=(5, 0))
        ttk.Label(top_frame, text=f"Database: {self.db_path}", font=("Segoe UI", 8, "italic"), foreground="gray").pack(side=tk.RIGHT)

        # 2. Main Split View (Horizontal)
        self.paned_main = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.paned_main.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # LEFT: List View
        left_frame = ttk.Frame(self.paned_main)
        self.paned_main.add(left_frame, weight=2)
        
        # Treeview Scrollbars
        tree_scroll_y = ttk.Scrollbar(left_frame)
        tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        tree_scroll_x = ttk.Scrollbar(left_frame, orient=tk.HORIZONTAL)
        tree_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Treeview
        columns = ("title", "source", "published_date", "downloaded_date")
        self.tree = ttk.Treeview(left_frame, columns=columns, show="headings", 
                                 yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)
        
        # Column Headings with Sort
        self.tree.heading("title", text="ID / Title", command=lambda: self._sort_column("title"))
        self.tree.heading("source", text="Source", command=lambda: self._sort_column("source"))
        self.tree.heading("published_date", text="Published", command=lambda: self._sort_column("published_date"))
        self.tree.heading("downloaded_date", text="Downloaded", command=lambda: self._sort_column("downloaded_date"))
        
        self.tree.column("title", width=400, minwidth=200)
        self.tree.column("source", width=100, minwidth=50)
        self.tree.column("published_date", width=100, minwidth=80)
        self.tree.column("downloaded_date", width=150, minwidth=100)
        
        self.tree.pack(fill=tk.BOTH, expand=True)
        tree_scroll_y.config(command=self.tree.yview)
        tree_scroll_x.config(command=self.tree.xview)
        
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # RIGHT: Detail View (Vertical Split)
        self.paned_detail = ttk.PanedWindow(self.paned_main, orient=tk.VERTICAL)
        self.paned_main.add(self.paned_detail, weight=1)
        
        # Upper Detail: Meta & Buttons
        right_upper = ttk.Frame(self.paned_detail, padding="10")
        self.paned_detail.add(right_upper, weight=0) # weight 0 for meta area
        
        # Title Label
        self.lbl_title = tk.Text(right_upper, wrap=tk.WORD, height=3, font=("Segoe UI", 12, "bold"), bg="#f0f0f0", relief="flat", state="disabled")
        self.lbl_title.pack(fill=tk.X, pady=(0, 10))
        
        # Meta Info
        meta_frame = ttk.Frame(right_upper)
        meta_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.lbl_authors = ttk.Label(meta_frame, text="Authors: -", wraplength=400)
        self.lbl_authors.pack(anchor="w")
        
        self.lbl_published = ttk.Label(meta_frame, text="Published: -")
        self.lbl_published.pack(anchor="w")

        # Buttons
        btn_frame = ttk.Frame(right_upper)
        btn_frame.pack(fill=tk.X, pady=10)
        
        self.btn_open_file = ttk.Button(btn_frame, text="📂 Open File", state="disabled", command=self._open_file)
        self.btn_open_file.pack(side=tk.LEFT, padx=(0, 10))
        
        self.btn_open_url = ttk.Button(btn_frame, text="🌐 Open URL", state="disabled", command=self._open_url)
        self.btn_open_url.pack(side=tk.LEFT, padx=(0, 10))
        
        self.btn_kindle = ttk.Button(btn_frame, text="📲 Send to Kindle", state="disabled", command=self._send_to_kindle)
        self.btn_kindle.pack(side=tk.LEFT, padx=(0, 10))
        
        self.btn_print = ttk.Button(btn_frame, text="🖨️ Print", state="disabled", command=self._print_file)
        self.btn_print.pack(side=tk.LEFT, padx=(0, 10))
        
        self.btn_email = ttk.Button(btn_frame, text="✉️ Email", state="disabled", command=self._email_info)
        self.btn_email.pack(side=tk.LEFT)

        # Lower Detail: Abstract
        right_lower = ttk.Frame(self.paned_detail, padding="10")
        self.paned_detail.add(right_lower, weight=1)

        # Abstract
        ttk.Label(right_lower, text="Abstract:", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.txt_abstract = scrolledtext.ScrolledText(right_lower, wrap=tk.WORD, font=("Segoe UI", 10))
        self.txt_abstract.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        self.txt_abstract.config(state="disabled")

        # Status Bar
        self.status_var = tk.StringVar()
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor="w")
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Set Initial Sash Positions
        self.root.after(500, self._set_initial_sashes)

    def _set_initial_sashes(self):
        # Force update to ensure window sizes are calculated
        self.root.update()
        
        # Set main split (List vs Details)
        # Use a percentage of width if possible, or check current width
        width = self.root.winfo_width()
        if width > 100:
            target_x = int(width * 0.6) # 60% for list
            self.paned_main.sashpos(0, target_x)
            
        # Set detail split (Meta vs Abstract)
        # We want about 300px for the top area
        self.paned_detail.sashpos(0, 300)

    def _format_authors(self, authors_str):
        if not authors_str:
            return "Unknown"
        
        # Split by common delimiters
        import re
        authors = re.split(r'[,;]', authors_str)
        authors = [a.strip() for a in authors if a.strip()]
        
        if len(authors) > 5:
            return ", ".join(authors[:5]) + ", et al."
        return ", ".join(authors)

    def refresh_data(self):
        self.status_var.set("Loading data...")
        self.root.update_idletasks()
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Fetch all papers (using papers_new schema implied by high_efficiency migration, 
            # but usually it's aliased to 'papers' or we use 'papers' if v4 migration renamed it back?
            # src/storage.py usually does renaming. Let's assume 'papers' table exists.)
            # We select relevant columns
            query = "SELECT id, title, source, published_date, downloaded_date, authors, abstract, pdf_path, source_url FROM papers"
            
            try:
                cursor.execute(query)
            except sqlite3.OperationalError:
                # Fallback if v4 not fully applied or table name mismatch?
                # Usually v4 renames 'papers_new' to 'papers'.
                # Check for 'papers_new' just in case?
                query = "SELECT id, title, source, published_date, downloaded_date, authors, abstract, pdf_path, source_url FROM papers_new"
                cursor.execute(query)
                
            self.all_papers = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            self._filter_and_sort()
            self.status_var.set(f"Loaded {len(self.all_papers)} papers.")
            
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to load database: {e}")
            self.status_var.set("Error loading data.")

    def _filter_and_sort(self):
        search_term = self.search_var.get().lower()
        
        # Filter
        filtered = []
        for p in self.all_papers:
            # Match title, authors, or abstract
            text = f"{p.get('title','')} {p.get('authors','')} {p.get('abstract','')}".lower()
            if not search_term or search_term in text:
                filtered.append(p)
                
        # Sort
        col = self.current_sort_col
        rev = self.current_sort_desc
        
        # Helper for handling None
        def sort_key(x):
            val = x.get(col)
            if val is None: return ""
            return str(val).lower()
            
        filtered.sort(key=sort_key, reverse=rev)
        
        # Update Treeview
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        for p in filtered:
            # Display ID in title column for reference
            clean_title = self._beautify_text(p.get('title', ''))
            display_title = f"[{p.get('id')}] {clean_title}"
            
            # Format dates nicely?
            pub = p.get('published_date', '')
            dl = p.get('downloaded_date', '')
            
            # Insert
            # We store the FULL paper dict in 'values' or tags? 
            # Treeview stores values for columns. We can store the index/ID in iid.
            # Using paper ID as iid is safe since it's integer PK.
            self.tree.insert("", "end", iid=str(p['id']), values=(display_title, p['source'], pub, dl))
            
        # Update Sort Indicator in header
        cols = ["title", "source", "published_date", "downloaded_date"]
        for c in cols:
            text = self.tree.heading(c, "text").replace(" ▲", "").replace(" ▼", "")
            if c == col:
                text += " ▼" if rev else " ▲"
            self.tree.heading(c, text=text)

    def _on_search_change(self, *args):
        self._filter_and_sort()

    def _sort_column(self, col):
        if self.current_sort_col == col:
            self.current_sort_desc = not self.current_sort_desc
        else:
            self.current_sort_col = col
            self.current_sort_desc = True # Default descending for new col? Or Ascending? 
            # Usually dates -> Descending default. Titles -> Ascending.
            if "date" in col:
                self.current_sort_desc = True
            else:
                self.current_sort_desc = False
                
        self._filter_and_sort()

    def _on_select(self, event):
        selection = self.tree.selection()
        if not selection:
            return
            
        paper_id = int(selection[0])
        paper = next((p for p in self.all_papers if p['id'] == paper_id), None)
        
        if paper:
            self._display_details(paper)

    def _beautify_text(self, text):
        if not text:
            return ""
        
        # 1. Replace newlines with spaces
        text = text.replace('\n', ' ').replace('\r', ' ')
        
        import re
        
        # 2. Fix missing spaces after punctuation
        # Case: "word.Next" -> "word. Next" (Letter/Digit + . + Capital)
        text = re.sub(r'([a-z0-9])\.([A-Z])', r'\1. \2', text)
        
        # Case: "word,word" -> "word, word" (Letter + , + Letter)
        text = re.sub(r'([a-z])\,([a-z])', r'\1, \2', text)
        
        # Case: "word:Next" -> "word: Next" (Letter + : + Letter/Capital)
        text = re.sub(r'([a-z])\:([a-zA-Z])', r'\1: \2', text)
        
        # Case: "word;Next" -> "word; Next"
        text = re.sub(r'([a-z])\;([a-zA-Z])', r'\1; \2', text)

        # 3. Fix Hyphenation stuck together? 
        # "word- next" -> "word-next" if it looks like a split word?
        # Only if we suspect it was a line break key. 
        # For now, let's just clean up spaces.
        
        # 4. Collapse multiple spaces
        text = ' '.join(text.split())
        
        return text

    def _resolve_pdf_path(self, db_path):
        """Try to find the PDF file even if the absolute path in the DB is broken"""
        if not db_path:
            return None
            
        # 1. Basic Cleaning and Normalization
        clean_path = db_path.strip().replace('\\', '/')
        if os.path.exists(clean_path):
            return os.path.normpath(clean_path)
            
        filename = os.path.basename(clean_path)
        
        # 2. Check Cloud Storage Root
        cloud_root = self.config.get("cloud_storage", {}).get("path")
        if cloud_root:
            cloud_root = cloud_root.strip().replace('\\', '/')
            if os.path.exists(cloud_root):
                # Try immediate subdirectories (categories) first - fast
                for item in os.listdir(cloud_root):
                    cat_path = os.path.join(cloud_root, item)
                    if os.path.isdir(cat_path):
                        prob_path = os.path.join(cat_path, filename)
                        if os.path.exists(prob_path):
                            return os.path.normpath(prob_path)
                
                # Recursive fallback - thorough but potentially slower
                # Using glob for efficient searching
                search_pattern = os.path.join(cloud_root, "**", filename)
                matches = glob.glob(search_pattern, recursive=True)
                if matches:
                    return os.path.normpath(matches[0])

        # 3. Check Local Papers Directory
        local_papers = self.config.get("papers_dir", "data/papers")
        if local_papers:
            local_papers = local_papers.strip().replace('\\', '/')
            # Check relative to app root
            if os.path.exists(local_papers):
                prob_path = os.path.join(local_papers, filename)
                if os.path.exists(prob_path):
                    return os.path.normpath(prob_path)
                
                # Recursive fallback for local as well
                search_pattern = os.path.join(local_papers, "**", filename)
                matches = glob.glob(search_pattern, recursive=True)
                if matches:
                    return os.path.normpath(matches[0])
                    
        return None

    def _display_details(self, paper):
        # Title
        raw_title = paper.get('title', 'No Title')
        beautified_title = self._beautify_text(raw_title)
        
        self.lbl_title.config(state="normal")
        self.lbl_title.delete("1.0", tk.END)
        self.lbl_title.insert("1.0", beautified_title)
        self.lbl_title.config(state="disabled")
        
        # Meta
        formatted_authors = self._format_authors(paper.get('authors'))
        self.lbl_authors.config(text=f"Authors: {formatted_authors}")
        self.lbl_published.config(text=f"Published: {paper.get('published_date', '-')}")
        
        # Abstract
        raw_abstract = paper.get('abstract', 'No Abstract Available')
        beautified_abstract = self._beautify_text(raw_abstract)
        
        self.txt_abstract.config(state="normal")
        self.txt_abstract.delete("1.0", tk.END)
        self.txt_abstract.insert("1.0", beautified_abstract)
        self.txt_abstract.config(state="disabled")
        
        # Buttons
        raw_file_path = paper.get('pdf_path')
        self.current_file_path = self._resolve_pdf_path(raw_file_path)
        self.current_url = paper.get('source_url')
        
        if self.current_file_path:
            self.btn_open_file.config(state="normal")
            self.btn_kindle.config(state="normal")
            self.btn_print.config(state="normal")
        else:
            self.btn_open_file.config(state="disabled")
            self.btn_kindle.config(state="disabled")
            self.btn_print.config(state="disabled")
            
        if self.current_url or self.current_file_path:
            self.btn_email.config(state="normal")
        else:
            self.btn_email.config(state="disabled")
            
        if self.current_url:
            self.btn_open_url.config(state="normal")
        else:
            self.btn_open_url.config(state="disabled")

    def _open_file(self):
        if self.current_file_path and os.path.exists(self.current_file_path):
            try:
                os.startfile(self.current_file_path)
            except Exception as e:
                messagebox.showerror("Error", f"Could not open file: {e}")

    def _open_url(self):
        if self.current_url:
            webbrowser.open(self.current_url)

    def _print_file(self):
        if self.current_file_path and os.path.exists(self.current_file_path):
            try:
                os.startfile(self.current_file_path, "print")
                self.status_var.set("Print job sent to system.")
            except Exception as e:
                messagebox.showerror("Print Error", f"Could not print: {e}")

    def _email_info(self):
        title = self.lbl_title.get("1.0", tk.END).strip()
        body = f"Paper Title: {title}\n\n"
        if self.current_url:
            body += f"URL: {self.current_url}\n"
        if self.current_file_path:
            body += f"Local Path: {self.current_file_path}\n"
            
        import urllib.parse
        subject = urllib.parse.quote(f"Research Paper: {title}")
        body_encoded = urllib.parse.quote(body)
        
        webbrowser.open(f"mailto:?subject={subject}&body={body_encoded}")

    def _send_to_kindle(self):
        if not self.current_file_path: return
        
        sender = KindleSender()
        valid, msg = sender.validate_config()
        if not valid:
            open_conf = messagebox.askyesno("Setup Required", "Email/SMTP settings are missing in config.yaml.\n\nWould you like to open the config file to add them?")
            if open_conf:
                 try:
                     os.startfile("config.yaml")
                 except:
                     pass
            return

        conf = messagebox.askyesno("Send to Kindle", f"Send '{os.path.basename(self.current_file_path)}' to Kindle?")
        if not conf: return
        
        self.status_var.set("Sending to Kindle...")
        self.root.update()
        
        def run_send():
            success, res = sender.send_file(self.current_file_path)
            self.root.after(0, lambda: self._on_send_complete(success, res))
            
        threading.Thread(target=run_send, daemon=True).start()

    def _on_send_complete(self, success, msg):
        self.status_var.set(msg)
        if success:
            messagebox.showinfo("Sent", msg)
        else:
            messagebox.showerror("Error", msg)

    def _open_settings_dialog(self):
        root = tk.Toplevel(self.root)
        root.title("Viewer Settings")
        root.geometry("500x400")
        
        # Load current
        email_conf = self.config.get("email", {})
        
        ttk.Label(root, text="Email / Kindle Settings", font=("Segoe UI", 12, "bold")).pack(pady=10)
        
        form_frame = ttk.Frame(root, padding=10)
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        # Fields
        ttk.Label(form_frame, text="SMTP Server:").grid(row=0, column=0, sticky="e", pady=5)
        ent_server = ttk.Entry(form_frame, width=30)
        ent_server.grid(row=0, column=1, sticky="w", pady=5)
        ent_server.insert(0, email_conf.get("smtp_server", "smtp.gmail.com"))
        
        ttk.Label(form_frame, text="SMTP Port:").grid(row=1, column=0, sticky="e", pady=5)
        ent_port = ttk.Entry(form_frame, width=10)
        ent_port.grid(row=1, column=1, sticky="w", pady=5)
        ent_port.insert(0, str(email_conf.get("smtp_port", 587)))

        ttk.Label(form_frame, text="SMTP Username:").grid(row=2, column=0, sticky="e", pady=5)
        ent_user = ttk.Entry(form_frame, width=30)
        ent_user.grid(row=2, column=1, sticky="w", pady=5)
        ent_user.insert(0, email_conf.get("smtp_user", ""))
        
        ttk.Label(form_frame, text="SMTP Password:").grid(row=3, column=0, sticky="e", pady=5)
        ent_pass = ttk.Entry(form_frame, width=30, show="*")
        ent_pass.grid(row=3, column=1, sticky="w", pady=5)
        
        # Load password from config first (fallback)
        conf_pass = email_conf.get("smtp_password", "")
        if conf_pass:
            ent_pass.insert(0, conf_pass)
            
        # Check if password exists in keyring (overrides config display usually, or implies security)
        current_user = email_conf.get("smtp_user", "")
        if keyring and current_user:
             try:
                 if keyring.get_password("research_agent", current_user):
                     ent_pass.delete(0, tk.END)
                     ent_pass.insert(0, "********")
             except: pass

        ttk.Label(form_frame, text="Kindle Email:").grid(row=4, column=0, sticky="e", pady=5)
        ent_kindle = ttk.Entry(form_frame, width=30)
        ent_kindle.grid(row=4, column=1, sticky="w", pady=5)
        ent_kindle.insert(0, email_conf.get("kindle_email", ""))
        
        def save():
            new_conf = self.config.copy()
            if "email" not in new_conf: new_conf["email"] = {}
            
            new_conf["email"]["smtp_server"] = ent_server.get()
            try:
                new_conf["email"]["smtp_port"] = int(ent_port.get())
            except:
                messagebox.showerror("Error", "Port must be a number")
                return
                
            new_conf["email"]["smtp_user"] = ent_user.get()
            new_conf["email"]["kindle_email"] = ent_kindle.get()
            
            # Handle Password
            pw_input = ent_pass.get()
            if pw_input and pw_input != "********":
                saved_to_keyring = False
                if keyring:
                    try:
                        keyring.set_password("research_agent", ent_user.get(), pw_input)
                        saved_to_keyring = True
                        messagebox.showinfo("Security", "Password securely stored in OS Keychain.")
                    except Exception as e:
                        print(f"Keyring failed: {e}") 
                        # Fall through to config save
                
                if saved_to_keyring:
                    # Remove from config if secure storage worked
                    if "smtp_password" in new_conf["email"]:
                        del new_conf["email"]["smtp_password"]
                else:
                    # Fallback to plain text config
                    new_conf["email"]["smtp_password"] = pw_input
                    if keyring:
                        msg = "Keyring save failed. Password saved to config.yaml in PLAIN TEXT."
                    else:
                        msg = "Keyring module not found. Password saved to config.yaml in PLAIN TEXT."
                    messagebox.showwarning("Security Warning", msg)
            
            # If password was cleared or not changed, we don't necessarily delete it 
            # unless we want to allow clearing? 
            # For now, simplistic approach.
            
            # Save to File
                
            try:
                save_config(new_conf)
                self.config = new_conf # Update runtime config
                messagebox.showinfo("Saved", "Configuration updated.")
                root.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Could not save config: {e}")

        ttk.Button(root, text="Save Settings", command=save).pack(pady=20)

if __name__ == "__main__":
    if sys.platform == 'win32':
        # High DPI fix
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except:
            pass

    root = tk.Tk()
    app = ResearchViewer(root)
    root.mainloop()
