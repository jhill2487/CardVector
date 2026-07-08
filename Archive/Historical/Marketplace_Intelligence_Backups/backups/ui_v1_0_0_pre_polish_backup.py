from __future__ import annotations

import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except Exception:
    DND_AVAILABLE = False
    TkinterDnD = None
    DND_FILES = None

from . import __version__
from .config import load_recent_files, remember_recent_file
from .engine import MarketplaceIntelligenceEngine
from .reports import result_row


BaseTk = TkinterDnD.Tk if DND_AVAILABLE else tk.Tk


class MarketplaceIntelligenceApp(BaseTk):
    def __init__(self):
        super().__init__()
        self.title(f"Marketplace Intelligence v{__version__}")
        self.geometry("1180x760")
        self.minsize(980, 640)
        self.engine = MarketplaceIntelligenceEngine()
        self.input_path = tk.StringVar(value="")
        self.status = tk.StringVar(value="Ready.")
        self.summary = tk.StringVar(value="Import an eBay Active Listings CSV to begin.")
        self.analysis_only = tk.BooleanVar(value=False)
        self.output_dir: Path | None = None
        self.last_results = []
        self.build_ui()

    def build_ui(self):
        root = ttk.Frame(self, padding=14)
        root.pack(fill="both", expand=True)
        ttk.Label(root, text="Marketplace Intelligence v1.0", font=("Segoe UI", 20, "bold")).pack(anchor="w")
        ttk.Label(
            root,
            text="Find active listings that deserve attention today. No automatic uploads. No Putnam OS inventory required.",
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(0, 12))

        input_frame = ttk.LabelFrame(root, text="CSV Import", padding=10)
        input_frame.pack(fill="x", pady=(0, 10))
        ttk.Entry(input_frame, textvariable=self.input_path).pack(side="left", fill="x", expand=True)
        ttk.Button(input_frame, text="Browse", command=self.browse).pack(side="left", padx=8)
        ttk.Button(input_frame, text="Analyze", command=self.analyze).pack(side="left")
        ttk.Checkbutton(input_frame, text="Analysis Only", variable=self.analysis_only).pack(side="left", padx=10)
        ttk.Button(input_frame, text="Open Report Folder", command=self.open_output_folder).pack(side="left")

        recent = load_recent_files()
        if recent:
            recent_frame = ttk.Frame(root)
            recent_frame.pack(fill="x", pady=(0, 10))
            ttk.Label(recent_frame, text="Recent:").pack(side="left")
            self.recent_var = tk.StringVar(value=recent[0])
            recent_box = ttk.Combobox(recent_frame, textvariable=self.recent_var, values=recent, state="readonly")
            recent_box.pack(side="left", fill="x", expand=True, padx=8)
            ttk.Button(recent_frame, text="Use Recent", command=lambda: self.input_path.set(self.recent_var.get())).pack(side="left")

        self.drop_frame = ttk.LabelFrame(root, text="Drop CSV Here", padding=18)
        self.drop_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(self.drop_frame, text="Drag an eBay Active Listings CSV here, or use Browse.").pack()
        if DND_AVAILABLE:
            self.drop_frame.drop_target_register(DND_FILES)
            self.drop_frame.dnd_bind("<<Drop>>", self.on_drop)

        summary_frame = ttk.LabelFrame(root, text="Report Summary", padding=10)
        summary_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(summary_frame, textvariable=self.summary, justify="left").pack(anchor="w")

        review_frame = ttk.LabelFrame(root, text="Review Screen - Changed / Review Listings", padding=10)
        review_frame.pack(fill="both", expand=True)
        filter_row = ttk.Frame(review_frame)
        filter_row.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        ttk.Label(filter_row, text="Filter:").pack(side="left")
        self.review_filter = tk.StringVar(value="Changed Only")
        filter_box = ttk.Combobox(
            filter_row,
            textvariable=self.review_filter,
            values=["Changed Only", "Review Required", "All Listings"],
            state="readonly",
            width=18,
        )
        filter_box.pack(side="left", padx=8)
        filter_box.bind("<<ComboboxSelected>>", lambda _event: self.populate_tree(self.last_results))
        columns = ("item_id", "title", "current_price", "market_price", "recommended_price", "difference", "recommendation", "reason")
        self.tree = ttk.Treeview(review_frame, columns=columns, show="headings")
        widths = {
            "item_id": 120,
            "title": 340,
            "current_price": 100,
            "market_price": 100,
            "recommended_price": 120,
            "difference": 90,
            "recommendation": 110,
            "reason": 320,
        }
        for column in columns:
            self.tree.heading(column, text=column.replace("_", " ").title())
            self.tree.column(column, width=widths[column], anchor="w")
        yscroll = ttk.Scrollbar(review_frame, orient="vertical", command=self.tree.yview)
        xscroll = ttk.Scrollbar(review_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.tree.grid(row=1, column=0, sticky="nsew")
        yscroll.grid(row=1, column=1, sticky="ns")
        xscroll.grid(row=2, column=0, sticky="ew")
        review_frame.rowconfigure(1, weight=1)
        review_frame.columnconfigure(0, weight=1)

        ttk.Label(root, textvariable=self.status, anchor="w").pack(fill="x", pady=(8, 0))

    def browse(self):
        path = filedialog.askopenfilename(
            title="Select eBay Active Listings CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if path:
            self.input_path.set(path)

    def on_drop(self, event):
        raw = str(event.data or "").strip()
        if raw.startswith("{") and raw.endswith("}"):
            raw = raw[1:-1]
        self.input_path.set(raw)

    def analyze(self):
        path = Path(self.input_path.get().strip().strip('"'))
        if not path.exists():
            messagebox.showinfo("Marketplace Intelligence", "Choose a valid eBay Active Listings CSV first.")
            return
        self.status.set("Analyzing listings...")
        self.clear_tree()
        thread = threading.Thread(target=self._analyze_worker, args=(path,), daemon=True)
        thread.start()

    def _analyze_worker(self, path: Path):
        try:
            result = self.engine.analyze_file(path, analysis_only=self.analysis_only.get())
            remember_recent_file(path)
            self.after(0, lambda: self.display_result(result))
        except Exception as exc:
            self.after(0, lambda: self.show_error(exc))

    def display_result(self, result: dict):
        self.output_dir = result["output_dir"]
        summary = result["summary"]
        reports = result["reports"]
        self.last_results = result["results"]
        self.summary.set(
            "\n".join([
                f"Listings Imported: {summary.listings_imported}",
                f"Listings Matched: {summary.listings_matched}",
                f"Listings Unmatched: {summary.listings_unmatched}",
                f"Price Increases: {summary.price_increases}",
                f"Price Decreases: {summary.price_decreases}",
                f"No Changes: {summary.no_changes}",
                f"Review Required: {summary.review_required}",
                f"Potential Revenue Impact: ${summary.potential_revenue_impact}",
                f"Reports: {self.output_dir}",
            ])
        )
        self.populate_tree(result["results"])
        self.status.set(f"Complete. Analysis report: {reports['analysis_report']}")

    def populate_tree(self, results):
        self.clear_tree()
        current_filter = self.review_filter.get() if hasattr(self, "review_filter") else "Changed Only"
        for result in results:
            if current_filter == "Changed Only" and not result.decision.changed:
                continue
            if current_filter == "Review Required" and not result.decision.review_required:
                continue
            row = result_row(result)
            self.tree.insert(
                "",
                "end",
                values=[
                    row["item_id"],
                    row["title"],
                    row["current_price"],
                    row["market_price"],
                    row["recommended_price"],
                    row["difference"],
                    row["recommendation"],
                    row["reason"],
                ],
            )

    def clear_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

    def show_error(self, exc: Exception):
        self.status.set("Analysis failed.")
        messagebox.showerror("Marketplace Intelligence", str(exc))

    def open_output_folder(self):
        if not self.output_dir:
            messagebox.showinfo("Marketplace Intelligence", "Run an analysis first.")
            return
        try:
            os.startfile(self.output_dir)
        except Exception as exc:
            messagebox.showinfo("Marketplace Intelligence", f"Report folder:\n{self.output_dir}\n\nCould not open automatically:\n{exc}")


def main():
    app = MarketplaceIntelligenceApp()
    app.mainloop()


if __name__ == "__main__":
    main()
