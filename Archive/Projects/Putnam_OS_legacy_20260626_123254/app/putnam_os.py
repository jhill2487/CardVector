from __future__ import annotations
import os, sys, subprocess, traceback
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

APP_VERSION = "2.2.0"

APP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_DIR))
from core.pricing_engine import detect_csv, audit_existing_listing, audit_carduploader_new_listing, run_auto, ROOT, INVENTORY_ROOT

class PutnamOS(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"Putnam OS v{APP_VERSION}")
        self.geometry("1120x720")
        self.configure(bg="#111111")
        self.selected_path = tk.StringVar()
        self.detected = tk.StringVar(value="No CSV loaded")
        self.last_job = None
        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        sidebar = tk.Frame(self, bg="#151515", width=210)
        sidebar.grid(row=0, column=0, sticky="ns")
        tk.Label(sidebar, text="PUTNAM OS", bg="#151515", fg="white", font=("Segoe UI", 22, "bold")).pack(pady=(24,4))
        tk.Label(sidebar, text=f"v{APP_VERSION}", bg="#151515", fg="#aaaaaa", font=("Segoe UI", 10)).pack(pady=(0,18))
        for name in ["Dashboard", "Pricing", "Inventory", "Shipping", "Content", "Analytics", "Settings"]:
            b = tk.Button(sidebar, text=name, height=2, width=20, command=lambda n=name: self.show_workspace(n), bg="#222222", fg="white", activebackground="#333333", activeforeground="white", relief="flat")
            b.pack(pady=4, padx=14)
        self.container = tk.Frame(self, bg="#f5f5f5")
        self.container.grid(row=0, column=1, sticky="nsew")
        self.show_workspace("Pricing")

    def clear(self):
        for w in self.container.winfo_children(): w.destroy()

    def show_workspace(self, name):
        self.clear()
        if name == "Pricing": self.pricing_workspace()
        elif name == "Dashboard": self.dashboard()
        else: self.coming_soon(name)

    def header(self, title, subtitle=""):
        tk.Label(self.container, text=title, bg="#f5f5f5", fg="#111111", font=("Segoe UI", 24, "bold")).pack(anchor="w", padx=28, pady=(24,2))
        if subtitle:
            tk.Label(self.container, text=subtitle, bg="#f5f5f5", fg="#555555", font=("Segoe UI", 11)).pack(anchor="w", padx=30, pady=(0,18))

    def dashboard(self):
        self.header("Dashboard", "Build the business. Document the journey. Improve the system.")
        box = tk.Frame(self.container, bg="white", bd=1, relief="solid")
        box.pack(fill="x", padx=30, pady=10)
        tk.Label(box, text="Current Mission", bg="white", fg="#333", font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=18, pady=(16,3))
        tk.Label(box, text="Pricing revision completed. Next: process at least 100 new cards and review the workflow recording.", bg="white", fg="#333", font=("Segoe UI", 12), wraplength=760, justify="left").pack(anchor="w", padx=18, pady=(0,16))

    def pricing_workspace(self):
        self.header("Pricing Workspace", "Existing listing revisions and CardUploader new-listing price audit")
        frame = tk.Frame(self.container, bg="white", bd=1, relief="solid")
        frame.pack(fill="both", expand=True, padx=30, pady=10)
        tk.Label(frame, text="CSV File", bg="white", fg="#222", font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=18, pady=(18,4))
        row = tk.Frame(frame, bg="white"); row.pack(fill="x", padx=18)
        tk.Entry(row, textvariable=self.selected_path, font=("Segoe UI", 10)).pack(side="left", fill="x", expand=True, ipady=5)
        tk.Button(row, text="Browse", command=self.browse_csv, width=14).pack(side="left", padx=(8,0), ipady=3)
        tk.Label(frame, textvariable=self.detected, bg="white", fg="#006400", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=18, pady=(8,16))
        info = tk.LabelFrame(frame, text="How this workspace works", bg="white", fg="#333", font=("Segoe UI", 11, "bold"))
        info.pack(fill="x", padx=18, pady=8)
        text = "• CardUploader new-listing CSV: preserves all fields, audits *StartPrice, applies $0.99 floor and Putnam ladder, flags $20+ cards.\n• eBay active listings CSV: creates changed-only bulk revise upload CSV for existing listings.\n• Original CSVs are backed up and never modified."
        tk.Label(info, text=text, bg="white", fg="#333", font=("Segoe UI", 10), justify="left", wraplength=800).pack(anchor="w", padx=12, pady=10)
        actions = tk.Frame(frame, bg="white"); actions.pack(fill="x", padx=18, pady=16)
        tk.Button(actions, text="Auto Detect + Run", command=self.run_auto, height=2, width=22, bg="#111111", fg="white").pack(side="left")
        tk.Button(actions, text="Run as New Listing Audit", command=self.run_new_listing, height=2, width=24).pack(side="left", padx=8)
        tk.Button(actions, text="Run as Existing Listing Revision", command=self.run_existing, height=2, width=28).pack(side="left", padx=8)
        tk.Button(actions, text="Open Completed Jobs", command=self.open_completed, height=2, width=20).pack(side="left", padx=8)
        self.result = tk.Text(frame, height=12, font=("Consolas", 10), bg="#fafafa")
        self.result.pack(fill="both", expand=True, padx=18, pady=(0,18))

    def coming_soon(self, name):
        self.header(name, "Coming in a future release")
        tk.Label(self.container, text=f"{name} Workspace", bg="#f5f5f5", fg="#222", font=("Segoe UI", 20, "bold")).pack(anchor="w", padx=30, pady=(40,5))
        tk.Label(self.container, text="This workspace is intentionally a placeholder until a real business workflow justifies the feature.", bg="#f5f5f5", fg="#555", font=("Segoe UI", 12)).pack(anchor="w", padx=30)

    def browse_csv(self):
        p = filedialog.askopenfilename(title="Select CSV", filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if not p: return
        self.selected_path.set(p)
        self.detect_file()

    def detect_file(self):
        p = Path(self.selected_path.get().strip().strip('"'))
        try:
            d = detect_csv(p)
            friendly = {"carduploader_new_listing":"CardUploader new-listing export", "ebay_active_listings":"eBay active listings export", "ebay_bulk_price_template":"eBay price/quantity template"}.get(d.csv_type,d.csv_type)
            self.detected.set(f"Detected: {friendly} | Rows: {d.row_count}")
        except Exception as e:
            self.detected.set(f"Not recognized: {e}")

    def _run(self, mode):
        p = Path(self.selected_path.get().strip().strip('"'))
        if not p.exists():
            messagebox.showerror("Missing file", "Please choose a valid CSV file first."); return
        try:
            if mode == "auto": r = run_auto(p)
            elif mode == "new": r = audit_carduploader_new_listing(p)
            else: r = audit_existing_listing(p)
            self.last_job = r["job_dir"]
            self.result.delete("1.0", "end")
            lines = ["Job complete", "", f"CSV type: {r.get('csv_type')}", f"Rows reviewed: {r.get('reviewed')}", f"Changed: {r.get('changed')}", f"Invalid: {r.get('invalid')}"]
            if "raised" in r: lines += [f"Raised to floor: {r.get('raised')}", f"$20+ flags: {r.get('flagged')}"]
            lines += ["", f"Output folder: {r['job_dir']}", f"Report: {r['report']}"]
            self.result.insert("end", "\n".join(lines))
            messagebox.showinfo("Complete", f"Pricing job complete.\n\nOutput folder:\n{r['job_dir']}")
            self.open_path(r["job_dir"])
        except Exception as e:
            tb = traceback.format_exc()
            self.result.delete("1.0", "end")
            self.result.insert("end", tb)
            messagebox.showerror("Error", str(e))

    def run_auto(self): self._run("auto")
    def run_new_listing(self): self._run("new")
    def run_existing(self): self._run("existing")
    def open_path(self, path):
        try: os.startfile(str(path))
        except Exception: subprocess.Popen(["explorer", str(path)])
    def open_completed(self):
        p = INVENTORY_ROOT / "Completed Jobs"
        p.mkdir(parents=True, exist_ok=True)
        self.open_path(p)

if __name__ == "__main__":
    PutnamOS().mainloop()
