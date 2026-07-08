import csv, json, os, shutil, sys, webbrowser, statistics, re, urllib.parse, urllib.request, subprocess, importlib.util, traceback
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from io import BytesIO
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
    DATA_CONFIG_DIR,
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

APP_VERSION = "1.2.2"
PLATFORM_VERSION = "CardVector Platform v1.2.2"
APP_NAME = "CardVector OS"
FLOOR = 0.99
REVIEW_THRESHOLD = 20.00

LISTING_OPTIMIZER_VERSION = "1.2"
COMP_ENGINE_VERSION = "CardVector Pricing Engine v1.2"
COMP_ENGINE_SUBTITLE = "Search Analytics + Explainable Rejections"
COMP_UI_VERSION = "CardVector Pricing Engine UI v1.2.1"
COMP_UI_SUBTITLE = "UI Bug Fix Patch"
EXPORT_FLOOR_PRICE = Decimal("0.99")
SHIPPING_POLICY_DEFAULT = ""
PAYMENT_POLICY_DEFAULT = ""
RETURN_POLICY_DEFAULT = ""
PROMOTION_POLICY_DEFAULT = "Free Shipping on 3+ Cards"

BRAND = {
    "bg": "#070B12",
    "panel": "#0D1420",
    "panel2": "#121C2B",
    "panel_hover": "#182437",
    "panel_tint": "#1F1B12",
    "sidebar": "#05080E",
    "sidebar_hover": "#111927",
    "toolbar": "#090F18",
    "statusbar": "#05080E",
    "border": "#263244",
    "border_soft": "#1A2433",
    "border_accent": "#9B7A32",
    "blue": "#2563EB",
    "blue2": "#3B82F6",
    "blue_dark": "#1D4ED8",
    "gold": "#D6A935",
    "gold_soft": "#E7C66A",
    "gold_dark": "#9B7A32",
    "bronze": "#B68A35",
    "bronze_hover": "#2A2113",
    "text": "#F4F7FB",
    "muted": "#A9B7CB",
    "muted2": "#73839A",
    "success": "#22C55E",
    "warning": "#FACC15",
    "danger": "#EF4444",
    "inactive": "#64748B",
    "disabled": "#334155",
    "table_even": "#0D1420",
    "table_odd": "#101A28",
    "table_hover": "#172338",
    "table_selected": "#262114",
}

FONT_FAMILY = "Segoe UI Variable"
FONT_FALLBACKS = ["Segoe UI", "Arial"]
FONT_SIZES = {
    "app_title": 22,
    "page_title": 22,
    "section": 11,
    "body": 10,
    "label": 9,
    "button": 10,
    "small": 8,
    "metric": 22,
}
SPACING = {
    "page_x": 28,
    "page_top": 18,
    "card_pad_x": 20,
    "card_title_top": 14,
    "card_gap": 14,
    "button_pad_x": 13,
    "button_pad_y": 6,
    "toolbar_height": 42,
    "sidebar_width": 255,
}

STATUS_COLORS = {
    "success": BRAND["success"],
    "ready": BRAND["success"],
    "connected": BRAND["success"],
    "active": BRAND["bronze"],
    "working": BRAND["bronze"],
    "current": BRAND["bronze"],
    "warning": BRAND["warning"],
    "waiting": BRAND["warning"],
    "review": BRAND["warning"],
    "error": BRAND["danger"],
    "failed": BRAND["danger"],
    "disconnected": BRAND["danger"],
    "inactive": BRAND["inactive"],
    "unknown": BRAND["inactive"],
    "disabled": BRAND["inactive"],
}

NAV_ICONS = {
    "Home": "[H]",
    "Capture": "[C]",
    "Import": "[I]",
    "Pricing": "[$]",
    "Inventory": "[N]",
    "Orders": "[O]",
    "Shipping": "[S]",
    "Content": "[T]",
    "Analytics": "[A]",
    "Sessions": "[W]",
    "Settings": "[G]",
}

BUTTON_ICONS = {
    "Analyze": "[>]",
    "Analyze & Prepare eBay CSV": "[>]",
    "Analyze Latest Export": "[>]",
    "Attach Current Session": "[+]",
    "Back": "[<]",
    "Browse CSV": "[...]",
    "Browse for CSV": "[...]",
    "Browse": "[...]",
    "Capture": "[C]",
    "Check OBS Status": "[?]",
    "Continue to Pricing": "[>]",
    "Copy": "[#]",
    "Create Acquisition": "[+]",
    "Create Next ETB": "[+]",
    "Finish Session": "[x]",
    "Generate Labels": "[#]",
    "Generate Reports": "[#]",
    "Import CardUploader CSV": "[I]",
    "Import eBay Orders CSV": "[I]",
    "Import Latest CardUploader Export": "[I]",
    "Import Latest Export": "[I]",
    "Mark Confirmed": "[+]",
    "Needs Review": "[!]",
    "Next": "[>]",
    "No Acquisition": "[-]",
    "Open": "[O]",
    "Open Audit Folder": "[O]",
    "Open Capture": "[O]",
    "Open Capture Folder": "[O]",
    "Open CardUploader": "[O]",
    "Open Completed Jobs": "[O]",
    "Open Content Folder": "[O]",
    "Open Exports": "[O]",
    "Open Imports": "[O]",
    "Open Incoming Files": "[O]",
    "Open Label Folder": "[O]",
    "Open Output Folder": "[O]",
    "Open Pick Slip Folder": "[O]",
    "Open Pricing Output": "[O]",
    "Open Pricing Output Folder": "[O]",
    "Open Printable Pick Slips": "[O]",
    "Open Session Folder": "[O]",
    "Open Sessions Folder": "[O]",
    "Previous": "[<]",
    "Refresh Counts": "[R]",
    "Resume Audit": "[R]",
    "Retake Last": "[R]",
    "Retry": "[R]",
    "Return Home": "[H]",
    "Save": "[S]",
    "Save Auto Settings": "[S]",
    "Save CardUploader URL": "[S]",
    "Save eBay Policies": "[S]",
    "Save OBS Settings": "[S]",
    "Save Progress": "[S]",
    "Select Acquisition": "[+]",
    "Skip": "[>]",
    "Start Capture Session": "[+]",
    "Start New Audit": "[+]",
    "Start Session": "[+]",
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
ACQUISITIONS_DIR = DATA / "acquisitions"
ACQUISITIONS_RECORDS_DIR = ACQUISITIONS_DIR / "records"
CURRENT_ACQUISITION_PATH = ACQUISITIONS_DIR / "current_acquisition.json"
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
IMPORT_MODULE_STATE = DATA_CONFIG_DIR / "import_module_state.json"
EBAY_BUSINESS_POLICIES_CONFIG = CONFIG / "ebay_business_policies.json"
APP_CONFIG_PATH = CONFIG / "putnam_os_config.json"
AUTO_CAPTURE_CONFIG = CONFIG / "auto_capture_settings.json"
UI_BUGFIX_LOG = DATA_LOGS_DIR / "ui_bugfix_log.txt"
CARDUPLOADER_INVENTORY_IMPORTS = IMPORTS / "CardUploader_Inventory"
SESSIONS = ROOT_SESSIONS
STARTUP_LOGS = LOGS / "Startup Logs"

PLATFORM = PUTNAM_PLATFORM_DIR
TOOLS = PLATFORM / "tools"
UTILITIES = PLATFORM / "utilities"
INSTALLERS = PLATFORM / "installers"

CONTENT = ROOT / "Putnam_Content"
CONTENT_IDEAS = CONTENT / "Ideas"
CONTENT_RECORDINGS = CONTENT / "Recordings"
CONTENT_CLIPS = CONTENT / "Clips"
CONTENT_EPISODES = CONTENT / "Episodes"

for p in [OS_DIR, SYSTEM, APP_DIR, CONFIG, LOGS, CACHE, DATA, ACQUISITIONS_DIR, ACQUISITIONS_RECORDS_DIR, INCOMING, COMPLETED,
          IMPORTS, CARDUPLOADER_INVENTORY_IMPORTS, EXPORTS, MEDIA, COLLECTR, ROOT_SESSIONS, ARCHIVE, DOCS, ROOT_LOGS,
          DATA_CONFIG_DIR, STARTUP_LOGS,
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
from capture_studio import CAPTURE_ROOT, OBS_CONFIG_PATH, CaptureStudioError, CaptureStudioService, load_obs_config, save_obs_config
from inventory_locations import (
    ETB_LOCATION_REGISTRY,
    LOCATION_STATUSES,
    create_etb_location,
    etb_location_rows,
    next_etb_code,
    update_etb_status,
)
from orders_fulfillment import PICK_LIST_ROOT, generate_pick_slips


LABEL_GENERATOR_SCRIPT = SYSTEM / "tools" / "generate_etb_qr_labels.py"
LABEL_EXPORT_ROOT = DATA_EXPORTS_DIR / "Labels"
LABEL_GENERATION_LOG = DATA_LOGS_DIR / "label_generation_log.txt"


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
        "Decision Engine Status",
        f"Business Goal: {result.get('business_goal', '')}",
        f"Modules Loaded: {result.get('modules_loaded', 0)}",
        f"Modules Pending: {placeholders}",
        f"Last Evaluation: {result.get('last_engine_check', '') or 'not run'}",
    ]
    if errors:
        lines.append(f"Errors: {errors}")
    for note in result.get("notes", []):
        lines.append(f"Note: {note}")
    return "\n".join(lines)


def latest_decision_log():
    try:
        logs = sorted((LOGS).glob("decision_engine_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        return logs[0] if logs else None
    except Exception:
        return None


def load_app_config():
    defaults = {"carduploader_url": ""}
    if not APP_CONFIG_PATH.exists():
        return defaults
    try:
        data = json.loads(APP_CONFIG_PATH.read_text(encoding="utf-8-sig"))
    except Exception:
        return defaults
    section = data.get("putnam_os", data) if isinstance(data, dict) else {}
    if not isinstance(section, dict):
        return defaults
    defaults["carduploader_url"] = str(section.get("carduploader_url", "") or "").strip()
    return defaults


def save_app_config(values):
    APP_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = {"putnam_os": {"carduploader_url": str(values.get("carduploader_url", "") or "").strip()}}
    APP_CONFIG_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


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


def payment_policy_column(fieldnames):
    exact = find_column(
        fieldnames,
        [
            "*PaymentProfileName",
            "PaymentProfileName",
            "Payment policy",
            "Payment Policy",
            "Payment profile",
            "Payment Profile",
        ],
    )
    if exact:
        return exact
    for name in fieldnames:
        norm = name.lower()
        if "payment" in norm and ("policy" in norm or "profile" in norm):
            return name
    return None


def return_policy_column(fieldnames):
    exact = find_column(
        fieldnames,
        [
            "*ReturnProfileName",
            "ReturnProfileName",
            "Return policy",
            "Return Policy",
            "Return profile",
            "Return Profile",
        ],
    )
    if exact:
        return exact
    for name in fieldnames:
        norm = name.lower()
        if "return" in norm and ("policy" in norm or "profile" in norm):
            return name
    return None


def promotion_policy_column(fieldnames):
    for name in fieldnames:
        norm = name.lower()
        if "promotion" in norm and ("policy" in norm or "profile" in norm or "name" in norm):
            return name
    return None


def load_ebay_business_policies():
    defaults = {
        "shipping_policy": SHIPPING_POLICY_DEFAULT,
        "payment_policy": PAYMENT_POLICY_DEFAULT,
        "return_policy": RETURN_POLICY_DEFAULT,
    }
    if not EBAY_BUSINESS_POLICIES_CONFIG.exists():
        return defaults
    try:
        data = json.loads(EBAY_BUSINESS_POLICIES_CONFIG.read_text(encoding="utf-8-sig"))
    except Exception:
        return defaults
    section = data.get("ebay_business_policies", data) if isinstance(data, dict) else {}
    if not isinstance(section, dict):
        return defaults
    for key in defaults:
        value = str(section.get(key, defaults[key]) or "").strip()
        defaults[key] = value
    return defaults


def save_ebay_business_policies(policies):
    EBAY_BUSINESS_POLICIES_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "ebay_business_policies": {
            "shipping_policy": str(policies.get("shipping_policy", "") or "").strip(),
            "payment_policy": str(policies.get("payment_policy", "") or "").strip(),
            "return_policy": str(policies.get("return_policy", "") or "").strip(),
        }
    }
    EBAY_BUSINESS_POLICIES_CONFIG.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def validate_ebay_business_policies(policies):
    required = {
        "shipping_policy": "shipping policy",
        "payment_policy": "payment policy",
        "return_policy": "return policy",
    }
    missing = [label for key, label in required.items() if not str(policies.get(key, "") or "").strip()]
    if missing:
        raise ExportCancelled(
            "eBay export stopped because required business policy values are missing: "
            + ", ".join(missing)
            + f". Configure them in Settings or {EBAY_BUSINESS_POLICIES_CONFIG}."
        )


def ensure_policy_column(row, existing_column, default_column):
    if existing_column:
        return existing_column
    row.setdefault(default_column, "")
    return default_column


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


def summarize_final_prices(final_prices, batch_location, output_csv_path, policies):
    total = len(final_prices)
    avg = (sum(final_prices, Decimal("0.00")) / Decimal(total)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    min_price = min(final_prices).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    max_price = max(final_prices).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    cart_sweeteners = sum(1 for price in final_prices if price <= Decimal("0.99"))
    return {
        "batch_location": batch_location,
        "total_listings": total,
        "shipping_policy": policies["shipping_policy"],
        "payment_policy": policies["payment_policy"],
        "return_policy": policies["return_policy"],
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


def prepare_listing_export_rows(rows, batch_location, policies=None, progress_callback=None):
    if not rows:
        raise ValueError("Input CSV has no data rows.")
    fieldnames = list(rows[0].keys())
    pcol = price_column(fieldnames)
    if not pcol:
        raise ValueError("Could not find an eBay price column such as *StartPrice.")

    batch_cols = batch_location_columns(fieldnames)
    ship_col = shipping_policy_column(fieldnames)
    pay_col = payment_policy_column(fieldnames)
    ret_col = return_policy_column(fieldnames)
    promo_col = promotion_policy_column(fieldnames)
    original_price_col = find_column(fieldnames, ["original_market_price", "Original Market Price", "OriginalMarketPrice"])
    policies = policies or load_ebay_business_policies()
    validate_ebay_business_policies(policies)

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
        ship_col = ensure_policy_column(r, ship_col, "*ShippingProfileName")
        pay_col = ensure_policy_column(r, pay_col, "*PaymentProfileName")
        ret_col = ensure_policy_column(r, ret_col, "*ReturnProfileName")
        if ship_col:
            r[ship_col] = policies["shipping_policy"]
        if pay_col:
            r[pay_col] = policies["payment_policy"]
        if ret_col:
            r[ret_col] = policies["return_policy"]
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
    return out_rows, review_rows, final_prices, price_changes, batch_cols, ship_col, pay_col, ret_col, promo_col


def export_summary_text(summary):
    acquisition = current_acquisition()
    acquisition_lines = ""
    if acquisition:
        acquisition_lines = (
            "\nAcquisition:\n"
            f"Acquisition ID: {acquisition.get('acquisition_id', '')}\n"
            f"Acquisition name: {acquisition.get('acquisition_name', '')}\n"
            f"Purchase price: ${acquisition.get('purchase_price', '0.00')}\n"
            f"Estimated listing value this export: ${summary.get('estimated_listing_value', '0.00')}\n"
        )
    return (
        "CardVector OS Pricing & Decisions\n\n"
        "User SKU = Batch Location\n"
        f"Total listings: {summary['total_listings']}\n"
        f"Batch/location: {summary['batch_location']}\n"
        f"Shipping policy: {summary['shipping_policy']}\n"
        f"Payment policy: {summary['payment_policy']}\n"
        f"Return policy: {summary['return_policy']}\n"
        f"Promotion policy: {summary['promotion_policy']}\n"
        f"Cart sweeteners: {summary['cart_sweetener_count']}\n"
        f"Average final export price: ${summary['average_final_price']}\n"
        f"Minimum final export price: ${summary['min_final_price']}\n"
        f"Maximum final export price: ${summary['max_final_price']}\n"
        f"{acquisition_lines}\n"
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
        "payment_policy",
        "return_policy",
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
                "payment_policy": summary["payment_policy"],
                "return_policy": summary["return_policy"],
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


def current_workflow_stage():
    cur = load_current_session()
    if cur:
        return "Capture"
    if latest_carduploader_export():
        return "Import"
    if latest_completed_job():
        return "Upload"
    return "Capture"


def next_recommended_action():
    stage = current_workflow_stage()
    if stage == "Capture":
        return "Open Capture and collect the next front/back photo pair."
    if stage == "Import":
        return "Import the latest CardUploader CSV, then continue to Pricing."
    if stage == "Upload":
        return "Review the pricing output, then upload through CardUploader/eBay."
    return "Start with Capture."


def latest_capture_session():
    try:
        folders = [p for p in CAPTURE_ROOT.iterdir() if p.is_dir()]
        if not folders:
            return None

        def session_mtime(folder):
            mtimes = []
            try:
                mtimes.append(folder.stat().st_mtime)
            except OSError:
                pass
            for pattern in ("*.jpg", "*.jpeg", "capture_session.json"):
                for path in folder.glob(pattern):
                    try:
                        if path.is_file():
                            mtimes.append(path.stat().st_mtime)
                    except OSError:
                        pass
            return max(mtimes) if mtimes else 0

        return max(folders, key=session_mtime)
    except Exception:
        return None


def resolve_capture_path(value, session_folder=None):
    raw = str(value or "").strip()
    if not raw:
        return None
    path = Path(raw)
    candidates = []
    if path.is_absolute():
        candidates.append(path)
        parts = path.parts
        if "Capture" in parts:
            capture_index = parts.index("Capture")
            candidates.append(CAPTURE_ROOT.joinpath(*parts[capture_index + 1:]))
    else:
        if session_folder:
            candidates.append(Path(session_folder) / path)
        candidates.append(CAPTURE_ROOT / path)
        candidates.append(ROOT / path)
    for candidate in candidates:
        try:
            if candidate.exists():
                return candidate
        except OSError:
            continue
    return candidates[0] if candidates else path


def load_capture_session_file(folder):
    session_path = Path(folder) / "capture_session.json"
    if not session_path.exists():
        return {}
    try:
        data = json.loads(session_path.read_text(encoding="utf-8-sig"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def capture_session_summary(limit=8):
    folder = latest_capture_session()
    if not folder:
        return None
    images = sorted(
        [p for p in folder.glob("*.jpg") if p.is_file()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    ordered = list(reversed(images))
    pair_count = 0
    incomplete_pairs = 0
    for idx in range(0, len(ordered), 2):
        pair = ordered[idx:idx + 2]
        if len(pair) == 2:
            pair_count += 1
        elif pair:
            incomplete_pairs += 1
    next_side = "front" if len(ordered) % 2 == 0 else "back"
    return {
        "folder": folder,
        "count": len(images),
        "recent": [p.name for p in images[:limit]],
        "recent_paths": images[:limit],
        "pair_count": pair_count,
        "incomplete_pairs": incomplete_pairs,
        "next_side": next_side,
        "session_updated": datetime.fromtimestamp(folder.stat().st_mtime).isoformat(timespec="seconds"),
    }


def capture_pair_rows(folder=None, limit=24):
    session_folder = Path(folder) if folder else latest_capture_session()
    if not session_folder or not session_folder.exists():
        return []
    pairs = {}
    session_data = load_capture_session_file(session_folder)
    session_records = session_data.get("records", [])
    if not isinstance(session_records, list):
        session_records = []
    for record in session_records:
        side = str(record.get("side", "")).lower()
        if side not in {"front", "back"}:
            continue
        try:
            number = int(record.get("card_number") or 0)
        except Exception:
            number = 0
        if number <= 0:
            match = re.match(r"^(\d{6})_(front|back)\.jpe?g$", str(record.get("filename", "")), re.IGNORECASE)
            number = int(match.group(1)) if match else 0
        image = resolve_capture_path(record.get("path") or record.get("filename"), session_folder)
        if number > 0 and image:
            item = pairs.setdefault(number, {"pair_number": number, "front": None, "back": None, "timestamp": ""})
            item[side] = image
    images = []
    for pattern in ("*.jpg", "*.jpeg"):
        images.extend([p for p in session_folder.glob(pattern) if p.is_file()])
    for image in images:
        match = re.match(r"^(\d{6})_(front|back)\.jpe?g$", image.name, re.IGNORECASE)
        if not match:
            continue
        number = int(match.group(1))
        side = match.group(2).lower()
        item = pairs.setdefault(number, {"pair_number": number, "front": None, "back": None, "timestamp": ""})
        item[side] = image
    rows = []
    for number, item in pairs.items():
        paths = [p for p in [item.get("front"), item.get("back")] if p]
        if not paths:
            continue
        mtimes = []
        for path in paths:
            try:
                mtimes.append(path.stat().st_mtime if path.exists() else 0)
            except OSError:
                mtimes.append(0)
        latest_mtime = max(mtimes) if mtimes else 0
        status = "Complete" if item.get("front") and item.get("back") else "Waiting for Back" if item.get("front") else "Needs Front"
        rows.append({
            "pair_number": number,
            "front": item.get("front"),
            "back": item.get("back"),
            "timestamp": datetime.fromtimestamp(latest_mtime).strftime("%H:%M:%S"),
            "latest_mtime": latest_mtime,
            "status": status,
        })
    sorted_rows = sorted(rows, key=lambda row: row["latest_mtime"], reverse=True)[:limit]
    for idx, row in enumerate(sorted_rows):
        row["latest"] = idx == 0
    return sorted_rows


def build_capture_thumbnail_image(path, size=(96, 70)):
    from PIL import Image, ImageOps

    image_path = resolve_capture_path(path)
    if not image_path or not image_path.exists():
        raise FileNotFoundError(f"Capture image not found: {path}")
    with Image.open(image_path) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
    resampling = getattr(getattr(Image, "Resampling", Image), "LANCZOS", Image.BICUBIC)
    image.thumbnail(size, resampling)
    canvas_image = Image.new("RGB", size, "#132238")
    offset = ((size[0] - image.width) // 2, (size[1] - image.height) // 2)
    canvas_image.paste(image, offset)
    return canvas_image


def capture_pair_status(session):
    if not session:
        return "Ready"
    records = session.get("records") or []
    if not records:
        return "Ready"
    last_side = str(records[-1].get("side", "")).lower()
    if last_side == "front":
        return "Waiting for Back"
    if last_side == "back":
        return "Ready for Next Card"
    return "Ready"


def capture_cards_completed(session):
    if not session:
        return 0
    folder = resolve_capture_path(session.get("folder", "")) or Path(session.get("folder", ""))
    return sum(1 for row in capture_pair_rows(folder, limit=9999) if row["status"] == "Complete")


def obs_status_is_connected(status_text):
    text = str(status_text or "").lower()
    if "disconnected" in text or "not connected" in text:
        return False
    return "connected" in text and "not running" not in text and "unavailable" not in text and "auth" not in text


def icon_text(text):
    value = str(text or "")
    if value.startswith("["):
        return value
    icon = BUTTON_ICONS.get(value)
    return f"{icon} {value}" if icon else value


def nav_text(text):
    value = str(text or "")
    icon = NAV_ICONS.get(value)
    return f"{icon}  {value}" if icon else value


def status_state_from_text(text):
    value = str(text or "").lower()
    if any(token in value for token in ("error", "failed", "not connected", "disconnected", "auth failed")):
        return "error"
    if any(token in value for token in ("warning", "review", "missing", "not generated", "canceled")):
        return "warning"
    if any(token in value for token in ("loading", "validating", "pricing", "generating", "importing", "capturing", "running")):
        return "active"
    if any(token in value for token in ("waiting", "paused", "ready when", "retry")):
        return "waiting"
    if any(token in value for token in ("complete", "generated", "saved", "captured", "connected", "ready", "opened")):
        return "ready"
    return "unknown"


def load_inventory_label_generator():
    if not LABEL_GENERATOR_SCRIPT.exists():
        raise FileNotFoundError(f"Label generator not found: {LABEL_GENERATOR_SCRIPT}")
    spec = importlib.util.spec_from_file_location("cardvector_etb_qr_labels", LABEL_GENERATOR_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load CardVector label generator.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def append_label_generation_log(message, exc=None):
    LABEL_GENERATION_LOG.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{datetime.now().isoformat(timespec='seconds')} | {message}"]
    if exc is not None:
        lines.append("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)).rstrip())
    with LABEL_GENERATION_LOG.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def ensure_label_dependencies():
    missing = []
    for module_name in ("qrcode", "reportlab"):
        if importlib.util.find_spec(module_name) is None:
            missing.append(module_name)
    if missing:
        raise RuntimeError(
            "qrcode[pil] and reportlab are required for Inventory Label Center.\n\n"
            'Install with:\npy -m pip install "qrcode[pil]" reportlab'
        )


def generate_inventory_label_pdf(label_type="ETB Labels"):
    if label_type != "ETB Labels":
        raise ValueError(f"{label_type} templates are planned for a future Label Center release.")
    ensure_label_dependencies()
    generator = load_inventory_label_generator()
    try:
        labels = generator.load_locations(ROOT)
    except SystemExit as exc:
        raise RuntimeError(str(exc) or "Could not load inventory locations.") from exc
    if not labels:
        raise ValueError(
            "No inventory locations were found in the registry.\n\n"
            "Create ETB locations in the Inventory tab or use the fallback CSV template:\n"
            "Platform/Putnam_OS/System/tools/sample_etb_locations.csv"
        )
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = LABEL_EXPORT_ROOT / f"cardvector_etb_qr_labels_{timestamp}.pdf"
    try:
        pdf_path = generator.write_pdf(labels, output_path)
    except SystemExit as exc:
        raise RuntimeError(str(exc) or "Label PDF generation failed.") from exc
    return {
        "label_type": label_type,
        "count": len(labels),
        "pdf": pdf_path,
        "output_dir": LABEL_EXPORT_ROOT,
    }


AUTO_CAPTURE_DEFAULTS = {
    "auto_capture_enabled": False,
    "stability_delay_seconds": 1.0,
    "duplicate_lockout_seconds": 2.0,
    "frame_poll_interval_ms": 200,
    "sensitivity": "Medium",
}

AUTO_CAPTURE_THRESHOLDS = {
    "Low": {"present": 0.14, "empty": 0.07, "stable": 0.026, "changed": 0.085},
    "Medium": {"present": 0.10, "empty": 0.05, "stable": 0.018, "changed": 0.065},
    "High": {"present": 0.07, "empty": 0.035, "stable": 0.012, "changed": 0.045},
}


def load_auto_capture_settings():
    settings = dict(AUTO_CAPTURE_DEFAULTS)
    if AUTO_CAPTURE_CONFIG.exists():
        try:
            data = json.loads(AUTO_CAPTURE_CONFIG.read_text(encoding="utf-8-sig"))
            if isinstance(data, dict):
                settings.update({key: value for key, value in data.items() if key in settings})
        except Exception:
            pass
    return normalize_auto_capture_settings(settings)


def normalize_auto_capture_settings(settings):
    normalized = dict(AUTO_CAPTURE_DEFAULTS)
    normalized.update(settings or {})
    normalized["auto_capture_enabled"] = bool(normalized.get("auto_capture_enabled"))
    try:
        normalized["stability_delay_seconds"] = max(0.25, min(5.0, float(normalized.get("stability_delay_seconds", 1.0))))
    except Exception:
        normalized["stability_delay_seconds"] = AUTO_CAPTURE_DEFAULTS["stability_delay_seconds"]
    try:
        normalized["duplicate_lockout_seconds"] = max(0.5, min(10.0, float(normalized.get("duplicate_lockout_seconds", 2.0))))
    except Exception:
        normalized["duplicate_lockout_seconds"] = AUTO_CAPTURE_DEFAULTS["duplicate_lockout_seconds"]
    try:
        normalized["frame_poll_interval_ms"] = max(100, min(2000, int(float(normalized.get("frame_poll_interval_ms", 200)))))
    except Exception:
        normalized["frame_poll_interval_ms"] = AUTO_CAPTURE_DEFAULTS["frame_poll_interval_ms"]
    sensitivity = str(normalized.get("sensitivity", "Medium")).title()
    normalized["sensitivity"] = sensitivity if sensitivity in AUTO_CAPTURE_THRESHOLDS else "Medium"
    return normalized


def save_auto_capture_settings(settings):
    normalized = normalize_auto_capture_settings(settings)
    AUTO_CAPTURE_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    AUTO_CAPTURE_CONFIG.write_text(json.dumps(normalized, indent=2) + "\n", encoding="utf-8")
    return normalized


def capture_frame_signature(image_bytes, size=(48, 48)):
    try:
        from PIL import Image, ImageOps

        with Image.open(BytesIO(image_bytes)) as source:
            image = ImageOps.exif_transpose(source).convert("L")
        image = image.resize(size)
        pixels = tuple(image.getdata())
        return pixels
    except Exception as exc:
        raise CaptureStudioError(f"Could not analyze OBS frame: {exc}") from exc


def signature_difference(sig_a, sig_b):
    if not sig_a or not sig_b or len(sig_a) != len(sig_b):
        return 1.0
    total = sum(abs(int(a) - int(b)) for a, b in zip(sig_a, sig_b))
    return total / (len(sig_a) * 255)


def auto_capture_thresholds(settings):
    return AUTO_CAPTURE_THRESHOLDS.get(str(settings.get("sensitivity", "Medium")).title(), AUTO_CAPTURE_THRESHOLDS["Medium"])


def etb_parent_from_batch(value):
    match = re.search(r"\bETB-(\d+)(?:-[A-Z0-9]+)?\b", str(value or "").upper())
    if not match:
        return ""
    return f"ETB-{int(match.group(1)):03d}"


def completed_session_etb_rollups():
    rollups = {}
    for session_folder in latest_sessions(250):
        meta = session_folder / "session.json"
        if not meta.exists():
            continue
        try:
            data = json.loads(meta.read_text(encoding="utf-8-sig"))
        except Exception:
            continue
        batch = data.get("batch_location", "")
        parent = etb_parent_from_batch(batch)
        if not parent:
            continue
        try:
            cards = int(str(data.get("completed_cards") or data.get("planned_cards") or "0").strip() or "0")
        except Exception:
            cards = 0
        item = rollups.setdefault(parent, {"assigned": 0, "batches": set()})
        item["assigned"] += max(0, cards)
        if batch:
            item["batches"].add(str(batch))
    for item in rollups.values():
        item["batches"] = sorted(item["batches"])
    return rollups


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
        f"CardVector OS v{APP_VERSION} - CardUploader Inventory Import",
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


CARDUPLOADER_IMPORT_REQUIRED_FIELDS = ["*Title", "*StartPrice"]


def load_import_module_state():
    try:
        return json.loads(IMPORT_MODULE_STATE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_import_module_state(state):
    IMPORT_MODULE_STATE.parent.mkdir(parents=True, exist_ok=True)
    IMPORT_MODULE_STATE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def import_last_folder():
    folder = load_import_module_state().get("last_carduploader_folder", "")
    if folder and Path(folder).exists():
        return folder
    return ""


def display_import_format(detected):
    labels = {
        "carduploader_new": "CardUploader / eBay new-listing CSV",
        "active_listings": "eBay active listings CSV",
        "unknown": "Unknown CSV format",
    }
    return labels.get(detected or "unknown", detected or "Unknown CSV format")


def missing_carduploader_import_fields(rows):
    if not rows:
        return CARDUPLOADER_IMPORT_REQUIRED_FIELDS[:]
    fieldnames = set(rows[0].keys())
    return [field for field in CARDUPLOADER_IMPORT_REQUIRED_FIELDS if field not in fieldnames]


def build_carduploader_import_summary(path, rows):
    detected = detect_type(rows)
    missing_fields = missing_carduploader_import_fields(rows)
    if not rows:
        readiness = "Not ready - CSV contains no listing rows."
    elif missing_fields:
        readiness = "Not ready - missing required CardUploader fields."
    elif detected != "carduploader_new":
        readiness = "Review needed - format is not recognized as a CardUploader listing export."
    else:
        readiness = "Ready for Listings."
    return {
        "filename": Path(path).name,
        "path": str(Path(path)),
        "detected_format": detected,
        "detected_format_label": display_import_format(detected),
        "row_count": len(rows),
        "readiness_status": readiness,
        "missing_required_fields": missing_fields,
    }


def format_carduploader_import_summary(summary):
    missing = summary.get("missing_required_fields") or []
    missing_text = ", ".join(missing) if missing else "None"
    return "\n".join([
        "Import Summary",
        f"Filename: {summary.get('filename', '')}",
        f"Detected format: {summary.get('detected_format_label', '')}",
        f"Rows: {summary.get('row_count', 0)}",
        f"Readiness: {summary.get('readiness_status', '')}",
        f"Missing required fields: {missing_text}",
        "",
        "Next step: click Proceed to Listings to open the Pricing workflow.",
    ])


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
        f"CardVector OS Inventory Audit Mode v2",
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
    policies = load_ebay_business_policies()
    validate_ebay_business_policies(policies)

    shipping_message = (
        "eBay business policy confirmation\n\n"
        f"Shipping policy: {policies['shipping_policy']}\n"
        f"Payment policy: {policies['payment_policy']}\n"
        f"Return policy: {policies['return_policy']}\n"
        f"Promotion policy: {PROMOTION_POLICY_DEFAULT}\n\n"
        "Continue with these settings?"
    )
    print("CardVector OS Pricing & Decisions")
    print(f"Batch/location: {batch_location}")
    print(f"Shipping policy: {policies['shipping_policy']}")
    print(f"Payment policy: {policies['payment_policy']}")
    print(f"Return policy: {policies['return_policy']}")
    print(f"Promotion policy: {PROMOTION_POLICY_DEFAULT}")
    if progress_callback:
        progress_callback("Confirming", percent=30, current=len(rows), total=len(rows))
    if not confirm_callback("shipping", shipping_message):
        raise ExportCancelled("Export canceled during shipping policy confirmation.")

    stamp = nowstamp()
    job = COMPLETED / f"Pricing_Analysis_{stamp}"
    ebay_ready = job / "ebay_upload_ready.csv"
    pricing_started = time.perf_counter()
    out_rows, review_rows, final_prices, changes, batch_cols, ship_col, pay_col, ret_col, promo_col = prepare_listing_export_rows(
        rows,
        batch_location,
        policies=policies,
        progress_callback=progress_callback,
    )
    pricing_time = time.perf_counter() - pricing_started
    validate_export_price_floor(final_prices)
    if progress_callback:
        progress_callback("Pricing", percent=65, current=len(rows), total=len(rows))
    export_summary = summarize_final_prices(final_prices, batch_location, ebay_ready, policies)
    export_summary["estimated_listing_value"] = format_decimal_money(sum(final_prices, Decimal("0.00")))
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
    acquisition_metadata = write_acquisition_job_metadata(job, out_rows, export_summary)
    acquisition_summary_lines = ""
    if acquisition_metadata:
        acquisition_summary_lines = (
            f"Acquisition ID: {acquisition_metadata['acquisition_id']}\n"
            f"Acquisition name: {acquisition_metadata['acquisition_name']}\n"
            f"Acquisition purchase price: ${acquisition_metadata['purchase_price']}\n"
            f"Acquisition metadata: {job / 'acquisition_metadata.json'}\n"
            f"Acquisition summary: {job / 'acquisition_summary.txt'}\n"
        )
    summary_path = job / "summary.txt"
    summary_path.write_text(
        f"CardVector OS v{APP_VERSION} - Pricing & Decisions\n"
        f"Rows: {len(rows)}\n"
        f"Optimized price changes: {changes}\n"
        f"Batch/location: {batch_location}\n"
        f"Batch/location columns updated: {', '.join(batch_cols) if batch_cols else 'none present'}\n"
        f"Shipping policy: {policies['shipping_policy']}\n"
        f"Payment policy: {policies['payment_policy']}\n"
        f"Return policy: {policies['return_policy']}\n"
        f"Promotion policy: {PROMOTION_POLICY_DEFAULT}\n"
        f"Shipping policy column: {ship_col or 'none present'}\n"
        f"Payment policy column: {pay_col or 'none present'}\n"
        f"Return policy column: {ret_col or 'none present'}\n"
        f"Promotion policy column: {promo_col or 'none present'}\n"
        f"Cart sweeteners: {export_summary['cart_sweetener_count']}\n"
        f"Average final export price: ${export_summary['average_final_price']}\n"
        f"Minimum final export price: ${export_summary['min_final_price']}\n"
        f"Maximum final export price: ${export_summary['max_final_price']}\n"
        f"Estimated listing value: ${export_summary['estimated_listing_value']}\n"
        f"{acquisition_summary_lines}"
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


def acquisition_record_path(acquisition_id):
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(acquisition_id or "").strip())[:100]
    return ACQUISITIONS_RECORDS_DIR / f"{safe}.json"


def acquisition_money_text(value):
    return format_decimal_money(decimal_money(value))


def acquisition_statuses():
    return ["open", "processing", "listed", "break_even", "closed"]


def default_acquisition_record(name="", purchase_price="", source="", seller_name="", platform="", notes=""):
    stamp = nowstamp()
    now = datetime.now().isoformat(timespec="seconds")
    purchase_date = datetime.now().strftime("%Y-%m-%d")
    return {
        "acquisition_id": f"ACQ-{stamp}",
        "acquisition_name": str(name or f"Acquisition {stamp}").strip(),
        "purchase_date": purchase_date,
        "purchase_price": acquisition_money_text(purchase_price),
        "source": str(source or "").strip(),
        "seller_name": str(seller_name or "").strip(),
        "platform": str(platform or "").strip(),
        "notes": str(notes or "").strip(),
        "created_at": now,
        "updated_at": now,
        "status": "open",
        # Future break-even tracking placeholders. These are not yet connected
        # to order/revenue accounting.
        "gross_revenue_collected": "0.00",
        "net_revenue_collected": "0.00",
        "remaining_to_break_even": acquisition_money_text(purchase_price),
        "break_even_date": "",
        "remaining_inventory_value": "0.00",
        "work_sessions": [],
        "imports": [],
        "pricing_jobs": [],
    }


def load_acquisition(acquisition_id):
    path = acquisition_record_path(acquisition_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def save_acquisition(record):
    ACQUISITIONS_RECORDS_DIR.mkdir(parents=True, exist_ok=True)
    record["purchase_price"] = acquisition_money_text(record.get("purchase_price", "0.00"))
    record["remaining_to_break_even"] = acquisition_money_text(
        Decimal(record["purchase_price"]) - decimal_money(record.get("net_revenue_collected", "0.00"))
    )
    record["updated_at"] = datetime.now().isoformat(timespec="seconds")
    path = acquisition_record_path(record.get("acquisition_id"))
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return path


def create_acquisition(name, purchase_price, source="", seller_name="", platform="", notes=""):
    record = default_acquisition_record(name, purchase_price, source, seller_name, platform, notes)
    save_acquisition(record)
    set_current_acquisition(record)
    append_activity(f"Acquisition created: {record['acquisition_name']} (${record['purchase_price']})")
    return record


def acquisition_sort_key(record):
    return str(record.get("updated_at") or record.get("created_at") or "")


def list_acquisitions(include_closed=True):
    records = []
    for path in sorted(ACQUISITIONS_RECORDS_DIR.glob("*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            continue
        if include_closed or record.get("status") != "closed":
            records.append(record)
    return sorted(records, key=acquisition_sort_key, reverse=True)


def open_acquisitions():
    return [record for record in list_acquisitions(include_closed=False) if record.get("status") in {"open", "processing"}]


def set_current_acquisition(record):
    ACQUISITIONS_DIR.mkdir(parents=True, exist_ok=True)
    if not record:
        if CURRENT_ACQUISITION_PATH.exists():
            CURRENT_ACQUISITION_PATH.unlink()
        return None
    payload = {
        "acquisition_id": record.get("acquisition_id", ""),
        "selected_at": datetime.now().isoformat(timespec="seconds"),
    }
    CURRENT_ACQUISITION_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def current_acquisition():
    if not CURRENT_ACQUISITION_PATH.exists():
        return None
    try:
        payload = json.loads(CURRENT_ACQUISITION_PATH.read_text(encoding="utf-8-sig"))
    except Exception:
        return None
    return load_acquisition(payload.get("acquisition_id"))


def acquisition_snapshot(record=None):
    record = record or current_acquisition()
    if not record:
        return {
            "acquisition_id": "",
            "acquisition_name": "",
            "purchase_price_snapshot": "",
        }
    return {
        "acquisition_id": record.get("acquisition_id", ""),
        "acquisition_name": record.get("acquisition_name", ""),
        "purchase_price_snapshot": record.get("purchase_price", "0.00"),
    }


def acquisition_display_text(record=None):
    record = record or current_acquisition()
    if not record:
        return "Current acquisition: No Acquisition\nIntake can continue without acquisition metadata."
    sessions = record.get("work_sessions", [])
    imports = record.get("imports", [])
    cards_processed = sum(int(item.get("row_count") or 0) for item in imports)
    estimated_value = sum(decimal_money(item.get("estimated_listing_value", "0.00")) for item in imports)
    return (
        f"Current acquisition: {record.get('acquisition_name', '')}\n"
        f"ID: {record.get('acquisition_id', '')}\n"
        f"Purchase price: ${record.get('purchase_price', '0.00')}\n"
        f"Source: {record.get('source', '') or '(not set)'}\n"
        f"Status: {record.get('status', 'open')}\n"
        f"Work sessions attached: {len(sessions)}\n"
        f"Cards processed: {cards_processed}\n"
        f"Estimated listing value: ${format_decimal_money(estimated_value)}\n"
        f"Next action: Capture/import cards, then run Pricing & Decisions."
    )


def attach_work_session_to_acquisition(session_data, acquisition=None):
    acquisition = acquisition or current_acquisition()
    if not session_data or not acquisition:
        return session_data
    snapshot = acquisition_snapshot(acquisition)
    session_data.update(snapshot)
    entry = {
        "session_id": session_data.get("session_id", ""),
        "folder": session_data.get("folder", ""),
        "batch_location": session_data.get("batch_location", ""),
        "attached_at": datetime.now().isoformat(timespec="seconds"),
    }
    acquisition.setdefault("work_sessions", [])
    if entry["session_id"] and not any(item.get("session_id") == entry["session_id"] for item in acquisition["work_sessions"]):
        acquisition["work_sessions"].append(entry)
    if acquisition.get("status") == "open":
        acquisition["status"] = "processing"
    save_acquisition(acquisition)
    return session_data


def attach_current_session_to_current_acquisition():
    session = load_current_session()
    acquisition = current_acquisition()
    if not session or not acquisition:
        return None
    session = attach_work_session_to_acquisition(session, acquisition)
    save_current_session(session)
    folder = Path(session.get("folder", ""))
    if folder.exists():
        (folder / "session.json").write_text(json.dumps(session, indent=2) + "\n", encoding="utf-8")
    append_activity(f"Attached session {session.get('session_id')} to acquisition {acquisition.get('acquisition_name')}")
    return session


def estimated_listing_value(rows):
    total = Decimal("0.00")
    for row in rows or []:
        total += decimal_money(row.get("*StartPrice") or row.get("StartPrice") or row.get("Price") or row.get("Current price"))
    return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def record_import_acquisition_metadata(path, rows, batch_location=""):
    acquisition = current_acquisition()
    session = load_current_session()
    if not acquisition:
        return None
    entry = {
        "session_id": session.get("session_id", "") if session else "",
        "acquisition_id": acquisition.get("acquisition_id", ""),
        "acquisition_name": acquisition.get("acquisition_name", ""),
        "purchase_price_snapshot": acquisition.get("purchase_price", "0.00"),
        "source_file": str(path),
        "row_count": len(rows or []),
        "estimated_listing_value": format_decimal_money(estimated_listing_value(rows)),
        "estimated_market_value": "0.00",
        "estimated_bulk_value": "0.00",
        "batch_location": batch_location or (session.get("batch_location", "") if session else ""),
        "imported_at": datetime.now().isoformat(timespec="seconds"),
    }
    acquisition.setdefault("imports", []).append(entry)
    if acquisition.get("status") == "open":
        acquisition["status"] = "processing"
    save_acquisition(acquisition)
    return entry


def write_acquisition_job_metadata(job_path, rows=None, export_summary=None):
    acquisition = current_acquisition()
    session = load_current_session()
    if not acquisition:
        return None
    rows = rows or []
    summary = export_summary or {}
    metadata = {
        "acquisition_id": acquisition.get("acquisition_id", ""),
        "acquisition_name": acquisition.get("acquisition_name", ""),
        "purchase_price": acquisition.get("purchase_price", "0.00"),
        "session_id": session.get("session_id", "") if session else "",
        "batch_location": summary.get("batch_location", session.get("batch_location", "") if session else ""),
        "cards_processed_in_session": len(rows),
        "estimated_listing_value": format_decimal_money(estimated_listing_value(rows)),
        "estimated_market_value": "0.00",
        "estimated_bulk_value": "0.00",
        "estimated_break_even_progress": "placeholder",
        "gross_revenue_collected": acquisition.get("gross_revenue_collected", "0.00"),
        "net_revenue_collected": acquisition.get("net_revenue_collected", "0.00"),
        "remaining_to_break_even": acquisition.get("remaining_to_break_even", acquisition.get("purchase_price", "0.00")),
        "break_even_date": acquisition.get("break_even_date", ""),
        "remaining_inventory_value": acquisition.get("remaining_inventory_value", "0.00"),
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    job_path = Path(job_path)
    job_path.mkdir(parents=True, exist_ok=True)
    metadata_path = job_path / "acquisition_metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    summary_path = job_path / "acquisition_summary.txt"
    summary_path.write_text(
        "\n".join([
            "CardVector OS Acquisition Intake Summary",
            f"Acquisition ID: {metadata['acquisition_id']}",
            f"Acquisition Name: {metadata['acquisition_name']}",
            f"Purchase Price: ${metadata['purchase_price']}",
            f"Session ID: {metadata['session_id']}",
            f"Batch Location: {metadata['batch_location']}",
            f"Cards Processed in Session: {metadata['cards_processed_in_session']}",
            f"Estimated Listing Value: ${metadata['estimated_listing_value']}",
            f"Estimated Market Value: ${metadata['estimated_market_value']} (placeholder)",
            f"Estimated Bulk Value: ${metadata['estimated_bulk_value']} (placeholder)",
            f"Estimated Break-even Progress: {metadata['estimated_break_even_progress']}",
            f"Remaining to Break Even: ${metadata['remaining_to_break_even']}",
        ]) + "\n",
        encoding="utf-8",
    )
    acquisition.setdefault("pricing_jobs", []).append({
        "job_path": str(job_path),
        "session_id": metadata["session_id"],
        "cards_processed": len(rows),
        "estimated_listing_value": metadata["estimated_listing_value"],
        "created_at": metadata["created_at"],
    })
    save_acquisition(acquisition)
    return metadata


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
    data = attach_work_session_to_acquisition(data)
    (folder / "session.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    (folder / "session_notes.md").write_text(
        f"# Putnam Work Session {stamp}\n\n"
        f"Started: {data['started_at']}\n\n"
        f"Goal: {goal}\n\nCards planned: {planned_cards}\n\n"
        f"Game: {display_location_game(game)}\n\nBatch Location: {batch_location}\n\n"
        f"Acquisition: {data.get('acquisition_name') or 'No Acquisition'}\n\n"
        f"Acquisition ID: {data.get('acquisition_id') or ''}\n\n"
        f"Purchase price snapshot: {data.get('purchase_price_snapshot') or ''}\n\n"
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
        note="Batch location assigned during CardVector OS work-session intake.",
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
    acquisition = current_acquisition()
    if acquisition and not data.get("acquisition_id"):
        data = attach_work_session_to_acquisition(data, acquisition)
    data.setdefault("pricing_jobs", []).append({
        "job_path": str(job_path),
        "rows": rows,
        "opportunities": opportunities,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "acquisition_id": data.get("acquisition_id", ""),
        "acquisition_name": data.get("acquisition_name", ""),
        "purchase_price_snapshot": data.get("purchase_price_snapshot", ""),
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
        self.option_add("*Font", self.ui_font("body"))
        self.loaded = None
        self.rows = []
        self.detected = ""
        self.nav_buttons = {}
        self.status = tk.StringVar(value="Ready.")
        self.status.trace_add("write", self.on_global_status_change)
        self.pricing_running = False
        self.pricing_started_at = None
        self.pricing_action_button = None
        self.current_pricing_job = None
        self.current_pricing_reports = {}
        self.capture_service = CaptureStudioService()
        self.capture_session = None
        self.capture_thumbnail_refs = []
        self.capture_obs_connected = False
        self.auto_capture_settings = load_auto_capture_settings()
        self.auto_capture_running = False
        self.auto_capture_paused = False
        self.auto_capture_pause_reason = ""
        self.auto_capture_after_id = None
        self.auto_capture_state = "Manual"
        self.auto_capture_baseline_signature = None
        self.auto_capture_last_signature = None
        self.auto_capture_stable_since = None
        self.auto_capture_last_capture_at = 0.0
        self.auto_capture_last_capture_signature = None
        self.auto_capture_pending_side = None
        self.auto_capture_pending_bytes = None
        self.auto_capture_last_presence_score = 0.0
        self.auto_capture_last_stability_score = 0.0
        self.auto_capture_logged_disconnect = False
        self.current_pick_list_result = None
        self.imported_carduploader_csv = None
        self.imported_carduploader_summary = None
        self.current_acquisition = current_acquisition()
        self.acquisition_name_var = tk.StringVar(value="")
        self.acquisition_price_var = tk.StringVar(value="")
        self.acquisition_source_var = tk.StringVar(value="")
        self.acquisition_notes_var = tk.StringVar(value="")
        self.acquisition_select_var = tk.StringVar(value="")
        self.acquisition_summary_var = tk.StringVar(value=acquisition_display_text(self.current_acquisition))
        self.build_styles()
        self.build_ui()
        self.after(900, self.auto_check_obs_connection)

    def build_styles(self):
        s = ttk.Style(self)
        try:
            s.theme_use("clam")
        except Exception:
            pass
        s.configure("Main.TFrame", background=BRAND["bg"])
        s.configure("Primary.TButton", font=self.ui_font("button", True), padding=(13, 7))
        s.configure("Secondary.TButton", font=self.ui_font("button"), padding=(13, 7))
        s.configure(
            "Treeview",
            background=BRAND["panel"],
            foreground=BRAND["text"],
            fieldbackground=BRAND["panel"],
            borderwidth=0,
            relief="flat",
            rowheight=35,
            font=self.ui_font("label"),
        )
        s.configure(
            "Treeview.Heading",
            background=BRAND["panel2"],
            foreground=BRAND["gold"],
            borderwidth=0,
            relief="flat",
            font=self.ui_font("label", True),
        )
        s.map(
            "Treeview",
            background=[("selected", BRAND["table_selected"])],
            foreground=[("selected", BRAND["text"])],
        )
        s.map("Treeview.Heading", background=[("active", BRAND["panel_hover"])])
        s.configure("TProgressbar", troughcolor=BRAND["panel2"], background=BRAND["bronze"], bordercolor=BRAND["border"])
        s.map("Primary.TButton", background=[("active", BRAND["bronze_hover"])])
        s.map("Secondary.TButton", background=[("active", BRAND["panel2"])])

    def ui_font(self, size="body", bold=False):
        return (FONT_FAMILY[0], FONT_SIZES.get(size, FONT_SIZES["body"]), "bold" if bold else "normal")

    def text_label(self, parent, text=None, textvariable=None, bg=None, color=None, size="body", bold=False, **pack):
        lbl = tk.Label(
            parent,
            text=text,
            textvariable=textvariable,
            bg=bg or BRAND["panel"],
            fg=color or BRAND["text"],
            font=self.ui_font(size, bold),
            justify="left",
        )
        if pack is not None:
            lbl.pack(**pack)
        return lbl

    def style_button(self, button, variant="secondary"):
        styles = {
            "primary": {
                "bg": BRAND["panel"],
                "fg": BRAND["gold_soft"],
                "activebackground": BRAND["bronze_hover"],
                "activeforeground": BRAND["text"],
                "highlightbackground": BRAND["bronze"],
                "highlightcolor": BRAND["bronze"],
            },
            "secondary": {
                "bg": BRAND["panel"],
                "fg": BRAND["text"],
                "activebackground": BRAND["panel_hover"],
                "activeforeground": BRAND["text"],
                "highlightbackground": BRAND["border"],
                "highlightcolor": BRAND["border"],
            },
            "quiet": {
                "bg": BRAND["panel"],
                "fg": BRAND["muted"],
                "activebackground": BRAND["panel2"],
                "activeforeground": BRAND["text"],
                "highlightbackground": BRAND["border_soft"],
                "highlightcolor": BRAND["border_soft"],
            },
            "danger": {
                "bg": BRAND["panel"],
                "fg": "#FCA5A5",
                "activebackground": "#5B1E2D",
                "activeforeground": "white",
                "highlightbackground": BRAND["danger"],
                "highlightcolor": BRAND["danger"],
            },
        }
        cfg = styles.get(variant, styles["secondary"])
        text = button.cget("text")
        button.configure(
            relief="flat",
            bd=0,
            highlightthickness=1,
            cursor="hand2",
            font=self.ui_font("button", variant == "primary"),
            padx=SPACING["button_pad_x"],
            pady=SPACING["button_pad_y"],
            disabledforeground=BRAND["muted2"],
            text=icon_text(text),
            **cfg,
        )
        normal_bg = cfg["bg"]
        hover_bg = cfg["activebackground"]
        button.bind("<Enter>", lambda _e, b=button: b.configure(bg=hover_bg) if str(b["state"]) != "disabled" else None)
        button.bind("<Leave>", lambda _e, b=button: b.configure(bg=normal_bg) if str(b["state"]) != "disabled" else None)
        return button

    def status_indicator(self, parent, textvariable, state="unknown", bg=None, **pack):
        bg = bg or BRAND["panel"]
        frame = tk.Frame(parent, bg=bg)
        if pack is not None:
            frame.pack(**pack)
        dot = tk.Canvas(frame, width=12, height=12, bg=bg, highlightthickness=0, bd=0)
        dot.pack(side="left", padx=(0, 7), pady=2)
        dot_id = dot.create_oval(2, 2, 10, 10, fill=STATUS_COLORS.get(state, STATUS_COLORS["unknown"]), outline="")
        dot._dot_id = dot_id
        label = tk.Label(
            frame,
            textvariable=textvariable,
            bg=bg,
            fg=BRAND["muted"],
            font=self.ui_font("small"),
            anchor="w",
        )
        label.pack(side="left")
        return dot, label

    def set_indicator_state(self, dot, state):
        if not dot:
            return
        try:
            dot.itemconfig(dot._dot_id, fill=STATUS_COLORS.get(state, STATUS_COLORS["unknown"]))
        except Exception:
            pass

    def on_global_status_change(self, *_args):
        state = status_state_from_text(self.status.get())
        if hasattr(self, "global_status_dot"):
            self.set_indicator_state(self.global_status_dot, state)
        if hasattr(self, "toolbar_status_dot"):
            self.set_indicator_state(self.toolbar_status_dot, state)

    def build_ui(self):
        side = tk.Frame(self, bg=BRAND["sidebar"], width=SPACING["sidebar_width"])
        side.pack(side="left", fill="y")
        side.pack_propagate(False)

        tk.Label(side, text="CARDVECTOR", bg=BRAND["sidebar"], fg=BRAND["text"],
                 font=self.ui_font("app_title", True)).pack(pady=(22, 0))
        tk.Label(side, text=f"OS v{APP_VERSION}", bg=BRAND["sidebar"], fg=BRAND["gold"],
                 font=self.ui_font("small", True)).pack(pady=(0, 14))

        nav_sections = [
            ("HOME", ["Home"]),
            ("OPERATIONS", ["Capture", "Import", "Pricing"]),
            ("INVENTORY", ["Inventory", "Orders", "Shipping"]),
            ("BUSINESS", ["Content", "Analytics"]),
            ("SYSTEM", ["Sessions", "Settings"]),
        ]
        for section, names in nav_sections:
            tk.Label(
                side,
                text=section,
                bg=BRAND["sidebar"],
                fg=BRAND["muted2"],
                font=self.ui_font("small", True),
                anchor="w",
            ).pack(fill="x", padx=22, pady=(13, 3))
            for name in names:
                b = tk.Button(
                    side, text=nav_text(name), anchor="w", bg=BRAND["sidebar"], fg=BRAND["muted"],
                    activebackground=BRAND["sidebar_hover"], activeforeground=BRAND["text"], relief="flat",
                    bd=0, cursor="hand2", font=self.ui_font("button", True), padx=18, pady=8,
                    command=lambda n=name: self.show_page(n)
                )
                b.pack(fill="x", padx=12, pady=1)
                b.bind("<Enter>", lambda _e, btn=b: btn.configure(bg=BRAND["sidebar_hover"]) if btn.cget("bg") != BRAND["panel_tint"] else None)
                b.bind("<Leave>", lambda _e, btn=b: btn.configure(bg=BRAND["sidebar"]) if btn.cget("bg") != BRAND["panel_tint"] else None)
                self.nav_buttons[name] = b

        bottom = tk.Frame(side, bg=BRAND["sidebar"])
        bottom.pack(side="bottom", fill="x", padx=14, pady=18)
        tk.Label(bottom, text="Root", bg=BRAND["sidebar"], fg=BRAND["gold"], font=self.ui_font("small", True)).pack(anchor="w")
        tk.Label(bottom, text=str(ROOT), bg=BRAND["sidebar"], fg=BRAND["muted2"], font=self.ui_font("small"),
                 wraplength=190, justify="left").pack(anchor="w")

        self.workspace = tk.Frame(self, bg=BRAND["bg"])
        self.workspace.pack(side="left", fill="both", expand=True)

        self.toolbar_page_var = tk.StringVar(value="Home")
        toolbar = tk.Frame(self.workspace, bg=BRAND["toolbar"], height=SPACING["toolbar_height"], highlightbackground=BRAND["border_soft"], highlightthickness=0)
        toolbar.pack(side="top", fill="x")
        toolbar.pack_propagate(False)
        tk.Label(
            toolbar,
            textvariable=self.toolbar_page_var,
            bg=BRAND["toolbar"],
            fg=BRAND["gold_soft"],
            font=self.ui_font("button", True),
            anchor="w",
        ).pack(side="left", padx=(18, 12), fill="y")
        tk.Label(
            toolbar,
            text="Capture > CardUploader > Pricing > eBay CSV > eBay Upload",
            bg=BRAND["toolbar"],
            fg=BRAND["muted2"],
            font=self.ui_font("label"),
            anchor="w",
        ).pack(side="left", fill="y")
        self.toolbar_status_var = tk.StringVar(value="Workflow Ready")
        toolbar_status = tk.Frame(toolbar, bg=BRAND["toolbar"])
        toolbar_status.pack(side="right", padx=18, fill="y")
        self.toolbar_status_dot, _label = self.status_indicator(
            toolbar_status,
            self.toolbar_status_var,
            state="ready",
            bg=BRAND["toolbar"],
            side="left",
            pady=11,
        )

        self.main = tk.Frame(self.workspace, bg=BRAND["bg"])
        self.main.pack(side="top", fill="both", expand=True)

        self.statusbar = tk.Frame(self.workspace, bg=BRAND["statusbar"], height=28, highlightbackground=BRAND["border_soft"], highlightthickness=1)
        self.statusbar.pack(side="bottom", fill="x")
        self.statusbar.pack_propagate(False)
        self.global_status_dot, _label = self.status_indicator(
            self.statusbar,
            self.status,
            state="ready",
            bg=BRAND["statusbar"],
            side="left",
            padx=(14, 0),
            pady=5,
        )
        self.show_page("Home")

    def clear(self):
        for w in self.main.winfo_children():
            w.destroy()

    def show_page(self, name):
        self.current_page = name
        if hasattr(self, "toolbar_page_var"):
            self.toolbar_page_var.set(nav_text(name))
        for n, b in self.nav_buttons.items():
            if n == name:
                b.configure(bg=BRAND["panel_tint"], fg=BRAND["gold_soft"])
            else:
                b.configure(bg=BRAND["sidebar"], fg=BRAND["muted"])
        self.clear()
        if name == "Home":
            self.home_page()
        elif name == "Import":
            self.import_page()
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
        elif name == "Settings":
            self.settings_page()
        else:
            self.placeholder_page(name)

    def header(self, title, subtitle=""):
        tk.Label(self.main, text=title, bg=BRAND["bg"], fg=BRAND["text"], font=self.ui_font("page_title", True)).pack(anchor="w", padx=SPACING["page_x"], pady=(SPACING["page_top"], 2))
        if subtitle:
            tk.Label(self.main, text=subtitle, bg=BRAND["bg"], fg=BRAND["muted"], font=self.ui_font("body")).pack(anchor="w", padx=SPACING["page_x"], pady=(0, 14))

    def card(self, parent, **pack):
        f = tk.Frame(parent, bg=BRAND["panel"], highlightbackground=BRAND["border"], highlightthickness=1)
        if pack is not None:
            f.pack(**pack)
        return f

    def label(self, parent, text, size=10, color=None, bold=False, bg=None, **pack):
        size_name = "body"
        if size <= 8:
            size_name = "small"
        elif size <= 9:
            size_name = "label"
        elif size >= 20:
            size_name = "metric"
        elif size >= 11:
            size_name = "section"
        return self.text_label(parent, text=text, bg=bg or BRAND["panel"], color=color or BRAND["text"], size=size_name, bold=bold, **pack)

    def metric_card(self, parent, title, value, subtitle=""):
        c = self.card(parent, side="left", fill="both", expand=True, padx=(0, 12), ipady=12)
        self.label(c, title, 9, BRAND["gold"], True, anchor="w", padx=18, pady=(14, 2))
        self.label(c, str(value), 22, BRAND["text"], True, anchor="w", padx=16)
        if subtitle:
            self.label(c, subtitle, 9, BRAND["muted"], False, anchor="w", padx=18, pady=(0, 10))
        return c

    def make_drop_zone(self, parent, text, command):
        zone = tk.Frame(parent, bg=BRAND["panel2"], highlightbackground=BRAND["border_accent"], highlightthickness=1)
        zone.pack(fill="x", pady=(0, 16), ipady=20)
        tk.Label(zone, text=text, bg=BRAND["panel2"], fg=BRAND["text"], font=self.ui_font("section", True)).pack(pady=(16, 4))
        tk.Label(zone, text="Drop CSV here or click to browse", bg=BRAND["panel2"], fg=BRAND["muted"], font=self.ui_font("body")).pack()
        self.primary_button(zone, "Browse for CSV", command).pack(pady=14)
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

    def refresh_acquisition_state(self):
        self.current_acquisition = current_acquisition()
        if hasattr(self, "acquisition_summary_var"):
            self.acquisition_summary_var.set(acquisition_display_text(self.current_acquisition))

    def acquisition_options(self):
        records = open_acquisitions()
        return [f"{record.get('acquisition_id')} | {record.get('acquisition_name')} | ${record.get('purchase_price', '0.00')}" for record in records]

    def selected_acquisition_id_from_var(self):
        value = self.acquisition_select_var.get().strip()
        if " | " in value:
            return value.split(" | ", 1)[0].strip()
        return value.strip()

    def build_acquisition_panel(self, parent, title="ACQUISITION"):
        panel = self.card(parent, fill="x", pady=(0, 16), ipady=12)
        self.label(panel, title, 12, BRAND["gold"], True, anchor="w", padx=18, pady=(12, 6))
        tk.Label(
            panel,
            textvariable=self.acquisition_summary_var,
            bg=BRAND["panel"],
            fg=BRAND["muted"],
            font=("Segoe UI", 10),
            justify="left",
            wraplength=940,
        ).pack(anchor="w", fill="x", padx=18, pady=(0, 10))

        fields = tk.Frame(panel, bg=BRAND["panel"])
        fields.pack(fill="x", padx=18, pady=(0, 8))
        labels = [
            ("Name", self.acquisition_name_var, 34),
            ("Purchase Price", self.acquisition_price_var, 12),
            ("Source", self.acquisition_source_var, 24),
        ]
        for label, var, width in labels:
            tk.Label(fields, text=label, bg=BRAND["panel"], fg=BRAND["muted"], font=self.ui_font("label", True)).pack(side="left", padx=(0, 6))
            tk.Entry(fields, textvariable=var, width=width, bg=BRAND["panel2"], fg=BRAND["text"], relief="flat", insertbackground=BRAND["text"]).pack(side="left", padx=(0, 12), ipady=4)

        notes_row = tk.Frame(panel, bg=BRAND["panel"])
        notes_row.pack(fill="x", padx=18, pady=(0, 8))
        tk.Label(notes_row, text="Notes", bg=BRAND["panel"], fg=BRAND["muted"], font=self.ui_font("label", True)).pack(side="left", padx=(0, 6))
        tk.Entry(notes_row, textvariable=self.acquisition_notes_var, bg=BRAND["panel2"], fg=BRAND["text"], relief="flat", insertbackground=BRAND["text"]).pack(side="left", fill="x", expand=True, ipady=4)

        select_row = tk.Frame(panel, bg=BRAND["panel"])
        select_row.pack(fill="x", padx=18, pady=(0, 8))
        tk.Label(select_row, text="Select open acquisition", bg=BRAND["panel"], fg=BRAND["muted"], font=self.ui_font("label", True)).pack(side="left", padx=(0, 8))
        combo = ttk.Combobox(select_row, textvariable=self.acquisition_select_var, values=self.acquisition_options(), width=70, state="readonly")
        combo.pack(side="left", fill="x", expand=True)

        buttons = tk.Frame(panel, bg=BRAND["panel"])
        buttons.pack(anchor="w", padx=18, pady=(0, 12))
        self.primary_button(buttons, "Create Acquisition", self.create_acquisition_ui).pack(side="left")
        self.action_button(buttons, "Select Acquisition", self.select_acquisition_ui).pack(side="left", padx=8)
        self.action_button(buttons, "Attach Current Session", self.attach_current_session_acquisition_ui).pack(side="left")
        self.action_button(buttons, "No Acquisition", self.clear_acquisition_ui).pack(side="left", padx=8)
        return panel

    def create_acquisition_ui(self):
        name = self.acquisition_name_var.get().strip()
        price = self.acquisition_price_var.get().strip()
        source = self.acquisition_source_var.get().strip()
        notes = self.acquisition_notes_var.get().strip()
        if not name:
            messagebox.showinfo("Acquisition", "Enter an acquisition name first.")
            return
        if decimal_money(price) <= 0:
            messagebox.showinfo("Acquisition", "Enter a purchase price greater than 0.")
            return
        record = create_acquisition(name, price, source=source, notes=notes)
        self.current_acquisition = record
        attach_current_session_to_current_acquisition()
        self.acquisition_select_var.set(f"{record.get('acquisition_id')} | {record.get('acquisition_name')} | ${record.get('purchase_price')}")
        self.refresh_acquisition_state()
        self.status.set(f"Acquisition selected: {record.get('acquisition_name')}")
        messagebox.showinfo("Acquisition", f"Created and selected acquisition:\n{record.get('acquisition_name')}")
        if getattr(self, "current_page", "") in {"Home", "Import", "Pricing"}:
            self.show_page(self.current_page)

    def select_acquisition_ui(self):
        acquisition_id = self.selected_acquisition_id_from_var()
        if not acquisition_id:
            messagebox.showinfo("Acquisition", "Select an open acquisition first.")
            return
        record = load_acquisition(acquisition_id)
        if not record:
            messagebox.showerror("Acquisition", "Selected acquisition could not be loaded.")
            return
        set_current_acquisition(record)
        self.current_acquisition = record
        attach_current_session_to_current_acquisition()
        self.refresh_acquisition_state()
        self.status.set(f"Acquisition selected: {record.get('acquisition_name')}")
        if getattr(self, "current_page", "") in {"Home", "Import", "Pricing"}:
            self.show_page(self.current_page)

    def clear_acquisition_ui(self):
        set_current_acquisition(None)
        self.current_acquisition = None
        self.refresh_acquisition_state()
        self.status.set("No Acquisition selected.")
        if getattr(self, "current_page", "") in {"Home", "Import", "Pricing"}:
            self.show_page(self.current_page)

    def attach_current_session_acquisition_ui(self):
        if not current_acquisition():
            messagebox.showinfo("Acquisition", "No acquisition selected.")
            return
        session = attach_current_session_to_current_acquisition()
        if not session:
            messagebox.showinfo("Acquisition", "No active work session to attach.")
            return
        self.refresh_acquisition_state()
        messagebox.showinfo("Acquisition", f"Attached session {session.get('session_id')} to current acquisition.")
        if getattr(self, "current_page", "") in {"Home", "Import", "Pricing"}:
            self.show_page(self.current_page)

    def home_page(self):
        self.header("Home", "Mission control for Putnam Collectibles.")
        wrap = tk.Frame(self.main, bg=BRAND["bg"])
        wrap.pack(fill="both", expand=True, padx=34, pady=0)

        mission = self.card(wrap, fill="x", pady=(0, 16), ipady=14)
        self.label(mission, "TODAY'S MISSION", 13, BRAND["gold"], True, anchor="w", padx=18, pady=(14, 4))
        cur = load_current_session()
        stage = current_workflow_stage()
        if cur:
            msg = (
                f"Active session: {Path(cur.get('folder','')).name}\n"
                f"Current game: {display_location_game(cur.get('game', 'pokemon'))}\n"
                f"Batch location: {cur.get('batch_location', '') or '(not set)'}\n"
                f"Current workflow stage: {stage}\n"
                f"Next recommended action: {next_recommended_action()}"
            )
        else:
            msg = (
                "Active session: none\n"
                "Current game: not selected\n"
                "Batch location: not selected\n"
                f"Current workflow stage: {stage}\n"
                f"Next recommended action: {next_recommended_action()}"
            )
        self.label(mission, msg, 10, BRAND["muted"], False, anchor="w", padx=18, pady=(0, 12))

        self.build_acquisition_panel(wrap, "CURRENT ACQUISITION")

        progress = self.card(wrap, fill="x", pady=(0, 16), ipady=12)
        self.label(progress, "WORKFLOW PROGRESS", 12, BRAND["gold"], True, anchor="w", padx=18, pady=(12, 6))
        steps = ["Capture", "Import", "Pricing", "Upload", "Inventory", "Shipping"]
        progress_lines = []
        for step in steps:
            marker = ">>" if step == stage else "  "
            progress_lines.append(f"{marker} {step}")
        self.label(progress, "\n".join(progress_lines), 11, BRAND["muted"], False, anchor="w", padx=18, pady=(0, 12))

        decision = self.card(wrap, fill="x", pady=(0, 16), ipady=12)
        self.label(decision, "DECISION ENGINE", 12, BRAND["gold"], True, anchor="w", padx=18, pady=(12, 6))
        initial_engine_status = run_decision_engine_check(write_log=False)
        self.decision_engine_var = tk.StringVar(value=decision_engine_summary_text(initial_engine_status))
        tk.Label(
            decision,
            textvariable=self.decision_engine_var,
            bg=BRAND["panel"],
            fg=BRAND["muted"],
            font=("Segoe UI", 9),
            justify="left",
            wraplength=980,
        ).pack(anchor="w", fill="x", padx=18, pady=(0, 10))
        decision_buttons = tk.Frame(decision, bg=BRAND["panel"])
        decision_buttons.pack(anchor="w", padx=18, pady=(0, 14))
        self.action_button(decision_buttons, "Run Decision Engine Check", self.run_decision_engine_check_ui).pack(side="left")
        self.action_button(decision_buttons, "Open Latest Decision Log", self.open_latest_decision_log).pack(side="left", padx=8)

        latest_card = self.card(wrap, fill="x", pady=(0, 16), ipady=12)
        self.label(latest_card, "LATEST CARDUPLOADER EXPORT", 12, BRAND["gold"], True, anchor="w", padx=18, pady=(12, 6))
        detected = latest_carduploader_export()
        detected_text = f"Detected: {detected}" if detected else "No CSV detected in Imports, Incoming Files, or Downloads."
        self.latest_csv_var = tk.StringVar(value=detected_text)
        tk.Label(latest_card, textvariable=self.latest_csv_var, bg=BRAND["panel"], fg=BRAND["muted"],
                 font=("Segoe UI", 9), justify="left", wraplength=820).pack(anchor="w", padx=18, pady=(0, 10))
        latest_buttons = self.button_bar(latest_card, pad_y=(0, 14))
        self.primary_button(latest_buttons, "Analyze Latest Export", self.analyze_latest_carduploader_export).pack(side="left")
        self.action_button(latest_buttons, "Browse for CSV", self.browse_and_run).pack(side="left", padx=10)

        actions = self.card(wrap, fill="x", pady=(0, 16), ipady=12)
        self.label(actions, "QUICK ACTIONS", 12, BRAND["gold"], True, anchor="w", padx=18, pady=(12, 8))
        btns = self.button_bar(actions, pad_y=(0, 8))
        self.action_button(btns, "Open Capture", lambda: self.show_page("Capture")).pack(side="left")
        self.action_button(btns, "Import Latest CardUploader Export", self.import_latest_carduploader_export_ui).pack(side="left", padx=8)
        self.action_button(btns, "Analyze Latest Export", self.analyze_latest_carduploader_export).pack(side="left", padx=8)
        self.action_button(btns, "Open Pricing Output", self.open_current_output_folder).pack(side="left", padx=8)
        self.action_button(btns, "Open CardUploader", self.open_carduploader).pack(side="left", padx=8)
        folder_btns = self.button_bar(actions, pad_y=(0, 14))
        self.action_button(folder_btns, "Open Imports", lambda: os.startfile(IMPORTS)).pack(side="left")
        self.action_button(folder_btns, "Open Exports", lambda: os.startfile(EXPORTS)).pack(side="left", padx=8)
        self.action_button(folder_btns, "Open Completed Jobs", lambda: os.startfile(COMPLETED)).pack(side="left", padx=8)

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
        return self.ui_button(parent, text, command, variant="secondary")

    def primary_button(self, parent, text, command):
        return self.ui_button(parent, text, command, variant="primary")

    def quiet_button(self, parent, text, command):
        return self.ui_button(parent, text, command, variant="quiet")

    def ui_button(self, parent, text, command, variant="secondary"):
        button = tk.Button(parent, text=text, command=command)
        return self.style_button(button, variant)

    def button_bar(self, parent, pad_x=18, pad_y=(0, 10)):
        shell = tk.Frame(parent, bg=BRAND["panel"])
        shell.pack(fill="x", padx=pad_x, pady=pad_y)
        canvas = tk.Canvas(shell, bg=BRAND["panel"], highlightthickness=0, height=46)
        scroll = ttk.Scrollbar(shell, orient="horizontal", command=canvas.xview)
        inner = tk.Frame(canvas, bg=BRAND["panel"])
        window_id = canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(xscrollcommand=scroll.set)

        def update_scroll(_event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfigure(window_id, height=inner.winfo_reqheight())

        inner.bind("<Configure>", update_scroll)
        canvas.pack(fill="x", expand=True)
        scroll.pack(fill="x")
        return inner

    def style_treeview(self, tree):
        tree.configure(selectmode="extended")
        tree.tag_configure("even", background=BRAND["table_even"])
        tree.tag_configure("odd", background=BRAND["table_odd"])
        tree.tag_configure("hover", background=BRAND["table_hover"])
        tree._hover_item = None

        def on_motion(event):
            item = tree.identify_row(event.y)
            if item == getattr(tree, "_hover_item", None):
                return
            previous = getattr(tree, "_hover_item", None)
            if previous and previous in tree.get_children(""):
                tree.item(previous, tags=tree.item(previous, "values") and tree._base_tags.get(previous, ()))
            tree._hover_item = item
            if item:
                tree.item(item, tags=("hover",))

        def on_leave(_event):
            item = getattr(tree, "_hover_item", None)
            if item and item in tree.get_children(""):
                tree.item(item, tags=tree._base_tags.get(item, ()))
            tree._hover_item = None

        tree._base_tags = {}
        tree.bind("<Motion>", on_motion, add="+")
        tree.bind("<Leave>", on_leave, add="+")
        return tree

    def tree_insert(self, tree, parent, index, values):
        row_index = len(tree.get_children(parent))
        tag = "even" if row_index % 2 == 0 else "odd"
        item = tree.insert(parent, index, values=values, tags=(tag,))
        if not hasattr(tree, "_base_tags"):
            tree._base_tags = {}
        tree._base_tags[item] = (tag,)
        return item

    def sortable_heading(self, tree, column, label, reverse=False, show_arrow=True):
        arrow = " ▼" if reverse else " ▲"
        heading_text = f"{label}{arrow}" if show_arrow else label
        next_reverse = not reverse if show_arrow else False
        tree.heading(column, text=heading_text, command=lambda c=column, r=next_reverse, l=label: self.sort_report_tree(tree, c, r, l))

    def open_latest_decision_log(self):
        path = latest_decision_log()
        if not path:
            messagebox.showinfo("Decision Engine", "No Decision Engine log found yet. Run a check first.")
            return
        try:
            os.startfile(path)
        except Exception as exc:
            messagebox.showinfo("Decision Engine", f"Latest log:\n{path}\n\nCould not open automatically:\n{exc}")

    def open_carduploader(self):
        url = load_app_config().get("carduploader_url", "")
        if not url:
            messagebox.showinfo(
                "CardUploader",
                "CardUploader URL is not configured yet.\n\nOpen Settings and enter carduploader_url once.",
            )
            self.show_page("Settings")
            return
        webbrowser.open(url)
        self.status.set("Opened CardUploader.")

    def import_latest_carduploader_export_ui(self):
        latest = latest_carduploader_export()
        if not latest:
            messagebox.showinfo("CardVector OS Import", "No CardUploader CSV found in Imports, Downloads, or Incoming Files.")
            return
        self.import_carduploader_csv_path(latest)
        self.show_page("Import")

    def import_page(self):
        self.header("Import", "Unified CardUploader CSV import and validation.")
        wrap = tk.Frame(self.main, bg=BRAND["bg"])
        wrap.pack(fill="both", expand=True, padx=34, pady=0)

        import_card = self.card(wrap, fill="x", pady=(0, 16), ipady=12)
        self.label(import_card, "IMPORT WORKFLOW", 12, BRAND["gold"], True, anchor="w", padx=18, pady=(12, 6))
        tk.Label(
            import_card,
            text=(
                "Browse for a CSV, drop a CardUploader export, or use the latest detected file. "
                "CardVector OS validates the file before handing it to Pricing & Decisions."
            ),
            bg=BRAND["panel"],
            fg=BRAND["muted"],
            font=("Segoe UI", 10),
            justify="left",
            wraplength=920,
        ).pack(anchor="w", padx=18, pady=(0, 12))
        button_row = tk.Frame(import_card, bg=BRAND["panel"])
        button_row.pack(anchor="w", padx=18, pady=(0, 14))
        self.primary_button(button_row, "Browse CSV", self.import_carduploader_csv_ui).pack(side="left")
        self.action_button(button_row, "Import Latest Export", self.import_latest_carduploader_export_ui).pack(side="left", padx=10)
        self.action_button(button_row, "Analyze", self.proceed_import_to_listings).pack(side="left")
        self.action_button(button_row, "Continue to Pricing", self.proceed_import_to_listings).pack(side="left", padx=10)
        self.action_button(button_row, "Open Output Folder", lambda: os.startfile(COMPLETED)).pack(side="left")
        self.action_button(button_row, "Return Home", lambda: self.show_page("Home")).pack(side="left", padx=10)

        self.build_acquisition_panel(wrap, "ACQUISITION FOR THIS INTAKE")

        self.make_drop_zone(wrap, "Drag & Drop CardUploader CSV", self.import_carduploader_csv_ui)

        summary_card = self.card(wrap, fill="x", pady=(0, 16), ipady=12)
        self.label(summary_card, "VALIDATION SUMMARY", 12, BRAND["gold"], True, anchor="w", padx=18, pady=(12, 6))
        if self.imported_carduploader_summary:
            summary_text = format_carduploader_import_summary(self.imported_carduploader_summary)
        else:
            last_folder = import_last_folder()
            last_text = f"\nLast folder: {last_folder}" if last_folder else ""
            detected = latest_carduploader_export()
            detected_text = f"\nLatest detected: {detected}" if detected else "\nLatest detected: none"
            summary_text = "No CardUploader CSV imported yet." + last_text + detected_text
        self.import_summary_var = tk.StringVar(value=summary_text)
        tk.Label(
            summary_card,
            textvariable=self.import_summary_var,
            bg=BRAND["panel"],
            fg=BRAND["muted"],
            font=("Segoe UI", 10),
            justify="left",
            wraplength=920,
        ).pack(anchor="w", padx=18, pady=(0, 14))

        handoff = self.card(wrap, fill="x", pady=(0, 16), ipady=12)
        self.label(handoff, "HANDOFF", 12, BRAND["gold"], True, anchor="w", padx=18, pady=(12, 6))
        tk.Label(
            handoff,
            text=(
                "Continue to Pricing loads the imported CSV into Pricing & Decisions. "
                "Pricing rules, eBay export columns, shipping confirmation, and export logging "
                "remain handled by the existing production workflow."
            ),
            bg=BRAND["panel"],
            fg=BRAND["muted"],
            font=("Segoe UI", 10),
            justify="left",
            wraplength=920,
        ).pack(anchor="w", padx=18, pady=(0, 14))

    def import_carduploader_csv_ui(self):
        initialdir = import_last_folder() or str(ROOT)
        path = filedialog.askopenfilename(
            title="Import CardUploader CSV",
            initialdir=initialdir,
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not path:
            return
        self.import_carduploader_csv_path(path)

    def import_carduploader_csv_path(self, path):
        try:
            rows = read_csv(path)
            summary = build_carduploader_import_summary(path, rows)
            acquisition_entry = record_import_acquisition_metadata(path, rows)
            active_session = attach_current_session_to_current_acquisition()
            self.imported_carduploader_csv = Path(path)
            self.imported_carduploader_summary = summary
            state = {
                "last_carduploader_folder": str(Path(path).parent),
                "last_carduploader_csv": str(Path(path)),
                "session_id": active_session.get("session_id", "") if active_session else "",
                "acquisition_id": acquisition_entry.get("acquisition_id", "") if acquisition_entry else "",
                "acquisition_name": acquisition_entry.get("acquisition_name", "") if acquisition_entry else "",
                "purchase_price_snapshot": acquisition_entry.get("purchase_price_snapshot", "") if acquisition_entry else "",
                "batch_location": acquisition_entry.get("batch_location", "") if acquisition_entry else "",
                "updated_at": datetime.now().isoformat(timespec="seconds"),
            }
            save_import_module_state(state)
            if hasattr(self, "import_summary_var"):
                acquisition_text = ""
                if acquisition_entry:
                    acquisition_text = (
                        "\n\nAcquisition:\n"
                        f"- {acquisition_entry['acquisition_name']}\n"
                        f"- Purchase price snapshot: ${acquisition_entry['purchase_price_snapshot']}\n"
                        f"- Estimated listing value: ${acquisition_entry['estimated_listing_value']}"
                    )
                self.import_summary_var.set(format_carduploader_import_summary(summary) + acquisition_text)
            self.load(path)
            self.status.set(f"Imported CardUploader CSV: {Path(path).name}")
            if hasattr(self, "capture_rail_inner"):
                self.schedule_capture_thumbnail_refresh()
        except Exception as exc:
            self.status.set("CardUploader import failed.")
            messagebox.showerror("CardVector OS Import", f"Could not import CSV:\n{exc}")

    def proceed_import_to_listings(self):
        if not self.imported_carduploader_csv:
            messagebox.showinfo("CardVector OS Import", "Import a CardUploader CSV before continuing to Pricing.")
            return
        if self.imported_carduploader_summary:
            status = self.imported_carduploader_summary.get("readiness_status", "")
            if not status.startswith("Ready"):
                if not messagebox.askyesno(
                    "CardVector OS Import",
                    f"{status}\n\nProceed to Listings anyway?",
                ):
                    return
        self.show_page("Pricing")
        self.load(self.imported_carduploader_csv)
        self.status.set("Imported CSV loaded in CardVector Pricing Engine. Ready to analyze.")

    def capture_page(self):
        self.header("Capture", "Capture the next card.")
        wrap = tk.Frame(self.main, bg=BRAND["bg"])
        wrap.pack(fill="both", expand=True, padx=34, pady=0)

        workspace = tk.Frame(wrap, bg=BRAND["bg"])
        workspace.pack(side="left", fill="both", expand=True, padx=(0, 14))
        rail = tk.Frame(wrap, bg=BRAND["panel"], width=315, highlightbackground=BRAND["border"], highlightthickness=1)
        rail.pack(side="right", fill="y")
        rail.pack_propagate(False)

        status_card = self.card(workspace, fill="x", pady=(0, 14), ipady=12)
        self.label(status_card, "CURRENT SESSION", 12, BRAND["gold"], True, anchor="w", padx=18, pady=(12, 6))
        self.capture_folder_var = tk.StringVar()
        self.capture_session_name_var = tk.StringVar()
        self.capture_card_var = tk.StringVar()
        self.capture_count_var = tk.StringVar()
        self.capture_pair_status_var = tk.StringVar()
        self.capture_obs_var = tk.StringVar(value="OBS Checking...")
        self.capture_mode_choice_var = tk.StringVar(value="Auto" if self.auto_capture_settings.get("auto_capture_enabled") else "Manual")
        self.auto_capture_status_var = tk.StringVar(value="Manual")
        self.auto_capture_score_var = tk.StringVar(value="")
        self.auto_stability_delay_var = tk.StringVar(value=str(self.auto_capture_settings.get("stability_delay_seconds", 1.0)))
        self.auto_lockout_var = tk.StringVar(value=str(self.auto_capture_settings.get("duplicate_lockout_seconds", 2.0)))
        self.auto_poll_interval_var = tk.StringVar(value=str(self.auto_capture_settings.get("frame_poll_interval_ms", 200)))
        self.auto_sensitivity_var = tk.StringVar(value=str(self.auto_capture_settings.get("sensitivity", "Medium")))

        for label_text, var in [
            ("Session name", self.capture_session_name_var),
            ("Capture folder", self.capture_folder_var),
            ("Cards captured", self.capture_count_var),
            ("Current card", self.capture_card_var),
            ("Current pair", self.capture_pair_status_var),
            ("Auto status", self.auto_capture_status_var),
        ]:
            row = tk.Frame(status_card, bg=BRAND["panel"])
            row.pack(fill="x", padx=18, pady=2)
            tk.Label(row, text=f"{label_text}:", bg=BRAND["panel"], fg=BRAND["gold"],
                     font=("Segoe UI", 9, "bold"), width=15, anchor="w").pack(side="left")
            tk.Label(row, textvariable=var, bg=BRAND["panel"], fg=BRAND["muted"],
                     font=("Segoe UI", 9), justify="left", wraplength=650).pack(side="left", fill="x", expand=True)

        obs_row = tk.Frame(status_card, bg=BRAND["panel"])
        obs_row.pack(fill="x", padx=18, pady=(8, 2))
        tk.Label(obs_row, text="OBS:", bg=BRAND["panel"], fg=BRAND["gold"],
                 font=("Segoe UI", 9, "bold"), width=15, anchor="w").pack(side="left")
        self.capture_obs_dot, self.capture_obs_label = self.status_indicator(
            obs_row,
            self.capture_obs_var,
            state="unknown",
            bg=BRAND["panel"],
            side="left",
        )
        self.capture_retry_button = self.action_button(obs_row, "Retry", self.check_obs_status_ui)
        self.capture_retry_button.pack(side="left", padx=10)
        self.capture_retry_button.pack_forget()

        mode_row = tk.Frame(status_card, bg=BRAND["panel"])
        mode_row.pack(fill="x", padx=18, pady=(8, 2))
        tk.Label(mode_row, text="Capture Mode:", bg=BRAND["panel"], fg=BRAND["gold"],
                 font=("Segoe UI", 9, "bold"), width=15, anchor="w").pack(side="left")
        for mode in ("Manual", "Auto"):
            tk.Radiobutton(
                mode_row,
                text=mode,
                value=mode,
                variable=self.capture_mode_choice_var,
                command=lambda m=mode: self.set_capture_mode(m),
                bg=BRAND["panel"],
                fg=BRAND["muted"],
                selectcolor=BRAND["panel2"],
                activebackground=BRAND["panel"],
                activeforeground=BRAND["text"],
                font=self.ui_font("label", True),
            ).pack(side="left", padx=(0, 10))
        tk.Label(
            status_card,
            textvariable=self.auto_capture_score_var,
            bg=BRAND["panel"],
            fg=BRAND["muted2"],
            font=self.ui_font("small"),
            justify="left",
        ).pack(anchor="w", padx=18, pady=(0, 6))

        actions = self.card(workspace, fill="x", pady=(0, 14), ipady=18)
        self.label(actions, "ACTIONS", 12, BRAND["gold"], True, anchor="w", padx=18, pady=(12, 8))
        row1 = tk.Frame(actions, bg=BRAND["panel"])
        row1.pack(anchor="w", padx=18, pady=(0, 12))
        self.action_button(row1, "Start Capture Session", self.start_capture_session_ui).pack(side="left")
        self.primary_button(row1, "Capture", self.capture_next_card_ui).pack(side="left", padx=10)
        self.action_button(row1, "Retake Last", self.retake_last_capture_ui).pack(side="left")
        self.action_button(row1, "Finish Session", self.finish_capture_session_ui).pack(side="left", padx=10)
        row2 = tk.Frame(actions, bg=BRAND["panel"])
        row2.pack(anchor="w", padx=18, pady=(0, 12))
        self.action_button(row2, "Open Capture Folder", self.open_capture_folder_ui).pack(side="left")
        self.pause_auto_button = self.action_button(row2, "Pause Auto Capture", self.pause_auto_capture_ui)
        self.pause_auto_button.pack(side="left", padx=10)
        self.resume_auto_button = self.action_button(row2, "Resume Auto Capture", self.resume_auto_capture_ui)
        self.resume_auto_button.pack(side="left")
        self.stop_auto_button = self.action_button(row2, "Stop Auto Capture", self.stop_auto_capture_ui)
        self.stop_auto_button.pack(side="left", padx=10)

        settings_card = self.card(workspace, fill="x", pady=(0, 14), ipady=12)
        self.label(settings_card, "AUTO CAPTURE SETTINGS", 12, BRAND["gold"], True, anchor="w", padx=18, pady=(12, 8))
        settings_row = tk.Frame(settings_card, bg=BRAND["panel"])
        settings_row.pack(fill="x", padx=18, pady=(0, 10))
        for label_text, var, width in [
            ("Stability sec", self.auto_stability_delay_var, 8),
            ("Lockout sec", self.auto_lockout_var, 8),
            ("Poll ms", self.auto_poll_interval_var, 8),
        ]:
            tk.Label(settings_row, text=label_text, bg=BRAND["panel"], fg=BRAND["muted"],
                     font=self.ui_font("label", True)).pack(side="left", padx=(0, 6))
            tk.Entry(settings_row, textvariable=var, width=width, bg=BRAND["panel2"], fg=BRAND["text"],
                     relief="flat", insertbackground=BRAND["text"]).pack(side="left", padx=(0, 12), ipady=3)
        tk.Label(settings_row, text="Sensitivity", bg=BRAND["panel"], fg=BRAND["muted"],
                 font=self.ui_font("label", True)).pack(side="left", padx=(0, 6))
        sensitivity_menu = tk.OptionMenu(settings_row, self.auto_sensitivity_var, "Low", "Medium", "High")
        sensitivity_menu.configure(bg=BRAND["panel2"], fg=BRAND["text"], activebackground=BRAND["bronze_hover"], relief="flat", width=9)
        sensitivity_menu.pack(side="left")
        self.action_button(settings_row, "Save Auto Settings", self.save_auto_capture_settings_ui).pack(side="left", padx=12)

        self.label(rail, "RECENT CAPTURES", 12, BRAND["gold"], True, anchor="w", padx=14, pady=(14, 8))
        rail_buttons = tk.Frame(rail, bg=BRAND["panel"])
        rail_buttons.pack(fill="x", padx=14, pady=(0, 10))
        self.action_button(rail_buttons, "Open Session Folder", self.open_latest_capture_session_folder).pack(anchor="w")
        rail_canvas = tk.Canvas(rail, bg=BRAND["panel"], highlightthickness=0)
        rail_scroll = ttk.Scrollbar(rail, orient="vertical", command=rail_canvas.yview)
        self.capture_rail_inner = tk.Frame(rail_canvas, bg=BRAND["panel"])
        rail_id = rail_canvas.create_window((0, 0), window=self.capture_rail_inner, anchor="nw")
        rail_canvas.configure(yscrollcommand=rail_scroll.set)
        self.capture_rail_inner.bind(
            "<Configure>",
            lambda _e: (
                rail_canvas.configure(scrollregion=rail_canvas.bbox("all")),
                rail_canvas.itemconfigure(rail_id, width=rail_canvas.winfo_width()),
            ),
        )
        rail_canvas.bind("<Configure>", lambda e: rail_canvas.itemconfigure(rail_id, width=e.width))
        rail_canvas.pack(side="left", fill="both", expand=True, padx=(14, 0), pady=(0, 12))
        rail_scroll.pack(side="right", fill="y", pady=(0, 12))
        self.refresh_capture_status()
        self.check_obs_status_ui(silent=True)
        if self.capture_mode_choice_var.get() == "Auto" and not self.auto_capture_running:
            self.after(300, self.start_auto_capture_ui)

    def refresh_capture_status(self):
        session = self.capture_session
        folder = (resolve_capture_path(session.get("folder", "")) if session else None) or CAPTURE_ROOT
        session_name = folder.name if session else "No active session"
        card_number = session.get("current_card_number", 1) if session else "-"
        count = capture_cards_completed(session)
        pair_status = capture_pair_status(session)
        for var_name, value in [
            ("capture_folder_var", str(folder)),
            ("capture_session_name_var", str(session_name)),
            ("capture_card_var", str(card_number)),
            ("capture_count_var", str(count)),
            ("capture_pair_status_var", str(pair_status)),
        ]:
            if hasattr(self, var_name):
                getattr(self, var_name).set(value)
        self.refresh_capture_preview_rail()

    def schedule_capture_thumbnail_refresh(self):
        self.refresh_capture_status()
        for delay in (150, 600):
            self.after(delay, self.refresh_capture_status)

    def refresh_capture_preview_rail(self):
        if not hasattr(self, "capture_rail_inner"):
            return
        for child in self.capture_rail_inner.winfo_children():
            child.destroy()
        self.capture_thumbnail_refs = []
        folder = (resolve_capture_path(self.capture_session.get("folder", "")) if self.capture_session else None) or latest_capture_session()
        rows = capture_pair_rows(folder, limit=30)
        if not rows:
            tk.Label(
                self.capture_rail_inner,
                text="No captures yet.",
                bg=BRAND["panel"],
                fg=BRAND["muted"],
                font=self.ui_font("body"),
                justify="left",
            ).pack(anchor="w", padx=4, pady=8)
            return
        for row in rows:
            self.capture_pair_tile(self.capture_rail_inner, row)

    def capture_pair_tile(self, parent, row):
        tile = tk.Frame(parent, bg=BRAND["panel2"], highlightbackground=BRAND["border"], highlightthickness=1)
        tile.pack(fill="x", padx=(0, 8), pady=(0, 10), ipady=8)
        header = tk.Frame(tile, bg=BRAND["panel2"])
        header.pack(fill="x", padx=10, pady=(8, 5))
        status_color = BRAND["success"] if row["status"] == "Complete" else BRAND["warning"]
        tk.Label(
            header,
            text=f"Pair #{row['pair_number']}",
            bg=BRAND["panel2"],
            fg=BRAND["text"],
            font=self.ui_font("label", True),
        ).pack(side="left")
        if row.get("latest"):
            tk.Label(
                header,
                text="LATEST",
                bg=BRAND["gold_dark"],
                fg=BRAND["text"],
                font=self.ui_font("small", True),
                padx=5,
                pady=1,
            ).pack(side="left", padx=6)
        tk.Label(
            header,
            text=row["timestamp"],
            bg=BRAND["panel2"],
            fg=BRAND["muted"],
            font=self.ui_font("small"),
        ).pack(side="right")
        thumbs = tk.Frame(tile, bg=BRAND["panel2"])
        thumbs.pack(fill="x", padx=10)
        self.capture_thumbnail(thumbs, row.get("front"), "Front")
        self.capture_thumbnail(thumbs, row.get("back"), "Back")
        tk.Label(
            tile,
            text=row["status"],
            bg=BRAND["panel2"],
            fg=status_color,
            font=self.ui_font("small", True),
        ).pack(anchor="w", padx=10, pady=(5, 2))
        badges = "CardUploader Pending  |  Pricing Pending  |  Inventory Pending"
        tk.Label(
            tile,
            text=badges,
            bg=BRAND["panel2"],
            fg=BRAND["muted2"],
            font=self.ui_font("small"),
            wraplength=250,
            justify="left",
        ).pack(anchor="w", padx=10, pady=(0, 7))

    def capture_thumbnail(self, parent, path, label):
        frame = tk.Frame(parent, bg=BRAND["panel2"])
        frame.pack(side="left", padx=(0, 8))
        image_path = resolve_capture_path(path) if path else None
        if image_path and image_path.exists():
            try:
                from PIL import ImageTk

                photo = ImageTk.PhotoImage(build_capture_thumbnail_image(image_path))
                self.capture_thumbnail_refs.append(photo)
                thumb = tk.Label(frame, image=photo, bg=BRAND["panel2"], cursor="hand2")
                thumb.pack()
                thumb.bind("<Button-1>", lambda _e, p=image_path: self.open_capture_preview(p))
            except Exception:
                thumb = tk.Label(frame, text=f"{label}\nUnreadable", width=12, height=4, bg=BRAND["panel"], fg=BRAND["warning"], cursor="hand2")
                thumb.pack()
                thumb.bind("<Button-1>", lambda _e, p=image_path: self.open_capture_preview(p))
        else:
            tk.Label(frame, text=f"{label}\nMissing", width=12, height=4, bg=BRAND["panel"], fg=BRAND["muted2"]).pack()
        tk.Label(frame, text=label, bg=BRAND["panel2"], fg=BRAND["muted"], font=self.ui_font("small")).pack(pady=(2, 0))

    def open_capture_preview(self, path):
        path = Path(path)
        if not path.exists():
            messagebox.showinfo("Capture Preview", "Capture image not found.")
            return
        try:
            from PIL import Image, ImageOps, ImageTk

            win = tk.Toplevel(self)
            win.title(path.name)
            win.configure(bg=BRAND["bg"])
            with Image.open(path) as source:
                image = ImageOps.exif_transpose(source).convert("RGB")
            image.thumbnail((760, 620))
            photo = ImageTk.PhotoImage(image)
            win._photo = photo
            tk.Label(win, image=photo, bg=BRAND["bg"]).pack(padx=18, pady=(18, 8))
            tk.Label(win, text=str(path), bg=BRAND["bg"], fg=BRAND["muted"], font=self.ui_font("small")).pack(padx=18, pady=(0, 18))
        except Exception:
            try:
                os.startfile(path)
            except Exception as exc:
                messagebox.showinfo("Capture Preview", f"Image:\n{path}\n\nCould not open automatically:\n{exc}")

    def update_capture_obs_indicator(self, status_text):
        connected = obs_status_is_connected(status_text)
        self.capture_obs_connected = connected
        if hasattr(self, "capture_obs_var"):
            self.capture_obs_var.set("OBS Connected" if connected else "OBS Not Connected")
        if hasattr(self, "capture_obs_label"):
            self.capture_obs_label.configure(fg=BRAND["success"] if connected else BRAND["danger"])
        if hasattr(self, "capture_obs_dot"):
            self.set_indicator_state(self.capture_obs_dot, "connected" if connected else "disconnected")
        if hasattr(self, "capture_retry_button"):
            if connected:
                self.capture_retry_button.pack_forget()
            elif not self.capture_retry_button.winfo_ismapped():
                self.capture_retry_button.pack(side="left", padx=10)
        return connected

    def auto_check_obs_connection(self):
        try:
            status = self.capture_service.obs_status()
            self.update_capture_obs_indicator(status)
        except Exception:
            self.update_capture_obs_indicator("")
        finally:
            self.after(30000, self.auto_check_obs_connection)

    def auto_status(self, text):
        self.auto_capture_state = text
        if hasattr(self, "auto_capture_status_var"):
            self.auto_capture_status_var.set(text)
        self.status.set(text if text.startswith("OBS") else f"Auto Capture: {text}")

    def auto_log(self, message):
        append_activity(f"Auto Capture {message}")

    def set_capture_mode(self, mode):
        if mode == "Auto":
            self.start_auto_capture_ui()
        else:
            self.stop_auto_capture_ui(set_manual=True)

    def save_auto_capture_settings_ui(self):
        values = {
            "auto_capture_enabled": self.capture_mode_choice_var.get() == "Auto" if hasattr(self, "capture_mode_choice_var") else False,
            "stability_delay_seconds": self.auto_stability_delay_var.get() if hasattr(self, "auto_stability_delay_var") else 1.0,
            "duplicate_lockout_seconds": self.auto_lockout_var.get() if hasattr(self, "auto_lockout_var") else 2.0,
            "frame_poll_interval_ms": self.auto_poll_interval_var.get() if hasattr(self, "auto_poll_interval_var") else 200,
            "sensitivity": self.auto_sensitivity_var.get() if hasattr(self, "auto_sensitivity_var") else "Medium",
        }
        self.auto_capture_settings = save_auto_capture_settings(values)
        self.status.set(f"Auto Capture settings saved: {AUTO_CAPTURE_CONFIG}")
        self.auto_log("Settings Saved")

    def reset_auto_capture_detection(self, keep_baseline=False):
        if not keep_baseline:
            self.auto_capture_baseline_signature = None
        self.auto_capture_last_signature = None
        self.auto_capture_stable_since = None
        self.auto_capture_pending_side = None
        self.auto_capture_pending_bytes = None
        self.auto_capture_last_presence_score = 0.0
        self.auto_capture_last_stability_score = 0.0

    def start_auto_capture_ui(self):
        self.save_auto_capture_settings_ui()
        if not self.capture_session:
            self.start_capture_session_ui()
            if not self.capture_session:
                if hasattr(self, "capture_mode_choice_var"):
                    self.capture_mode_choice_var.set("Manual")
                return
        self.auto_capture_settings["auto_capture_enabled"] = True
        self.auto_capture_settings = save_auto_capture_settings(self.auto_capture_settings)
        self.auto_capture_running = True
        self.auto_capture_paused = False
        self.auto_capture_pause_reason = ""
        self.auto_capture_logged_disconnect = False
        self.reset_auto_capture_detection()
        self.auto_log("Started")
        self.auto_status("Waiting for Card")
        self.schedule_auto_capture_poll(delay_ms=10)

    def pause_auto_capture_ui(self, reason="operator"):
        if not self.auto_capture_running:
            return
        self.auto_capture_paused = True
        self.auto_capture_pause_reason = reason
        self.auto_log("Paused")
        self.auto_status("Paused")

    def resume_auto_capture_ui(self):
        if not self.auto_capture_running:
            self.start_auto_capture_ui()
            return
        self.auto_capture_paused = False
        self.auto_capture_pause_reason = ""
        self.reset_auto_capture_detection()
        self.auto_log("Resumed")
        self.auto_status("Waiting for Card")
        self.schedule_auto_capture_poll(delay_ms=10)

    def stop_auto_capture_ui(self, set_manual=True):
        if self.auto_capture_after_id:
            try:
                self.after_cancel(self.auto_capture_after_id)
            except Exception:
                pass
            self.auto_capture_after_id = None
        was_running = self.auto_capture_running
        self.auto_capture_running = False
        self.auto_capture_paused = False
        self.auto_capture_pause_reason = ""
        self.reset_auto_capture_detection()
        self.auto_capture_settings["auto_capture_enabled"] = False
        self.auto_capture_settings = save_auto_capture_settings(self.auto_capture_settings)
        if set_manual and hasattr(self, "capture_mode_choice_var"):
            self.capture_mode_choice_var.set("Manual")
        if was_running:
            self.auto_log("Stopped")
        self.auto_status("Manual")

    def schedule_auto_capture_poll(self, delay_ms=None):
        if not self.auto_capture_running:
            return
        if self.auto_capture_after_id:
            try:
                self.after_cancel(self.auto_capture_after_id)
            except Exception:
                pass
        poll_ms = int(self.auto_capture_settings.get("frame_poll_interval_ms", 200))
        self.auto_capture_after_id = self.after(int(delay_ms if delay_ms is not None else poll_ms), self.auto_capture_poll)

    def auto_capture_poll(self):
        self.auto_capture_after_id = None
        if not self.auto_capture_running:
            return
        if self.auto_capture_paused and self.auto_capture_pause_reason != "disconnect":
            return
        try:
            image_bytes = self.capture_service.capture_obs_jpeg()
            if self.auto_capture_pause_reason == "disconnect":
                self.auto_log("OBS Reconnect")
                self.auto_capture_paused = False
                self.auto_capture_pause_reason = ""
                self.auto_capture_logged_disconnect = False
                self.auto_status("Waiting for Card")
                self.reset_auto_capture_detection()
            self.update_capture_obs_indicator("OBS status: connected")
            signature = capture_frame_signature(image_bytes)
            self.process_auto_capture_frame(image_bytes, signature)
        except Exception as exc:
            self.update_capture_obs_indicator(str(exc))
            if not self.auto_capture_logged_disconnect:
                self.auto_log(f"OBS Disconnect: {exc}")
                self.auto_capture_logged_disconnect = True
            self.auto_capture_paused = True
            self.auto_capture_pause_reason = "disconnect"
            self.auto_status("Paused")
        finally:
            self.schedule_auto_capture_poll()

    def process_auto_capture_frame(self, image_bytes, signature):
        now = time.monotonic()
        settings = self.auto_capture_settings
        thresholds = auto_capture_thresholds(settings)
        side = self.capture_service.next_capture_side(self.capture_session)

        if self.auto_capture_baseline_signature is None:
            self.auto_capture_baseline_signature = signature
            self.auto_capture_last_signature = signature
            self.auto_capture_stable_since = now
            self.auto_status("Ready")
            return

        present_score = signature_difference(signature, self.auto_capture_baseline_signature)
        stability_score = signature_difference(signature, self.auto_capture_last_signature)
        self.auto_capture_last_presence_score = present_score
        self.auto_capture_last_stability_score = stability_score
        if hasattr(self, "auto_capture_score_var"):
            self.auto_capture_score_var.set(f"Present score: {present_score:.3f}  |  Stability score: {stability_score:.3f}")

        is_empty = present_score <= thresholds["empty"]
        is_present = present_score >= thresholds["present"]
        stable = stability_score <= thresholds["stable"]
        same_as_last_capture = (
            self.auto_capture_last_capture_signature is not None
            and signature_difference(signature, self.auto_capture_last_capture_signature) <= thresholds["changed"]
        )
        in_lockout = (now - self.auto_capture_last_capture_at) < float(settings.get("duplicate_lockout_seconds", 2.0))

        if is_empty:
            self.auto_capture_baseline_signature = signature
            self.auto_capture_pending_side = None
            self.auto_capture_pending_bytes = None
            self.auto_capture_stable_since = now if stable else None
            self.auto_capture_last_signature = signature
            self.auto_status("Waiting for Card" if side == "front" else "Waiting for Back")
            return

        if not is_present:
            self.auto_capture_last_signature = signature
            self.auto_status("Waiting for Card" if side == "front" else "Waiting for Back")
            return

        if same_as_last_capture or in_lockout:
            self.auto_capture_last_signature = signature
            self.auto_status("Waiting for Back" if side == "back" else "Ready for Next Card")
            return

        expected_status = "Card Detected" if side == "front" else "Back Detected"
        if not stable or self.auto_capture_pending_side != side:
            self.auto_capture_stable_since = now if stable else None
            self.auto_capture_pending_side = side
            self.auto_capture_pending_bytes = image_bytes
            self.auto_capture_last_signature = signature
            self.auto_status("Stabilizing" if stable else expected_status)
            return

        if self.auto_capture_stable_since is None:
            self.auto_capture_stable_since = now
            self.auto_capture_pending_bytes = image_bytes
            self.auto_capture_last_signature = signature
            self.auto_status("Stabilizing")
            return

        if (now - self.auto_capture_stable_since) < float(settings.get("stability_delay_seconds", 1.0)):
            self.auto_capture_pending_bytes = image_bytes
            self.auto_capture_last_signature = signature
            self.auto_status("Stabilizing")
            return

        self.auto_capture_last_signature = signature
        self.perform_auto_capture(side, self.auto_capture_pending_bytes or image_bytes, signature)

    def perform_auto_capture(self, side, image_bytes, signature):
        try:
            self.auto_status("Capturing Front" if side == "front" else "Capturing Back")
            result = self.capture_service.capture_bytes(self.capture_session, side, image_bytes, capture_mode="OBS Auto Capture")
            self.auto_capture_last_capture_at = time.monotonic()
            self.auto_capture_last_capture_signature = signature
            self.auto_capture_pending_side = None
            self.auto_capture_pending_bytes = None
            self.auto_capture_stable_since = None
            label = "Front Captured" if side == "front" else "Back Captured"
            self.auto_log(label)
            append_activity(f"Auto captured {result.path.name} with CardVector Capture Studio")
            self.schedule_capture_thumbnail_refresh()
            if side == "front":
                self.auto_status("Waiting for Back")
            else:
                self.auto_status("Pair Complete")
                self.after(700, lambda: self.auto_status("Ready for Next Card") if self.auto_capture_running and not self.auto_capture_paused else None)
        except Exception as exc:
            self.auto_log(f"Capture Error: {exc}")
            self.auto_status("Capture Error")
            messagebox.showwarning("Auto Capture", f"Automatic capture failed:\n{exc}")

    def start_capture_session_ui(self):
        try:
            self.capture_session = self.capture_service.start_session()
            acquisition = current_acquisition()
            if acquisition:
                self.capture_session.update(acquisition_snapshot(acquisition))
                self.capture_session["batch_location"] = (load_current_session() or {}).get("batch_location", "")
                self.capture_service._save_session(self.capture_session)
            folder = Path(self.capture_session["folder"])
            append_activity(f"Started CardVector Capture Studio session: {folder.name}")
            self.status.set(f"Capture session started: {folder}")
            self.schedule_capture_thumbnail_refresh()
        except Exception as exc:
            messagebox.showerror("Capture Studio", str(exc))

    def capture_next_card_ui(self):
        if not self.capture_session:
            self.start_capture_session_ui()
            if not self.capture_session:
                return
        status = self.capture_service.obs_status()
        if not self.update_capture_obs_indicator(status) and not self.capture_service.allow_placeholder:
            self.status.set("OBS Not Connected. Retry when OBS is ready.")
            messagebox.showwarning("Capture Studio", "OBS Not Connected.\n\nStart OBS or check the saved OBS WebSocket settings, then use Retry.")
            return
        try:
            result = self.capture_service.capture_next(self.capture_session)
            append_activity(f"Captured {result.path.name} with CardVector Capture Studio")
            self.status.set(f"Captured {result.path.name}")
            self.schedule_capture_thumbnail_refresh()
        except CaptureStudioError as exc:
            self.update_capture_obs_indicator(str(exc))
            self.status.set("Capture failed; OBS is not ready.")
            messagebox.showwarning("Capture Studio", str(exc))
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
            append_activity(f"Captured {result.path.name} with CardVector Capture Studio")
            self.status.set(f"Captured {result.path.name}")
            self.schedule_capture_thumbnail_refresh()
        except CaptureStudioError as exc:
            self.status.set("Capture failed; see OBS screenshot error.")
            messagebox.showwarning("Capture Studio", str(exc))
        except Exception as exc:
            messagebox.showerror("Capture Studio", str(exc))

    def capture_next_photo_ui(self):
        self.capture_next_card_ui()

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
            self.schedule_capture_thumbnail_refresh()
        except Exception as exc:
            messagebox.showerror("Capture Studio", str(exc))

    def finish_capture_session_ui(self):
        if not self.capture_session:
            messagebox.showinfo("Capture Studio", "No active capture session.")
            return
        try:
            folder = Path(self.capture_session["folder"])
            self.capture_service.finish_session(self.capture_session)
            append_activity(f"Finished CardVector Capture Studio session: {folder.name}")
            self.status.set(f"Capture session finished: {folder}")
            self.schedule_capture_thumbnail_refresh()
        except Exception as exc:
            messagebox.showerror("Capture Studio", str(exc))

    def open_capture_folder_ui(self):
        folder = (resolve_capture_path(self.capture_session.get("folder", "")) if self.capture_session else None) or CAPTURE_ROOT
        folder.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(folder)
        except Exception as exc:
            messagebox.showinfo("Capture Studio", f"Capture folder:\n{folder}\n\nCould not open automatically:\n{exc}")

    def open_latest_capture_session_folder(self):
        folder = latest_capture_session() or CAPTURE_ROOT
        folder.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(folder)
        except Exception as exc:
            messagebox.showinfo("Capture Studio", f"Capture session folder:\n{folder}\n\nCould not open automatically:\n{exc}")

    def launch_obs_ui(self):
        try:
            launched = self.capture_service.launch_obs()
            self.status.set(f"OBS launch requested: {launched}")
        except CaptureStudioError as exc:
            messagebox.showwarning("Capture Studio", str(exc))
        except Exception as exc:
            messagebox.showerror("Capture Studio", str(exc))

    def check_obs_status_ui(self, silent=False):
        status = self.capture_service.obs_status()
        self.update_capture_obs_indicator(status)
        self.status.set(status)
        if not silent and not obs_status_is_connected(status):
            messagebox.showinfo("Capture Studio", status)

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
        self.label(note, "PICK SLIP OUTPUT", 12, BRAND["gold"], True, anchor="w", padx=18, pady=(12, 4))
        self.label(
            note,
            "Import an eBay orders CSV to generate printable TXT/HTML pick slips. Printing remains manual in this release.",
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
            messagebox.showwarning("CardVector OS", "Decision Engine check completed with warnings.\n\n" + decision_engine_summary_text(result))
        else:
            messagebox.showinfo("CardVector OS", f"Decision Engine check complete.\n\nLog:\n{log_path}")
        append_activity("Decision Engine check complete")

    def inventory_location_registry_panel(self, wrap):
        registry = self.card(wrap, fill="x", pady=(0, 12), ipady=10)
        self.label(registry, "ETB LOCATION REGISTRY", 12, BRAND["gold"], True, anchor="w", padx=18, pady=(12, 4))
        self.label(
            registry,
            "Container registry for physical ETBs. These are storage labels like ETB-001 and do not modify eBay listings or assign real inventory yet.",
            9,
            BRAND["muted"],
            False,
            anchor="w",
            padx=18,
            pady=(0, 8),
        )

        self.etb_registry_summary_var = tk.StringVar(value="")
        tk.Label(
            registry,
            textvariable=self.etb_registry_summary_var,
            bg=BRAND["panel"],
            fg=BRAND["muted"],
            font=("Segoe UI", 9),
            justify="left",
            wraplength=980,
        ).pack(anchor="w", padx=18, pady=(0, 8))

        columns = ("location_code", "status", "assigned", "remaining", "capacity", "batches")
        table_frame = tk.Frame(registry, bg=BRAND["panel"])
        table_frame.pack(fill="x", padx=18, pady=(0, 8))
        self.etb_location_tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=5)
        self.style_treeview(self.etb_location_tree)
        headings = {
            "location_code": "Location Code",
            "status": "Status",
            "assigned": "Estimated Assigned",
            "remaining": "Estimated Remaining",
            "capacity": "Capacity",
            "batches": "Batches Assigned",
        }
        widths = {
            "location_code": 160,
            "status": 120,
            "assigned": 150,
            "remaining": 160,
            "capacity": 100,
            "batches": 280,
        }
        for column in columns:
            self.sortable_heading(self.etb_location_tree, column, headings[column], False, show_arrow=False)
            self.etb_location_tree.column(column, width=widths[column], anchor="w", stretch=True)
        yscroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.etb_location_tree.yview)
        self.etb_location_tree.configure(yscrollcommand=yscroll.set)
        self.etb_location_tree.pack(side="left", fill="x", expand=True)
        yscroll.pack(side="right", fill="y")

        actions = tk.Frame(registry, bg=BRAND["panel"])
        actions.pack(anchor="w", padx=18, pady=(0, 12))
        self.primary_button(actions, "Create Next ETB", self.inventory_create_next_etb).pack(side="left")
        for status in LOCATION_STATUSES:
            self.action_button(actions, f"Mark {status}", lambda s=status: self.inventory_mark_etb_status(s)).pack(side="left", padx=(8, 0))
        self.action_button(actions, "Refresh Counts", self.inventory_refresh_etb_locations).pack(side="left")

        self.inventory_refresh_etb_locations()

    def inventory_label_center_panel(self, wrap):
        panel = self.card(wrap, fill="x", pady=(0, 12), ipady=10)
        self.label(panel, "LABEL CENTER", 12, BRAND["gold"], True, anchor="w", padx=18, pady=(12, 4))
        self.label(
            panel,
            "Generate professional QR labels for storage locations. Labels are PDF exports only; inventory records are not modified.",
            9,
            BRAND["muted"],
            False,
            anchor="w",
            padx=18,
            pady=(0, 8),
        )
        self.label_center_type_var = tk.StringVar(value="ETB Labels")
        self.label_center_status_var = tk.StringVar(value=f"Output folder: {LABEL_EXPORT_ROOT}")
        row = tk.Frame(panel, bg=BRAND["panel"])
        row.pack(fill="x", padx=18, pady=(0, 8))
        self.label(row, "Label type", 9, BRAND["muted"], False, side="left", padx=(0, 8))
        label_menu = tk.OptionMenu(
            row,
            self.label_center_type_var,
            "ETB Labels",
            "Long Box Labels",
            "Binder Spine Labels",
            "Shelf Labels",
            "Card Show Case Labels",
        )
        label_menu.configure(bg=BRAND["panel2"], fg=BRAND["text"], activebackground=BRAND["bronze_hover"], relief="flat", width=22)
        label_menu.pack(side="left")
        self.primary_button(row, "Generate Labels", self.inventory_generate_etb_labels).pack(side="left", padx=10)
        self.action_button(row, "Open Label Folder", self.inventory_open_etb_label_folder).pack(side="left")
        tk.Label(
            panel,
            textvariable=self.label_center_status_var,
            bg=BRAND["panel"],
            fg=BRAND["muted"],
            font=("Segoe UI", 9),
            justify="left",
            wraplength=980,
        ).pack(anchor="w", padx=18, pady=(0, 10))

    def inventory_selected_etb_code(self):
        if not hasattr(self, "etb_location_tree"):
            return ""
        selected = self.etb_location_tree.selection()
        if not selected:
            return ""
        values = self.etb_location_tree.item(selected[0], "values")
        return str(values[0]) if values else ""

    def inventory_refresh_etb_locations(self, select_code=""):
        if not hasattr(self, "etb_location_tree"):
            return
        for item in self.etb_location_tree.get_children():
            self.etb_location_tree.delete(item)
        self.etb_location_tree._base_tags = {}
        rows = etb_location_rows()
        rollups = completed_session_etb_rollups()
        known = {row["location_code"] for row in rows}
        for code, item in rollups.items():
            if code not in known:
                rows.append({
                    "location_code": code,
                    "status": "Available",
                    "estimated_capacity": 100,
                    "estimated_assigned_count": 0,
                    "estimated_remaining_capacity": 100,
                    "created_at": "",
                    "updated_at": "",
                })
        rows = sorted(rows, key=lambda row: row["location_code"])
        selected_item = None
        for row in rows:
            rollup = rollups.get(row["location_code"], {})
            assigned = int(row["estimated_assigned_count"] or 0) + int(rollup.get("assigned", 0) or 0)
            capacity = int(row["estimated_capacity"] or 100)
            values = (
                row["location_code"],
                row["status"],
                assigned,
                max(0, capacity - assigned),
                capacity,
                ", ".join(rollup.get("batches", [])),
            )
            item = self.tree_insert(self.etb_location_tree, "", "end", values=values)
            if select_code and row["location_code"] == select_code:
                selected_item = item
        if selected_item:
            self.etb_location_tree.selection_set(selected_item)
            self.etb_location_tree.see(selected_item)
        next_code = next_etb_code()
        self.etb_registry_summary_var.set(
            f"Registry: {ETB_LOCATION_REGISTRY}\n"
            f"Locations: {len(rows)}  |  Next ETB: {next_code}  |  Default capacity: 100 cards\n"
            "Counts include completed work sessions rolled up by ETB batch location."
        )

    def inventory_create_next_etb(self):
        try:
            location = create_etb_location()
            code = location["location_code"]
            self.inventory_refresh_etb_locations(select_code=code)
            self.status.set(f"Created ETB location {code}.")
        except Exception as exc:
            messagebox.showerror("ETB Location Registry", str(exc))

    def inventory_mark_etb_status(self, status):
        code = self.inventory_selected_etb_code()
        if not code:
            messagebox.showinfo("ETB Location Registry", "Select an ETB location first.")
            return
        try:
            update_etb_status(code, status)
            self.inventory_refresh_etb_locations(select_code=code)
            self.status.set(f"{code} marked {status}.")
        except Exception as exc:
            messagebox.showerror("ETB Location Registry", str(exc))

    def inventory_generate_etb_labels(self):
        label_type = self.label_center_type_var.get() if hasattr(self, "label_center_type_var") else "ETB Labels"
        try:
            result = generate_inventory_label_pdf(label_type)
            status = f"Generated {result['count']} {label_type} label(s).\nPDF: {result['pdf']}"
            if hasattr(self, "label_center_status_var"):
                self.label_center_status_var.set(status)
            self.status.set(f"Generated {result['count']} inventory label(s).")
            append_label_generation_log(f"SUCCESS | {label_type} | {result['count']} labels | {result['pdf']}")
            messagebox.showinfo(
                "Inventory Label Center",
                "Printable QR labels generated.\n\n"
                f"PDF:\n{result['pdf']}\n\n"
                f"Folder:\n{result['output_dir']}\n\n"
                "Use Open Label Folder when you are ready to view or print labels.",
            )
        except SystemExit as exc:
            message = (
                "Label generation could not complete.\n\n"
                "qrcode[pil] and reportlab are required.\n\n"
                'Install with:\npy -m pip install "qrcode[pil]" reportlab'
            )
            append_label_generation_log(f"ERROR | {label_type} | SystemExit: {exc}", exc)
            if hasattr(self, "label_center_status_var"):
                self.label_center_status_var.set(message)
            self.status.set("Inventory label generation failed.")
            messagebox.showerror("Inventory Label Center", message)
        except Exception as exc:
            message = str(exc) or "Label generation failed."
            append_label_generation_log(f"ERROR | {label_type} | {message}", exc)
            if hasattr(self, "label_center_status_var"):
                self.label_center_status_var.set(message)
            self.status.set("Inventory label generation failed.")
            messagebox.showerror("Inventory Label Center", message)

    def inventory_open_etb_label_folder(self):
        LABEL_EXPORT_ROOT.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(LABEL_EXPORT_ROOT)
        except Exception as exc:
            messagebox.showinfo("Inventory Label Center", f"Label folder:\n{LABEL_EXPORT_ROOT}\n\nCould not open automatically:\n{exc}")

    def inventory_page(self):
        self.header("Inventory", "Inventory Audit verifies physical cards and trusted Batch Locations before any eBay revision.")
        wrap = tk.Frame(self.main, bg=BRAND["bg"])
        wrap.pack(fill="both", expand=True, padx=34, pady=0)

        self.inventory_location_registry_panel(wrap)
        self.inventory_label_center_panel(wrap)

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
        game_menu.configure(bg=BRAND["panel2"], fg=BRAND["text"], activebackground=BRAND["bronze_hover"], relief="flat", width=12)
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
        self.primary_button(setup_actions, "Start New Audit", self.inventory_start_audit).pack(side="left")
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
        self.primary_button(actions, "Mark Confirmed", lambda: self.inventory_apply_action("confirm")).pack(side="left")
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
            messagebox.showinfo("CardVector OS", "No eBay Active Listings CSV found in eBay Store Items.")
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
            messagebox.showinfo("CardVector OS", "Choose an inventory source first.")
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
            messagebox.showerror("CardVector OS", str(exc))

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
            messagebox.showinfo("CardVector OS", "No saved inventory audit session found.")
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
            messagebox.showinfo("CardVector OS", "Load or resume an audit queue first.")
            return
        try:
            self.inventory_audit_session = apply_inventory_audit_action(session, action, self.inventory_notes_var.get())
            self.inventory_update_queue_view()
            self.status.set(f"Inventory audit saved: {action}.")
        except Exception as exc:
            messagebox.showerror("CardVector OS", str(exc))

    def inventory_use_last_location(self):
        session = getattr(self, "inventory_audit_session", None)
        if not session:
            messagebox.showinfo("CardVector OS", "Load or resume an audit queue first.")
            return
        self.inventory_new_location_var.set(session.get("last_location") or session.get("batch_location", ""))

    def inventory_save_location(self):
        session = getattr(self, "inventory_audit_session", None)
        if not session:
            messagebox.showinfo("CardVector OS", "Load or resume an audit queue first.")
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
            messagebox.showerror("CardVector OS", str(exc))

    def inventory_save_progress(self):
        session = getattr(self, "inventory_audit_session", None)
        if not session:
            messagebox.showinfo("CardVector OS", "Load or resume an audit queue first.")
            return
        try:
            self.inventory_audit_session = save_inventory_audit_progress(session, self.inventory_notes_var.get())
            self.inventory_update_queue_view()
            stats = inventory_audit_stats(self.inventory_audit_session)
            messagebox.showinfo("Audit Progress", self.inventory_summary_text(self.inventory_audit_session, stats))
            self.status.set("Inventory audit progress saved.")
        except Exception as exc:
            messagebox.showerror("CardVector OS", str(exc))

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
            messagebox.showinfo("CardVector OS", "No inventory audit session found.")
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
            messagebox.showerror("CardVector OS", str(exc))

    def launch_capture_studio(self):
        self.show_page("Capture")
        append_activity("Opened CardVector Capture Studio tab for inventory audit verification")
        self.status.set("CardVector Capture Studio is open. Use it to save internal verification JPEGs only.")

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
            messagebox.showinfo("CardVector OS", "No CSV found in Imports, Incoming Files, or Downloads.\nUse Browse for CSV or drop a CardUploader CSV on Home.")
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
                "CardVector OS",
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
            messagebox.showerror("CardVector OS", str(e))

    def open_inventory_snapshot(self):
        if INVENTORY_SNAPSHOT.exists():
            os.startfile(INVENTORY_SNAPSHOT)
        else:
            messagebox.showinfo("CardVector OS", f"No inventory snapshot found yet.\n\nExpected path:\n{INVENTORY_SNAPSHOT}")

    def on_drop(self, event):
        raw = event.data
        # Handles {C:\path with spaces\file.csv}
        paths = self.tk.splitlist(raw)
        if not paths:
            return
        p = paths[0]
        if not str(p).lower().endswith(".csv"):
            messagebox.showwarning("CardVector OS", "Please drop a CSV file.")
            return
        if getattr(self, "current_page", "") == "Import":
            self.import_carduploader_csv_path(p)
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
            messagebox.showinfo("CardVector OS", "Work session canceled because batch location was blank.")
            return
        try:
            batch_location = validate_location(batch_location)
        except ValueError as exc:
            messagebox.showerror("CardVector OS", str(exc))
            return
        method = simpledialog.askstring("Work Session", "Capture method:", initialvalue="iPhone camera") or "iPhone camera"
        folder = create_work_session(goal, planned, method, game, batch_location)
        session = load_current_session() or {}
        acquisition_line = session.get("acquisition_name") or "No Acquisition"
        messagebox.showinfo("CardVector OS", f"Work session started:\n{folder}\n\nAcquisition: {acquisition_line}")
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
            messagebox.showinfo("CardVector OS", f"Work session ended:\n{folder}")
            try:
                os.startfile(folder)
            except Exception:
                pass
        else:
            messagebox.showwarning("CardVector OS", "No active work session found.")
        self.show_page("Sessions")

    def run_split_recording_tool(self):
        tool = TOOLS / "Split_Putnam_Work_Session.ps1"
        if not tool.exists():
            messagebox.showwarning("CardVector OS", f"Split tool not found:\n{tool}")
            return
        try:
            subprocess.Popen(["powershell", "-ExecutionPolicy", "Bypass", "-File", str(tool)], cwd=str(ROOT))
            append_activity("Launched split work session tool")
        except Exception as e:
            messagebox.showerror("CardVector OS", str(e))

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

    def settings_page(self):
        self.header("Settings", "Configure local CardVector OS settings.")
        wrap = tk.Frame(self.main, bg=BRAND["bg"])
        wrap.pack(fill="both", expand=True, padx=34, pady=0)
        panel = self.card(wrap, fill="x", ipady=14)
        self.label(panel, "OBS WEBSOCKET", 12, BRAND["gold"], True, anchor="w", padx=18, pady=(12, 8))
        obs_config = load_obs_config()
        self.obs_host_var = tk.StringVar(value=str(obs_config.get("obs_host", "127.0.0.1")))
        self.obs_port_var = tk.StringVar(value=str(obs_config.get("obs_port", 4455)))
        self.obs_password_var = tk.StringVar(value=str(obs_config.get("obs_password", "")))
        for label_text, var, show in [
            ("Host", self.obs_host_var, ""),
            ("Port", self.obs_port_var, ""),
            ("Password", self.obs_password_var, "*"),
        ]:
            row = tk.Frame(panel, bg=BRAND["panel"])
            row.pack(fill="x", padx=18, pady=4)
            self.label(row, label_text, 9, BRAND["muted"], False, side="left", padx=(0, 8))
            entry = tk.Entry(row, textvariable=var, bg=BRAND["panel2"], fg=BRAND["text"], insertbackground=BRAND["text"], relief="flat", show=show)
            entry.pack(side="left", fill="x", expand=True)
        self.label(
            panel,
            f"Saved locally at {OBS_CONFIG_PATH}. Exact keys: obs.host, obs.port, obs.password. PUTNAM_OBS_PASSWORD overrides the saved password.",
            9,
            BRAND["muted"],
            False,
            anchor="w",
            padx=18,
            pady=(8, 8),
        )
        btns = tk.Frame(panel, bg=BRAND["panel"])
        btns.pack(anchor="w", padx=18, pady=(0, 12))
        self.action_button(btns, "Save OBS Settings", self.save_obs_settings_ui).pack(side="left")
        self.action_button(btns, "Check OBS Status", self.check_obs_status_ui).pack(side="left", padx=8)

        ebay_panel = self.card(wrap, fill="x", pady=(14, 0), ipady=14)
        self.label(ebay_panel, "EBAY BUSINESS POLICIES", 12, BRAND["gold"], True, anchor="w", padx=18, pady=(12, 8))
        policies = load_ebay_business_policies()
        self.ebay_shipping_policy_var = tk.StringVar(value=policies.get("shipping_policy", ""))
        self.ebay_payment_policy_var = tk.StringVar(value=policies.get("payment_policy", ""))
        self.ebay_return_policy_var = tk.StringVar(value=policies.get("return_policy", ""))
        for label_text, var in [
            ("Shipping policy", self.ebay_shipping_policy_var),
            ("Payment policy", self.ebay_payment_policy_var),
            ("Return policy", self.ebay_return_policy_var),
        ]:
            row = tk.Frame(ebay_panel, bg=BRAND["panel"])
            row.pack(fill="x", padx=18, pady=4)
            self.label(row, label_text, 9, BRAND["muted"], False, side="left", padx=(0, 8))
            tk.Entry(row, textvariable=var, bg=BRAND["panel2"], fg=BRAND["text"],
                     insertbackground=BRAND["text"], relief="flat").pack(side="left", fill="x", expand=True)
        self.label(
            ebay_panel,
            f"Saved locally at {EBAY_BUSINESS_POLICIES_CONFIG}. Export stops if any required policy is blank.",
            9,
            BRAND["muted"],
            False,
            anchor="w",
            padx=18,
            pady=(8, 8),
        )
        ebay_btns = tk.Frame(ebay_panel, bg=BRAND["panel"])
        ebay_btns.pack(anchor="w", padx=18, pady=(0, 12))
        self.action_button(ebay_btns, "Save eBay Policies", self.save_ebay_policies_ui).pack(side="left")

        app_panel = self.card(wrap, fill="x", pady=(14, 0), ipady=14)
        self.label(app_panel, "CARDUPLOADER", 12, BRAND["gold"], True, anchor="w", padx=18, pady=(12, 8))
        app_config = load_app_config()
        self.carduploader_url_var = tk.StringVar(value=app_config.get("carduploader_url", ""))
        row = tk.Frame(app_panel, bg=BRAND["panel"])
        row.pack(fill="x", padx=18, pady=4)
        self.label(row, "carduploader_url", 9, BRAND["muted"], False, side="left", padx=(0, 8))
        tk.Entry(row, textvariable=self.carduploader_url_var, bg=BRAND["panel2"], fg=BRAND["text"],
                 insertbackground=BRAND["text"], relief="flat").pack(side="left", fill="x", expand=True)
        self.label(
            app_panel,
            f"Saved locally at {APP_CONFIG_PATH}. Leave blank to disable the Open CardUploader button.",
            9,
            BRAND["muted"],
            False,
            anchor="w",
            padx=18,
            pady=(8, 8),
        )
        app_btns = tk.Frame(app_panel, bg=BRAND["panel"])
        app_btns.pack(anchor="w", padx=18, pady=(0, 12))
        self.action_button(app_btns, "Save CardUploader URL", self.save_carduploader_settings_ui).pack(side="left")
        self.action_button(app_btns, "Open CardUploader", self.open_carduploader).pack(side="left", padx=8)
        self.action_button(app_btns, "About CardVector OS", self.show_about_dialog).pack(side="left")

    def save_obs_settings_ui(self):
        try:
            host = self.obs_host_var.get().strip() or "127.0.0.1"
            port = int((self.obs_port_var.get() or "4455").strip())
            password = self.obs_password_var.get()
            save_obs_config(host, port, password)
            self.status.set(f"OBS settings saved to {OBS_CONFIG_PATH}")
            append_activity("Updated local OBS WebSocket settings")
            messagebox.showinfo("CardVector OS Settings", "OBS settings saved.")
        except Exception as exc:
            self.status.set("Could not save OBS settings.")
            messagebox.showerror("CardVector OS Settings", str(exc))

    def save_ebay_policies_ui(self):
        try:
            policies = {
                "shipping_policy": self.ebay_shipping_policy_var.get(),
                "payment_policy": self.ebay_payment_policy_var.get(),
                "return_policy": self.ebay_return_policy_var.get(),
            }
            save_ebay_business_policies(policies)
            self.status.set(f"eBay business policies saved to {EBAY_BUSINESS_POLICIES_CONFIG}")
            append_activity("Updated local eBay business policy settings")
            messagebox.showinfo("CardVector OS Settings", "eBay business policies saved.")
        except Exception as exc:
            self.status.set("Could not save eBay business policies.")
            messagebox.showerror("CardVector OS Settings", str(exc))

    def save_carduploader_settings_ui(self):
        try:
            save_app_config({"carduploader_url": self.carduploader_url_var.get()})
            self.status.set(f"CardUploader URL saved to {APP_CONFIG_PATH}")
            append_activity("Updated local CardUploader URL setting")
            messagebox.showinfo("CardVector OS Settings", "CardUploader URL saved.")
        except Exception as exc:
            self.status.set("Could not save CardUploader URL.")
            messagebox.showerror("CardVector OS Settings", str(exc))

    def show_about_dialog(self):
        messagebox.showinfo(
            "About CardVector OS",
            f"CardVector OS v{APP_VERSION}\n{PLATFORM_VERSION}\n\n"
            "CardVector OS orchestrates Capture Studio, Pricing Engine, inventory, "
            "business intelligence, and workflow guidance.\n\n"
            "Putnam Collectibles is the operating business. CardUploader owns card recognition and listing generation.",
        )

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
            checklist.write_text("""CardVector Workflow Recording Checklist

1. Open OBS.
2. Select scene: Workflow Analysis.
3. Confirm desktop capture and cameras.
4. Confirm microphone levels.
5. Start Recording.
6. Work naturally. Do not stop for mistakes.
7. Stop recording when the session is done.
8. Use CardVector Platform splitter if the file is too large.
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
            messagebox.showinfo("CardVector OS", "Output folder: Not generated yet.")
            return
        os.startfile(self.current_pricing_job)

    def copy_current_output_folder(self):
        path = str(self.current_pricing_job or "")
        if not path:
            self.status.set("Output folder: Not generated yet.")
            messagebox.showinfo("CardVector OS", "Output folder: Not generated yet.")
            return
        self.clipboard_clear()
        self.clipboard_append(path)
        self.status.set("Output folder copied.")

    def open_pricing_report(self, key, title):
        path = self.current_pricing_reports.get(key)
        if not path or not path.exists():
            self.status.set(f"{title}: Not generated yet.")
            messagebox.showinfo("CardVector OS", f"{title}: Not generated yet.")
            return
        if path.suffix.lower() == ".csv":
            self.show_csv_report(path, title)
        else:
            self.show_text_report(path, title)

    def show_text_report(self, path, title):
        win = tk.Toplevel(self)
        win.title(title)
        win.geometry("920x560")
        win.configure(bg=BRAND["bg"])
        frame = tk.Frame(win, bg=BRAND["bg"])
        frame.pack(fill="both", expand=True)
        text = tk.Text(frame, wrap="word", font=("Consolas", 10), bg=BRAND["panel"], fg=BRAND["text"], insertbackground=BRAND["text"], relief="flat")
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
        win.configure(bg=BRAND["bg"])
        frame = tk.Frame(win, bg=BRAND["bg"])
        frame.pack(fill="both", expand=True)
        columns = list(rows[0].keys()) if rows else []
        tree = ttk.Treeview(frame, columns=columns, show="headings")
        self.style_treeview(tree)
        yscroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        xscroll = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        for column in columns:
            width = 260 if column in {"candidate_title", "rejection_details", "Search Query Used"} else 130
            self.sortable_heading(tree, column, column, False, show_arrow=False)
            tree.column(column, width=width, minwidth=90, stretch=True, anchor="w")
        for row in rows:
            self.tree_insert(tree, "", "end", values=[str(row.get(column, "")) for column in columns])
        tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        if not rows:
            tk.Label(win, text="No rows in this report.", font=("Segoe UI", 10)).pack(pady=8)

    def sort_report_tree(self, tree, column, reverse, label=None):
        label = str(label or column)
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
            tag = "even" if index % 2 == 0 else "odd"
            tree.item(item, tags=(tag,))
            if hasattr(tree, "_base_tags"):
                tree._base_tags[item] = (tag,)
        self.sortable_heading(tree, column, label, reverse)

    def pricing_page(self):
        self.header("Pricing & Decisions", "Analyze CardUploader exports, validate pricing, and prepare upload-ready eBay CSV files.")
        wrap = tk.Frame(self.main, bg=BRAND["bg"])
        wrap.pack(fill="both", expand=True, padx=34, pady=0)
        self.build_acquisition_panel(wrap, "ACQUISITION SUMMARY")

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
        self.primary_button(actions, "Analyze & Prepare eBay CSV", self.auto_run).pack(side="left")
        self.action_button(actions, "Open Completed Jobs", lambda: os.startfile(COMPLETED)).pack(side="left", padx=12)
        self.action_button(actions, "Open Incoming Files", lambda: os.startfile(INCOMING)).pack(side="left")
        self.pricing_action_button = actions.winfo_children()[0]

        reports = self.card(wrap, fill="x", pady=(0, 16), ipady=10)
        self.label(reports, "PRICING SUMMARY", 12, BRAND["gold"], True, anchor="w", padx=18, pady=(12, 6))
        self.label(
            reports,
            "Cards analyzed, pricing changes, market opportunities, export path, and decision details appear here after analysis.",
            9,
            BRAND["muted"],
            False,
            anchor="w",
            padx=18,
            pady=(0, 8),
        )
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

        complete = self.card(wrap, fill="x", pady=(12, 16), ipady=10)
        self.label(complete, "PRICING COMPLETE", 12, BRAND["gold"], True, anchor="w", padx=18, pady=(12, 4))
        self.label(
            complete,
            "When analysis is complete, the batch is ready for CardUploader/eBay upload.",
            9,
            BRAND["muted"],
            False,
            anchor="w",
            padx=18,
            pady=(0, 10),
        )
        complete_buttons = tk.Frame(complete, bg=BRAND["panel"])
        complete_buttons.pack(anchor="w", padx=18, pady=(0, 12))
        self.action_button(complete_buttons, "Open Pricing Output Folder", self.open_current_output_folder).pack(side="left")
        self.action_button(complete_buttons, "Open CardUploader", self.open_carduploader).pack(side="left", padx=8)
        self.action_button(complete_buttons, "Open Exports", lambda: os.startfile(EXPORTS)).pack(side="left")
        self.action_button(complete_buttons, "Return Home", lambda: self.show_page("Home")).pack(side="left", padx=8)

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
            "Pricing & Decisions",
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
        return messagebox.askyesno("CardVector Pricing Engine", message)

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
                    messagebox.showerror("CardVector OS", message)
                    return
                if validation_warnings:
                    warning_text = "\n".join(dict.fromkeys(validation_warnings))
                    self.status.set(warning_text)
                    messagebox.showwarning("CardVector OS", warning_text)
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
                acquisition = current_acquisition()
                acquisition_status = ""
                if acquisition:
                    acquisition_status = (
                        f"\nAcquisition: {acquisition.get('acquisition_name', '')}"
                        f"\nPurchase price: ${acquisition.get('purchase_price', '0.00')}"
                        f"\nEstimated listing value: ${export_summary.get('estimated_listing_value', '0.00')}"
                        "\nEstimated break-even progress: placeholder"
                    )
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
                        f"{acquisition_status}\n"
                        f"Runtime: {runtime_text or 'n/a'}\n"
                        f"Output: {job}"
                    )
                except Exception:
                    pass
                self.status.set(comp_status.replace("\n", " "))
                messagebox.showinfo(
                    "CardVector OS",
                    f"Analysis complete.\nRows: {rows}\nOptimized price changes: {changes}\n"
                    f"Cart sweeteners: {export_summary['cart_sweetener_count']}\n"
                    f"Market opportunities: {opp}\n"
                    f"{acquisition_status}\n"
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
                messagebox.showwarning("CardVector OS", "This workflow currently analyzes CardUploader new-listing CSVs. Existing listing revision support remains available through the pricing engine.")
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
            messagebox.showinfo("CardVector OS", str(e))
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
            messagebox.showerror("CardVector OS", str(e))
        finally:
            self.set_pricing_busy(False)
            self.pricing_started_at = None


if __name__ == "__main__":
    print(f"{APP_NAME} v{APP_VERSION} - {PLATFORM_VERSION}")
    append_activity(f"CardVector OS launched v{APP_VERSION}")
    PutnamOS().mainloop()

