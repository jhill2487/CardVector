import csv, json, os, shutil, sys, webbrowser, statistics, re, urllib.parse, urllib.request, subprocess
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
import time
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except Exception:
    DND_AVAILABLE = False

import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog


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

from Platform.putnam_paths import (
    DATA_EXPORTS_DIR,
    DATA_IMPORTS_DIR,
    DATA_LOGS_DIR,
    DATA_MEDIA_DIR,
    DOCS_DIR,
    PUTNAM_OS_DIR,
    PUTNAM_PLATFORM_DIR,
    ROOT,
    WORK_SESSIONS_DIR,
)

APP_VERSION = "3.4.1"
APP_NAME = "Putnam OS"
FLOOR = 0.99
REVIEW_THRESHOLD = 20.00

LISTING_OPTIMIZER_VERSION = "1.2"
COMP_ENGINE_VERSION = "Putnam Comp Engine v1.2"
COMP_ENGINE_SUBTITLE = "Search Analytics + Explainable Rejections"
COMP_UI_VERSION = "Putnam Comp Engine UI v1.2.1"
COMP_UI_SUBTITLE = "UI Bug Fix Patch"
EXPORT_FLOOR_PRICE = Decimal("0.99")
SHIPPING_POLICY_DEFAULT = "Buyer Pays Shipping"
PROMOTION_POLICY_DEFAULT = "Free Shipping on 3+ Cards"

BRAND = {
    "bg": "#080A0F",
    "panel": "#0B1426",
    "panel2": "#101B33",
    "sidebar": "#05070C",
    "blue": "#0077FF",
    "blue2": "#20A4FF",
    "gold": "#D8A72E",
    "gold_dark": "#8A6418",
    "text": "#F5F7FB",
    "muted": "#B9C4D8",
    "success": "#22C55E",
    "warning": "#FACC15",
    "danger": "#EF4444",
}

EXCLUDE_TERMS = [
    "world championship", "worlds", "world championship deck", " deck", "theme deck",
    "battle deck", "starter deck", "psa", "bgs", "cgc", "sgc", "ace", "tag", "slab",
    "graded", "lot", "bundle", "playset", "4x", "x4", "pack", "booster", "wrapper",
    "sealed", "proxy", "custom", "reprint", "metal", "gold foil", "jumbo", "oversized",
    "complete set", "binder", "master set"
]
NAME_MATCH_SCORE_THRESHOLD = 90
GRADED_EXCLUDE_TERMS = {"psa", "bgs", "cgc", "tag", "sgc"}
NON_SINGLE_EXCLUDE_TERMS = {
    "lot", "lots", "playset", "pack", "packs", "booster", "box", "deck", "sealed", "case"
}
COMP_ANALYTICS_FIELDS = [
    "Card Name", "Set Name", "Card Number", "Search Query Used", "Total Candidates Returned",
    "Accepted Candidates", "Rejected Candidates", "Rejected: card name mismatch",
    "Rejected: card number mismatch", "Rejected: excluded graded term",
    "Rejected: excluded lot/pack/playset/booster/deck/sealed term", "Rejected: other reason",
]
REJECTION_DIAGNOSTIC_FIELDS = [
    "card_name_expected", "candidate_title", "normalized_card_name", "normalized_candidate_title",
    "name_match_score", "matched_name_tokens", "missing_name_tokens", "card_number_expected",
    "card_number_found", "card_number_match", "set_expected", "set_match_score",
    "excluded_terms_found", "final_rejection_reason", "rejection_details",
]


OS_DIR = PUTNAM_OS_DIR
SYSTEM = OS_DIR / "System"
APP_DIR = SYSTEM / "app"
DECISION_ENGINE_DIR = SYSTEM / "decision_engine"
CONFIG = SYSTEM / "config"
LOGS = SYSTEM / "logs"
CACHE = SYSTEM / "cache"
DATA = SYSTEM / "data"
INVENTORY_SNAPSHOT = DATA / "carduploader_inventory_snapshot.csv"
INVENTORY_AUDIT_DIR = DATA / "inventory_audit"
INVENTORY_AUDIT_IMAGES = INVENTORY_AUDIT_DIR / "audit_images"
INVENTORY_AUDIT_REPORTS = INVENTORY_AUDIT_DIR / "reports"
INVENTORY_AUDIT_HISTORY = INVENTORY_AUDIT_DIR / "inventory_audit_history.csv"
CURRENT_INVENTORY_AUDIT = INVENTORY_AUDIT_DIR / "current_inventory_audit.json"
INVENTORY_AUDIT_SESSIONS_DIR = DATA_LOGS_DIR / "inventory_audit_sessions"
LOCATION_UPDATE_LOG = DATA_LOGS_DIR / "location_update_log.csv"
INVENTORY_AUDIT_EVENT_LOG = DATA_LOGS_DIR / "inventory_audit_event_log.csv"
INCOMING = OS_DIR / "Incoming Files"
COMPLETED = OS_DIR / "Completed Jobs"
IMPORTS = DATA_IMPORTS_DIR
EXPORTS = DATA_EXPORTS_DIR
MEDIA = DATA_MEDIA_DIR
COLLECTR = ROOT / "Collectr"
ROOT_SESSIONS = WORK_SESSIONS_DIR
ARCHIVE = ROOT / "Archive"
DOCS = DOCS_DIR
DOWNLOADS = ROOT / "Downloads"
ROOT_LOGS = DATA_LOGS_DIR
EXPORT_HISTORY_LOG = ROOT_LOGS / "export_history.csv"
PRICING_PERFORMANCE_LOG = DATA_LOGS_DIR / "pricing_performance_log.csv"
UI_BUGFIX_LOG = DATA_LOGS_DIR / "ui_bugfix_log.txt"
CARDUPLOADER_INVENTORY_IMPORTS = IMPORTS / "CardUploader_Inventory"
SESSIONS = ROOT_SESSIONS

PLATFORM = PUTNAM_PLATFORM_DIR
TOOLS = PLATFORM / "tools"
UTILITIES = PLATFORM / "utilities"
INSTALLERS = PLATFORM / "installers"

CONTENT = ROOT / "Putnam_Content"
CONTENT_IDEAS = CONTENT / "Ideas"
CONTENT_RECORDINGS = CONTENT / "Recordings"
CONTENT_CLIPS = CONTENT / "Clips"
CONTENT_EPISODES = CONTENT / "Episodes"

for p in [OS_DIR, SYSTEM, APP_DIR, CONFIG, LOGS, CACHE, DATA, INCOMING, COMPLETED,
          IMPORTS, CARDUPLOADER_INVENTORY_IMPORTS, EXPORTS, MEDIA, COLLECTR, ROOT_SESSIONS, ARCHIVE, DOCS, ROOT_LOGS,
          INVENTORY_AUDIT_DIR, INVENTORY_AUDIT_IMAGES, INVENTORY_AUDIT_REPORTS,
          PLATFORM, TOOLS, UTILITIES, INSTALLERS, CONTENT, CONTENT_IDEAS, CONTENT_RECORDINGS,
          CONTENT_CLIPS, CONTENT_EPISODES]:
    p.mkdir(parents=True, exist_ok=True)

if str(SYSTEM) not in sys.path:
    sys.path.insert(0, str(SYSTEM))
if str(OS_DIR) not in sys.path:
    sys.path.insert(0, str(OS_DIR))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Putnam_Seller_Tools.location_registry import (
    canonical_game,
    display_game as display_location_game,
    record_location,
    registry_path,
    registry_summary_text,
    suggest_next_location,
    validate_location,
)
from capture_studio import CAPTURE_ROOT, CaptureStudioError, CaptureStudioService
from orders_fulfillment import PICK_LIST_ROOT, generate_pick_slips


def nowstamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def today_id():
    return datetime.now().strftime("%Y-%m-%d")


def append_activity(message: str):
    LOGS.mkdir(parents=True, exist_ok=True)
    line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {message}\n"
    with open(LOGS / "activity.log", "a", encoding="utf-8") as f:
        f.write(line)


def recent_activity(limit=8):
    path = LOGS / "activity.log"
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
        return lines[-limit:][::-1]
    except Exception:
        return []


def decision_engine_unavailable(reason: str):
    return {
        "business_goal": "unavailable",
        "secondary_goal": "",
        "risk_tolerance": "",
        "modules_loaded": 0,
        "modules_active": 0,
        "placeholders": 0,
        "errors": 1,
        "last_engine_check": "",
        "module_results": [],
        "log_path": "",
        "notes": [reason],
    }


def run_decision_engine_check(write_log=True):
    try:
        from decision_engine.engine import DecisionEngine

        return DecisionEngine(ROOT).run_check(write_log=write_log)
    except Exception as exc:
        return decision_engine_unavailable(str(exc))


def decision_engine_summary_text(result):
    placeholders = result.get("placeholders", 0)
    errors = result.get("errors", 0)
    lines = [
        f"Business goal: {result.get('business_goal', '')}",
        f"Modules loaded: {result.get('modules_loaded', 0)}",
        f"Modules active: {result.get('modules_active', 0)}",
        f"Placeholders: {placeholders}",
        f"Last engine check: {result.get('last_engine_check', '') or 'not run'}",
    ]
    if errors:
        lines.append(f"Errors: {errors}")
    for note in result.get("notes", []):
        lines.append(f"Note: {note}")
    return "\n".join(lines)


def money(v):
    try:
        return float(str(v).replace("$", "").replace(",", "").strip() or 0)
    except Exception:
        return 0.0


def read_csv(path):
    for enc in ["utf-8-sig", "utf-8", "cp1252"]:
        try:
            with open(path, newline="", encoding=enc) as f:
                return list(csv.DictReader(f))
        except UnicodeDecodeError:
            continue
    with open(path, newline="", encoding="utf-8-sig", errors="replace") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, fields=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not fields:
        fields = list(rows[0].keys()) if rows else []
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


class ExportCancelled(RuntimeError):
    pass


def decimal_money(value) -> Decimal:
    raw = str(value or "").replace("$", "").replace(",", "").strip()
    if not raw:
        return Decimal("0.00")
    try:
        return Decimal(raw)
    except InvalidOperation:
        return Decimal("0.00")


def format_decimal_money(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def normalize_column_name(value: str) -> str:
    return "".join(ch for ch in str(value or "").lower().strip() if ch.isalnum())


def find_column(fieldnames, candidates):
    by_norm = {normalize_column_name(name): name for name in fieldnames}
    for candidate in candidates:
        found = by_norm.get(normalize_column_name(candidate))
        if found:
            return found
    return None


def find_columns(fieldnames, candidates):
    wanted = {normalize_column_name(candidate) for candidate in candidates}
    return [name for name in fieldnames if normalize_column_name(name) in wanted]


def price_column(fieldnames):
    return find_column(fieldnames, ["*StartPrice", "StartPrice", "Price", "BuyItNowPrice"])


def batch_location_columns(fieldnames):
    # Only known batch/location fields are stamped; product, catalog, and internal SKUs are left intact.
    return find_columns(
        fieldnames,
        [
            "*CustomLabel",
            "Custom label (SKU)",
            "Custom Label (SKU)",
            "Custom Label",
            "CustomLabel",
            "Custom SKU",
            "User SKU",
            "UserSKU",
            "Inventory Location",
            "InventoryLocation",
        ],
    )


def shipping_policy_column(fieldnames):
    exact = find_column(
        fieldnames,
        [
            "*ShippingProfileName",
            "ShippingProfileName",
            "Shipping policy",
            "Shipping Policy",
            "Shipping profile",
            "Shipping Profile",
            "Business policy",
            "Business Policy",
        ],
    )
    if exact:
        return exact
    for name in fieldnames:
        norm = name.lower()
        if "shipping" in norm and ("policy" in norm or "profile" in norm):
            return name
    return None


def promotion_policy_column(fieldnames):
    for name in fieldnames:
        norm = name.lower()
        if "promotion" in norm and ("policy" in norm or "profile" in norm or "name" in norm):
            return name
    return None


def optimized_export_price(market_price: Decimal) -> Decimal:
    # Listing Optimizer v1.2 cart-sweetener ladder:
    # <= $1.50 lists at $0.99, $1.51-$2.99 lists at $1.49,
    # $3.00-$4.99 lists at $2.99, and $5.00+ keeps market-based pricing.
    if market_price <= Decimal("1.50"):
        final_price = Decimal("0.99")
    elif market_price <= Decimal("2.99"):
        final_price = Decimal("1.49")
    elif market_price <= Decimal("4.99"):
        final_price = Decimal("2.99")
    else:
        final_price = market_price
    return max(final_price, EXPORT_FLOOR_PRICE).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def summarize_final_prices(final_prices, batch_location, output_csv_path):
    total = len(final_prices)
    avg = (sum(final_prices, Decimal("0.00")) / Decimal(total)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    min_price = min(final_prices).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    max_price = max(final_prices).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    cart_sweeteners = sum(1 for price in final_prices if price <= Decimal("0.99"))
    return {
        "batch_location": batch_location,
        "total_listings": total,
        "shipping_policy": SHIPPING_POLICY_DEFAULT,
        "promotion_policy": PROMOTION_POLICY_DEFAULT,
        "cart_sweetener_count": cart_sweeteners,
        "average_final_price": format_decimal_money(avg),
        "min_final_price": format_decimal_money(min_price),
        "max_final_price": format_decimal_money(max_price),
        "output_csv_path": str(output_csv_path),
    }


def validate_export_price_floor(final_prices):
    below_floor = [price for price in final_prices if price < EXPORT_FLOOR_PRICE]
    if below_floor:
        raise ValueError(
            f"Export price floor violation: {len(below_floor)} row(s) below "
            f"${format_decimal_money(EXPORT_FLOOR_PRICE)}."
        )


def prepare_listing_export_rows(rows, batch_location, progress_callback=None):
    if not rows:
        raise ValueError("Input CSV has no data rows.")
    fieldnames = list(rows[0].keys())
    pcol = price_column(fieldnames)
    if not pcol:
        raise ValueError("Could not find an eBay price column such as *StartPrice.")

    batch_cols = batch_location_columns(fieldnames)
    ship_col = shipping_policy_column(fieldnames)
    promo_col = promotion_policy_column(fieldnames)
    original_price_col = find_column(fieldnames, ["original_market_price", "Original Market Price", "OriginalMarketPrice"])

    out_rows = []
    review_rows = []
    final_prices = []
    price_changes = 0
    total_rows = len(rows)
    for idx, row in enumerate(rows, 1):
        if progress_callback:
            progress_callback(
                "Pricing",
                percent=35 + int((idx / max(1, total_rows)) * 30),
                current=idx,
                total=total_rows,
            )
        r = dict(row)
        original_market_price = decimal_money(r.get(pcol))
        final_price = optimized_export_price(original_market_price)
        if final_price != original_market_price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP):
            price_changes += 1
        r[pcol] = format_decimal_money(final_price)
        if original_price_col:
            r[original_price_col] = format_decimal_money(original_market_price)
        for col in batch_cols:
            r[col] = batch_location
        if ship_col:
            r[ship_col] = SHIPPING_POLICY_DEFAULT
        if promo_col:
            r[promo_col] = PROMOTION_POLICY_DEFAULT

        cart_sweetener = final_price <= Decimal("0.99")
        review = dict(r)
        review.update(
            {
                "optimizer_row": idx,
                "original_market_price": format_decimal_money(original_market_price),
                "final_export_price": format_decimal_money(final_price),
                "cart_sweetener": "TRUE" if cart_sweetener else "FALSE",
            }
        )
        out_rows.append(r)
        review_rows.append(review)
        final_prices.append(final_price)
    return out_rows, review_rows, final_prices, price_changes, batch_cols, ship_col, promo_col


def export_summary_text(summary):
    return (
        "Putnam OS Listing Optimizer v1.2\n\n"
        "User SKU = Batch Location\n"
        f"Total listings: {summary['total_listings']}\n"
        f"Batch/location: {summary['batch_location']}\n"
        f"Shipping policy: {summary['shipping_policy']}\n"
        f"Promotion policy: {summary['promotion_policy']}\n"
        f"Cart sweeteners: {summary['cart_sweetener_count']}\n"
        f"Average final export price: ${summary['average_final_price']}\n"
        f"Minimum final export price: ${summary['min_final_price']}\n"
        f"Maximum final export price: ${summary['max_final_price']}\n\n"
        "Export CSV now?"
    )


def append_export_history(summary):
    header = [
        "timestamp",
        "batch/location",
        "total_listings",
        "cart_sweetener_count",
        "average_final_price",
        "min_final_price",
        "max_final_price",
        "shipping_policy",
        "promotion_policy",
        "output_csv_path",
    ]
    EXPORT_HISTORY_LOG.parent.mkdir(parents=True, exist_ok=True)
    exists = EXPORT_HISTORY_LOG.exists()
    with EXPORT_HISTORY_LOG.open("a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        if not exists:
            writer.writeheader()
        writer.writerow(
            {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "batch/location": summary["batch_location"],
                "total_listings": summary["total_listings"],
                "cart_sweetener_count": summary["cart_sweetener_count"],
                "average_final_price": summary["average_final_price"],
                "min_final_price": summary["min_final_price"],
                "max_final_price": summary["max_final_price"],
                "shipping_policy": summary["shipping_policy"],
                "promotion_policy": summary["promotion_policy"],
                "output_csv_path": summary["output_csv_path"],
            }
        )


def format_seconds(value) -> str:
    try:
        return f"{float(value):.3f}"
    except Exception:
        return ""


def elapsed_display(seconds) -> str:
    try:
        total = max(0, int(seconds))
    except Exception:
        total = 0
    minutes, secs = divmod(total, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def append_pricing_performance_log(record):
    header = [
        "timestamp",
        "input_filename",
        "row_count",
        "total_runtime_seconds",
        "load_time_seconds",
        "pricing_time_seconds",
        "export_write_time_seconds",
        "output_folder",
        "status",
    ]
    try:
        PRICING_PERFORMANCE_LOG.parent.mkdir(parents=True, exist_ok=True)
        exists = PRICING_PERFORMANCE_LOG.exists()
        with PRICING_PERFORMANCE_LOG.open("a", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=header, extrasaction="ignore")
            if not exists:
                writer.writeheader()
            writer.writerow({name: record.get(name, "") for name in header})
    except Exception as exc:
        append_activity(f"Pricing performance log unavailable: {exc}")


def pricing_performance_record(input_path=None, row_count=0, started_at=None, output_folder="", status=""):
    elapsed = ""
    if started_at is not None:
        elapsed = format_seconds(time.perf_counter() - started_at)
    return {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "input_filename": Path(input_path).name if input_path else "",
        "row_count": row_count,
        "total_runtime_seconds": elapsed,
        "load_time_seconds": "",
        "pricing_time_seconds": "",
        "export_write_time_seconds": "",
        "output_folder": str(output_folder or ""),
        "status": status,
    }


def append_ui_bugfix_log(message):
    try:
        UI_BUGFIX_LOG.parent.mkdir(parents=True, exist_ok=True)
        with UI_BUGFIX_LOG.open("a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat(timespec='seconds')} - {message}\n")
    except Exception as exc:
        append_activity(f"UI bugfix log unavailable: {exc}")


def count_files(folder, pattern="*"):
    try:
        return len([p for p in Path(folder).glob(pattern) if p.is_file()])
    except Exception:
        return 0


def todays_jobs_count():
    today = datetime.now().strftime("%Y%m%d")
    try:
        return len([p for p in COMPLETED.iterdir() if p.is_dir() and today in p.name])
    except Exception:
        return 0


def latest_completed_job():
    try:
        jobs = [p for p in COMPLETED.iterdir() if p.is_dir()]
        if not jobs:
            return None
        return max(jobs, key=lambda p: p.stat().st_mtime)
    except Exception:
        return None


def unique_path(path: Path) -> Path:
    path = Path(path)
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    i = 1
    while True:
        candidate = parent / f"{stem}_{i:02d}{suffix}"
        if not candidate.exists():
            return candidate
        i += 1


def copy_to_folder(source: Path, folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    destination = unique_path(folder / source.name)
    if source.resolve() == destination.resolve():
        return destination
    shutil.copy2(source, destination)
    return destination


def latest_carduploader_export():
    search_dirs = [IMPORTS, INCOMING, DOWNLOADS]
    preferred_terms = ["ebay", "carduploader", "pokemon-english"]
    candidates = []
    for folder in search_dirs:
        if not folder.exists():
            continue
        try:
            for path in folder.glob("*.csv"):
                if not path.is_file():
                    continue
                lower = path.name.lower()
                preferred = any(term in lower for term in preferred_terms)
                candidates.append({
                    "path": path,
                    "preferred": preferred,
                    "mtime": path.stat().st_mtime,
                })
        except Exception:
            continue
    if not candidates:
        return None
    preferred = [c for c in candidates if c["preferred"]]
    pool = preferred or candidates
    return max(pool, key=lambda c: c["mtime"])["path"]


CARDUPLOADER_INVENTORY_COLUMNS = [
    "Title",
    "User SKU",
    "Catalog SKU",
    "TCGplayer SKU",
    "TCGplayer Product ID",
    "TCG",
    "Set",
    "Card Number",
    "Rarity",
    "Condition",
    "Variant",
    "Finish",
    "Price",
    "Qty",
    "Status",
    "Grading Company",
    "Cert Number",
    "Grade",
]


def require_carduploader_inventory_columns(rows):
    if not rows:
        raise ValueError("Inventory CSV is empty.")
    available = set(rows[0].keys())
    missing = [c for c in CARDUPLOADER_INVENTORY_COLUMNS if c not in available]
    if missing:
        raise ValueError("Missing CardUploader inventory columns: " + ", ".join(missing))


def normalize_carduploader_inventory_row(row):
    normalized = {column: str(row.get(column, "") or "").strip() for column in CARDUPLOADER_INVENTORY_COLUMNS}
    normalized["Price"] = f"{money(normalized.get('Price')):.2f}"
    try:
        qty = int(float(str(normalized.get("Qty") or "0").replace(",", "").strip()))
    except Exception:
        qty = 0
    normalized["Qty"] = str(max(0, qty))
    return normalized


def write_counter_csv(path, rows, headers):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def import_carduploader_inventory(path):
    source = Path(path)
    rows = read_csv(source)
    require_carduploader_inventory_columns(rows)
    normalized = [normalize_carduploader_inventory_row(r) for r in rows]
    DATA.mkdir(parents=True, exist_ok=True)
    write_csv(INVENTORY_SNAPSHOT, normalized, CARDUPLOADER_INVENTORY_COLUMNS)
    copied_source = copy_to_folder(source, CARDUPLOADER_INVENTORY_IMPORTS)

    stamp = nowstamp()
    job = COMPLETED / f"Inventory_Import_{stamp}"
    job.mkdir(parents=True, exist_ok=True)

    total_rows = len(normalized)
    processed_rows = sum(1 for r in normalized if int(r.get("Qty") or 0) > 0)
    listed_rows = sum(1 for r in normalized if r.get("Status", "").strip().lower() in {"listed", "active", "for sale", "live"})
    quantity_total = sum(int(r.get("Qty") or 0) for r in normalized)
    total_listed_value = sum(money(r.get("Price")) * int(r.get("Qty") or 0) for r in normalized if r.get("Status", "").strip().lower() in {"listed", "active", "for sale", "live"})

    by_tcg = {}
    by_status = {}
    by_product_id = {}
    by_catalog_sku = {}
    for r in normalized:
        tcg = r.get("TCG") or "(blank)"
        status = r.get("Status") or "(blank)"
        product_id = r.get("TCGplayer Product ID") or ""
        catalog_sku = r.get("Catalog SKU") or ""
        qty = int(r.get("Qty") or 0)
        by_tcg[tcg] = by_tcg.get(tcg, 0) + qty
        by_status[status] = by_status.get(status, 0) + qty
        if product_id:
            by_product_id.setdefault(product_id, {"key": product_id, "count": 0, "qty": 0, "titles": set()})
            by_product_id[product_id]["count"] += 1
            by_product_id[product_id]["qty"] += qty
            by_product_id[product_id]["titles"].add(r.get("Title") or "")
        if catalog_sku:
            by_catalog_sku.setdefault(catalog_sku, {"key": catalog_sku, "count": 0, "qty": 0, "titles": set()})
            by_catalog_sku[catalog_sku]["count"] += 1
            by_catalog_sku[catalog_sku]["qty"] += qty
            by_catalog_sku[catalog_sku]["titles"].add(r.get("Title") or "")

    duplicate_product_ids = [v for v in by_product_id.values() if v["count"] > 1]
    duplicate_catalog_skus = [v for v in by_catalog_sku.values() if v["count"] > 1]
    top_repeated = sorted(duplicate_product_ids, key=lambda v: (v["count"], v["qty"]), reverse=True)[:20]

    write_counter_csv(job / "counts_by_tcg.csv", [{"TCG": k, "quantity": v} for k, v in sorted(by_tcg.items())], ["TCG", "quantity"])
    write_counter_csv(job / "counts_by_status.csv", [{"Status": k, "quantity": v} for k, v in sorted(by_status.items())], ["Status", "quantity"])
    write_counter_csv(
        job / "duplicate_tcgplayer_product_ids.csv",
        [{"TCGplayer Product ID": v["key"], "rows": v["count"], "quantity": v["qty"], "titles": " | ".join(sorted(t for t in v["titles"] if t))} for v in duplicate_product_ids],
        ["TCGplayer Product ID", "rows", "quantity", "titles"],
    )
    write_counter_csv(
        job / "duplicate_catalog_skus.csv",
        [{"Catalog SKU": v["key"], "rows": v["count"], "quantity": v["qty"], "titles": " | ".join(sorted(t for t in v["titles"] if t))} for v in duplicate_catalog_skus],
        ["Catalog SKU", "rows", "quantity", "titles"],
    )
    write_counter_csv(
        job / "top_repeated_cards_by_product_id.csv",
        [{"TCGplayer Product ID": v["key"], "rows": v["count"], "quantity": v["qty"], "titles": " | ".join(sorted(t for t in v["titles"] if t))} for v in top_repeated],
        ["TCGplayer Product ID", "rows", "quantity", "titles"],
    )

    report = [
        f"Putnam OS v{APP_VERSION} - CardUploader Inventory Import",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        f"Source CSV: {source}",
        f"Copied source CSV: {copied_source}",
        f"Snapshot: {INVENTORY_SNAPSHOT}",
        "",
        f"Total rows: {total_rows}",
        f"Listed rows: {listed_rows}",
        f"Processed rows: {processed_rows}",
        f"Quantity total: {quantity_total}",
        f"Total listed value: ${total_listed_value:.2f}",
        "",
        "Counts by TCG:",
    ]
    for k, v in sorted(by_tcg.items()):
        report.append(f"  {k}: {v}")
    report.append("")
    report.append("Counts by Status:")
    for k, v in sorted(by_status.items()):
        report.append(f"  {k}: {v}")
    report.extend([
        "",
        f"Duplicate TCGplayer Product IDs: {len(duplicate_product_ids)}",
        f"Duplicate Catalog SKUs: {len(duplicate_catalog_skus)}",
        "",
        "Top repeated cards by Product ID:",
    ])
    if top_repeated:
        for v in top_repeated:
            titles = " | ".join(sorted(t for t in v["titles"] if t))
            report.append(f"  {v['key']}: rows={v['count']}, qty={v['qty']}, titles={titles}")
    else:
        report.append("  None")
    report.extend([
        "",
        "Output files:",
        f"  counts_by_tcg.csv: {job / 'counts_by_tcg.csv'}",
        f"  counts_by_status.csv: {job / 'counts_by_status.csv'}",
        f"  duplicate_tcgplayer_product_ids.csv: {job / 'duplicate_tcgplayer_product_ids.csv'}",
        f"  duplicate_catalog_skus.csv: {job / 'duplicate_catalog_skus.csv'}",
        f"  top_repeated_cards_by_product_id.csv: {job / 'top_repeated_cards_by_product_id.csv'}",
    ])
    (job / "inventory_import_report.txt").write_text("\n".join(report), encoding="utf-8")
    append_activity(f"Inventory import complete: {total_rows} rows, {quantity_total} quantity")
    return {
        "job": job,
        "snapshot": INVENTORY_SNAPSHOT,
        "copied_source": copied_source,
        "total_rows": total_rows,
        "listed_rows": listed_rows,
        "processed_rows": processed_rows,
        "quantity_total": quantity_total,
        "total_listed_value": total_listed_value,
        "duplicate_product_ids": len(duplicate_product_ids),
        "duplicate_catalog_skus": len(duplicate_catalog_skus),
    }


def detect_type(rows):
    if not rows:
        return "unknown"
    cols = set(rows[0].keys())
    if "*Title" in cols and "*StartPrice" in cols:
        return "carduploader_new"
    if any(c.lower() == "itemid" for c in cols) and any("price" in c.lower() for c in cols):
        return "active_listings"
    if "Item number" in cols and any("price" in c.lower() for c in cols):
        return "active_listings"
    return "unknown"


def infer_game_from_rows(rows):
    if not rows:
        return "pokemon"
    counts = {"one_piece": 0, "magic": 0, "pokemon": 0}
    for row in rows[:50]:
        values = " ".join(str(row.get(col, "") or "") for col in row.keys()).lower()
        if "one piece" in values or re.search(r"\bop[- ]?\d{2}[- ]?\d{3}\b", values):
            counts["one_piece"] += 1
        if "magic: the gathering" in values or "magic the gathering" in values or re.search(r"\bmtg\b", values):
            counts["magic"] += 1
        if "pokemon" in values or "pokémon" in values:
            counts["pokemon"] += 1
    game, count = max(counts.items(), key=lambda item: item[1])
    return game if count else "pokemon"


def infer_game_from_text(*values):
    text = " ".join(str(value or "") for value in values).lower()
    if "one piece" in text or re.search(r"\bop[- ]?\d{2}[- ]?\d{3}\b", text):
        return "one_piece"
    if "magic: the gathering" in text or "magic the gathering" in text or re.search(r"\bmtg\b", text):
        return "magic"
    if "pokemon" in text or "pokémon" in text:
        return "pokemon"
    return "unknown"


def parse_quantity(value):
    try:
        return str(max(0, int(float(str(value or "1").replace(",", "").strip()))))
    except Exception:
        return "1"


def normalize_inventory_source_type(fieldnames):
    names = {normalize_column_name(name) for name in fieldnames}
    if "itemnumber" in names and ("currentprice" in names or "startprice" in names):
        return "ebay_active_listings"
    if "itemid" in names and ("currentprice" in names or "startprice" in names):
        return "ebay_active_listings"
    if "title" in names and "usersku" in names and "tcg" in names:
        return "carduploader_export"
    if "title" in names and ("usersku" in names or "customlabelsku" in names or "customlabel" in names):
        return "manual_inventory_csv"
    return "unknown_csv"


def inventory_price_column(fieldnames):
    return find_column(fieldnames, ["Current price", "Start price", "Price", "BuyItNowPrice", "Auction Buy It Now price"])


def inventory_sku_column(fieldnames):
    return find_column(
        fieldnames,
        ["Custom label (SKU)", "Custom Label (SKU)", "Custom Label", "CustomLabel", "User SKU", "UserSKU", "Custom SKU", "SKU"],
    )


def normalize_inventory_rows(source_file):
    source = Path(source_file)
    rows = read_csv(source)
    if not rows:
        raise ValueError("Inventory source CSV has no rows.")
    fieldnames = list(rows[0].keys())
    source_type = normalize_inventory_source_type(fieldnames)
    item_col = find_column(fieldnames, ["Item number", "Item ID", "ItemID", "item_id"])
    title_col = find_column(fieldnames, ["Title", "Item title", "Listing title", "*Title"])
    category_col = find_column(fieldnames, ["eBay category 1 name", "Category", "Category name", "TCG"])
    quantity_col = find_column(fieldnames, ["Available quantity", "Quantity", "Qty", "*Quantity"])
    sku_col = inventory_sku_column(fieldnames)
    price_col = inventory_price_column(fieldnames)
    game_col = find_column(fieldnames, ["Game", "TCG", "Product Line"])

    if not title_col:
        raise ValueError("Inventory source must contain a title column.")

    normalized = []
    for idx, row in enumerate(rows, 1):
        title = str(row.get(title_col, "") or "").strip()
        if not title:
            continue
        item_id = str(row.get(item_col, "") or "").strip() if item_col else f"row-{idx}"
        category = str(row.get(category_col, "") or "").strip() if category_col else ""
        game_raw = str(row.get(game_col, "") or "").strip() if game_col else ""
        inferred_game = canonical_game(game_raw) if game_raw else infer_game_from_text(title, category)
        normalized.append(
            {
                "item_id": item_id,
                "title": title,
                "game": inferred_game,
                "category": category,
                "quantity": parse_quantity(row.get(quantity_col, "1") if quantity_col else "1"),
                "user_sku": str(row.get(sku_col, "") or "").strip() if sku_col else "",
                "source_file": str(source),
                "source_type": source_type,
                "price": str(row.get(price_col, "") or "").strip() if price_col else "",
                "notes": "",
            }
        )
    return normalized, source_type


def latest_ebay_active_listings_report():
    folders = [ROOT / "eBay Store Items", ROOT / "Ebay Store Items", ROOT / "Business" / "eBay_Store_Items"]
    candidates = []
    for folder in folders:
        if not folder.exists():
            continue
        for path in folder.glob("*.csv"):
            if not path.is_file():
                continue
            lower = path.name.lower()
            score = 1
            if "active" in lower or "listing" in lower:
                score += 2
            if "ebay" in lower:
                score += 1
            candidates.append((score, path.stat().st_mtime, path))
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: (item[0], item[1]), reverse=True)[0][2]


def inventory_audit_paths(audit_root=None):
    root = Path(audit_root or INVENTORY_AUDIT_DIR)
    return {
        "root": root,
        "images": root / "audit_images",
        "reports": root / "reports",
        "history": root / "inventory_audit_history.csv",
        "current": root / "current_inventory_audit.json",
        "sessions": INVENTORY_AUDIT_SESSIONS_DIR,
        "location_log": LOCATION_UPDATE_LOG,
        "event_log": INVENTORY_AUDIT_EVENT_LOG,
    }


def inventory_audit_session_id(session):
    return str(session.get("audit_session_id") or session.get("session_id") or "")


def inventory_record_identifier(record):
    return str(record.get("item_id") or record.get("card_id") or record.get("title") or "")


def inventory_audit_session_path(session):
    session_id = inventory_audit_session_id(session) or nowstamp()
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", session_id)[:80]
    return INVENTORY_AUDIT_SESSIONS_DIR / f"{safe}.json"


def save_inventory_audit_session(session, audit_root=None):
    paths = inventory_audit_paths(audit_root)
    paths["root"].mkdir(parents=True, exist_ok=True)
    paths["sessions"].mkdir(parents=True, exist_ok=True)
    session.setdefault("audit_session_id", session.get("session_id") or nowstamp())
    session.setdefault("session_id", session["audit_session_id"])
    session["updated_at"] = datetime.now().isoformat(timespec="seconds")
    stats = inventory_audit_stats(session)
    session["total_rows"] = stats["total"]
    session["confirmed_count"] = stats["confirmed"]
    session["pending_count"] = stats["pending"]
    session["needs_review_count"] = stats["needs_review"]
    session["missing_count"] = stats["missing"]
    session["location_updated_count"] = stats["location_updated"]
    paths["current"].write_text(json.dumps(session, indent=2), encoding="utf-8")
    inventory_audit_session_path(session).write_text(json.dumps(session, indent=2), encoding="utf-8")
    return paths["current"]


def load_inventory_audit_session(audit_root=None):
    path = inventory_audit_paths(audit_root)["current"]
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def load_inventory_audit_session_file(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def unfinished_inventory_audit_sessions():
    INVENTORY_AUDIT_SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    sessions = []
    seen = set()
    current = load_inventory_audit_session()
    candidates = []
    if current:
        candidates.append(current)
    for path in INVENTORY_AUDIT_SESSIONS_DIR.glob("*.json"):
        session = load_inventory_audit_session_file(path)
        if session:
            candidates.append(session)
    for session in candidates:
        session_id = inventory_audit_session_id(session)
        if not session_id or session_id in seen:
            continue
        seen.add(session_id)
        stats = inventory_audit_stats(session)
        if stats["pending"] > 0:
            session["_stats"] = stats
            sessions.append(session)
    sessions.sort(key=lambda s: str(s.get("updated_at") or s.get("created_at") or ""), reverse=True)
    return sessions


def inventory_audit_stats(session):
    records = session.get("records", [])
    total = len(records)
    counts = {
        "total": total,
        "audited": 0,
        "remaining": 0,
        "pending": 0,
        "confirmed": 0,
        "already_correct": 0,
        "missing": 0,
        "needs_review": 0,
        "location_updated": 0,
        "skipped": 0,
        "completion_pct": "0.0",
    }
    for record in records:
        status = str(record.get("audit_status", "") or "pending")
        if status and status != "pending":
            counts["audited"] += 1
        if status == "confirmed":
            counts["confirmed"] += 1
        elif status == "already_correct":
            counts["already_correct"] += 1
        elif status == "missing":
            counts["missing"] += 1
        elif status == "needs_review":
            counts["needs_review"] += 1
        elif status == "location_updated":
            counts["location_updated"] += 1
        elif status == "skipped":
            counts["skipped"] += 1
        else:
            counts["pending"] += 1
    counts["remaining"] = max(0, total - counts["audited"])
    counts["completion_pct"] = f"{((counts['audited'] / total) * 100.0) if total else 0.0:.1f}"
    return counts


def batch_size_warning(total):
    if total < 50:
        return f"Warning: batch has {total} cards. Target is 100; healthy range is 75-125."
    if total > 125:
        return f"Warning: batch has {total} cards. Target is 100; healthy range is 75-125."
    return ""


def create_inventory_audit_session(source_file, game, batch_location, capture_enabled=False, audit_root=None):
    batch_location = validate_location(batch_location)
    records, source_type = normalize_inventory_rows(source_file)
    selected_game = canonical_game(game)
    if selected_game and selected_game != "all":
        records = [record for record in records if canonical_game(record.get("game")) == selected_game]
    for record in records:
        record.update(
            {
                "confirmed_location": "",
                "audit_status": "pending",
                "audit_timestamp": "",
                "capture_image_path": "",
                "notes": record.get("notes", ""),
            }
        )
    session_id = nowstamp()
    session = {
        "session_id": session_id,
        "audit_session_id": session_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "updated_at": "",
        "source_file": str(Path(source_file)),
        "source_scope": f"{display_location_game(selected_game)} inventory audit",
        "source_type": source_type,
        "game": selected_game,
        "batch_location": batch_location,
        "last_location": batch_location,
        "capture_enabled": bool(capture_enabled),
        "current_index": 0,
        "records": records,
        "reports_folder": str(inventory_audit_paths(audit_root)["reports"]),
        "rule": "User SKU = Batch Location",
        "notes": "",
    }
    save_inventory_audit_session(session, audit_root)
    return session


def latest_capture_image():
    base = INCOMING / "Capture_Sessions"
    if not base.exists():
        return None
    images = []
    for ext in ("*.jpg", "*.jpeg"):
        images.extend(base.glob(f"**/{ext}"))
    images = [path for path in images if path.is_file()]
    if not images:
        return None
    return max(images, key=lambda path: path.stat().st_mtime)


def attach_inventory_audit_image(record, audit_root=None, capture_source=None):
    source = Path(capture_source) if capture_source else latest_capture_image()
    if not source or not source.exists():
        return ""
    paths = inventory_audit_paths(audit_root)
    paths["images"].mkdir(parents=True, exist_ok=True)
    safe_item = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(record.get("item_id") or "row"))[:80]
    destination = unique_path(paths["images"] / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{safe_item}.jpg")
    shutil.copy2(source, destination)
    return str(destination)


def append_inventory_audit_history(session, record, audit_root=None):
    paths = inventory_audit_paths(audit_root)
    paths["root"].mkdir(parents=True, exist_ok=True)
    header = [
        "item_id",
        "title",
        "game",
        "audit_timestamp",
        "confirmed_location",
        "audit_status",
        "notes",
        "capture_image_path",
        "source_file",
    ]
    exists = paths["history"].exists()
    with paths["history"].open("a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        if not exists:
            writer.writeheader()
        writer.writerow({key: record.get(key, "") for key in header} | {"source_file": session.get("source_file", "")})


def append_location_update_log(session, record, previous_location, new_location):
    LOCATION_UPDATE_LOG.parent.mkdir(parents=True, exist_ok=True)
    header = [
        "timestamp",
        "audit_session_id",
        "card/listing identifier",
        "previous location",
        "new location",
        "source",
    ]
    exists = LOCATION_UPDATE_LOG.exists()
    with LOCATION_UPDATE_LOG.open("a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        if not exists:
            writer.writeheader()
        writer.writerow(
            {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "audit_session_id": inventory_audit_session_id(session),
                "card/listing identifier": inventory_record_identifier(record),
                "previous location": previous_location,
                "new location": new_location,
                "source": "inventory_audit",
            }
        )


def append_inventory_audit_event_log(session, record, action, previous_status, new_status, note=""):
    INVENTORY_AUDIT_EVENT_LOG.parent.mkdir(parents=True, exist_ok=True)
    header = [
        "timestamp",
        "audit_session_id",
        "card/listing identifier",
        "action",
        "previous_status",
        "new_status",
        "note if available",
    ]
    exists = INVENTORY_AUDIT_EVENT_LOG.exists()
    with INVENTORY_AUDIT_EVENT_LOG.open("a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        if not exists:
            writer.writeheader()
        writer.writerow(
            {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "audit_session_id": inventory_audit_session_id(session),
                "card/listing identifier": inventory_record_identifier(record),
                "action": action,
                "previous_status": previous_status,
                "new_status": new_status,
                "note if available": note,
            }
        )


def apply_inventory_audit_action(session, action, notes="", audit_root=None, capture_source=None):
    records = session.get("records", [])
    if not records:
        return session
    idx = max(0, min(int(session.get("current_index", 0)), len(records) - 1))
    record = records[idx]
    timestamp = datetime.now().isoformat(timespec="seconds")
    previous_status = str(record.get("audit_status", "") or "pending")
    if action == "confirm":
        record["audit_status"] = "confirmed"
        record["confirmed_location"] = record.get("confirmed_location") or session.get("last_location") or session.get("batch_location", "")
    elif action == "already_correct":
        record["audit_status"] = "already_correct"
        record["confirmed_location"] = record.get("user_sku", "") or session.get("batch_location", "")
    elif action == "missing":
        record["audit_status"] = "missing"
        record["confirmed_location"] = ""
    elif action == "needs_review":
        record["audit_status"] = "needs_review"
        record["confirmed_location"] = ""
    elif action == "skip":
        record["audit_status"] = "skipped"
        record["confirmed_location"] = ""
    else:
        raise ValueError(f"Unknown audit action: {action}")
    record["audit_timestamp"] = timestamp
    record["notes"] = notes
    if session.get("capture_enabled") and action in {"confirm", "already_correct"}:
        image_path = attach_inventory_audit_image(record, audit_root, capture_source)
        if image_path:
            record["capture_image_path"] = image_path
    append_inventory_audit_history(session, record, audit_root)
    append_inventory_audit_event_log(session, record, action, previous_status, record.get("audit_status", ""), notes)
    session["current_index"] = min(idx + 1, max(0, len(records) - 1))
    save_inventory_audit_session(session, audit_root)
    return session


def update_inventory_audit_location(session, new_location, notes="", audit_root=None):
    records = session.get("records", [])
    if not records:
        return session
    new_location = validate_location(new_location)
    idx = max(0, min(int(session.get("current_index", 0)), len(records) - 1))
    record = records[idx]
    previous_status = str(record.get("audit_status", "") or "pending")
    previous_location = str(record.get("confirmed_location") or record.get("user_sku") or "")
    timestamp = datetime.now().isoformat(timespec="seconds")
    record["confirmed_location"] = new_location
    record["audit_status"] = "location_updated"
    record["audit_timestamp"] = timestamp
    record["notes"] = notes
    session["last_location"] = new_location
    append_location_update_log(session, record, previous_location, new_location)
    append_inventory_audit_event_log(session, record, "location_updated", previous_status, "location_updated", notes)
    append_inventory_audit_history(session, record, audit_root)
    save_inventory_audit_session(session, audit_root)
    return session


def save_inventory_audit_progress(session, notes="", audit_root=None):
    records = session.get("records", [])
    if records:
        idx = max(0, min(int(session.get("current_index", 0)), len(records) - 1))
        record = records[idx]
        previous_status = str(record.get("audit_status", "") or "pending")
        record["notes"] = notes
        append_inventory_audit_event_log(session, record, "save_progress", previous_status, previous_status, notes)
    session["notes"] = notes
    save_inventory_audit_session(session, audit_root)
    return session


def move_inventory_audit_index(session, delta, audit_root=None):
    records = session.get("records", [])
    if not records:
        session["current_index"] = 0
    else:
        session["current_index"] = max(0, min(int(session.get("current_index", 0)) + delta, len(records) - 1))
    save_inventory_audit_session(session, audit_root)
    return session


def inventory_audit_report_rows(session):
    rows = []
    for record in session.get("records", []):
        rows.append(
            {
                "item_id": record.get("item_id", ""),
                "title": record.get("title", ""),
                "game": record.get("game", ""),
                "category": record.get("category", ""),
                "quantity": record.get("quantity", ""),
                "price": record.get("price", ""),
                "current_user_sku": record.get("user_sku", ""),
                "confirmed_location": record.get("confirmed_location", ""),
                "audit_status": record.get("audit_status", ""),
                "notes": record.get("notes", ""),
                "capture_image_path": record.get("capture_image_path", ""),
                "source_file": session.get("source_file", ""),
                "source_type": session.get("source_type", ""),
            }
        )
    return rows


def generate_inventory_audit_reports(session, audit_root=None):
    paths = inventory_audit_paths(audit_root)
    paths["reports"].mkdir(parents=True, exist_ok=True)
    stats = inventory_audit_stats(session)
    rows = inventory_audit_report_rows(session)
    audit_csv = paths["reports"] / "inventory_location_audit.csv"
    summary_txt = paths["reports"] / "inventory_location_summary.txt"
    bulk_csv = paths["reports"] / "ebay_bulk_revise_location_confirmed.csv"

    write_csv(audit_csv, rows, [
        "item_id", "title", "game", "category", "quantity", "price", "current_user_sku",
        "confirmed_location", "audit_status", "notes", "capture_image_path", "source_file", "source_type",
    ])
    confirmed = [row for row in rows if row.get("audit_status") == "confirmed" and row.get("item_id")]
    write_csv(
        bulk_csv,
        [{"Action": "Revise", "ItemID": row["item_id"], "CustomLabel": row["confirmed_location"]} for row in confirmed],
        ["Action", "ItemID", "CustomLabel"],
    )
    warning = batch_size_warning(stats["total"])
    summary = [
        f"Putnam OS Inventory Audit Mode v2",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        f"Session ID: {session.get('session_id', '')}",
        f"Source file: {session.get('source_file', '')}",
        f"Source type: {session.get('source_type', '')}",
        f"Game: {display_location_game(session.get('game', 'unknown'))}",
        f"Batch Location: {session.get('batch_location', '')}",
        "Rule: User SKU = Batch Location",
        "",
        f"Cards audited: {stats['audited']}",
        f"Cards remaining: {stats['remaining']}",
        f"Pending: {stats['pending']}",
        f"Confirmed: {stats['confirmed']}",
        f"Already correct: {stats['already_correct']}",
        f"Missing: {stats['missing']}",
        f"Needs review: {stats['needs_review']}",
        f"Location updated: {stats['location_updated']}",
        f"Skipped: {stats['skipped']}",
        f"Completion: {stats['completion_pct']}%",
        f"Bulk revise confirmed rows: {len(confirmed)}",
        f"Session save path: {inventory_audit_session_path(session)}",
    ]
    if warning:
        summary.extend(["", warning])
    summary.extend(
        [
            "",
            "Safety:",
            "- eBay was not modified.",
            "- Only confirmed rows are included in ebay_bulk_revise_location_confirmed.csv.",
            "- Missing, needs-review, skipped, and already-correct rows are excluded from the bulk revise CSV.",
            "- Capture images are internal only and should never be uploaded to eBay.",
        ]
    )
    summary_txt.write_text("\n".join(summary) + "\n", encoding="utf-8")
    return {"audit_csv": audit_csv, "summary_txt": summary_txt, "bulk_csv": bulk_csv, "stats": stats}


def card_fields(row):
    title = row.get("*Title") or row.get("Title") or row.get("title") or ""
    name = row.get("*C:Card Name") or row.get("Card Name") or ""
    setname = row.get("*C:Set") or row.get("Set") or ""
    number = row.get("*C:Card Number") or row.get("Card Number") or ""
    price = money(row.get("*StartPrice") or row.get("StartPrice") or row.get("Price") or row.get("BuyItNowPrice"))
    return title, name, setname, number, price


def build_query(row):
    title, name, setname, number, price = card_fields(row)
    parts = []
    if name:
        parts.append(name)
    if setname:
        parts.append(setname)
    if number:
        parts.append(number)
    if not parts:
        parts = [title]
    return " ".join(parts).strip()


def cache_file(q):
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", q)[:120]
    return CACHE / (safe + ".json")


def fetch_carduploader_sales(q):
    cf = cache_file(q)
    if cf.exists():
        try:
            data = json.loads(cf.read_text(encoding="utf-8-sig"))
            if data.get("cached_at"):
                return data
        except Exception:
            pass
    url = "https://carduploader.com/backend/sales/search?q=" + urllib.parse.quote(q)
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "PutnamOS/3.3 market intelligence", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read().decode("utf-8"))
    data["cached_at"] = datetime.now().isoformat()
    cf.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data


def normalize_match_text(value):
    text = str(value or "").lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def match_tokens(value):
    return [token for token in normalize_match_text(value).split() if token]


def token_match_score(expected, candidate):
    expected_tokens = match_tokens(expected)
    candidate_tokens = set(match_tokens(candidate))
    if not expected_tokens:
        return 100, [], []
    matched = [token for token in expected_tokens if token in candidate_tokens]
    missing = [token for token in expected_tokens if token not in candidate_tokens]
    score = round((len(matched) / len(expected_tokens)) * 100)
    return score, matched, missing


def normalized_card_number(value):
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def find_card_number(title, number):
    expected = normalized_card_number(number)
    if not expected:
        return "", True
    normalized_title = normalized_card_number(title)
    candidates = {expected}
    if expected.startswith("0"):
        candidates.add(expected.lstrip("0"))
    for candidate in candidates:
        if candidate and candidate in normalized_title:
            return number, True
    found = re.findall(r"[a-z]{1,5}\s*-?\s*\d{1,5}|\d{1,5}\s*/\s*\d{1,5}", str(title or "").lower())
    return "; ".join(dict.fromkeys(s.strip() for s in found)), False


def excluded_terms_found(title):
    normalized_title = f" {normalize_match_text(title)} "
    found = []
    for term in EXCLUDE_TERMS:
        normalized_term = normalize_match_text(term)
        if normalized_term and f" {normalized_term} " in normalized_title:
            found.append(normalized_term)
    return sorted(set(found))


def build_rejection_details(card_name, matched, missing, score, reason, card_number, found_number, setname, set_score, excluded):
    details = []
    if card_name:
        details.append(
            f'Expected "{card_name}"; matched token(s): {", ".join(matched) or "none"}; '
            f'missing token(s): {", ".join(missing) or "none"}; name score {score}'
        )
        if score < NAME_MATCH_SCORE_THRESHOLD:
            details[-1] += f" below threshold {NAME_MATCH_SCORE_THRESHOLD}."
        else:
            details[-1] += f" meets threshold {NAME_MATCH_SCORE_THRESHOLD}."
    if card_number:
        details.append(f'Expected card number "{card_number}"; found "{found_number or "none"}".')
    if setname:
        details.append(f'Set "{setname}" title-token score: {set_score}.')
    if excluded:
        details.append(f"Excluded term(s) found: {', '.join(excluded)}.")
    if reason and reason != "accepted":
        details.append(f"Final rejection reason: {reason}.")
    return " ".join(details)


def comp_match_diagnostics(title, name, setname, number):
    normalized_name = normalize_match_text(name)
    normalized_title = normalize_match_text(title)
    name_score, matched, missing = token_match_score(name, title)
    set_score, _set_matched, _set_missing = token_match_score(setname, title)
    found_number, number_match = find_card_number(title, number)
    excluded = excluded_terms_found(title)
    excluded_set = set(excluded)
    final_reason = "accepted"
    if excluded_set.intersection(GRADED_EXCLUDE_TERMS):
        final_reason = "excluded graded term"
    elif excluded_set.intersection(NON_SINGLE_EXCLUDE_TERMS):
        final_reason = "excluded lot/pack/playset/booster/deck/sealed term"
    elif any(term in excluded_set for term in ("graded", "slab", "ace")):
        final_reason = "excluded graded term"
    elif excluded:
        final_reason = f"excluded term: {excluded[0]}"
    elif name and name_score < NAME_MATCH_SCORE_THRESHOLD:
        final_reason = "card name mismatch"
    elif number and not number_match:
        final_reason = "card number mismatch"
    elif setname:
        words = [w for w in re.split(r"\W+", str(setname).lower()) if len(w) > 3]
        if words and not any(w in str(title or "").lower() for w in words):
            final_reason = "set not evident in title"
    details = build_rejection_details(
        name, matched, missing, name_score, final_reason, number, found_number, setname, set_score, excluded
    )
    return {
        "card_name_expected": name,
        "candidate_title": title,
        "normalized_card_name": normalized_name,
        "normalized_candidate_title": normalized_title,
        "name_match_score": name_score,
        "matched_name_tokens": "; ".join(matched),
        "missing_name_tokens": "; ".join(missing),
        "card_number_expected": number,
        "card_number_found": found_number,
        "card_number_match": "yes" if number_match else "no",
        "set_expected": setname,
        "set_match_score": set_score,
        "excluded_terms_found": "; ".join(excluded),
        "final_rejection_reason": final_reason,
        "rejection_details": details,
    }


def comparable_reason(title, name, setname, number):
    diagnostics = comp_match_diagnostics(title, name, setname, number)
    reason = diagnostics["final_rejection_reason"]
    return reason == "accepted", reason, diagnostics


def analytics_bucket(reason):
    if reason == "card name mismatch":
        return "Rejected: card name mismatch"
    if reason == "card number mismatch":
        return "Rejected: card number mismatch"
    if reason == "excluded graded term":
        return "Rejected: excluded graded term"
    if reason == "excluded lot/pack/playset/booster/deck/sealed term":
        return "Rejected: excluded lot/pack/playset/booster/deck/sealed term"
    return "Rejected: other reason"


def write_comp_search_analytics_summary(path, analytics):
    total_candidates = sum(int(row.get("Total Candidates Returned") or 0) for row in analytics)
    total_accepted = sum(int(row.get("Accepted Candidates") or 0) for row in analytics)
    total_rejected = sum(int(row.get("Rejected Candidates") or 0) for row in analytics)
    reason_totals = {
        field: sum(int(row.get(field) or 0) for row in analytics)
        for field in COMP_ANALYTICS_FIELDS
        if field.startswith("Rejected:")
    }
    top_reasons = sorted(reason_totals.items(), key=lambda item: item[1], reverse=True)
    lines = [
        COMP_ENGINE_VERSION,
        COMP_ENGINE_SUBTITLE,
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        "",
        f"Searches: {len(analytics)}",
        f"Total candidates reviewed: {total_candidates}",
        f"Total accepted: {total_accepted}",
        f"Total rejected: {total_rejected}",
        "",
        "Top rejection reasons:",
    ]
    for reason, count in top_reasons:
        if count:
            lines.append(f"- {reason}: {count}")
    if not any(count for _reason, count in top_reasons):
        lines.append("- None")
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def market_analyze(rows):
    print(COMP_ENGINE_VERSION)
    print(COMP_ENGINE_SUBTITLE)
    reports = []
    rejected = []
    analytics = []
    for i, row in enumerate(rows, 1):
        title, name, setname, number, current = card_fields(row)
        q = build_query(row)
        rec = {
            "row": i, "title": title, "card_name": name, "set": setname, "number": number,
            "current_price": current, "query": q, "status": "NO_DATA", "accepted_count": 0,
            "rejected_count": 0, "last_sale": "", "last3_avg": "", "median": "", "confidence": 0,
            "reason": "",
        }
        try:
            data = fetch_carduploader_sales(q)
            results = data.get("results", [])
            accepted = []
            rejection_counts = {
                "Rejected: card name mismatch": 0,
                "Rejected: card number mismatch": 0,
                "Rejected: excluded graded term": 0,
                "Rejected: excluded lot/pack/playset/booster/deck/sealed term": 0,
                "Rejected: other reason": 0,
            }
            for r in results:
                ok, reason, diagnostics = comparable_reason(r.get("title", ""), name, setname, number)
                if ok:
                    accepted.append(r)
                else:
                    rejection_counts[analytics_bucket(reason)] += 1
                    rr = dict(rec)
                    rr.update({
                        "candidate_title": r.get("title", ""),
                        "candidate_price": r.get("price", ""),
                        "reject_reason": reason,
                    })
                    rr.update(diagnostics)
                    rejected.append(rr)
            prices = [money(r.get("price")) for r in accepted if money(r.get("price")) > 0]
            rec["accepted_count"] = len(accepted)
            rec["rejected_count"] = max(0, len(results) - len(accepted))
            analytics_row = {
                "Card Name": name,
                "Set Name": setname,
                "Card Number": number,
                "Search Query Used": q,
                "Total Candidates Returned": len(results),
                "Accepted Candidates": len(accepted),
                "Rejected Candidates": rec["rejected_count"],
            }
            analytics_row.update(rejection_counts)
            analytics.append(analytics_row)
            if prices:
                last3 = prices[:3]
                rec["last_sale"] = prices[0]
                rec["last3_avg"] = round(sum(last3) / len(last3), 2)
                rec["median"] = round(statistics.median(prices[:min(20, len(prices))]), 2)
                # Conservative confidence for review only.
                count_score = min(40, len(prices) * 4)
                spread_score = 20
                if len(last3) == 3:
                    avg = rec["last3_avg"]
                    spread = max(last3) - min(last3)
                    spread_score = max(0, 25 - int((spread / max(avg, 0.01)) * 25))
                query_score = 20 if (name and number and setname) else 10
                rec["confidence"] = min(100, count_score + spread_score + query_score)
                if current <= FLOOR and len(prices) >= 3 and rec["last3_avg"] >= 2 * FLOOR and rec["confidence"] >= 70:
                    rec["status"] = "MARKET_OPPORTUNITY_REVIEW"
                    rec["reason"] = f"Last 3 avg ${rec['last3_avg']:.2f} is >= 2x floor after validation."
                else:
                    rec["status"] = "NO_CHANGE"
                    rec["reason"] = "Market data did not exceed opportunity threshold."
            else:
                rec["reason"] = "No accepted comparables after validation."
        except Exception as e:
            rec["status"] = "ERROR"
            rec["reason"] = str(e)[:200]
            analytics.append({
                "Card Name": name,
                "Set Name": setname,
                "Card Number": number,
                "Search Query Used": q,
                "Total Candidates Returned": 0,
                "Accepted Candidates": 0,
                "Rejected Candidates": 0,
                "Rejected: card name mismatch": 0,
                "Rejected: card number mismatch": 0,
                "Rejected: excluded graded term": 0,
                "Rejected: excluded lot/pack/playset/booster/deck/sealed term": 0,
                "Rejected: other reason": 0,
            })
        reports.append(rec)
    return reports, rejected, analytics


def audit_new_listing(
    path,
    use_market=True,
    batch_location=None,
    game=None,
    confirm_callback=None,
    dry_run=False,
    progress_callback=None,
):
    run_started = time.perf_counter()
    load_time = 0.0
    pricing_time = 0.0
    export_write_time = 0.0
    source_path = Path(path)
    if progress_callback:
        progress_callback("Loading", percent=10)
    load_started = time.perf_counter()
    rows = read_csv(path)
    load_time = time.perf_counter() - load_started
    typ = detect_type(rows)
    if progress_callback:
        progress_callback("Validating", percent=20, current=0, total=len(rows))
    if typ != "carduploader_new":
        raise ValueError("This does not appear to be a CardUploader/eBay new-listing CSV.")
    batch_location = str(batch_location or "").strip()
    if not batch_location:
        raise ExportCancelled("Export canceled because batch/location was blank.")
    batch_location = validate_location(batch_location)
    if confirm_callback is None:
        confirm_callback = lambda _phase, message: input(message + " [Y/N]: ").strip().lower() == "y"

    shipping_message = (
        "Shipping policy confirmation\n\n"
        f"Default shipping policy: {SHIPPING_POLICY_DEFAULT}\n"
        f"Promotion policy: {PROMOTION_POLICY_DEFAULT}\n\n"
        "Continue with these settings?"
    )
    print("Putnam OS Listing Optimizer v1.2")
    print(f"Batch/location: {batch_location}")
    print(f"Shipping policy: {SHIPPING_POLICY_DEFAULT}")
    print(f"Promotion policy: {PROMOTION_POLICY_DEFAULT}")
    if progress_callback:
        progress_callback("Confirming", percent=30, current=len(rows), total=len(rows))
    if not confirm_callback("shipping", shipping_message):
        raise ExportCancelled("Export canceled during shipping policy confirmation.")

    stamp = nowstamp()
    job = COMPLETED / f"Pricing_Analysis_{stamp}"
    ebay_ready = job / "ebay_upload_ready.csv"
    pricing_started = time.perf_counter()
    out_rows, review_rows, final_prices, changes, batch_cols, ship_col, promo_col = prepare_listing_export_rows(
        rows,
        batch_location,
        progress_callback=progress_callback,
    )
    pricing_time = time.perf_counter() - pricing_started
    validate_export_price_floor(final_prices)
    if progress_callback:
        progress_callback("Pricing", percent=65, current=len(rows), total=len(rows))
    export_summary = summarize_final_prices(final_prices, batch_location, ebay_ready)
    print("Pre-export summary")
    print(f"Total listings: {export_summary['total_listings']}")
    print(f"Cart sweeteners: {export_summary['cart_sweetener_count']}")
    print(f"Average final export price: ${export_summary['average_final_price']}")
    print(f"Minimum final export price: ${export_summary['min_final_price']}")
    print(f"Maximum final export price: ${export_summary['max_final_price']}")
    if progress_callback:
        progress_callback("Confirming", percent=75, current=len(rows), total=len(rows))
    if not confirm_callback("summary", export_summary_text(export_summary)):
        raise ExportCancelled("Export canceled during final summary confirmation.")

    if dry_run:
        append_activity(f"Listing Optimizer dry run canceled before writing CSV: {len(rows)} rows")
        return job, len(rows), changes, 0, export_summary

    if progress_callback:
        progress_callback("Writing output", percent=85, current=len(rows), total=len(rows))
    export_started = time.perf_counter()
    (job / "source_backup").mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, job / "source_backup" / Path(path).name)
    ebay_ready = job / "ebay_upload_ready.csv"
    write_csv(ebay_ready, out_rows, list(rows[0].keys()))
    write_csv(job / "review.csv", out_rows, list(rows[0].keys()))
    review_fields = list(rows[0].keys())
    for extra in ["optimizer_row", "original_market_price", "final_export_price", "cart_sweetener"]:
        if extra not in review_fields:
            review_fields.append(extra)
    write_csv(
        job / "optimization_review.csv",
        review_rows,
        review_fields,
    )
    export_copy = copy_to_folder(ebay_ready, EXPORTS)
    export_summary["output_csv_path"] = str(export_copy)
    if progress_callback:
        progress_callback("Writing output", percent=92, current=len(rows), total=len(rows))
    append_export_history(export_summary)
    location_registry = record_location(
        batch_location,
        game or infer_game_from_rows(rows),
        "ebay_export",
        root=ROOT,
        status="exported",
        note="Listing Optimizer export wrote User SKU / Custom Label as batch location.",
        total_listings=len(rows),
    )
    processed_source = copy_to_folder(Path(path), IMPORTS / "Processed")
    market_reports = []
    rejected = []
    comp_analytics = []
    if use_market:
        if progress_callback:
            progress_callback("Writing output", percent=95, current=len(rows), total=len(rows))
        market_reports, rejected, comp_analytics = market_analyze(out_rows)
        write_csv(job / "market_report.csv", market_reports)
        if rejected:
            write_csv(job / "rejected_comps.csv", rejected)
        if comp_analytics:
            write_csv(job / "comp_search_analytics.csv", comp_analytics, COMP_ANALYTICS_FIELDS)
            write_comp_search_analytics_summary(job / "comp_search_analytics_summary.txt", comp_analytics)
        comp_total_accepted = sum(int(row.get("Accepted Candidates") or 0) for row in comp_analytics)
        comp_total_rejected = sum(int(row.get("Rejected Candidates") or 0) for row in comp_analytics)
        export_summary["comp_total_accepted"] = comp_total_accepted
        export_summary["comp_total_rejected"] = comp_total_rejected
        export_summary["rejected_comps_path"] = str(job / "rejected_comps.csv")
        export_summary["comp_search_analytics_path"] = str(job / "comp_search_analytics.csv")
        export_summary["comp_search_analytics_summary_path"] = str(job / "comp_search_analytics_summary.txt")
        if progress_callback:
            progress_callback(
                "Complete",
                percent=98,
                current=len(rows),
                total=len(rows),
            )
    else:
        export_summary["comp_total_accepted"] = 0
        export_summary["comp_total_rejected"] = 0
        export_summary["rejected_comps_path"] = str(job / "rejected_comps.csv")
        export_summary["comp_search_analytics_path"] = str(job / "comp_search_analytics.csv")
        export_summary["comp_search_analytics_summary_path"] = str(job / "comp_search_analytics_summary.txt")
    opp = sum(1 for r in market_reports if r.get("status") == "MARKET_OPPORTUNITY_REVIEW")
    summary_path = job / "summary.txt"
    summary_path.write_text(
        f"Putnam OS v{APP_VERSION} - Listing Optimizer v{LISTING_OPTIMIZER_VERSION}\n"
        f"Rows: {len(rows)}\n"
        f"Optimized price changes: {changes}\n"
        f"Batch/location: {batch_location}\n"
        f"Batch/location columns updated: {', '.join(batch_cols) if batch_cols else 'none present'}\n"
        f"Shipping policy: {SHIPPING_POLICY_DEFAULT}\n"
        f"Promotion policy: {PROMOTION_POLICY_DEFAULT}\n"
        f"Shipping policy column: {ship_col or 'none present'}\n"
        f"Promotion policy column: {promo_col or 'none present'}\n"
        f"Cart sweeteners: {export_summary['cart_sweetener_count']}\n"
        f"Average final export price: ${export_summary['average_final_price']}\n"
        f"Minimum final export price: ${export_summary['min_final_price']}\n"
        f"Maximum final export price: ${export_summary['max_final_price']}\n"
        f"Market opportunities: {opp}\n"
        f"Output: {job}\n"
        f"Export copy: {export_copy}\n"
        f"Export history log: {EXPORT_HISTORY_LOG}\n"
        f"Location registry: {location_registry}\n"
        f"Processed source copy: {processed_source}\n",
        encoding="utf-8",
    )
    export_write_time = time.perf_counter() - export_started
    append_activity(
        f"Listing export complete: {len(rows)} rows, {changes} optimized prices, "
        f"{export_summary['cart_sweetener_count']} cart sweeteners, export copied to Exports"
    )
    attach_job_to_session(job, rows=len(rows), opportunities=opp)
    total_runtime = time.perf_counter() - run_started
    export_summary["total_runtime_seconds"] = total_runtime
    export_summary["output_folder"] = str(job)
    append_pricing_performance_log(
        {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "input_filename": source_path.name,
            "row_count": len(rows),
            "total_runtime_seconds": format_seconds(total_runtime),
            "load_time_seconds": format_seconds(load_time),
            "pricing_time_seconds": format_seconds(pricing_time),
            "export_write_time_seconds": format_seconds(export_write_time),
            "output_folder": str(job),
            "status": "completed",
        }
    )
    if progress_callback:
        progress_callback("Complete", percent=100, current=len(rows), total=len(rows))
    return job, len(rows), changes, opp, export_summary


def current_session_path():
    return DATA / "current_session.json"


def load_current_session():
    p = current_session_path()
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8-sig"))
        if data.get("active"):
            return data
    except Exception:
        return None
    return None


def save_current_session(data):
    DATA.mkdir(parents=True, exist_ok=True)
    current_session_path().write_text(json.dumps(data, indent=2), encoding="utf-8")


def create_work_session(
    goal="List new inventory",
    planned_cards="100",
    capture_method="iPhone camera",
    game="pokemon",
    batch_location="ETB-01-A",
):
    batch_location = validate_location(batch_location)
    stamp = nowstamp()
    folder = SESSIONS / f"Work_Session_{stamp}"
    folder.mkdir(parents=True, exist_ok=True)
    data = {
        "active": True,
        "session_id": stamp,
        "folder": str(folder),
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "ended_at": "",
        "goal": goal,
        "planned_cards": planned_cards,
        "game": game,
        "batch_location": batch_location,
        "completed_cards": "",
        "capture_method": capture_method,
        "recording_path": "",
        "pricing_jobs": [],
        "notes": [],
    }
    (folder / "session.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    (folder / "session_notes.md").write_text(
        f"# Putnam Work Session {stamp}\n\n"
        f"Started: {data['started_at']}\n\n"
        f"Goal: {goal}\n\nCards planned: {planned_cards}\n\n"
        f"Game: {display_location_game(game)}\n\nBatch Location: {batch_location}\n\n"
        f"Capture method: {capture_method}\n\n"
        "## Notes\n\n- \n\n## Bottlenecks\n\n- \n\n## Content moments\n\n- \n",
        encoding="utf-8",
    )
    save_current_session(data)
    registry = record_location(
        batch_location,
        game,
        "intake_batch_creation",
        root=ROOT,
        status="planned",
        note="Batch location assigned during Putnam OS work-session intake.",
    )
    append_activity(f"Work session started: {folder.name}, batch location {batch_location}")
    return folder


def end_work_session(completed_cards="", recording_path="", notes=""):
    data = load_current_session()
    if not data:
        return None
    data["active"] = False
    data["ended_at"] = datetime.now().isoformat(timespec="seconds")
    if completed_cards:
        data["completed_cards"] = completed_cards
    if recording_path:
        data["recording_path"] = recording_path
    if notes:
        data.setdefault("notes", []).append(notes)
    folder = Path(data["folder"])
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "session.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    try:
        current_session_path().unlink()
    except Exception:
        pass
    append_activity(f"Work session ended: {folder.name}")
    return folder


def attach_job_to_session(job_path, rows=0, opportunities=0):
    data = load_current_session()
    if not data:
        return
    data.setdefault("pricing_jobs", []).append({
        "job_path": str(job_path),
        "rows": rows,
        "opportunities": opportunities,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    })
    save_current_session(data)
    folder = Path(data["folder"])
    if folder.exists():
        (folder / "session.json").write_text(json.dumps(data, indent=2), encoding="utf-8")


def latest_sessions(limit=6):
    try:
        folders = [p for p in SESSIONS.iterdir() if p.is_dir()]
        folders = sorted(folders, key=lambda p: p.stat().st_mtime, reverse=True)
        return folders[:limit]
    except Exception:
        return []


BaseTk = TkinterDnD.Tk if DND_AVAILABLE else tk.Tk


class PutnamOS(BaseTk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("1240x800")
        self.minsize(1100, 720)
        self.configure(bg=BRAND["bg"])
        self.loaded = None
        self.rows = []
        self.detected = ""
        self.nav_buttons = {}
        self.status = tk.StringVar(value="Ready.")
        self.pricing_running = False
        self.pricing_started_at = None
        self.pricing_action_button = None
        self.current_pricing_job = None
        self.current_pricing_reports = {}
        self.capture_service = CaptureStudioService()
        self.capture_session = None
        self.current_pick_list_result = None
        self.build_styles()
        self.build_ui()

    def build_styles(self):
        s = ttk.Style(self)
        try:
            s.theme_use("clam")
        except Exception:
            pass
        s.configure("Main.TFrame", background=BRAND["bg"])
        s.configure("Primary.TButton", font=("Segoe UI", 12, "bold"), padding=12)
        s.configure("Secondary.TButton", font=("Segoe UI", 10), padding=8)
        s.map("Primary.TButton", background=[("active", BRAND["blue2"])])
        s.map("Secondary.TButton", background=[("active", BRAND["panel2"])])

    def build_ui(self):
        side = tk.Frame(self, bg=BRAND["sidebar"], width=235)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)

        tk.Label(side, text="PUTNAM", bg=BRAND["sidebar"], fg=BRAND["text"],
                 font=("Segoe UI", 24, "bold")).pack(pady=(28, 0))
        tk.Label(side, text=f"OS v{APP_VERSION}", bg=BRAND["sidebar"], fg=BRAND["gold"],
                 font=("Segoe UI", 10, "bold")).pack(pady=(0, 22))

        for name in ["Home", "Capture", "Pricing", "Orders", "Sessions", "Content", "Inventory", "Shipping", "Analytics", "Settings"]:
            b = tk.Button(
                side, text=name.upper(), anchor="w", bg=BRAND["sidebar"], fg=BRAND["muted"],
                activebackground=BRAND["panel2"], activeforeground=BRAND["text"], relief="flat",
                font=("Segoe UI", 10, "bold"), padx=24, pady=11, command=lambda n=name: self.show_page(n)
            )
            b.pack(fill="x", padx=12, pady=2)
            self.nav_buttons[name] = b

        bottom = tk.Frame(side, bg=BRAND["sidebar"])
        bottom.pack(side="bottom", fill="x", padx=14, pady=18)
        tk.Label(bottom, text="Root", bg=BRAND["sidebar"], fg=BRAND["gold"], font=("Segoe UI", 8, "bold")).pack(anchor="w")
        tk.Label(bottom, text=str(ROOT), bg=BRAND["sidebar"], fg=BRAND["muted"], font=("Segoe UI", 7),
                 wraplength=190, justify="left").pack(anchor="w")

        self.main = tk.Frame(self, bg=BRAND["bg"])
        self.main.pack(side="left", fill="both", expand=True)

        self.statusbar = tk.Label(self, textvariable=self.status, bg=BRAND["sidebar"], fg=BRAND["muted"],
                                  anchor="w", font=("Segoe UI", 9), padx=10)
        self.statusbar.pack(side="bottom", fill="x")
        self.show_page("Home")

    def clear(self):
        for w in self.main.winfo_children():
            w.destroy()

    def show_page(self, name):
        for n, b in self.nav_buttons.items():
            if n == name:
                b.configure(bg=BRAND["panel2"], fg=BRAND["text"])
            else:
                b.configure(bg=BRAND["sidebar"], fg=BRAND["muted"])
        self.clear()
        if name == "Home":
            self.home_page()
        elif name == "Capture":
            self.capture_page()
        elif name == "Pricing":
            self.pricing_page()
        elif name == "Orders":
            self.orders_page()
        elif name == "Sessions":
            self.sessions_page()
        elif name == "Content":
            self.content_page()
        elif name == "Inventory":
            self.inventory_page()
        else:
            self.placeholder_page(name)

    def header(self, title, subtitle=""):
        tk.Label(self.main, text=title, bg=BRAND["bg"], fg=BRAND["text"], font=("Segoe UI", 24, "bold")).pack(anchor="w", padx=34, pady=(28, 2))
        if subtitle:
            tk.Label(self.main, text=subtitle, bg=BRAND["bg"], fg=BRAND["muted"], font=("Segoe UI", 10)).pack(anchor="w", padx=34, pady=(0, 18))

    def card(self, parent, **pack):
        f = tk.Frame(parent, bg=BRAND["panel"], highlightbackground=BRAND["gold_dark"], highlightthickness=1)
        if pack is not None:
            f.pack(**pack)
        return f

    def label(self, parent, text, size=10, color=None, bold=False, bg=None, **pack):
        lbl = tk.Label(parent, text=text, bg=bg or BRAND["panel"], fg=color or BRAND["text"],
                       font=("Segoe UI", size, "bold" if bold else "normal"), justify="left")
        if pack is not None:
            lbl.pack(**pack)
        return lbl

    def metric_card(self, parent, title, value, subtitle=""):
        c = self.card(parent, side="left", fill="both", expand=True, padx=(0, 12), ipady=10)
        self.label(c, title, 9, BRAND["gold"], True, anchor="w", padx=16, pady=(12, 2))
        self.label(c, str(value), 22, BRAND["text"], True, anchor="w", padx=16)
        if subtitle:
            self.label(c, subtitle, 9, BRAND["muted"], False, anchor="w", padx=16, pady=(0, 8))
        return c

    def make_drop_zone(self, parent, text, command):
        zone = tk.Frame(parent, bg=BRAND["panel2"], highlightbackground=BRAND["blue"], highlightthickness=2)
        zone.pack(fill="x", pady=(0, 16), ipady=22)
        tk.Label(zone, text=text, bg=BRAND["panel2"], fg=BRAND["text"], font=("Segoe UI", 20, "bold")).pack(pady=(16, 4))
        tk.Label(zone, text="Drop CSV here or click to browse", bg=BRAND["panel2"], fg=BRAND["muted"], font=("Segoe UI", 10)).pack()
        tk.Button(zone, text="Browse for CSV", bg=BRAND["blue"], fg="white", activebackground=BRAND["blue2"],
                  relief="flat", font=("Segoe UI", 11, "bold"), padx=16, pady=8, command=command).pack(pady=14)
        zone.bind("<Button-1>", lambda e: command())
        for child in zone.winfo_children():
            child.bind("<Button-1>", lambda e: command())
        if DND_AVAILABLE:
            zone.drop_target_register(DND_FILES)
            zone.dnd_bind("<<Drop>>", self.on_drop)
            for child in zone.winfo_children():
                try:
                    child.drop_target_register(DND_FILES)
                    child.dnd_bind("<<Drop>>", self.on_drop)
                except Exception:
                    pass
        return zone

    def home_page(self):
        self.header("Home", "Mission control for Putnam Collectibles.")
        wrap = tk.Frame(self.main, bg=BRAND["bg"])
        wrap.pack(fill="both", expand=True, padx=34, pady=0)

        mission = self.card(wrap, fill="x", pady=(0, 16), ipady=14)
        self.label(mission, "TODAY'S MISSION", 13, BRAND["gold"], True, anchor="w", padx=18, pady=(14, 4))
        cur = load_current_session()
        if cur:
            msg = (
                f"Active work session: {Path(cur.get('folder','')).name}\n"
                f"Goal: {cur.get('goal','')}\n"
                f"Game: {display_location_game(cur.get('game', 'pokemon'))}\n"
                f"Batch Location: {cur.get('batch_location', '') or '(not set)'}"
            )
        else:
            msg = "Analyze the next CardUploader export or start a tracked work session."
        self.label(mission, msg, 10, BRAND["muted"], False, anchor="w", padx=18, pady=(0, 12))

        latest_card = self.card(wrap, fill="x", pady=(0, 16), ipady=12)
        self.label(latest_card, "ANALYZE LATEST CARDUPLOADER EXPORT", 12, BRAND["gold"], True, anchor="w", padx=18, pady=(12, 6))
        detected = latest_carduploader_export()
        detected_text = f"Detected: {detected}" if detected else "No CSV detected in Imports, Incoming Files, or Downloads."
        self.latest_csv_var = tk.StringVar(value=detected_text)
        tk.Label(latest_card, textvariable=self.latest_csv_var, bg=BRAND["panel"], fg=BRAND["muted"],
                 font=("Segoe UI", 9), justify="left", wraplength=820).pack(anchor="w", padx=18, pady=(0, 10))
        latest_buttons = tk.Frame(latest_card, bg=BRAND["panel"])
        latest_buttons.pack(anchor="w", padx=18, pady=(0, 14))
        tk.Button(latest_buttons, text="Analyze Latest CardUploader Export", bg=BRAND["blue"], fg="white",
                  activebackground=BRAND["blue2"], relief="flat", font=("Segoe UI", 11, "bold"),
                  padx=16, pady=9, command=self.analyze_latest_carduploader_export).pack(side="left")
        self.action_button(latest_buttons, "Browse for CSV", self.browse_and_run).pack(side="left", padx=10)

        self.make_drop_zone(wrap, "Drop CardUploader CSV Here", self.browse_and_run)

        actions = self.card(wrap, fill="x", pady=(0, 16), ipady=12)
        self.label(actions, "QUICK ACTIONS", 12, BRAND["gold"], True, anchor="w", padx=18, pady=(12, 8))
        btns = tk.Frame(actions, bg=BRAND["panel"])
        btns.pack(anchor="w", padx=18, pady=(0, 8))
        self.action_button(btns, "Start Work Session", self.start_work_session).pack(side="left")
        self.action_button(btns, "Import CardUploader Inventory Export", self.import_carduploader_inventory_ui).pack(side="left", padx=8)
        self.action_button(btns, "Split Recording", self.run_split_recording_tool).pack(side="left", padx=8)
        folder_btns = tk.Frame(actions, bg=BRAND["panel"])
        folder_btns.pack(anchor="w", padx=18, pady=(0, 14))
        self.action_button(folder_btns, "Open Collectr", lambda: os.startfile(COLLECTR)).pack(side="left")
        self.action_button(folder_btns, "Open Imports", lambda: os.startfile(IMPORTS)).pack(side="left", padx=8)
        self.action_button(folder_btns, "Open Exports", lambda: os.startfile(EXPORTS)).pack(side="left", padx=8)
        self.action_button(folder_btns, "Open Completed Jobs", lambda: os.startfile(COMPLETED)).pack(side="left", padx=8)
        self.action_button(folder_btns, "Open Work Sessions", lambda: os.startfile(SESSIONS)).pack(side="left", padx=8)
        self.action_button(folder_btns, "Open Inventory Snapshot", self.open_inventory_snapshot).pack(side="left", padx=8)

        decision = self.card(wrap, fill="x", pady=(0, 16), ipady=12)
        self.label(decision, "DECISION ENGINE", 12, BRAND["gold"], True, anchor="w", padx=18, pady=(12, 6))
        initial_engine_status = run_decision_engine_check(write_log=False)
        self.decision_engine_var = tk.StringVar(value=decision_engine_summary_text(initial_engine_status))
        tk.Label(decision, textvariable=self.decision_engine_var, bg=BRAND["panel"], fg=BRAND["muted"],
                 font=("Segoe UI", 9), justify="left").pack(anchor="w", padx=18, pady=(0, 10))
        self.action_button(decision, "Run Decision Engine Check", self.run_decision_engine_check_ui).pack(anchor="w", padx=18, pady=(0, 14))

        row = tk.Frame(wrap, bg=BRAND["bg"])
        row.pack(fill="x", pady=(0, 16))
        self.metric_card(row, "Pricing Jobs Today", todays_jobs_count(), "Completed job folders")
        self.metric_card(row, "Work Sessions", len(latest_sessions(99)), "Tracked sessions")
        self.metric_card(row, "Raw Recordings", count_files(CONTENT_RECORDINGS, "*"), "Saved footage")
        self.metric_card(row, "Content Ideas", count_files(CONTENT_IDEAS, "*"), "Backlog")

        lower = tk.Frame(wrap, bg=BRAND["bg"])
        lower.pack(fill="both", expand=True)
        activity = self.card(lower, side="left", fill="both", expand=True, padx=(0, 12), ipady=10)
        self.label(activity, "RECENT ACTIVITY", 12, BRAND["gold"], True, anchor="w", padx=18, pady=(12, 6))
        acts = recent_activity(7) or ["No activity recorded yet."]
        for a in acts:
            self.label(activity, "OK - " + a, 9, BRAND["muted"], False, anchor="w", padx=18, pady=2)

        content = self.card(lower, side="left", fill="both", expand=True, ipady=10)
        self.label(content, "CONTENT SNAPSHOT", 12, BRAND["gold"], True, anchor="w", padx=18, pady=(12, 6))
        lines = [
            f"Recordings saved: {count_files(CONTENT_RECORDINGS, '*')}",
            f"Clips captured: {count_files(CONTENT_CLIPS, '*')}",
            f"Episodes planned: {count_files(CONTENT_EPISODES, '*')}",
            "Current concept: 100-card listing workflow",
        ]
        for line in lines:
            self.label(content, line, 9, BRAND["muted"], False, anchor="w", padx=18, pady=2)
        self.action_button(content, "Open OBS Checklist", self.open_recording_checklist).pack(anchor="w", padx=18, pady=12)

    def action_button(self, parent, text, command):
        return tk.Button(parent, text=text, bg=BRAND["panel2"], fg=BRAND["text"],
                         activebackground=BRAND["blue"], activeforeground="white", relief="flat",
                         font=("Segoe UI", 10, "bold"), padx=14, pady=8, command=command)

    def capture_page(self):
        self.header("Capture", "Capture Studio v1: save clean front/back card photos for later workflow steps.")
        wrap = tk.Frame(self.main, bg=BRAND["bg"])
        wrap.pack(fill="both", expand=True, padx=34, pady=0)

        status_card = self.card(wrap, fill="x", pady=(0, 14), ipady=12)
        self.label(status_card, "CAPTURE SESSION", 12, BRAND["gold"], True, anchor="w", padx=18, pady=(12, 6))
        self.capture_folder_var = tk.StringVar()
        self.capture_mode_var = tk.StringVar()
        self.capture_card_var = tk.StringVar()
        self.capture_count_var = tk.StringVar()
        self.capture_obs_var = tk.StringVar(value="OBS status not checked.")

        for label_text, var in [
            ("Current capture folder", self.capture_folder_var),
            ("Capture mode", self.capture_mode_var),
            ("Current card number", self.capture_card_var),
            ("Photos captured", self.capture_count_var),
            ("OBS status", self.capture_obs_var),
        ]:
            row = tk.Frame(status_card, bg=BRAND["panel"])
            row.pack(fill="x", padx=18, pady=2)
            tk.Label(row, text=f"{label_text}:", bg=BRAND["panel"], fg=BRAND["gold"],
                     font=("Segoe UI", 9, "bold"), width=22, anchor="w").pack(side="left")
            tk.Label(row, textvariable=var, bg=BRAND["panel"], fg=BRAND["muted"],
                     font=("Segoe UI", 9), justify="left", wraplength=780).pack(side="left", fill="x", expand=True)

        actions = self.card(wrap, fill="x", pady=(0, 14), ipady=12)
        self.label(actions, "ACTIONS", 12, BRAND["gold"], True, anchor="w", padx=18, pady=(12, 8))
        row1 = tk.Frame(actions, bg=BRAND["panel"])
        row1.pack(anchor="w", padx=18, pady=(0, 8))
        self.action_button(row1, "Start Capture Session", self.start_capture_session_ui).pack(side="left")
        self.action_button(row1, "Capture Front", lambda: self.capture_side_ui("front")).pack(side="left", padx=8)
        self.action_button(row1, "Capture Back", lambda: self.capture_side_ui("back")).pack(side="left")
        self.action_button(row1, "Retake Last", self.retake_last_capture_ui).pack(side="left", padx=8)
        self.action_button(row1, "Finish Session", self.finish_capture_session_ui).pack(side="left")
        row2 = tk.Frame(actions, bg=BRAND["panel"])
        row2.pack(anchor="w", padx=18, pady=(0, 12))
        self.action_button(row2, "Open Capture Folder", self.open_capture_folder_ui).pack(side="left")
        self.action_button(row2, "Launch OBS", self.launch_obs_ui).pack(side="left", padx=8)
        self.action_button(row2, "OBS Status", self.check_obs_status_ui).pack(side="left")

        note = self.card(wrap, fill="x", pady=(0, 14), ipady=10)
        self.label(note, "SCOPE", 12, BRAND["gold"], True, anchor="w", padx=18, pady=(12, 4))
        self.label(
            note,
            "Capture Studio only saves JPEGs. It does not run OCR, identify cards, hand off to CardUploader, or assign inventory.",
            9,
            BRAND["muted"],
            False,
            anchor="w",
            padx=18,
            pady=(0, 12),
        )
        self.refresh_capture_status()

    def refresh_capture_status(self):
        session = self.capture_session
        folder = Path(session["folder"]) if session else CAPTURE_ROOT
        mode = session.get("capture_mode", "OBS WebSocket") if session else "No active session"
        card_number = session.get("current_card_number", 1) if session else 1
        count = session.get("photos_captured", 0) if session else 0
        for var_name, value in [
            ("capture_folder_var", str(folder)),
            ("capture_mode_var", str(mode)),
            ("capture_card_var", str(card_number)),
            ("capture_count_var", str(count)),
        ]:
            if hasattr(self, var_name):
                getattr(self, var_name).set(value)

    def start_capture_session_ui(self):
        try:
            self.capture_session = self.capture_service.start_session()
            folder = Path(self.capture_session["folder"])
            append_activity(f"Started Capture Studio session: {folder.name}")
            self.status.set(f"Capture session started: {folder}")
            self.refresh_capture_status()
        except Exception as exc:
            messagebox.showerror("Capture Studio", str(exc))

    def capture_side_ui(self, side):
        if not self.capture_session:
            if not messagebox.askyesno("Capture Studio", "No active capture session. Start one now?"):
                return
            self.start_capture_session_ui()
            if not self.capture_session:
                return
        try:
            result = self.capture_service.capture(self.capture_session, side)
            append_activity(f"Captured {result.path.name} with Capture Studio")
            self.status.set(f"Captured {result.path.name}")
            self.refresh_capture_status()
        except CaptureStudioError as exc:
            self.status.set("Capture failed; OBS is not ready.")
            messagebox.showwarning("Capture Studio", str(exc))
        except Exception as exc:
            messagebox.showerror("Capture Studio", str(exc))

    def retake_last_capture_ui(self):
        if not self.capture_session:
            messagebox.showinfo("Capture Studio", "No active capture session.")
            return
        try:
            moved = self.capture_service.retake_last(self.capture_session)
            if moved:
                append_activity(f"Moved last capture to retakes: {moved.name}")
                self.status.set(f"Last capture moved to retakes: {moved.name}")
            else:
                self.status.set("No capture to retake.")
            self.refresh_capture_status()
        except Exception as exc:
            messagebox.showerror("Capture Studio", str(exc))

    def finish_capture_session_ui(self):
        if not self.capture_session:
            messagebox.showinfo("Capture Studio", "No active capture session.")
            return
        try:
            folder = Path(self.capture_session["folder"])
            self.capture_service.finish_session(self.capture_session)
            append_activity(f"Finished Capture Studio session: {folder.name}")
            self.status.set(f"Capture session finished: {folder}")
            self.refresh_capture_status()
        except Exception as exc:
            messagebox.showerror("Capture Studio", str(exc))

    def open_capture_folder_ui(self):
        folder = Path(self.capture_session["folder"]) if self.capture_session else CAPTURE_ROOT
        folder.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(folder)
        except Exception as exc:
            messagebox.showinfo("Capture Studio", f"Capture folder:\n{folder}\n\nCould not open automatically:\n{exc}")

    def launch_obs_ui(self):
        try:
            launched = self.capture_service.launch_obs()
            self.status.set(f"OBS launch requested: {launched}")
        except CaptureStudioError as exc:
            messagebox.showwarning("Capture Studio", str(exc))
        except Exception as exc:
            messagebox.showerror("Capture Studio", str(exc))

    def check_obs_status_ui(self):
        status = self.capture_service.obs_status()
        if hasattr(self, "capture_obs_var"):
            self.capture_obs_var.set(status)
        self.status.set(status)

    def orders_page(self):
        self.header("Orders", "Orders v1: import eBay orders CSVs and generate printable pick slips.")
        wrap = tk.Frame(self.main, bg=BRAND["bg"])
        wrap.pack(fill="both", expand=True, padx=34, pady=0)

        setup = self.card(wrap, fill="x", pady=(0, 14), ipady=12)
        self.label(setup, "PICK SLIP FOUNDATION", 12, BRAND["gold"], True, anchor="w", padx=18, pady=(12, 6))
        self.orders_status_var = tk.StringVar(value="No orders CSV imported yet.")
        tk.Label(
            setup,
            textvariable=self.orders_status_var,
            bg=BRAND["panel"],
            fg=BRAND["muted"],
            font=("Segoe UI", 10),
            justify="left",
            wraplength=900,
        ).pack(anchor="w", padx=18, pady=(0, 12))

        buttons = tk.Frame(setup, bg=BRAND["panel"])
        buttons.pack(anchor="w", padx=18, pady=(0, 12))
        self.action_button(buttons, "Import eBay Orders CSV", self.import_orders_csv_ui).pack(side="left")
        self.action_button(buttons, "Open Pick Slip Folder", self.open_pick_slip_folder_ui).pack(side="left", padx=8)
        self.action_button(buttons, "Open Printable Pick Slips", self.open_printable_pick_slips_ui).pack(side="left")

        note = self.card(wrap, fill="x", pady=(0, 14), ipady=12)
        self.label(note, "SCOPE", 12, BRAND["gold"], True, anchor="w", padx=18, pady=(12, 4))
        self.label(
            note,
            "Orders v1 reads a CSV and writes TXT/HTML pick slips only. It does not buy labels, modify inventory, call the eBay API, or watch for new orders automatically.",
            9,
            BRAND["muted"],
            False,
            anchor="w",
            padx=18,
            pady=(0, 12),
        )

    def import_orders_csv_ui(self):
        path = filedialog.askopenfilename(
            title="Choose eBay orders CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            self.status.set("Generating pick slips...")
            self.update_idletasks()
            result = generate_pick_slips(path)
            self.current_pick_list_result = result
            msg = (
                f"Input: {path}\n"
                f"Orders grouped: {result['order_count']}\n"
                f"Line items: {result['line_count']}\n"
                f"Pick slips saved to:\n{result['output_dir']}\n\n"
                "Printing is manual in v1: open the printable HTML files and print from the browser."
            )
            self.orders_status_var.set(msg)
            self.status.set(f"Pick slips generated for {result['order_count']} orders.")
            append_activity(f"Generated pick slips for {result['order_count']} orders")
            messagebox.showinfo("Orders v1", msg)
        except Exception as exc:
            self.status.set(f"Orders import failed: {exc}")
            messagebox.showerror("Orders v1", str(exc))

    def open_pick_slip_folder_ui(self):
        folder = Path((self.current_pick_list_result or {}).get("output_dir") or PICK_LIST_ROOT)
        folder.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(folder)
        except Exception as exc:
            messagebox.showinfo("Orders v1", f"Pick slip folder:\n{folder}\n\nCould not open automatically:\n{exc}")

    def open_printable_pick_slips_ui(self):
        result = self.current_pick_list_result or {}
        html_files = [Path(path) for path in result.get("html_files", [])]
        if not html_files:
            messagebox.showinfo(
                "Orders v1",
                "No printable pick slips generated yet.\n\nImport an eBay orders CSV first.",
            )
            return
        first = html_files[0]
        try:
            os.startfile(first)
            self.status.set("Opened first printable pick slip. Print from the browser.")
        except Exception as exc:
            messagebox.showinfo(
                "Orders v1",
                f"Printable pick slip:\n{first}\n\nCould not open automatically:\n{exc}",
            )

    def run_decision_engine_check_ui(self):
        result = run_decision_engine_check(write_log=True)
        try:
            self.decision_engine_var.set(decision_engine_summary_text(result))
        except Exception:
            pass
        log_path = result.get("log_path", "")
        if result.get("errors"):
            messagebox.showwarning("Putnam OS", "Decision Engine check completed with warnings.\n\n" + decision_engine_summary_text(result))
        else:
            messagebox.showinfo("Putnam OS", f"Decision Engine check complete.\n\nLog:\n{log_path}")
        append_activity("Decision Engine check complete")

    def inventory_page(self):
        self.header("Inventory", "Inventory Audit verifies physical cards and trusted Batch Locations before any eBay revision.")
        wrap = tk.Frame(self.main, bg=BRAND["bg"])
        wrap.pack(fill="both", expand=True, padx=34, pady=0)

        setup = self.card(wrap, fill="x", pady=(0, 12), ipady=10)
        self.label(setup, "INVENTORY AUDIT MODE v2", 12, BRAND["gold"], True, anchor="w", padx=18, pady=(12, 4))
        self.label(
            setup,
            "User SKU = Batch Location. The operator confirms the card; no OCR, scanner identification, CardUploader recognition, or eBay revision happens here.",
            9,
            BRAND["muted"],
            False,
            anchor="w",
            padx=18,
            pady=(0, 10),
        )

        latest = latest_ebay_active_listings_report()
        self.inventory_source_var = tk.StringVar(value=str(latest or ""))
        self.inventory_game_var = tk.StringVar(value="Pokemon")
        self.inventory_location_var = tk.StringVar(value=suggest_next_location("Pokemon", root=ROOT))
        self.inventory_capture_var = tk.BooleanVar(value=False)

        source_row = tk.Frame(setup, bg=BRAND["panel"])
        source_row.pack(fill="x", padx=18, pady=3)
        self.label(source_row, "Source", 9, BRAND["muted"], False, side="left", padx=(0, 8))
        tk.Entry(source_row, textvariable=self.inventory_source_var, bg=BRAND["panel2"], fg=BRAND["text"],
                 insertbackground=BRAND["text"], relief="flat", width=92).pack(side="left", fill="x", expand=True)
        self.action_button(source_row, "Latest eBay", self.inventory_use_latest_source).pack(side="left", padx=8)
        self.action_button(source_row, "Browse", self.inventory_browse_source).pack(side="left")

        config_row = tk.Frame(setup, bg=BRAND["panel"])
        config_row.pack(fill="x", padx=18, pady=6)
        self.label(config_row, "Game", 9, BRAND["muted"], False, side="left", padx=(0, 8))
        game_menu = tk.OptionMenu(config_row, self.inventory_game_var, "Pokemon", "Magic", "One Piece", "All")
        game_menu.configure(bg=BRAND["panel2"], fg=BRAND["text"], activebackground=BRAND["blue"], relief="flat", width=12)
        game_menu.pack(side="left")
        self.action_button(config_row, "Suggest Location", self.inventory_suggest_location).pack(side="left", padx=8)
        self.label(config_row, "Batch Location", 9, BRAND["muted"], False, side="left", padx=(12, 8))
        tk.Entry(config_row, textvariable=self.inventory_location_var, bg=BRAND["panel2"], fg=BRAND["text"],
                 insertbackground=BRAND["text"], relief="flat", width=14).pack(side="left")
        tk.Checkbutton(
            config_row,
            text="Capture verification images",
            variable=self.inventory_capture_var,
            bg=BRAND["panel"],
            fg=BRAND["muted"],
            selectcolor=BRAND["panel2"],
            activebackground=BRAND["panel"],
            activeforeground=BRAND["text"],
        ).pack(side="left", padx=16)

        setup_actions = tk.Frame(setup, bg=BRAND["panel"])
        setup_actions.pack(anchor="w", padx=18, pady=(4, 12))
        tk.Button(setup_actions, text="Start New Audit", bg=BRAND["blue"], fg="white",
                  activebackground=BRAND["blue2"], relief="flat", font=("Segoe UI", 11, "bold"),
                  padx=18, pady=10, command=self.inventory_start_audit).pack(side="left")
        self.action_button(setup_actions, "Resume Audit", self.inventory_resume_audit).pack(side="left", padx=8)
        self.action_button(setup_actions, "Generate Reports", self.inventory_generate_reports).pack(side="left", padx=8)
        self.action_button(setup_actions, "Launch Capture Studio", self.launch_capture_studio).pack(side="left", padx=8)
        self.action_button(setup_actions, "Open Audit Folder", lambda: os.startfile(INVENTORY_AUDIT_DIR)).pack(side="left", padx=8)

        queue = self.card(wrap, fill="both", expand=True, ipady=12)
        self.label(queue, "AUDIT QUEUE", 12, BRAND["gold"], True, anchor="w", padx=18, pady=(12, 4))
        self.inventory_progress_var = tk.StringVar(value="No audit loaded.")
        self.inventory_title_var = tk.StringVar(value="")
        self.inventory_meta_var = tk.StringVar(value="")
        self.inventory_stats_var = tk.StringVar(value="")
        tk.Label(queue, textvariable=self.inventory_progress_var, bg=BRAND["panel"], fg=BRAND["gold"],
                 font=("Segoe UI", 11, "bold"), justify="left").pack(anchor="w", padx=18, pady=(0, 6))
        tk.Label(queue, textvariable=self.inventory_title_var, bg=BRAND["panel"], fg=BRAND["text"],
                 font=("Segoe UI", 14, "bold"), justify="left", wraplength=940).pack(anchor="w", padx=18, pady=(0, 8))
        tk.Label(queue, textvariable=self.inventory_meta_var, bg=BRAND["panel"], fg=BRAND["muted"],
                 font=("Segoe UI", 10), justify="left", wraplength=1000).pack(anchor="w", padx=18, pady=(0, 8))

        location_row = tk.Frame(queue, bg=BRAND["panel"])
        location_row.pack(fill="x", padx=18, pady=(0, 8))
        self.inventory_current_location_var = tk.StringVar(value="")
        self.inventory_new_location_var = tk.StringVar(value="")
        self.label(location_row, "Current Location", 9, BRAND["muted"], False, side="left", padx=(0, 8))
        tk.Entry(location_row, textvariable=self.inventory_current_location_var, bg=BRAND["panel2"], fg=BRAND["text"],
                 relief="flat", width=18, state="readonly", readonlybackground=BRAND["panel2"]).pack(side="left")
        self.label(location_row, "New Location", 9, BRAND["muted"], False, side="left", padx=(12, 8))
        tk.Entry(location_row, textvariable=self.inventory_new_location_var, bg=BRAND["panel2"], fg=BRAND["text"],
                 insertbackground=BRAND["text"], relief="flat", width=18).pack(side="left")
        self.action_button(location_row, "Save Location", self.inventory_save_location).pack(side="left", padx=8)
        self.action_button(location_row, "Use Last Location", self.inventory_use_last_location).pack(side="left")

        notes_row = tk.Frame(queue, bg=BRAND["panel"])
        notes_row.pack(fill="x", padx=18, pady=(0, 8))
        self.label(notes_row, "Notes", 9, BRAND["muted"], False, side="left", padx=(0, 8))
        self.inventory_notes_var = tk.StringVar(value="")
        tk.Entry(notes_row, textvariable=self.inventory_notes_var, bg=BRAND["panel2"], fg=BRAND["text"],
                 insertbackground=BRAND["text"], relief="flat").pack(side="left", fill="x", expand=True)

        actions = tk.Frame(queue, bg=BRAND["panel"])
        actions.pack(anchor="w", padx=18, pady=(0, 10))
        tk.Button(actions, text="Mark Confirmed", bg=BRAND["blue"], fg="white", activebackground=BRAND["blue2"],
                  relief="flat", font=("Segoe UI", 12, "bold"), padx=18, pady=12,
                  command=lambda: self.inventory_apply_action("confirm")).pack(side="left")
        self.action_button(actions, "Already Correct", lambda: self.inventory_apply_action("already_correct")).pack(side="left", padx=8)
        self.action_button(actions, "Mark Missing", lambda: self.inventory_apply_action("missing")).pack(side="left", padx=8)
        self.action_button(actions, "Needs Review", lambda: self.inventory_apply_action("needs_review")).pack(side="left", padx=8)
        self.action_button(actions, "Save Progress", self.inventory_save_progress).pack(side="left", padx=8)
        self.action_button(actions, "Skip", lambda: self.inventory_apply_action("skip")).pack(side="left", padx=8)
        self.action_button(actions, "Previous", lambda: self.inventory_move(-1)).pack(side="left", padx=(18, 8))
        self.action_button(actions, "Next", lambda: self.inventory_move(1)).pack(side="left")

        tk.Label(queue, textvariable=self.inventory_stats_var, bg=BRAND["panel"], fg=BRAND["muted"],
                 font=("Segoe UI", 10), justify="left", wraplength=1000).pack(anchor="w", padx=18, pady=(0, 10))
        self.label(queue, "Audit Progress", 9, BRAND["gold"], True, anchor="w", padx=18, pady=(0, 4))
        self.inventory_audit_session = load_inventory_audit_session()
        if self.inventory_audit_session:
            self.inventory_update_queue_view()

    def inventory_use_latest_source(self):
        latest = latest_ebay_active_listings_report()
        if not latest:
            messagebox.showinfo("Putnam OS", "No eBay Active Listings CSV found in eBay Store Items.")
            return
        self.inventory_source_var.set(str(latest))

    def inventory_browse_source(self):
        path = filedialog.askopenfilename(title="Choose inventory source CSV", filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if path:
            self.inventory_source_var.set(path)

    def inventory_suggest_location(self):
        game = self.inventory_game_var.get()
        self.inventory_location_var.set(suggest_next_location(game, root=ROOT))

    def inventory_start_audit(self):
        source = self.inventory_source_var.get().strip()
        if not source:
            messagebox.showinfo("Putnam OS", "Choose an inventory source first.")
            return
        if unfinished_inventory_audit_sessions():
            if not messagebox.askyesno("Start New Audit", "Unfinished audit sessions exist.\n\nStart a new audit anyway?"):
                return
        try:
            session = create_inventory_audit_session(
                source,
                self.inventory_game_var.get(),
                self.inventory_location_var.get(),
                self.inventory_capture_var.get(),
            )
            self.inventory_audit_session = session
            warning = batch_size_warning(len(session.get("records", [])))
            self.status.set(f"Inventory audit queue loaded: {len(session.get('records', []))} cards.")
            if warning:
                messagebox.showwarning("Inventory Audit", warning)
            self.inventory_update_queue_view()
        except Exception as exc:
            messagebox.showerror("Putnam OS", str(exc))

    def inventory_resume_audit(self):
        sessions = unfinished_inventory_audit_sessions()
        if sessions:
            summary_lines = []
            for idx, candidate in enumerate(sessions, 1):
                stats = candidate.get("_stats") or inventory_audit_stats(candidate)
                summary_lines.append(
                    f"{idx}. {candidate.get('created_at', '')} | "
                    f"{Path(candidate.get('source_file', '')).name or candidate.get('source_scope', '')} | "
                    f"{stats['confirmed']} / {stats['total']} confirmed | "
                    f"last updated {candidate.get('updated_at', '')}"
                )
            if len(sessions) == 1:
                session = sessions[0]
            else:
                choice = simpledialog.askinteger(
                    "Resume Audit",
                    "Unfinished audit sessions:\n\n" + "\n".join(summary_lines) + "\n\nEnter session number to resume:",
                    minvalue=1,
                    maxvalue=len(sessions),
                )
                if not choice:
                    return
                session = sessions[choice - 1]
        else:
            session = load_inventory_audit_session()
        if not session:
            messagebox.showinfo("Putnam OS", "No saved inventory audit session found.")
            return
        self.inventory_audit_session = session
        self.inventory_source_var.set(session.get("source_file", ""))
        self.inventory_game_var.set(display_location_game(session.get("game", "Pokemon")).replace(" / MTG", ""))
        self.inventory_location_var.set(session.get("batch_location", ""))
        self.inventory_capture_var.set(bool(session.get("capture_enabled")))
        self.inventory_update_queue_view()
        self.status.set("Inventory audit resumed.")

    def current_inventory_record(self):
        session = getattr(self, "inventory_audit_session", None)
        if not session:
            return None
        records = session.get("records", [])
        if not records:
            return None
        idx = max(0, min(int(session.get("current_index", 0)), len(records) - 1))
        return records[idx]

    def inventory_update_queue_view(self):
        session = getattr(self, "inventory_audit_session", None)
        if not session:
            return
        record = self.current_inventory_record()
        stats = inventory_audit_stats(session)
        total = stats["total"]
        idx = int(session.get("current_index", 0)) + 1 if total else 0
        self.inventory_progress_var.set(f"{idx} / {total}  |  {stats['completion_pct']}% complete")
        if not record:
            self.inventory_title_var.set("No cards in this audit queue.")
            self.inventory_meta_var.set("")
            if hasattr(self, "inventory_current_location_var"):
                self.inventory_current_location_var.set("")
            if hasattr(self, "inventory_new_location_var"):
                self.inventory_new_location_var.set("")
        else:
            current_location = record.get("confirmed_location") or record.get("user_sku") or ""
            self.inventory_title_var.set(record.get("title", ""))
            self.inventory_meta_var.set(
                f"eBay Item ID: {record.get('item_id', '')}\n"
                f"Current User SKU: {record.get('user_sku', '') or '(blank)'}\n"
                f"Quantity: {record.get('quantity', '')}    Game: {display_location_game(record.get('game', 'unknown'))}    "
                f"Price: {record.get('price', '') or '(blank)'}\n"
                f"Selected Batch Location: {session.get('batch_location', '')}\n"
                f"Status: {record.get('audit_status', '') or 'pending'}    Confirmed location: {record.get('confirmed_location', '') or '(none)'}"
            )
            if hasattr(self, "inventory_current_location_var"):
                self.inventory_current_location_var.set(current_location or "(blank)")
            if hasattr(self, "inventory_new_location_var"):
                self.inventory_new_location_var.set(record.get("confirmed_location") or session.get("last_location") or session.get("batch_location", ""))
            self.inventory_notes_var.set(record.get("notes", ""))
        self.inventory_stats_var.set(
            f"Total rows: {stats['total']}  Pending: {stats['pending']}  Audited: {stats['audited']}  Remaining: {stats['remaining']}  Confirmed: {stats['confirmed']}  "
            f"Already correct: {stats['already_correct']}  Missing: {stats['missing']}  "
            f"Needs review: {stats['needs_review']}  Location updated: {stats['location_updated']}  Skipped: {stats['skipped']}\n"
            f"Session save path: {inventory_audit_session_path(session)}"
        )

    def inventory_apply_action(self, action):
        session = getattr(self, "inventory_audit_session", None)
        if not session:
            messagebox.showinfo("Putnam OS", "Load or resume an audit queue first.")
            return
        try:
            self.inventory_audit_session = apply_inventory_audit_action(session, action, self.inventory_notes_var.get())
            self.inventory_update_queue_view()
            self.status.set(f"Inventory audit saved: {action}.")
        except Exception as exc:
            messagebox.showerror("Putnam OS", str(exc))

    def inventory_use_last_location(self):
        session = getattr(self, "inventory_audit_session", None)
        if not session:
            messagebox.showinfo("Putnam OS", "Load or resume an audit queue first.")
            return
        self.inventory_new_location_var.set(session.get("last_location") or session.get("batch_location", ""))

    def inventory_save_location(self):
        session = getattr(self, "inventory_audit_session", None)
        if not session:
            messagebox.showinfo("Putnam OS", "Load or resume an audit queue first.")
            return
        record = self.current_inventory_record()
        if not record:
            return
        new_location = self.inventory_new_location_var.get().strip()
        previous = record.get("confirmed_location") or record.get("user_sku") or ""
        if previous and previous != new_location:
            if not messagebox.askyesno(
                "Save Location",
                f"Previous location:\n{previous}\n\nNew location:\n{new_location}\n\nReplace the saved audit location for this row?",
            ):
                return
        try:
            self.inventory_audit_session = update_inventory_audit_location(session, new_location, self.inventory_notes_var.get())
            self.inventory_update_queue_view()
            self.status.set("Inventory audit saved: location updated.")
        except Exception as exc:
            messagebox.showerror("Putnam OS", str(exc))

    def inventory_save_progress(self):
        session = getattr(self, "inventory_audit_session", None)
        if not session:
            messagebox.showinfo("Putnam OS", "Load or resume an audit queue first.")
            return
        try:
            self.inventory_audit_session = save_inventory_audit_progress(session, self.inventory_notes_var.get())
            self.inventory_update_queue_view()
            stats = inventory_audit_stats(self.inventory_audit_session)
            messagebox.showinfo("Audit Progress", self.inventory_summary_text(self.inventory_audit_session, stats))
            self.status.set("Inventory audit progress saved.")
        except Exception as exc:
            messagebox.showerror("Putnam OS", str(exc))

    def inventory_summary_text(self, session, stats=None):
        stats = stats or inventory_audit_stats(session)
        return (
            f"Total rows: {stats['total']}\n"
            f"Confirmed: {stats['confirmed']}\n"
            f"Pending: {stats['pending']}\n"
            f"Needs review: {stats['needs_review']}\n"
            f"Missing: {stats['missing']}\n"
            f"Location updated: {stats['location_updated']}\n\n"
            f"Session save path:\n{inventory_audit_session_path(session)}"
        )

    def inventory_move(self, delta):
        session = getattr(self, "inventory_audit_session", None)
        if not session:
            return
        self.inventory_audit_session = move_inventory_audit_index(session, delta)
        self.inventory_update_queue_view()

    def inventory_generate_reports(self):
        session = getattr(self, "inventory_audit_session", None) or load_inventory_audit_session()
        if not session:
            messagebox.showinfo("Putnam OS", "No inventory audit session found.")
            return
        try:
            result = generate_inventory_audit_reports(session)
            self.status.set("Inventory audit reports generated.")
            messagebox.showinfo(
                "Inventory Audit Reports",
                "Reports generated.\n\n"
                + self.inventory_summary_text(session, result["stats"])
                + "\n\n"
                f"Audit CSV:\n{result['audit_csv']}\n\n"
                f"Summary:\n{result['summary_txt']}\n\n"
                f"Bulk revise CSV:\n{result['bulk_csv']}",
            )
            os.startfile(result["summary_txt"])
        except Exception as exc:
            messagebox.showerror("Putnam OS", str(exc))

    def launch_capture_studio(self):
        self.show_page("Capture")
        append_activity("Opened Capture Studio tab for inventory audit verification")
        self.status.set("Capture Studio is open. Use it to save internal verification JPEGs only.")

    def browse_and_run(self):
        p = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if not p:
            return
        self.load(p)
        self.auto_run()

    def analyze_latest_carduploader_export(self):
        latest = latest_carduploader_export()
        if not latest:
            try:
                self.latest_csv_var.set("No CSV found. Use Browse for CSV or drop a CardUploader CSV on Home.")
            except Exception:
                pass
            self.status.set("No CardUploader CSV found in Imports, Incoming Files, or Downloads.")
            messagebox.showinfo("Putnam OS", "No CSV found in Imports, Incoming Files, or Downloads.\nUse Browse for CSV or drop a CardUploader CSV on Home.")
            return
        try:
            self.latest_csv_var.set(f"Detected: {latest}\nRunning analysis now...")
        except Exception:
            pass
        self.status.set(f"Detected latest export: {latest}")
        self.update()
        self.load(latest)
        self.auto_run()

    def import_carduploader_inventory_ui(self):
        p = filedialog.askopenfilename(
            title="Select CardUploader Inventory Export",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if not p:
            return
        try:
            self.status.set("Importing CardUploader inventory export...")
            self.update()
            result = import_carduploader_inventory(p)
            self.status.set(f"Inventory snapshot updated. Rows: {result['total_rows']}.")
            messagebox.showinfo(
                "Putnam OS",
                "Inventory import complete.\n\n"
                f"Rows: {result['total_rows']}\n"
                f"Listed rows: {result['listed_rows']}\n"
                f"Quantity total: {result['quantity_total']}\n"
                f"Listed value: ${result['total_listed_value']:.2f}\n\n"
                f"Snapshot:\n{result['snapshot']}\n\n"
                f"Report folder:\n{result['job']}"
            )
            os.startfile(result["job"])
        except Exception as e:
            self.status.set("Inventory import error.")
            messagebox.showerror("Putnam OS", str(e))

    def open_inventory_snapshot(self):
        if INVENTORY_SNAPSHOT.exists():
            os.startfile(INVENTORY_SNAPSHOT)
        else:
            messagebox.showinfo("Putnam OS", f"No inventory snapshot found yet.\n\nExpected path:\n{INVENTORY_SNAPSHOT}")

    def on_drop(self, event):
        raw = event.data
        # Handles {C:\path with spaces\file.csv}
        paths = self.tk.splitlist(raw)
        if not paths:
            return
        p = paths[0]
        if not str(p).lower().endswith(".csv"):
            messagebox.showwarning("Putnam OS", "Please drop a CSV file.")
            return
        self.load(p)
        self.auto_run()

    def start_work_session(self):
        goal = simpledialog.askstring("Work Session", "Goal:", initialvalue="List new inventory") or "List new inventory"
        planned = simpledialog.askstring("Work Session", "Planned cards:", initialvalue="100") or "100"
        game = simpledialog.askstring("Work Session", "Game/category:", initialvalue="Pokemon") or "Pokemon"
        suggested = suggest_next_location(game, root=ROOT)
        batch_location = simpledialog.askstring(
            "Batch Location",
            "User SKU = Batch Location.\n\n"
            f"Suggested next location for {display_location_game(game)}: {suggested}\n\n"
            "Override if needed:",
            initialvalue=suggested,
        )
        if not batch_location:
            messagebox.showinfo("Putnam OS", "Work session canceled because batch location was blank.")
            return
        try:
            batch_location = validate_location(batch_location)
        except ValueError as exc:
            messagebox.showerror("Putnam OS", str(exc))
            return
        method = simpledialog.askstring("Work Session", "Capture method:", initialvalue="iPhone camera") or "iPhone camera"
        folder = create_work_session(goal, planned, method, game, batch_location)
        messagebox.showinfo("Putnam OS", f"Work session started:\n{folder}")
        try:
            os.startfile(folder)
        except Exception:
            pass
        self.show_page("Home")

    def end_current_session_ui(self):
        completed = simpledialog.askstring("End Session", "Cards completed:", initialvalue="")
        recording = filedialog.askopenfilename(title="Select raw recording or cancel", filetypes=[("Video files", "*.mp4 *.mkv *.mov"), ("All files", "*.*")])
        notes = simpledialog.askstring("End Session", "Session notes / bottlenecks:", initialvalue="")
        folder = end_work_session(completed or "", recording or "", notes or "")
        if folder:
            messagebox.showinfo("Putnam OS", f"Work session ended:\n{folder}")
            try:
                os.startfile(folder)
            except Exception:
                pass
        else:
            messagebox.showwarning("Putnam OS", "No active work session found.")
        self.show_page("Sessions")

    def run_split_recording_tool(self):
        tool = TOOLS / "Split_Putnam_Work_Session.ps1"
        if not tool.exists():
            messagebox.showwarning("Putnam OS", f"Split tool not found:\n{tool}")
            return
        try:
            subprocess.Popen(["powershell", "-ExecutionPolicy", "Bypass", "-File", str(tool)], cwd=str(ROOT))
            append_activity("Launched split work session tool")
        except Exception as e:
            messagebox.showerror("Putnam OS", str(e))

    def sessions_page(self):
        self.header("Work Sessions", "Track production sessions, footage, bottlenecks, and metrics.")
        wrap = tk.Frame(self.main, bg=BRAND["bg"])
        wrap.pack(fill="both", expand=True, padx=34, pady=0)

        current = self.card(wrap, fill="x", pady=(0, 16), ipady=12)
        self.label(current, "CURRENT SESSION", 12, BRAND["gold"], True, anchor="w", padx=18, pady=(12, 8))
        cur = load_current_session()
        if cur:
            txt = (
                f"Active: {Path(cur.get('folder','')).name}\n"
                f"Started: {cur.get('started_at','')}\n"
                f"Goal: {cur.get('goal','')}\n"
                f"Game: {display_location_game(cur.get('game', 'pokemon'))}\n"
                f"Batch Location: {cur.get('batch_location', '') or '(not set)'}\n"
                f"Planned cards: {cur.get('planned_cards','')}"
            )
        else:
            txt = "No active session."
        self.label(current, txt, 10, BRAND["muted"], False, anchor="w", padx=18, pady=(0, 10))
        btns = tk.Frame(current, bg=BRAND["panel"])
        btns.pack(anchor="w", padx=18, pady=(0, 14))
        self.action_button(btns, "Start Session", self.start_work_session).pack(side="left")
        self.action_button(btns, "End Session", self.end_current_session_ui).pack(side="left", padx=8)
        self.action_button(btns, "Split Recording", self.run_split_recording_tool).pack(side="left", padx=8)
        self.action_button(btns, "Open Sessions Folder", lambda: os.startfile(SESSIONS)).pack(side="left", padx=8)

        history = self.card(wrap, fill="both", expand=True, ipady=12)
        self.label(history, "RECENT SESSIONS", 12, BRAND["gold"], True, anchor="w", padx=18, pady=(12, 8))
        sessions = latest_sessions(8)
        if not sessions:
            self.label(history, "No sessions recorded yet.", 10, BRAND["muted"], False, anchor="w", padx=18, pady=4)
        for s in sessions:
            summary = s.name
            meta = s / "session.json"
            if meta.exists():
                try:
                    d = json.loads(meta.read_text(encoding="utf-8-sig"))
                    summary += (
                        f"  |  goal: {d.get('goal','')}"
                        f"  |  location: {d.get('batch_location','') or '(none)'}"
                        f"  |  cards: {d.get('completed_cards','') or d.get('planned_cards','')}"
                    )
                    if d.get("pricing_jobs"):
                        summary += f"  |  pricing jobs: {len(d.get('pricing_jobs', []))}"
                except Exception:
                    pass
            row = tk.Frame(history, bg=BRAND["panel"])
            row.pack(fill="x", padx=18, pady=3)
            self.label(row, summary, 9, BRAND["muted"], False, side="left", fill="x", expand=True)
            self.action_button(row, "Open", lambda path=s: os.startfile(path)).pack(side="right")

    def content_page(self):
        self.header("Content", "Track recordings, clips, episode ideas, and publishing preparation.")
        wrap = tk.Frame(self.main, bg=BRAND["bg"])
        wrap.pack(fill="both", expand=True, padx=34, pady=0)
        row = tk.Frame(wrap, bg=BRAND["bg"])
        row.pack(fill="x", pady=(0, 16))
        self.metric_card(row, "Recordings", count_files(CONTENT_RECORDINGS, "*"), "Raw footage")
        self.metric_card(row, "Clips", count_files(CONTENT_CLIPS, "*"), "Potential shorts")
        self.metric_card(row, "Ideas", count_files(CONTENT_IDEAS, "*"), "Backlog")
        self.metric_card(row, "Episodes", count_files(CONTENT_EPISODES, "*"), "Planned videos")
        panel = self.card(wrap, fill="x", ipady=12)
        self.label(panel, "QUICK ACTIONS", 12, BRAND["gold"], True, anchor="w", padx=18, pady=(12, 8))
        btns = tk.Frame(panel, bg=BRAND["panel"])
        btns.pack(anchor="w", padx=18, pady=(0, 14))
        self.action_button(btns, "Open OBS Checklist", self.open_recording_checklist).pack(side="left")
        self.action_button(btns, "Open Content Folder", lambda: os.startfile(CONTENT)).pack(side="left", padx=10)
        self.action_button(btns, "Split Recording", self.run_split_recording_tool).pack(side="left", padx=10)

    def placeholder_page(self, name):
        self.header(name, "This workspace is under active development.")
        wrap = tk.Frame(self.main, bg=BRAND["bg"])
        wrap.pack(fill="both", expand=True, padx=34, pady=0)
        panel = self.card(wrap, fill="x", ipady=18)
        self.label(panel, f"{name.upper()} WORKSPACE", 14, BRAND["gold"], True, anchor="w", padx=18, pady=(16, 6))
        self.label(panel, "This area will be built from real production bottlenecks, not guesses.", 10, BRAND["muted"], False, anchor="w", padx=18, pady=(0, 16))

    def open_recording_checklist(self):
        checklist = CONTENT / "OBS_Workflow_Recording_Checklist.txt"
        if not checklist.exists():
            checklist.write_text("""Putnam Workflow Recording Checklist

1. Open OBS.
2. Select scene: Workflow Analysis.
3. Confirm desktop capture and cameras.
4. Confirm microphone levels.
5. Start Recording.
6. Work naturally. Do not stop for mistakes.
7. Stop recording when the session is done.
8. Use Putnam Platform splitter if the file is too large.
9. Record cards completed, bottlenecks, and notes.

Goal: Capture the real listing workflow for process improvement and content creation.
""", encoding="utf-8")
        append_activity("Opened OBS recording checklist")
        try:
            os.startfile(checklist)
        except Exception:
            messagebox.showinfo("OBS Checklist", str(checklist))

    def pricing_progress_text(self, stage, current=None, total=None, elapsed=None):
        lines = [
            "Processing CardUploader export...",
            f"Stage: {stage}",
        ]
        if current is not None and total is not None:
            lines.append(f"Rows: {current} / {total}")
        if elapsed is not None:
            lines.append(f"Elapsed: {elapsed_display(elapsed)}")
        return "\n".join(lines)

    def update_pricing_progress(self, stage, percent=None, current=None, total=None):
        elapsed = None
        if self.pricing_started_at is not None:
            elapsed = time.perf_counter() - self.pricing_started_at
        try:
            if hasattr(self, "pricing_stage_var"):
                self.pricing_stage_var.set(self.pricing_progress_text(stage, current, total, elapsed))
            if percent is not None and hasattr(self, "pricing_progress_var"):
                self.pricing_progress_var.set(max(0, min(100, int(percent))))
        except Exception:
            pass
        self.status.set(stage)
        try:
            self.update_idletasks()
            self.update()
        except Exception:
            pass

    def set_pricing_busy(self, running):
        self.pricing_running = running
        if self.pricing_action_button is not None:
            try:
                self.pricing_action_button.configure(state=("disabled" if running else "normal"))
            except Exception:
                pass

    def pricing_input_messages(self):
        missing_names = []
        missing_numbers = 0
        missing_sets = 0
        for index, row in enumerate(self.rows or [], 1):
            _title, name, setname, number, _price = card_fields(row)
            if not str(name or "").strip():
                missing_names.append(index)
            if not str(number or "").strip():
                missing_numbers += 1
            if not str(setname or "").strip():
                missing_sets += 1
        warnings = []
        if missing_numbers:
            warnings.append("Card number missing; comp matching may be less precise.")
        if missing_sets:
            warnings.append("Set name missing; comp matching may be less precise.")
        return missing_names, warnings

    def set_current_pricing_job(self, job=None, export_summary=None):
        self.current_pricing_job = Path(job) if job else None
        summary = export_summary or {}
        self.current_pricing_reports = {
            "rejected": Path(summary.get("rejected_comps_path") or (self.current_pricing_job / "rejected_comps.csv" if self.current_pricing_job else "")),
            "analytics": Path(summary.get("comp_search_analytics_path") or (self.current_pricing_job / "comp_search_analytics.csv" if self.current_pricing_job else "")),
            "analytics_summary": Path(summary.get("comp_search_analytics_summary_path") or (self.current_pricing_job / "comp_search_analytics_summary.txt" if self.current_pricing_job else "")),
        } if self.current_pricing_job else {}
        try:
            self.output_path_var.set(str(self.current_pricing_job or ""))
        except Exception:
            pass

    def open_current_output_folder(self):
        if not self.current_pricing_job or not self.current_pricing_job.exists():
            self.status.set("Output folder: Not generated yet.")
            messagebox.showinfo("Putnam OS", "Output folder: Not generated yet.")
            return
        os.startfile(self.current_pricing_job)

    def copy_current_output_folder(self):
        path = str(self.current_pricing_job or "")
        if not path:
            self.status.set("Output folder: Not generated yet.")
            messagebox.showinfo("Putnam OS", "Output folder: Not generated yet.")
            return
        self.clipboard_clear()
        self.clipboard_append(path)
        self.status.set("Output folder copied.")

    def open_pricing_report(self, key, title):
        path = self.current_pricing_reports.get(key)
        if not path or not path.exists():
            self.status.set(f"{title}: Not generated yet.")
            messagebox.showinfo("Putnam OS", f"{title}: Not generated yet.")
            return
        if path.suffix.lower() == ".csv":
            self.show_csv_report(path, title)
        else:
            self.show_text_report(path, title)

    def show_text_report(self, path, title):
        win = tk.Toplevel(self)
        win.title(title)
        win.geometry("920x560")
        frame = tk.Frame(win)
        frame.pack(fill="both", expand=True)
        text = tk.Text(frame, wrap="word", font=("Consolas", 10))
        yscroll = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=yscroll.set)
        text.insert("1.0", path.read_text(encoding="utf-8-sig", errors="replace"))
        text.configure(state="disabled")
        text.pack(side="left", fill="both", expand=True)
        yscroll.pack(side="right", fill="y")

    def show_csv_report(self, path, title):
        rows = read_csv(path)
        win = tk.Toplevel(self)
        win.title(title)
        win.geometry("1180x640")
        frame = tk.Frame(win)
        frame.pack(fill="both", expand=True)
        columns = list(rows[0].keys()) if rows else []
        tree = ttk.Treeview(frame, columns=columns, show="headings")
        yscroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        xscroll = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        for column in columns:
            width = 260 if column in {"candidate_title", "rejection_details", "Search Query Used"} else 130
            tree.heading(column, text=column, command=lambda c=column: self.sort_report_tree(tree, c, False))
            tree.column(column, width=width, minwidth=90, stretch=True, anchor="w")
        for row in rows:
            tree.insert("", "end", values=[str(row.get(column, "")) for column in columns])
        tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        if not rows:
            tk.Label(win, text="No rows in this report.", font=("Segoe UI", 10)).pack(pady=8)

    def sort_report_tree(self, tree, column, reverse):
        values = []
        for item in tree.get_children(""):
            raw = tree.set(item, column)
            try:
                value = float(str(raw).replace("$", "").replace(",", ""))
            except Exception:
                value = str(raw).lower()
            values.append((value, item))
        values.sort(reverse=reverse)
        for index, (_value, item) in enumerate(values):
            tree.move(item, "", index)
        tree.heading(column, command=lambda: self.sort_report_tree(tree, column, not reverse))

    def pricing_page(self):
        self.header("Pricing", "Analyze CardUploader exports, validate pricing, and prepare upload-ready eBay CSV files.")
        wrap = tk.Frame(self.main, bg=BRAND["bg"])
        wrap.pack(fill="both", expand=True, padx=34, pady=0)
        version = self.card(wrap, fill="x", pady=(0, 12), ipady=8)
        self.label(version, COMP_UI_VERSION, 12, BRAND["gold"], True, anchor="w", padx=18, pady=(10, 2))
        self.label(version, COMP_UI_SUBTITLE, 9, BRAND["muted"], False, anchor="w", padx=18, pady=(0, 10))
        note = self.card(wrap, fill="x", pady=(0, 12), ipady=8)
        self.label(note, "FAST PATH", 11, BRAND["gold"], True, anchor="w", padx=18, pady=(10, 2))
        tk.Label(
            note,
            text="Home is now the fastest way to analyze a CardUploader export: use Analyze Latest CardUploader Export or drop the CSV there.",
            bg=BRAND["panel"],
            fg=BRAND["muted"],
            font=("Segoe UI", 9),
            justify="left",
            wraplength=920,
        ).pack(anchor="w", padx=18, pady=(0, 10))
        self.make_drop_zone(wrap, "DROP CSV HERE", self.browse)

        info = self.card(wrap, fill="x", pady=(0, 16), ipady=10)
        self.info_var = tk.StringVar(value="No CSV loaded.")
        self.label(info, "LOADED FILE", 12, BRAND["gold"], True, anchor="w", padx=18, pady=(12, 2))
        tk.Label(info, textvariable=self.info_var, bg=BRAND["panel"], fg=BRAND["muted"],
                 font=("Segoe UI", 10), justify="left", wraplength=920).pack(anchor="w", padx=18, pady=(0, 12))

        flow = self.card(wrap, fill="x", pady=(0, 16), ipady=10)
        self.label(flow, "WORKFLOW", 12, BRAND["gold"], True, anchor="w", padx=18, pady=(12, 2))
        self.flow_var = tk.StringVar(value="1. Load CSV -> 2. Validate -> 3. Price -> 4. Export")
        tk.Label(flow, textvariable=self.flow_var, bg=BRAND["panel"], fg=BRAND["muted"],
                 font=("Segoe UI", 10)).pack(anchor="w", padx=18, pady=(0, 12))

        progress = self.card(wrap, fill="x", pady=(0, 16), ipady=10)
        self.label(progress, "PROGRESS", 12, BRAND["gold"], True, anchor="w", padx=18, pady=(12, 2))
        self.pricing_stage_var = tk.StringVar(value="No pricing run active.")
        self.pricing_progress_var = tk.DoubleVar(value=0)
        tk.Label(
            progress,
            textvariable=self.pricing_stage_var,
            bg=BRAND["panel"],
            fg=BRAND["muted"],
            font=("Segoe UI", 10),
            justify="left",
        ).pack(anchor="w", padx=18, pady=(0, 8))
        ttk.Progressbar(
            progress,
            variable=self.pricing_progress_var,
            maximum=100,
            mode="determinate",
        ).pack(fill="x", padx=18, pady=(0, 12))

        actions = tk.Frame(wrap, bg=BRAND["bg"])
        actions.pack(fill="x", pady=(2, 12))
        tk.Button(actions, text="Analyze & Prepare eBay CSV", bg=BRAND["blue"], fg="white",
                  activebackground=BRAND["blue2"], relief="flat", font=("Segoe UI", 12, "bold"),
                  padx=18, pady=12, command=self.auto_run).pack(side="left")
        self.action_button(actions, "Open Completed Jobs", lambda: os.startfile(COMPLETED)).pack(side="left", padx=12)
        self.action_button(actions, "Open Incoming Files", lambda: os.startfile(INCOMING)).pack(side="left")
        self.pricing_action_button = actions.winfo_children()[0]

        reports = self.card(wrap, fill="x", pady=(0, 16), ipady=10)
        self.label(reports, "COMP REPORTS", 12, BRAND["gold"], True, anchor="w", padx=18, pady=(12, 6))
        report_buttons = tk.Frame(reports, bg=BRAND["panel"])
        report_buttons.pack(anchor="w", padx=18, pady=(0, 10))
        self.action_button(report_buttons, "Open Rejected Comps", lambda: self.open_pricing_report("rejected", "Rejected Comps")).pack(side="left")
        self.action_button(report_buttons, "Open Search Analytics", lambda: self.open_pricing_report("analytics", "Comp Search Analytics")).pack(side="left", padx=8)
        self.action_button(report_buttons, "Open Analytics Summary", lambda: self.open_pricing_report("analytics_summary", "Comp Search Analytics Summary")).pack(side="left")
        output_row = tk.Frame(reports, bg=BRAND["panel"])
        output_row.pack(fill="x", padx=18, pady=(0, 12))
        self.output_path_var = tk.StringVar(value=str(self.current_pricing_job or ""))
        tk.Label(output_row, text="Output folder:", bg=BRAND["panel"], fg=BRAND["muted"],
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        output_entry = tk.Entry(output_row, textvariable=self.output_path_var, bg=BRAND["panel2"], fg=BRAND["text"],
                                relief="flat", readonlybackground=BRAND["panel2"])
        output_entry.configure(state="readonly")
        output_entry.pack(side="left", fill="x", expand=True, padx=8)
        self.action_button(output_row, "Copy", self.copy_current_output_folder).pack(side="left")
        self.action_button(output_row, "Open Output Folder", self.open_current_output_folder).pack(side="left", padx=(8, 0))
        self.result_var = tk.StringVar(value="")
        tk.Label(wrap, textvariable=self.result_var, bg=BRAND["bg"], fg=BRAND["muted"],
                 font=("Segoe UI", 10), justify="left", wraplength=960).pack(anchor="w", pady=(4, 0))

    def browse(self):
        p = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if not p:
            return
        self.load(p)

    def load(self, p):
        self.loaded = Path(p)
        self.rows = read_csv(p)
        self.detected = detect_type(self.rows)
        self.set_current_pricing_job(None)
        try:
            self.info_var.set(f"{self.loaded.name}\nDetected: {self.detected}\nRows: {len(self.rows)}")
            if hasattr(self, "pricing_stage_var"):
                self.pricing_stage_var.set("CSV loaded. Ready to analyze.")
            if hasattr(self, "pricing_progress_var"):
                self.pricing_progress_var.set(0)
            if hasattr(self, "result_var"):
                self.result_var.set("")
        except Exception:
            pass
        self.status.set("CSV loaded. Ready to analyze.")

    def prompt_listing_export_batch(self, game_hint=None):
        cur = load_current_session()
        if cur and cur.get("batch_location"):
            default = cur.get("batch_location")
            game_hint = cur.get("game") or game_hint
        else:
            default = suggest_next_location(game_hint or "pokemon", root=ROOT)
        value = simpledialog.askstring(
            "Listing Optimizer v1.2",
            "User SKU = Batch Location.\n\n"
            f"Game/category: {display_location_game(game_hint or 'pokemon')}\n"
            f"Suggested batch location: {default}\n\n"
            "Override if needed:",
            initialvalue=default,
        )
        if not value:
            return ""
        return validate_location(value)

    def confirm_listing_export_step(self, _phase, message):
        return messagebox.askyesno("Putnam OS Listing Optimizer v1.2", message)

    def auto_run(self):
        if self.pricing_running:
            return
        if not self.loaded:
            self.browse()
            if not self.loaded:
                return
        self.pricing_started_at = time.perf_counter()
        self.set_pricing_busy(True)
        try:
            self.set_current_pricing_job(None)
            self.update_pricing_progress("Loading", percent=5, current=0, total=len(self.rows or []))
            if hasattr(self, "result_var"):
                self.result_var.set("")
            if hasattr(self, "flow_var"):
                self.flow_var.set("Loading -> Validating -> Pricing -> Confirming -> Writing output -> Complete")
            self.status.set("Loading.")
            if self.detected == "carduploader_new":
                self.update_pricing_progress("Validating", percent=15, current=0, total=len(self.rows))
                missing_names, validation_warnings = self.pricing_input_messages()
                if missing_names:
                    message = "Card name is required."
                    if len(missing_names) <= 5:
                        message += f"\nRows missing card name: {', '.join(str(i) for i in missing_names)}"
                    else:
                        message += f"\nRows missing card name: {len(missing_names)} rows."
                    self.update_pricing_progress("Card name is required.", percent=0)
                    self.status.set("Card name is required.")
                    append_pricing_performance_log(
                        pricing_performance_record(
                            self.loaded,
                            row_count=len(self.rows or []),
                            started_at=self.pricing_started_at,
                            status="validation_error",
                        )
                    )
                    messagebox.showerror("Putnam OS", message)
                    return
                if validation_warnings:
                    warning_text = "\n".join(dict.fromkeys(validation_warnings))
                    self.status.set(warning_text)
                    messagebox.showwarning("Putnam OS", warning_text)
                game_hint = infer_game_from_rows(self.rows)
                self.update_pricing_progress("Confirming", percent=25, current=len(self.rows), total=len(self.rows))
                batch_location = self.prompt_listing_export_batch(game_hint)
                if not batch_location:
                    raise ExportCancelled("Export canceled because batch/location was blank.")
                self.update_pricing_progress("Confirming", percent=30, current=len(self.rows), total=len(self.rows))
                job, rows, changes, opp, export_summary = audit_new_listing(
                    self.loaded,
                    use_market=True,
                    batch_location=batch_location,
                    game=game_hint,
                    confirm_callback=self.confirm_listing_export_step,
                    progress_callback=self.update_pricing_progress,
                )
                total_runtime = export_summary.get("total_runtime_seconds")
                runtime_text = elapsed_display(total_runtime) if total_runtime is not None else ""
                accepted = int(export_summary.get("comp_total_accepted") or 0)
                rejected = int(export_summary.get("comp_total_rejected") or 0)
                self.set_current_pricing_job(job, export_summary)
                self.update_pricing_progress("Complete", percent=100, current=rows, total=rows)
                comp_status = f"Search complete: {accepted} accepted, {rejected} rejected."
                if accepted == 0:
                    comp_status += "\nNo accepted comps found. Review rejected comps report for details."
                    comp_status += "\nNo pricing data available for this card. See rejected comps for explanation."
                try:
                    self.flow_var.set(f"OK Loaded {rows} rows -> OK Optimized pricing -> OK Confirmed policies -> OK Output ready")
                    self.result_var.set(
                        f"{comp_status}\n"
                        f"Complete.\nRows: {rows}\nOptimized price changes: {changes}\n"
                        f"Cart sweeteners: {export_summary['cart_sweetener_count']}\n"
                        f"Market opportunities: {opp}\n"
                        f"Runtime: {runtime_text or 'n/a'}\n"
                        f"Output: {job}"
                    )
                except Exception:
                    pass
                self.status.set(comp_status.replace("\n", " "))
                messagebox.showinfo(
                    "Putnam OS",
                    f"Analysis complete.\nRows: {rows}\nOptimized price changes: {changes}\n"
                    f"Cart sweeteners: {export_summary['cart_sweetener_count']}\n"
                    f"Market opportunities: {opp}\n"
                    f"{comp_status}\n"
                    f"Runtime: {runtime_text or 'n/a'}\n\nOutput folder:\n{job}"
                )
                os.startfile(job)
            else:
                append_pricing_performance_log(
                    pricing_performance_record(
                        self.loaded,
                        row_count=len(self.rows or []),
                        started_at=self.pricing_started_at,
                        status="unsupported_type",
                    )
                )
                messagebox.showwarning("Putnam OS", "This workflow currently analyzes CardUploader new-listing CSVs. Existing listing revision support remains available through the pricing engine.")
        except ExportCancelled as e:
            self.update_pricing_progress("Canceled", percent=0)
            self.status.set("Export canceled.")
            append_pricing_performance_log(
                pricing_performance_record(
                    self.loaded,
                    row_count=len(self.rows or []),
                    started_at=self.pricing_started_at,
                    output_folder=self.current_pricing_job or "",
                    status="canceled",
                )
            )
            messagebox.showinfo("Putnam OS", str(e))
        except Exception as e:
            self.update_pricing_progress("Error", percent=0)
            self.status.set(f"Error: {e}")
            append_pricing_performance_log(
                pricing_performance_record(
                    self.loaded,
                    row_count=len(self.rows or []),
                    started_at=self.pricing_started_at,
                    output_folder=self.current_pricing_job or "",
                    status="error",
                )
            )
            append_ui_bugfix_log(f"Runtime UI error: {e}")
            messagebox.showerror("Putnam OS", str(e))
        finally:
            self.set_pricing_busy(False)
            self.pricing_started_at = None


if __name__ == "__main__":
    append_activity(f"Putnam OS launched v{APP_VERSION}")
    PutnamOS().mainloop()

