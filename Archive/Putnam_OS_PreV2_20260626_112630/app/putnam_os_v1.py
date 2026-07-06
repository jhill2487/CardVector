import csv
import json
import os
import subprocess
import sys
from collections import Counter
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

VERSION = "v1.0.0"

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except Exception:
    DND_AVAILABLE = False
    TkinterDnD = None
    DND_FILES = None


def find_root() -> Path:
    env = os.environ.get("USERENVIRONMENT")
    if env and Path(env).exists():
        return Path(env)
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".putnam_root").exists():
            return parent
    return Path.home() / "OneDrive" / "PutnamCollectibles"


ROOT = find_root()
OS_ROOT = ROOT / "Putnam_OS"
CONFIG_DIR = OS_ROOT / "config"
LOGS_DIR = OS_ROOT / "logs"
OUTPUT_DIR = OS_ROOT / "output" / "Pricing"
SHARED_TEMPLATE_DIR = ROOT / "Shared" / "Templates" / "eBay" / "Bulk_Revise"

REQUIRED_ACTIVE_COLUMNS = ["Item number", "Title", "Current price"]
UPLOAD_COLUMNS = [
    "Action", "Category name", "Item number", "Title", "Listing site", "Currency",
    "Start price", "Buy It Now price", "Available quantity", "Relationship",
    "Relationship details", "Custom label (SKU)"
]
INFO_LINE = "#INFO,Version=1.0.0,Template= eBay-active-revise-price-quantity-download_US,,,,,,,,,"


def money(value) -> Decimal | None:
    if value is None:
        return None
    text = str(value).strip().replace("$", "").replace(",", "")
    if not text:
        return None
    try:
        return Decimal(text).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except InvalidOperation:
        return None


def fmt_money(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):.2f}"


def load_ladder() -> dict[Decimal, Decimal]:
    cfg = CONFIG_DIR / "pricing_ladder.json"
    if not cfg.exists():
        return {}
    data = json.loads(cfg.read_text(encoding="utf-8"))
    return {money(k): money(v) for k, v in data.get("price_ladder", {}).items() if money(k) is not None}


def read_active_csv(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames or []
    missing = [c for c in REQUIRED_ACTIVE_COLUMNS if c not in fieldnames]
    if missing:
        raise ValueError("This does not appear to be an eBay Active Listings CSV. Missing columns: " + ", ".join(missing))
    return rows, fieldnames


def category_name(row):
    name = (row.get("eBay category 1 name") or row.get("Category name") or "").strip()
    num = (row.get("eBay category 1 number") or "").strip()
    if name and num:
        return f"{name} ({num})"
    return name


def analyze(rows, ladder):
    distribution = Counter()
    changes = []
    for row in rows:
        old = money(row.get("Current price") or row.get("Start price"))
        if old is None:
            continue
        distribution[fmt_money(old)] += 1
        new = ladder.get(old)
        if new is not None and new != old:
            changes.append((row, old, new))
    return distribution, changes


def write_outputs(source_path: Path, rows, ladder):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    outdir = OUTPUT_DIR / timestamp
    outdir.mkdir(parents=True, exist_ok=True)

    distribution, changes = analyze(rows, ladder)
    changed_ids = {row.get("Item number") for row, old, new in changes}

    review_path = outdir / f"putnam_price_revision_review_{timestamp}.csv"
    changed_path = outdir / f"putnam_price_revision_changed_only_{timestamp}.csv"
    upload_path = outdir / f"putnam_ebay_price_revision_UPLOAD_CANDIDATE_{timestamp}.csv"
    report_path = outdir / f"putnam_price_revision_report_{timestamp}.txt"
    log_path = LOGS_DIR / f"putnam_os_pricing_{timestamp}.log"

    # Review all rows
    review_fields = [
        "Item number", "Title", "Custom label (SKU)", "Available quantity", "Currency",
        "Old price", "New price", "Changed", "Rule"
    ]
    with review_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=review_fields)
        writer.writeheader()
        for row in rows:
            old = money(row.get("Current price") or row.get("Start price"))
            new = ladder.get(old) if old is not None else None
            changed = new is not None and new != old
            writer.writerow({
                "Item number": row.get("Item number", ""),
                "Title": row.get("Title", ""),
                "Custom label (SKU)": row.get("Custom label (SKU)", ""),
                "Available quantity": row.get("Available quantity", ""),
                "Currency": row.get("Currency", "USD") or "USD",
                "Old price": fmt_money(old) if old is not None else "",
                "New price": fmt_money(new if changed else old) if old is not None else "",
                "Changed": "YES" if changed else "NO",
                "Rule": f"{fmt_money(old)} -> {fmt_money(new)}" if changed else "No ladder match / unchanged"
            })

    # Changed only detailed
    with changed_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=review_fields)
        writer.writeheader()
        for row, old, new in changes:
            writer.writerow({
                "Item number": row.get("Item number", ""),
                "Title": row.get("Title", ""),
                "Custom label (SKU)": row.get("Custom label (SKU)", ""),
                "Available quantity": row.get("Available quantity", ""),
                "Currency": row.get("Currency", "USD") or "USD",
                "Old price": fmt_money(old),
                "New price": fmt_money(new),
                "Changed": "YES",
                "Rule": f"{fmt_money(old)} -> {fmt_money(new)}"
            })

    # eBay upload candidate, changed rows only
    with upload_path.open("w", encoding="utf-8-sig", newline="") as f:
        f.write(INFO_LINE + "\n")
        writer = csv.DictWriter(f, fieldnames=UPLOAD_COLUMNS)
        writer.writeheader()
        for row, old, new in changes:
            writer.writerow({
                "Action": "Revise",
                "Category name": category_name(row),
                "Item number": row.get("Item number", ""),
                "Title": row.get("Title", ""),
                "Listing site": "US",
                "Currency": row.get("Currency", "USD") or "USD",
                "Start price": fmt_money(new),
                "Buy It Now price": "",
                "Available quantity": row.get("Available quantity", "1") or "1",
                "Relationship": "",
                "Relationship details": "",
                "Custom label (SKU)": row.get("Custom label (SKU)", "")
            })

    total_old = sum((old for row, old, new in changes), Decimal("0.00"))
    total_new = sum((new for row, old, new in changes), Decimal("0.00"))
    reduction = total_old - total_new

    dist_lines = "\n".join([f"${price}: {count}" for price, count in sorted(distribution.items(), key=lambda kv: Decimal(kv[0]))])
    ladder_lines = "\n".join([f"${fmt_money(k)} -> ${fmt_money(v)}" for k, v in sorted(ladder.items())])

    report = f"""Putnam OS Pricing Workspace Report
Version: {VERSION}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Source CSV: {source_path}

Listings read: {len(rows)}
Listings changed: {len(changes)}
Listings unchanged: {len(rows) - len(changes)}

Total old price of changed listings: ${fmt_money(total_old)}
Total new price of changed listings: ${fmt_money(total_new)}
Total catalog reduction on changed listings: ${fmt_money(reduction)}

Pricing ladder used:
{ladder_lines}

Current price distribution:
{dist_lines}

Output files:
Review CSV: {review_path}
Changed Only CSV: {changed_path}
eBay Upload Candidate: {upload_path}

IMPORTANT:
Review the upload candidate before uploading to eBay.
This tool does not modify live listings.
"""
    report_path.write_text(report, encoding="utf-8")
    log_path.write_text(report, encoding="utf-8")

    return {
        "outdir": outdir,
        "review": review_path,
        "changed": changed_path,
        "upload": upload_path,
        "report": report_path,
        "count": len(rows),
        "changed_count": len(changes),
        "reduction": fmt_money(reduction),
    }


class PutnamOS:
    def __init__(self, root):
        self.root = root
        self.csv_path = None
        self.rows = []
        self.ladder = load_ladder()
        self.last_output = None

        self.root.title(f"Putnam OS {VERSION}")
        self.root.geometry("1100x720")
        self.root.minsize(1000, 650)
        self.root.configure(bg="#0f172a")

        self.build_layout()
        self.show_dashboard()

    def clear_main(self):
        for w in self.main.winfo_children():
            w.destroy()

    def nav_button(self, text, command):
        btn = tk.Button(self.sidebar, text=text, command=command, anchor="w", padx=14,
                        bg="#1e293b", fg="white", activebackground="#334155",
                        activeforeground="white", relief="flat", font=("Segoe UI", 11), height=2)
        btn.pack(fill="x", padx=10, pady=4)
        return btn

    def build_layout(self):
        self.sidebar = tk.Frame(self.root, bg="#020617", width=230)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        tk.Label(self.sidebar, text="PUTNAM OS", bg="#020617", fg="white",
                 font=("Segoe UI", 20, "bold")).pack(pady=(24, 2))
        tk.Label(self.sidebar, text=VERSION, bg="#020617", fg="#94a3b8",
                 font=("Segoe UI", 9)).pack(pady=(0, 20))

        self.nav_button("Dashboard", self.show_dashboard)
        self.nav_button("Pricing", self.show_pricing)
        self.nav_button("Inventory  • Coming Soon", lambda: self.coming("Inventory"))
        self.nav_button("Shipping  • Coming Soon", lambda: self.coming("Shipping"))
        self.nav_button("Content  • Coming Soon", lambda: self.coming("Content"))
        self.nav_button("Warehouse  • Coming Soon", lambda: self.coming("Warehouse"))
        self.nav_button("Analytics  • Coming Soon", lambda: self.coming("Analytics"))
        self.nav_button("Settings", self.show_settings)

        self.main = tk.Frame(self.root, bg="#f8fafc")
        self.main.pack(side="right", fill="both", expand=True)

    def header(self, title, subtitle=""):
        tk.Label(self.main, text=title, bg="#f8fafc", fg="#0f172a",
                 font=("Segoe UI", 24, "bold")).pack(anchor="w", padx=30, pady=(24, 2))
        if subtitle:
            tk.Label(self.main, text=subtitle, bg="#f8fafc", fg="#475569",
                     font=("Segoe UI", 11)).pack(anchor="w", padx=30, pady=(0, 18))

    def show_dashboard(self):
        self.clear_main()
        self.header("Dashboard", "Build the business. Document the journey. Improve the system.")
        card = tk.Frame(self.main, bg="white", highlightbackground="#e2e8f0", highlightthickness=1)
        card.pack(fill="x", padx=30, pady=10)
        tk.Label(card, text="Today's Priority", bg="white", fg="#0f172a",
                 font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=20, pady=(18, 4))
        tk.Label(card, text="Bulk Price Revision", bg="white", fg="#dc2626",
                 font=("Segoe UI", 18, "bold")).pack(anchor="w", padx=20)
        tk.Label(card, text="Reason: Existing inventory is overpriced after moving to buyer-paid shipping.",
                 bg="white", fg="#475569", font=("Segoe UI", 11)).pack(anchor="w", padx=20, pady=(6, 14))
        tk.Button(card, text="Start Pricing Workspace", command=self.show_pricing,
                  bg="#2563eb", fg="white", activebackground="#1d4ed8", relief="flat",
                  font=("Segoe UI", 12, "bold"), padx=18, pady=8).pack(anchor="w", padx=20, pady=(0, 20))

        info = tk.Frame(self.main, bg="white", highlightbackground="#e2e8f0", highlightthickness=1)
        info.pack(fill="x", padx=30, pady=10)
        tk.Label(info, text="Current Business Phase", bg="white", fg="#0f172a",
                 font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=20, pady=(16, 3))
        tk.Label(info, text="Inventory Monetization — convert already-owned inventory into cash while protecting profit per envelope.",
                 bg="white", fg="#475569", font=("Segoe UI", 11)).pack(anchor="w", padx=20, pady=(0, 16))

    def show_settings(self):
        self.clear_main()
        self.header("Settings", "System paths and configuration.")
        text = f"Putnam root:\n{ROOT}\n\nOutput folder:\n{OUTPUT_DIR}\n\nShared eBay templates:\n{SHARED_TEMPLATE_DIR}"
        tk.Label(self.main, text=text, bg="#f8fafc", fg="#0f172a", justify="left",
                 font=("Consolas", 10)).pack(anchor="w", padx=30, pady=20)
        tk.Button(self.main, text="Open Putnam Root", command=lambda: self.open_folder(ROOT),
                  font=("Segoe UI", 11)).pack(anchor="w", padx=30)

    def coming(self, name):
        self.clear_main()
        self.header(name, "Coming in a future Putnam OS release.")
        tk.Label(self.main, text="This workspace is intentionally not built yet. Pricing is the current priority.",
                 bg="#f8fafc", fg="#475569", font=("Segoe UI", 12)).pack(anchor="w", padx=30, pady=20)

    def show_pricing(self):
        self.clear_main()
        self.header("Pricing Workspace", "Generate an eBay bulk price revision CSV safely.")

        top = tk.Frame(self.main, bg="#f8fafc")
        top.pack(fill="both", expand=True, padx=30, pady=5)

        left = tk.Frame(top, bg="white", highlightbackground="#e2e8f0", highlightthickness=1)
        left.pack(side="left", fill="both", expand=True, padx=(0, 12), pady=5)

        tk.Label(left, text="Active Listings CSV", bg="white", fg="#0f172a",
                 font=("Segoe UI", 15, "bold")).pack(anchor="w", padx=20, pady=(18, 8))

        drop_text = "Drag & Drop CSV Here\n\nor\n\nBrowse for CSV"
        if not DND_AVAILABLE:
            drop_text = "CSV Drop Zone\n\nDrag/drop support requires tkinterdnd2.\nBrowse works now."
        self.drop = tk.Label(left, text=drop_text, bg="#eff6ff", fg="#1e3a8a",
                             font=("Segoe UI", 13, "bold"), relief="groove", height=8)
        self.drop.pack(fill="x", padx=20, pady=8)

        if DND_AVAILABLE:
            self.drop.drop_target_register(DND_FILES)
            self.drop.dnd_bind("<<Drop>>", self.handle_drop)

        row = tk.Frame(left, bg="white")
        row.pack(fill="x", padx=20, pady=8)
        tk.Button(row, text="Browse for CSV", command=self.browse_csv,
                  bg="#2563eb", fg="white", relief="flat", padx=14, pady=7,
                  font=("Segoe UI", 11, "bold")).pack(side="left")
        tk.Button(row, text="Clear", command=self.clear_file, padx=14, pady=7,
                  font=("Segoe UI", 11)).pack(side="left", padx=10)

        self.file_status = tk.Label(left, text="No file loaded.", bg="white", fg="#475569",
                                    font=("Segoe UI", 10), wraplength=430, justify="left")
        self.file_status.pack(anchor="w", padx=20, pady=(8, 10))

        tk.Label(left, text="Pricing Ladder", bg="white", fg="#0f172a",
                 font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=20, pady=(8, 4))
        ladder_text = "\n".join([f"${fmt_money(k)} → ${fmt_money(v)}" for k, v in sorted(self.ladder.items())]) or "No ladder loaded."
        tk.Label(left, text=ladder_text, bg="white", fg="#334155", justify="left",
                 font=("Consolas", 10)).pack(anchor="w", padx=20, pady=(0, 16))

        right = tk.Frame(top, bg="white", highlightbackground="#e2e8f0", highlightthickness=1)
        right.pack(side="right", fill="both", expand=True, padx=(12, 0), pady=5)

        tk.Label(right, text="Preview", bg="white", fg="#0f172a",
                 font=("Segoe UI", 15, "bold")).pack(anchor="w", padx=20, pady=(18, 8))
        self.preview = tk.Text(right, height=20, wrap="word", bg="#f8fafc", fg="#0f172a",
                               font=("Consolas", 10), relief="flat")
        self.preview.pack(fill="both", expand=True, padx=20, pady=8)
        self.preview.insert("end", "Load an eBay Active Listings CSV to preview changes.")
        self.preview.configure(state="disabled")

        actions = tk.Frame(right, bg="white")
        actions.pack(fill="x", padx=20, pady=(8, 18))
        self.generate_btn = tk.Button(actions, text="Generate Revision CSV", command=self.generate,
                                      bg="#16a34a", fg="white", relief="flat", padx=14, pady=8,
                                      font=("Segoe UI", 11, "bold"), state="disabled")
        self.generate_btn.pack(side="left")
        tk.Button(actions, text="Open Output Folder", command=lambda: self.open_folder(OUTPUT_DIR),
                  padx=14, pady=8, font=("Segoe UI", 11)).pack(side="left", padx=10)

    def handle_drop(self, event):
        raw = event.data.strip()
        # tkinterdnd2 may wrap paths in braces
        if raw.startswith("{") and raw.endswith("}"):
            raw = raw[1:-1]
        # If multiple files, use first
        if "} {" in raw:
            raw = raw.split("} {")[0].strip("{}")
        self.load_csv(Path(raw))

    def browse_csv(self):
        p = filedialog.askopenfilename(title="Select eBay Active Listings CSV", filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if p:
            self.load_csv(Path(p))

    def clear_file(self):
        self.csv_path = None
        self.rows = []
        self.file_status.configure(text="No file loaded.")
        self.set_preview("Load an eBay Active Listings CSV to preview changes.")
        self.generate_btn.configure(state="disabled")

    def load_csv(self, path: Path):
        try:
            rows, fieldnames = read_active_csv(path)
            distribution, changes = analyze(rows, self.ladder)
            self.csv_path = path
            self.rows = rows
            self.file_status.configure(text=f"Loaded: {path.name}\n{len(rows)} listings detected. {len(changes)} would change.")
            self.generate_btn.configure(state="normal")
            lines = [
                f"File: {path.name}",
                f"Listings detected: {len(rows)}",
                f"Listings that would change: {len(changes)}",
                "",
                "Current price distribution:",
            ]
            for price, count in sorted(distribution.items(), key=lambda kv: Decimal(kv[0])):
                lines.append(f"  ${price}: {count}")
            lines.append("")
            lines.append("First 20 proposed changes:")
            for row, old, new in changes[:20]:
                title = (row.get("Title") or "")[:70]
                lines.append(f"  {row.get('Item number','')} | ${fmt_money(old)} -> ${fmt_money(new)} | {title}")
            if len(changes) > 20:
                lines.append(f"  ... plus {len(changes)-20} more")
            self.set_preview("\n".join(lines))
        except Exception as e:
            messagebox.showerror("Invalid CSV", str(e))
            self.clear_file()

    def set_preview(self, text):
        self.preview.configure(state="normal")
        self.preview.delete("1.0", "end")
        self.preview.insert("end", text)
        self.preview.configure(state="disabled")

    def generate(self):
        if not self.csv_path or not self.rows:
            messagebox.showwarning("No file", "Load an Active Listings CSV first.")
            return
        try:
            result = write_outputs(self.csv_path, self.rows, self.ladder)
            self.last_output = result
            msg = (
                f"Revision complete.\n\n"
                f"Listings read: {result['count']}\n"
                f"Listings changed: {result['changed_count']}\n"
                f"Catalog reduction on changed listings: ${result['reduction']}\n\n"
                f"Output folder:\n{result['outdir']}"
            )
            self.set_preview(msg + "\n\nFiles created:\n" + "\n".join([str(result[k]) for k in ["review", "changed", "upload", "report"]]))
            if messagebox.askyesno("Revision Complete", msg + "\n\nOpen output folder now?"):
                self.open_folder(result["outdir"])
        except Exception as e:
            messagebox.showerror("Generation failed", str(e))

    def open_folder(self, path):
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        subprocess.Popen(f'explorer "{path}"')


def main():
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if DND_AVAILABLE:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    app = PutnamOS(root)
    root.mainloop()


if __name__ == "__main__":
    main()
