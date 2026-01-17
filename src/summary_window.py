import tkinter as tk
from tkinter import ttk, scrolledtext
import os
import subprocess
import platform

class SummaryWindow:
    def __init__(self, papers, run_id, mode="DAILY"):
        self.papers = papers
        self.run_id = run_id
        self.mode = mode
        self.window = tk.Toplevel()

        # Update title and size based on mode
        if mode == "BACKFILL":
            self.window.title(f"Backfill Summary - {len(papers)} total papers")
            self.window.geometry("450x300")  # Smaller for stats-only display
            self.window.resizable(False, False)  # Fixed size for stats
        elif mode == "TESTING":
            self.window.title(f"Testing Run Summary - {len(papers)} papers")
            self.window.geometry("1400x700")  # Wide enough to show full abstracts
        else:
            self.window.title(f"Daily Run Summary - {len(papers)} new papers")
            self.window.geometry("1400x700")  # Wide enough to show full abstracts

        self._create_ui()

    def _create_ui(self):
        # Only show stats frame at top for BACKFILL mode
        if self.mode == "BACKFILL":
            # Stats summary frame at top (BACKFILL only)
            stats_frame = ttk.LabelFrame(self.window, text="Run Statistics", padding=10)
            stats_frame.pack(fill="x", padx=10, pady=(10, 5))

            # Calculate stats by source
            source_stats = self._calculate_source_stats()

            # Display stats in vertical format
            for idx, (source, count) in enumerate(source_stats.items()):
                source_label = ttk.Label(stats_frame, text=f"{source}:", font=("Consolas", 10, "bold"))
                source_label.grid(row=idx, column=0, sticky="w", padx=5, pady=2)
                count_label = ttk.Label(stats_frame, text=f"{count} papers", font=("Consolas", 10))
                count_label.grid(row=idx, column=1, sticky="w", padx=5, pady=2)

            # Separator line
            separator = ttk.Separator(stats_frame, orient="horizontal")
            separator.grid(row=len(source_stats), column=0, columnspan=2, sticky="ew", pady=5, padx=5)

            # Total count - centered
            total_label = ttk.Label(stats_frame, text=f"TOTAL: {len(self.papers)} papers", font=("Consolas", 11, "bold"))
            total_label.grid(row=len(source_stats)+1, column=0, columnspan=2, pady=(5, 2))

            # Close button at bottom
            btn_frame = ttk.Frame(self.window)
            btn_frame.pack(pady=10)
            ttk.Button(btn_frame, text="Close", command=self.window.destroy).pack()
            return  # Skip creating paper details section

        # Main scrollable frame (for DAILY/TESTING modes)
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        # Configure scrolling
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Group papers by source
        grouped = self._group_papers_by_source()

        # Create collapsible sections for each source
        for source, source_papers in grouped.items():
            self._create_source_section(scrollable_frame, source, source_papers)

        # For DAILY/TESTING modes, add summary footer with counts (centered)
        if self.mode in ["DAILY", "TESTING"]:
            footer_frame = ttk.Frame(self.window, relief="sunken", borderwidth=1)
            footer_frame.pack(fill="x", padx=10, pady=(5, 10))

            # Source counts - centered
            source_stats = self._calculate_source_stats()
            summary_text = "Summary: " + " | ".join([f"{source}: {count}" for source, count in source_stats.items()])
            summary_text += f" | TOTAL: {len(self.papers)}"

            counts_label = ttk.Label(footer_frame, text=summary_text, font=("Consolas", 10))
            counts_label.pack(pady=5, anchor="center")

        # Close button at bottom
        btn_frame = ttk.Frame(self.window)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Close", command=self.window.destroy).pack()

    def _calculate_source_stats(self):
        """Calculate paper counts by source"""
        stats = {}
        source_names = {
            'arxiv': 'ArXiv',
            'lesswrong': 'LessWrong',
            'labs_anthropic': 'Anthropic',
            'labs_openai': 'OpenAI',
            'labs_deepmind': 'DeepMind',
            'labs_meta': 'Meta AI',
            'labs_google': 'Google Research',
            'labs_microsoft': 'Microsoft Research',
            'labs_mistral': 'Mistral',
            'labs_nvidia': 'NVIDIA'
        }

        for paper in self.papers:
            source = paper.get('source', 'unknown')
            display_name = source_names.get(source, source.title())

            if display_name not in stats:
                stats[display_name] = 0
            stats[display_name] += 1

        return dict(sorted(stats.items()))

    def _group_papers_by_source(self):
        groups = {}
        source_names = {
            'arxiv': 'ArXiv',
            'lesswrong': 'LessWrong',
            'labs_anthropic': 'Anthropic',
            'labs_openai': 'OpenAI',
            'labs_deepmind': 'DeepMind',
            'labs_meta': 'Meta AI',
            'labs_google': 'Google Research',
            'labs_microsoft': 'Microsoft Research',
            'labs_mistral': 'Mistral',
            'labs_nvidia': 'NVIDIA'
        }

        for paper in self.papers:
            source = paper.get('source', 'unknown')
            display_name = source_names.get(source, source.title())

            if display_name not in groups:
                groups[display_name] = []
            groups[display_name].append(paper)

        return groups

    def _create_source_section(self, parent, source_name, papers):
        # Section header (collapsible)
        section_frame = ttk.LabelFrame(parent, text=f"{source_name} ({len(papers)} papers)", padding=10)
        section_frame.pack(fill="x", pady=5)

        # Create paper cards
        for paper in papers:
            self._create_paper_card(section_frame, paper)

    def _create_paper_card(self, parent, paper):
        card_frame = ttk.Frame(parent, relief="ridge", borderwidth=1)
        card_frame.pack(fill="x", pady=5)

        # Left side: Title, Authors, Date (fixed 360px width)
        left_frame = ttk.Frame(card_frame, width=360)
        left_frame.pack(side="left", fill="y", expand=False, padx=10, pady=10)
        left_frame.pack_propagate(False)  # Prevent frame from shrinking

        # Title (clickable)
        title_label = tk.Label(
            left_frame,
            text=paper['title'][:80] + ("..." if len(paper['title']) > 80 else ""),
            fg="blue",
            cursor="hand2",
            font=("Consolas", 12, "bold underline"),
            wraplength=340,
            justify="left"
        )
        title_label.pack(anchor="w")
        title_label.bind("<Button-1>", lambda e, p=paper['pdf_path']: self._open_pdf(p))

        # Authors
        authors_label = ttk.Label(
            left_frame,
            text=f"Authors: {paper['authors'][:50]}{'...' if len(paper['authors']) > 50 else ''}",
            wraplength=340,
            font=("Consolas", 11)
        )
        authors_label.pack(anchor="w", pady=(5, 0))

        # Date
        date_label = ttk.Label(left_frame, text=f"Date: {paper['published_date']}", font=("Consolas", 11))
        date_label.pack(anchor="w")

        # Right side: Abstract (60%)
        right_frame = ttk.Frame(card_frame)
        right_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        # Abstract (scrollable)
        abstract = paper.get('abstract', '')
        if not abstract or abstract.strip() == '':
            abstract = self._generate_summary_if_needed(paper)
        else:
            # Clean up abstract formatting
            abstract = self._clean_abstract_text(abstract)

        abstract_text = scrolledtext.ScrolledText(
            right_frame,
            height=5,
            wrap=tk.WORD,
            font=("Consolas", 11),
            state=tk.DISABLED
        )
        abstract_text.pack(fill="both", expand=True)
        abstract_text.config(state=tk.NORMAL)
        abstract_text.insert("1.0", abstract)
        abstract_text.config(state=tk.DISABLED)

    def _open_pdf(self, pdf_path):
        """Open PDF file using system default application"""
        try:
            if platform.system() == 'Windows':
                os.startfile(pdf_path)
            elif platform.system() == 'Darwin':  # macOS
                subprocess.call(['open', pdf_path])
            else:  # Linux
                subprocess.call(['xdg-open', pdf_path])
        except Exception as e:
            print(f"Error opening PDF: {e}")

    def _clean_abstract_text(self, text):
        """
        Clean up abstract text formatting issues:
        - Fix words running together (add spaces where needed)
        - Compress multiple blank lines to single blank line
        - Remove excessive whitespace
        """
        import re

        # Replace common HTML entities if present
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')

        # Fix words running together - add space after punctuation if missing
        text = re.sub(r'([.!?])([A-Z])', r'\1 \2', text)

        # Fix missing spaces after commas (if not followed by space or digit)
        text = re.sub(r',([A-Za-z])', r', \1', text)

        # Normalize whitespace within lines (collapse multiple spaces to one)
        text = re.sub(r'[ \t]+', ' ', text)

        # Compress multiple consecutive blank lines to just one blank line
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)

        # Remove leading/trailing whitespace
        text = text.strip()

        return text

    def _generate_summary_if_needed(self, paper):
        """Generate summary using Claude API if abstract is empty"""
        # Check if abstract exists
        if paper.get('abstract') and paper['abstract'].strip():
            return paper['abstract']

        # Fallback: Generate summary using Claude API
        # (Only for web pages without proper abstracts)
        try:
            import anthropic

            # Read PDF or HTML content
            pdf_path = paper.get('pdf_path', '')
            if not os.path.exists(pdf_path):
                return "[No abstract available]"

            # For PDFs: Extract first page text (simple approach)
            # For HTML-to-PDF: Already have abstract from BeautifulSoup

            # Call Claude API
            client = anthropic.Anthropic()
            # TODO: Implement actual API call
            # For now, return placeholder
            return "[Summary generation not yet implemented]"

        except Exception as e:
            return f"[Could not generate summary: {e}]"
