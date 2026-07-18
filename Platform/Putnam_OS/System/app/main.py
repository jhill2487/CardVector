from __future__ import annotations

import csv
import json
import os
import shutil
import subprocess
import sys
import traceback
from collections import Counter
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk



def _bootstrap_repo_import_path() -> Path:
    current = Path(__file__).resolve()
    for candidate in [current.parent, *current.parents]:
        if (
            (candidate / ".putnam_root").exists()
            or ((candidate / "AGENTS.md").exists() and (candidate / "Docs" / "AGENTS.md").exists())
        ):
            if str(candidate) not in sys.path:
                sys.path.insert(0, str(candidate))
            return candidate
    raise RuntimeError("Could not locate PutnamCollectibles root for imports.")


_bootstrap_repo_import_path()

from Platform.cardvector.marketplace_intelligence import (
    pricing as canonical_pricing,
)
from Platform.putnam_paths import BUSINESS_INVENTORY_DIR, PUTNAM_OS_DIR, ROOT
from Platform.Putnam_OS.System.app import bulk_price_engine

VERSION = "2.1.0"
APP_NAME = "Putnam OS"

DEFAULT_LADDER = dict(canonical_pricing.LEGACY_DEFAULT_LADDER)

DEFAULT_EBAY_TEMPLATE_INFO = ["#INFO", "Version=1.0.0", "Template= eBay-active-revise-price-quantity-download_US", "", "", "", "", "", "", "", "", ""]
DEFAULT_EBAY_TEMPLATE_HEADER = [
    "Action", "Category name", "Item number", "Title", "Listing site", "Currency",
    "Start price", "Buy It Now price", "Available quantity", "Relationship", "Relationship details", "Custom label (SKU)"
]

PRICE_COLUMN_CANDIDATES = [
    "Start price", "Price", "Buy It Now price", "Current price", "List price", "Listing price", "price"
]
ITEM_NUMBER_CANDIDATES = ["Item number", "Item ID", "ItemID", "item_number"]
TITLE_CANDIDATES = ["Title", "title", "Item title", "Listing title"]
QTY_CANDIDATES = ["Available quantity", "Quantity", "Qty", "quantity"]
SKU_CANDIDATES = ["Custom label (SKU)", "SKU", "Custom Label", "Custom label"]
CATEGORY_NAME_CANDIDATES = ["eBay category 1 name", "Category name", "Category", "category"]
CATEGORY_NUMBER_CANDIDATES = ["eBay category 1 number", "Category number", "Category ID", "category_id"]
CURRENCY_CANDIDATES = ["Currency", "currency"]


def money(value) -> Decimal:
    if value is None:
        raise InvalidOperation("None")
    s = str(value).strip().replace("$", "").replace(",", "")
    if s == "":
        raise InvalidOperation("blank")
    return Decimal(s).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def money_str(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}"


def find_root() -> Path:
    return ROOT


ROOT = find_root()
OS_ROOT = PUTNAM_OS_DIR
SYSTEM_DIR = OS_ROOT / "System"
APP_DIR = SYSTEM_DIR / "app"
CONFIG_DIR = SYSTEM_DIR / "config"
LOG_DIR = SYSTEM_DIR / "logs"
DATA_DIR = SYSTEM_DIR / "data"
PRICING_DIR = BUSINESS_INVENTORY_DIR / "Pricing_Revisions"
COMPLETED_DIR = PRICING_DIR / "Completed Jobs"
INCOMING_DIR = PRICING_DIR / "Incoming Files"
SHARED_TEMPLATE_DIR = ROOT / "Shared" / "Templates" / "eBay" / "Bulk_Revise"
CONFIG_PATH = CONFIG_DIR / "pricing_rules.json"


def ensure_dirs() -> None:
    for p in [SYSTEM_DIR, APP_DIR, CONFIG_DIR, LOG_DIR, DATA_DIR, PRICING_DIR, COMPLETED_DIR, INCOMING_DIR, SHARED_TEMPLATE_DIR]:
        p.mkdir(parents=True, exist_ok=True)


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def load_rules() -> dict:
    default_rules = {
        "version": VERSION,
        "strategy_name": "Putnam Buyer-Paid Shipping Pricing Rules",
        "minimum_new_listing_price": "0.99",
        "high_value_review_threshold": "20.00",
        "price_ladder": DEFAULT_LADDER,
    }
    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(json.dumps(default_rules, indent=2), encoding="utf-8")
        return default_rules
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))
        merged = default_rules | data
        if "price_ladder" not in merged or not isinstance(merged["price_ladder"], dict):
            merged["price_ladder"] = DEFAULT_LADDER
        return merged
    except Exception:
        backup = CONFIG_PATH.with_suffix(f".bad_{now_stamp()}.json")
        shutil.copy2(CONFIG_PATH, backup)
        CONFIG_PATH.write_text(json.dumps(default_rules, indent=2), encoding="utf-8")
        return default_rules


def normalized_ladder(rules: dict) -> dict[str, str]:
    ladder = rules.get("price_ladder", DEFAULT_LADDER)
    return canonical_pricing.normalize_price_ladder(
        ladder,
        parse_money=money,
        format_money=money_str,
    )


def open_folder(path: Path) -> None:
    try:
        os.startfile(str(path))
    except Exception:
        subprocess.Popen(["explorer", str(path)])


def sniff_rows(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        sample = f.read(4096)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample)
        except csv.Error:
            dialect = csv.excel
        rows = list(csv.reader(f, dialect))
    return rows, dialect


def detect_file(rows):
    """
    Identify supported CSV types.

    eBay exports may include informational rows before the actual column
    headers, so inspect the first several rows rather than assuming that
    the header is always row zero.
    """
    if not rows:
        return None, None

    # Inspect enough rows to handle eBay metadata/information rows.
    for idx, row in enumerate(rows[:20]):
        header = [str(cell).strip() for cell in row]

        item_i = find_col(header, ITEM_NUMBER_CANDIDATES, False)
        title_i = find_col(header, TITLE_CANDIDATES, False)
        price_i = find_col(header, PRICE_COLUMN_CANDIDATES, False)
        action_i = find_col(header, ["Action"], False)

        # eBay bulk revise/upload template.
        if (
            action_i is not None
            and item_i is not None
            and find_col(header, ["Start price"], False) is not None
        ):
            return "bulk_template", idx

        # eBay Active Listings export.
        #
        # Item number is the key distinction between an existing listing
        # export and a CardUploader/new-listing CSV.
        if item_i is not None and price_i is not None:
            return "active_listings", idx

    # CardUploader/new-listing exports normally have title and price,
    # but may not yet have an eBay item number.
    first = [str(cell).strip() for cell in rows[0]]

    if (
        find_col(first, TITLE_CANDIDATES, False) is not None
        and find_col(first, PRICE_COLUMN_CANDIDATES, False) is not None
    ):
        return "new_listing_csv", 0

    return None, None


def find_col(header, candidates, required=True):
    norm = {str(c).strip().lower(): i for i, c in enumerate(header)}
    for cand in candidates:
        key = cand.strip().lower()
        if key in norm:
            return norm[key]
    if required:
        raise ValueError(f"Required column missing. Expected one of: {', '.join(candidates)}")
    return None


def get_cell(row, index, default=""):
    if index is None or index >= len(row):
        return default
    return str(row[index]).strip()


def build_category(record):
    name = record.get("category_name") or "CCG Individual Cards"
    number = record.get("category_number") or "183454"
    if "(" in name and name.endswith(")"):
        return name
    return f"{name} ({number})"


def choose_template_rows():
    candidates = sorted(SHARED_TEMPLATE_DIR.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True) if SHARED_TEMPLATE_DIR.exists() else []
    for path in candidates:
        try:
            rows, _ = sniff_rows(path)
            ftype, hidx = detect_file(rows)
            if ftype == "bulk_template":
                return rows[0], rows[hidx]
        except Exception:
            continue
    return DEFAULT_EBAY_TEMPLATE_INFO, DEFAULT_EBAY_TEMPLATE_HEADER


def normalize_existing_records(rows, header_index, file_type):
    header = [c.strip() for c in rows[header_index]]
    data = rows[header_index + 1:]

    if file_type == "active_listings":
        item_i = find_col(header, ITEM_NUMBER_CANDIDATES)
        title_i = find_col(header, TITLE_CANDIDATES, False)
        price_i = find_col(header, PRICE_COLUMN_CANDIDATES)
        catn_i = find_col(header, CATEGORY_NAME_CANDIDATES, False)
        catid_i = find_col(header, CATEGORY_NUMBER_CANDIDATES, False)

    else:
        item_i = find_col(header, ITEM_NUMBER_CANDIDATES)
        title_i = find_col(header, TITLE_CANDIDATES, False)
        price_i = find_col(header, ["Start price"])
        catn_i = find_col(header, ["Category name"], False)
        catid_i = None

    qty_i = find_col(header, QTY_CANDIDATES, False)
    curr_i = find_col(header, CURRENCY_CANDIDATES, False)
    sku_i = find_col(header, SKU_CANDIDATES, False)

    records = []

    for line_no, row in enumerate(data, start=header_index + 2):
        if not any(str(x).strip() for x in row):
            continue

        records.append({
            "line_no": line_no,
            "item_number": get_cell(row, item_i),
            "title": get_cell(row, title_i),
            "currency": get_cell(row, curr_i, "USD") or "USD",
            "old_price_raw": get_cell(row, price_i),
            "available_qty": get_cell(row, qty_i, "1") or "1",
            "category_name": get_cell(row, catn_i),
            "category_number": get_cell(row, catid_i),
            "sku": get_cell(row, sku_i),
        })

    return records


def apply_existing_ladder(records, ladder):
    return canonical_pricing.apply_exact_price_ladder(
        records,
        ladder,
        parse_money=money,
        format_money=money_str,
    )


def write_dict_csv(path: Path, rows: list[dict], header: list[str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def write_existing_upload_csv(path: Path, changed: list[dict]):
    info, header = choose_template_rows()
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(info)
        writer.writerow(header)
        for rec in changed:
            row_map = {
                "Action": "Revise",
                "Category name": build_category(rec),
                "Item number": rec["item_number"],
                "Title": rec["title"],
                "Listing site": "US",
                "Currency": rec.get("currency") or "USD",
                "Start price": rec["new_price"],
                "Buy It Now price": "",
                "Available quantity": rec.get("available_qty") or "1",
                "Relationship": "",
                "Relationship details": "",
                "Custom label (SKU)": rec.get("sku") or "",
            }
            writer.writerow([row_map.get(h, "") for h in header])


def existing_price_revision(source_path: Path) -> tuple[Path, dict]:
    rules = load_rules()
    ladder = normalized_ladder(rules)
    rows, _ = sniff_rows(source_path)
    file_type, hidx = detect_file(rows)
    if file_type not in {"active_listings", "bulk_template"}:
        raise ValueError("This does not appear to be an eBay Active Listings CSV or eBay price/quantity template.")
    records = normalize_existing_records(rows, hidx, file_type)
    processed, invalid = apply_existing_ladder(records, ladder)
    changed = [r for r in processed if r["status"] == "CHANGE"]
    stamp = now_stamp()
    job_dir = COMPLETED_DIR / f"Existing_Listing_Price_Revision_{stamp}"
    job_dir.mkdir(parents=True, exist_ok=True)
    backup = job_dir / "source_backup"
    backup.mkdir(exist_ok=True)
    shutil.copy2(source_path, backup / source_path.name)

    review_header = ["status", "item_number", "title", "old_price", "new_price", "change", "reason", "available_qty", "currency", "category_name", "category_number", "sku", "line_no"]
    review_csv = job_dir / f"review_all_rows_{stamp}.csv"
    changed_csv = job_dir / f"changed_only_{stamp}.csv"
    upload_csv = job_dir / f"EBAY_UPLOAD_price_revision_{stamp}.csv"
    rollback_csv = job_dir / f"ROLLBACK_old_prices_{stamp}.csv"
    report_txt = job_dir / f"price_revision_report_{stamp}.txt"
    invalid_csv = job_dir / f"invalid_rows_{stamp}.csv"

    write_dict_csv(review_csv, processed + invalid, review_header)
    write_dict_csv(changed_csv, changed, review_header)
    if invalid:
        write_dict_csv(invalid_csv, invalid, review_header)
    write_existing_upload_csv(upload_csv, changed)
    rollback_records = []
    for r in changed:
        rb = dict(r)
        rb["new_price"] = r["old_price"]
        rollback_records.append(rb)
    write_existing_upload_csv(rollback_csv, rollback_records)

    total_reduction = sum((money(r["old_price"]) - money(r["new_price"]) for r in changed), Decimal("0.00"))
    change_counter = Counter((r["old_price"], r["new_price"]) for r in changed)
    old_counter = Counter(r["old_price"] for r in processed if r.get("old_price"))
    lines = [
        f"Putnam OS v{VERSION} - Existing Listing Price Revision",
        "Generated: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "",
        f"Source file: {source_path}",
        f"Detected type: {file_type}",
        "",
        f"Listings read: {len(processed) + len(invalid)}",
        f"Changed rows: {len(changed)}",
        f"Unchanged rows: {len([r for r in processed if r['status'] == 'UNCHANGED'])}",
        f"Invalid rows: {len(invalid)}",
        f"Total listed price reduction if uploaded: ${money_str(total_reduction)}",
        "",
        "Change summary:",
    ]
    for (old, new), count in sorted(change_counter.items(), key=lambda kv: money(kv[0][0])):
        lines.append(f"  ${old} -> ${new}: {count}")
    lines.append("")
    lines.append("Current price distribution:")
    for price, count in sorted(old_counter.items(), key=lambda kv: money(kv[0])):
        lines.append(f"  ${price}: {count}")
    lines.append("")
    lines.append("Output files:")
    for p in [review_csv, changed_csv, upload_csv, rollback_csv, report_txt]:
        lines.append(f"  {p.name}: {p}")
    report_txt.write_text("\n".join(lines), encoding="utf-8")
    log_run("existing_price_revision", source_path, job_dir, len(changed))
    return job_dir, {"read": len(processed) + len(invalid), "changed": len(changed), "reduction": money_str(total_reduction), "invalid": len(invalid)}


def log_run(action: str, source: Path, job_dir: Path, changed: int) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"putnam_os_{now_stamp()}.log"
    log_path.write_text(f"Putnam OS v{VERSION}\nAction: {action}\nSource: {source}\nJob: {job_dir}\nChanged: {changed}\n", encoding="utf-8")


def review_new_listing_prices(source_path: Path) -> tuple[Path, dict]:
    rules = load_rules()
    ladder = normalized_ladder(rules)
    floor = money(rules.get("minimum_new_listing_price", "0.99"))
    high_review = money(rules.get("high_value_review_threshold", "20.00"))
    rows, dialect = sniff_rows(source_path)
    file_type, hidx = detect_file(rows)
    if file_type != "new_listing_csv" and file_type != "bulk_template":
        # Some CardUploader exports might look like eBay template. We'll allow bulk_template as new listing if no item numbers are required.
        if file_type not in {"active_listings"}:
            raise ValueError("This does not appear to be a CardUploader/new-listing CSV with title and price columns.")
    header = [c.strip() for c in rows[hidx]]
    data_rows = rows[hidx + 1:]
    title_i = find_col(header, TITLE_CANDIDATES, False)
    price_i = find_col(header, PRICE_COLUMN_CANDIDATES, True)
    sku_i = find_col(header, SKU_CANDIDATES, False)
    item_i = find_col(header, ITEM_NUMBER_CANDIDATES, False)

    stamp = now_stamp()
    job_dir = COMPLETED_DIR / f"New_Listing_Price_Review_{stamp}"
    job_dir.mkdir(parents=True, exist_ok=True)
    backup = job_dir / "source_backup"
    backup.mkdir(exist_ok=True)
    shutil.copy2(source_path, backup / source_path.name)

    output_rows = [list(r) for r in rows]
    review_records = []
    changed = 0
    invalid = 0
    flagged = 0
    for offset, row in enumerate(data_rows, start=hidx + 1):
        if not any(str(x).strip() for x in row):
            continue
        while len(output_rows[offset]) < len(header):
            output_rows[offset].append("")
        old_raw = get_cell(row, price_i)
        title = get_cell(row, title_i) if title_i is not None else ""
        sku = get_cell(row, sku_i) if sku_i is not None else ""
        item = get_cell(row, item_i) if item_i is not None else ""
        try:
            pricing = canonical_pricing.evaluate_new_listing_price(
                old_raw,
                ladder,
                floor=floor,
                high_review_threshold=high_review,
                parse_money=money,
                format_money=money_str,
            )
            old = pricing["old_price"]
            new = pricing["new_price"]
            status = pricing["status"]
            reason = pricing["reason"]
            if pricing["high_review"]:
                flagged += 1
            if new != old:
                changed += 1
                output_rows[offset][price_i] = money_str(new)
            review_records.append({
                "status": status,
                "title": title,
                "sku": sku,
                "item_number": item,
                "old_price": money_str(old),
                "new_price": money_str(new),
                "change": money_str(new - old),
                "reason": reason,
                "line_no": offset + 1,
            })
        except Exception as e:
            invalid += 1
            review_records.append({
                "status": "INVALID_PRICE",
                "title": title,
                "sku": sku,
                "item_number": item,
                "old_price": old_raw,
                "new_price": "",
                "change": "",
                "reason": str(e),
                "line_no": offset + 1,
            })

    revised_csv = job_dir / f"CARDUPLOADER_REVISED_new_listings_{stamp}.csv"
    with revised_csv.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f, dialect)
        writer.writerows(output_rows)

    review_header = ["status", "title", "sku", "item_number", "old_price", "new_price", "change", "reason", "line_no"]
    review_csv = job_dir / f"new_listing_price_review_{stamp}.csv"
    changed_csv = job_dir / f"new_listing_changed_only_{stamp}.csv"
    report_txt = job_dir / f"new_listing_price_report_{stamp}.txt"
    write_dict_csv(review_csv, review_records, review_header)
    write_dict_csv(changed_csv, [r for r in review_records if r["status"] == "CHANGE"], review_header)

    total_delta = sum((money(r["new_price"]) - money(r["old_price"]) for r in review_records if r["status"] == "CHANGE"), Decimal("0.00"))
    lines = [
        f"Putnam OS v{VERSION} - New Listing Price Review",
        "Generated: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "",
        f"Source file: {source_path}",
        f"Rows reviewed: {len(review_records)}",
        f"Changed prices: {changed}",
        f"High-value review flags: {flagged}",
        f"Invalid price rows: {invalid}",
        f"Net listed price delta: ${money_str(total_delta)}",
        "",
        "Rules used:",
        f"  Minimum new listing price: ${money_str(floor)}",
        f"  High-value review threshold: ${money_str(high_review)}",
        "  Exact ladder prices are adjusted when matched.",
        "",
        "Output files:",
        f"  Revised new-listing CSV: {revised_csv}",
        f"  Review CSV: {review_csv}",
        f"  Changed-only CSV: {changed_csv}",
        "",
        "Safety notes:",
        "  - Original CSV was not modified.",
        "  - Review the revised CSV before uploading to eBay.",
        "  - This tool uses CardUploader/source price as the starting point; it does not scrape live market prices.",
    ]
    report_txt.write_text("\n".join(lines), encoding="utf-8")
    log_run("new_listing_price_review", source_path, job_dir, changed)
    return job_dir, {"read": len(review_records), "changed": changed, "delta": money_str(total_delta), "invalid": invalid, "flagged": flagged}


class PutnamOS(tk.Tk):
    def __init__(self):
        super().__init__()
        ensure_dirs()
        self.title(f"Putnam OS v{VERSION}")
        self.geometry("1060x700")
        self.minsize(980, 640)
        self.configure(bg="#f4f4f4")
        self.current_workspace = tk.StringVar(value="Dashboard")
        self.last_job_dir: Path | None = None
        self._build_ui()

    def _build_ui(self):
        self.sidebar = tk.Frame(self, bg="#121212", width=210)
        self.sidebar.pack(side="left", fill="y")
        self.main = tk.Frame(self, bg="#f4f4f4")
        self.main.pack(side="left", fill="both", expand=True)
        tk.Label(self.sidebar, text="PUTNAM OS", font=("Arial", 18, "bold"), bg="#121212", fg="white").pack(pady=(28, 4))
        tk.Label(self.sidebar, text=f"v{VERSION}", font=("Arial", 9), bg="#121212", fg="#aaaaaa").pack(pady=(0, 22))
        for name in ["Dashboard", "Pricing", "Inventory", "Shipping", "Content", "Analytics", "Settings"]:
            tk.Button(self.sidebar, text=name, font=("Arial", 12), anchor="w", width=20, height=2, command=lambda n=name: self.show(n)).pack(padx=14, pady=4)
        tk.Button(self.sidebar, text="Open Putnam Root", font=("Arial", 10), command=lambda: open_folder(ROOT)).pack(side="bottom", pady=18, padx=12, fill="x")
        self.show("Dashboard")

    def clear_main(self):
        for child in self.main.winfo_children():
            child.destroy()

    def show(self, name: str):
        self.current_workspace.set(name)
        self.clear_main()
        if name == "Dashboard":
            self.dashboard()
        elif name == "Pricing":
            self.pricing()
        elif name == "Settings":
            self.settings()
        else:
            self.placeholder(name)

    def header(self, title, subtitle=""):
        frame = tk.Frame(self.main, bg="#f4f4f4")
        frame.pack(fill="x", padx=30, pady=(24, 10))
        tk.Label(frame, text=title, font=("Arial", 24, "bold"), bg="#f4f4f4", fg="#111111").pack(anchor="w")
        if subtitle:
            tk.Label(frame, text=subtitle, font=("Arial", 11), bg="#f4f4f4", fg="#555555").pack(anchor="w", pady=(4, 0))

    def card(self, parent=None):
        if parent is None:
            parent = self.main
        frame = tk.Frame(parent, bg="white", bd=1, relief="solid")
        frame.pack(fill="x", padx=30, pady=10)
        return frame

    def dashboard(self):
        self.header("Dashboard", "Build the business. Document the journey. Improve the system.")
        c = self.card()
        tk.Label(c, text="Current Mission", font=("Arial", 15, "bold"), bg="white").pack(anchor="w", padx=18, pady=(16, 4))
        tk.Label(c, text="Pricing updated. Next: record and process the first 100-card listing batch.", font=("Arial", 12), bg="white", fg="#333333").pack(anchor="w", padx=18, pady=(0, 14))
        tk.Button(c, text="Open Pricing Workspace", font=("Arial", 12), command=lambda: self.show("Pricing")).pack(anchor="w", padx=18, pady=(0, 18))
        grid = tk.Frame(self.main, bg="#f4f4f4")
        grid.pack(fill="x", padx=20, pady=5)
        for label, value in [("Goal", "10,000 listings"), ("Business Phase", "Inventory monetization"), ("Primary KPI", "Profit per envelope")]:
            f = tk.Frame(grid, bg="white", bd=1, relief="solid")
            f.pack(side="left", expand=True, fill="x", padx=10)
            tk.Label(f, text=label, bg="white", fg="#666", font=("Arial", 10)).pack(anchor="w", padx=14, pady=(12, 2))
            tk.Label(f, text=value, bg="white", fg="#111", font=("Arial", 14, "bold")).pack(anchor="w", padx=14, pady=(0, 14))

    def pricing(self):
        self.header("Pricing Workspace", "Existing listing revisions and new CardUploader listing price review.")
        notebook = ttk.Notebook(self.main)
        notebook.pack(fill="both", expand=True, padx=30, pady=10)
        existing_tab = tk.Frame(notebook, bg="white")
        new_tab = tk.Frame(notebook, bg="white")
        notebook.add(existing_tab, text="Existing Listing Price Reviser")
        notebook.add(new_tab, text="New Listing Price Reviewer")
        self._existing_tab(existing_tab)
        self._new_listing_tab(new_tab)

    def file_row(self, parent, label_text):
        var = tk.StringVar()
        row = tk.Frame(parent, bg="white")
        row.pack(fill="x", padx=20, pady=(16, 6))
        tk.Label(row, text=label_text, font=("Arial", 12, "bold"), bg="white").pack(anchor="w")
        entry = tk.Entry(row, textvariable=var, font=("Arial", 10))
        entry.pack(side="left", fill="x", expand=True, pady=(8, 0))
        def browse():
            path = filedialog.askopenfilename(title="Select CSV", filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
            if path:
                var.set(path)
        tk.Button(row, text="Browse", command=browse).pack(side="left", padx=(8, 0), pady=(8, 0))
        return var

    def _existing_tab(self, tab):
        tk.Label(
            tab,
            text="Use this after changing store pricing strategy for active eBay listings.",
            bg="white",
            fg="#444",
            font=("Arial", 11),
        ).pack(anchor="w", padx=20, pady=(20, 4))

        var = self.file_row(
            tab,
            "eBay Active Listings CSV or eBay price/quantity template",
        )

        info = tk.Label(
            tab,
            text="Output: eBay upload candidate, review CSV, rollback CSV, report.",
            bg="white",
            fg="#666",
        )
        info.pack(anchor="w", padx=20, pady=8)

        result = tk.Text(tab, height=9, wrap="word")
        result.pack(fill="x", padx=20, pady=10)

        def run():
            try:
                src = Path(var.get().strip().strip('"'))

                if not src.exists():
                    raise FileNotFoundError(f"CSV not found:\n{src}")

                summary = bulk_price_engine.run_revision(
                    source_path=src,
                    root=ROOT,
                    config_path=CONFIG_PATH,
                    output_base=COMPLETED_DIR,
                )

                job = Path(summary["job_dir"])
                self.last_job_dir = job

                result.delete("1.0", tk.END)
                result.insert(
                    tk.END,
                    f"Complete.\n\n"
                    f"Rows read: {summary['total_rows']}\n"
                    f"Changed: {summary['changed_rows']}\n"
                    f"Unchanged: {summary['unchanged_rows']}\n"
                    f"Invalid: {summary['invalid_rows']}\n"
                    f"Total reduction: ${summary['total_reduction']}\n\n"
                    f"Upload CSV:\n{summary['upload_csv']}\n\n"
                    f"Output folder:\n{job}",
                )

                messagebox.showinfo(
                    "Price Revision Complete",
                    f"Changed {summary['changed_rows']} rows.\n"
                    "Output folder opened.",
                )

                open_folder(job)

            except Exception as e:
                result.delete("1.0", tk.END)
                result.insert(tk.END, traceback.format_exc())
                messagebox.showerror("Error", str(e))

        btns = tk.Frame(tab, bg="white")
        btns.pack(fill="x", padx=20, pady=10)

        tk.Button(
            btns,
            text="Generate Existing Listing Revision",
            font=("Arial", 12, "bold"),
            command=run,
        ).pack(side="left")

        tk.Button(
            btns,
            text="Open Completed Jobs",
            command=lambda: open_folder(COMPLETED_DIR),
        ).pack(side="left", padx=10)

    def _new_listing_tab(self, tab):
        tk.Label(tab, text="Use this after CardUploader generates a CSV for new eBay listings.", bg="white", fg="#444", font=("Arial", 11)).pack(anchor="w", padx=20, pady=(20, 4))
        tk.Label(tab, text="This does not scrape live market prices. It uses CardUploader/source price as the starting point, then applies Putnam guardrails.", bg="white", fg="#666", font=("Arial", 10)).pack(anchor="w", padx=20, pady=(0, 8))
        var = self.file_row(tab, "CardUploader / New Listing CSV")
        rules = load_rules()
        tk.Label(tab, text=f"Rules: minimum ${rules.get('minimum_new_listing_price', '0.99')} · review flag at ${rules.get('high_value_review_threshold', '20.00')} · exact ladder prices adjusted", bg="white", fg="#333", font=("Arial", 10)).pack(anchor="w", padx=20, pady=8)
        result = tk.Text(tab, height=9, wrap="word")
        result.pack(fill="x", padx=20, pady=10)
        def run():
            try:
                src = Path(var.get().strip().strip('"'))
                job, summary = review_new_listing_prices(src)
                self.last_job_dir = job
                result.delete("1.0", tk.END)
                result.insert(tk.END, f"Complete.\n\nRows reviewed: {summary['read']}\nChanged prices: {summary['changed']}\nNet delta: ${summary['delta']}\nHigh-value flags: {summary['flagged']}\nInvalid: {summary['invalid']}\n\nOutput folder:\n{job}")
                messagebox.showinfo("New Listing Review Complete", f"Changed {summary['changed']} prices.\nOutput folder opened.")
                open_folder(job)
            except Exception as e:
                result.delete("1.0", tk.END)
                result.insert(tk.END, traceback.format_exc())
                messagebox.showerror("Error", str(e))
        btns = tk.Frame(tab, bg="white")
        btns.pack(fill="x", padx=20, pady=10)
        tk.Button(btns, text="Review New Listing Prices", font=("Arial", 12, "bold"), command=run).pack(side="left")
        tk.Button(btns, text="Open Completed Jobs", command=lambda: open_folder(COMPLETED_DIR)).pack(side="left", padx=10)

    def placeholder(self, name: str):
        self.header(name, "Coming in a future Putnam OS release.")
        c = self.card()
        tk.Label(c, text=f"{name} Workspace", font=("Arial", 15, "bold"), bg="white").pack(anchor="w", padx=18, pady=(16, 4))
        tk.Label(c, text="This workspace is intentionally not fully built yet. It will be driven by observed workflow bottlenecks.", bg="white", fg="#444", font=("Arial", 11)).pack(anchor="w", padx=18, pady=(0, 16))

    def settings(self):
        self.header("Settings", "Current Putnam OS paths and pricing rules.")
        c = self.card()
        txt = tk.Text(c, height=18, wrap="word")
        txt.pack(fill="both", expand=True, padx=18, pady=18)
        rules = load_rules()
        txt.insert(tk.END, f"Root: {ROOT}\n")
        txt.insert(tk.END, f"Putnam OS: {OS_ROOT}\n")
        txt.insert(tk.END, f"Pricing completed jobs: {COMPLETED_DIR}\n")
        txt.insert(tk.END, f"Shared eBay templates: {SHARED_TEMPLATE_DIR}\n\n")
        txt.insert(tk.END, json.dumps(rules, indent=2))
        txt.config(state="disabled")


def main():
    ensure_dirs()
    app = PutnamOS()
    app.mainloop()


if __name__ == "__main__":
    main()
