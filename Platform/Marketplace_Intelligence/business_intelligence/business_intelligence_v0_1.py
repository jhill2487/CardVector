from __future__ import annotations

import argparse
import csv
import os
import re
import statistics
from datetime import datetime
from pathlib import Path


VERSION = "Business Intelligence & Action Queue v0.1"
APP_NAME = "Putnam OS - Business Intelligence & Action Queue v0.1"

# Business cost constants. Keep these visible and easy to tune.
CONFIG = {
    "envelope_cost": 0.02,
    "penny_sleeve_cost": 0.01,
    "shipping_shield_cost": 0.088,
    "team_bag_cost": 0.05,
    "ese_1oz": 0.74,
    "ese_2oz": 1.03,
    "ese_3oz": 1.32,
    "max_cards_ese": 15,
    "free_shipping_threshold_items": 3,
}

ACTION_FIELDS = [
    "priority_score",
    "priority_label",
    "module",
    "action",
    "reason",
    "estimated_time_minutes",
    "expected_impact",
    "source_file",
    "status",
]

KPI_FIELDS = [
    "timestamp",
    "active_listings",
    "orders",
    "items_sold",
    "cards_per_order",
    "average_order_value",
    "revenue_per_envelope",
    "missing_user_sku_count",
    "free_shipping_suspected_count",
    "title_issue_count",
    "pricing_issue_count",
]


def userprofile_root() -> Path:
    profile = Path(os.environ.get("USERPROFILE", str(Path.home())))
    return profile / "OneDrive" / "PutnamCollectibles"


def script_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in current.parents:
        if (candidate / "AGENTS.md").exists() and (candidate / "Docs").exists():
            return candidate
    return userprofile_root()


ROOT = script_root()
LEGACY_TOOLS = ROOT / "Putnam_Seller_Tools"
BI_DIR = LEGACY_TOOLS / "putnam_os" / "business_intelligence"
REPORTS_DIR = BI_DIR / "reports"

INPUT_GROUPS = {
    "eBay Store Items": [
        ROOT / "eBay Store Items",
        ROOT / "Business" / "eBay_Store_Items",
    ],
    "seller_audit_reports": [
        LEGACY_TOOLS / "seller_audit" / "reports",
        ROOT / "Platform" / "Putnam_OS" / "Putnam_Seller_Tools" / "seller_audit" / "reports",
    ],
    "listing_optimizer": [
        LEGACY_TOOLS / "listing_optimizer",
        ROOT / "Platform" / "Putnam_OS" / "Putnam_Seller_Tools" / "listing_optimizer",
        ROOT / "Platform" / "Putnam_OS" / "Completed Jobs",
        ROOT / "Data" / "Exports",
    ],
    "comp_engine": [
        LEGACY_TOOLS / "comp_engine",
        ROOT / "Platform" / "Putnam_OS" / "Completed Jobs",
        ROOT / "Work_Sessions",
    ],
    "carduploader_inventory": [
        ROOT / "Data" / "Imports" / "CardUploader_Inventory",
    ],
    "logs": [
        ROOT / "Data" / "Logs",
    ],
}


def read_csv_rows(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    for enc in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            with path.open(newline="", encoding=enc) as f:
                reader = csv.DictReader(f)
                return list(reader), list(reader.fieldnames or [])
        except UnicodeDecodeError:
            continue
    with path.open(newline="", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f)
        return list(reader), list(reader.fieldnames or [])


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def money(value: object) -> float:
    try:
        return float(str(value or "").replace("$", "").replace(",", "").strip() or 0)
    except Exception:
        return 0.0


def truthy(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def latest_file(paths: list[Path], pattern: str) -> Path | None:
    files: list[Path] = []
    for base in paths:
        if base.exists():
            files.extend([p for p in base.rglob(pattern) if p.is_file()])
    if not files:
        return None
    return max(files, key=lambda p: p.stat().st_mtime)


def load_report(path: Path | None, files_used: list[str], metrics_missing: list[str]) -> tuple[list[dict[str, str]], list[str]]:
    if not path or not path.exists():
        metrics_missing.append("Missing report file.")
        return [], []
    try:
        rows, fields = read_csv_rows(path)
        files_used.append(str(path))
        return rows, fields
    except Exception as exc:
        metrics_missing.append(f"Could not read {path}: {exc}")
        return [], []


def parse_summary_metrics(summary_path: Path | None, files_used: list[str]) -> dict[str, int]:
    values: dict[str, int] = {}
    if not summary_path or not summary_path.exists():
        return values
    files_used.append(str(summary_path))
    text = summary_path.read_text(encoding="utf-8-sig", errors="replace")
    patterns = {
        "active_listings": r"Total active listings:\s*([0-9,]+)",
        "free_shipping_suspected_count": r"Free shipping suspected:\s*([0-9,]+)",
        "missing_user_sku_count": r"Missing User SKU count:\s*([0-9,]+)",
        "invalid_user_sku_count": r"Invalid User SKU count:\s*([0-9,]+)",
        "duplicate_title_rows": r"Duplicate title rows:\s*([0-9,]+)",
        "listings_at_0_99": r"Listings at \$0\.99:\s*([0-9,]+)",
        "listings_under_1_49": r"Listings under \$1\.49:\s*([0-9,]+)",
        "high_price_manual_review_count": r"High price manual review count:\s*([0-9,]+)",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            values[key] = int(match.group(1).replace(",", ""))
    return values


def count_price_flags(rows: list[dict[str, str]]) -> tuple[int, int, int]:
    at_099 = 0
    under_149 = 0
    under_099 = 0
    for row in rows:
        if truthy(row.get("price_equal_0_99")):
            at_099 += 1
        if truthy(row.get("price_under_1_49")):
            under_149 += 1
        if truthy(row.get("price_under_0_99")):
            under_099 += 1
    return at_099, under_149, under_099


def priority_label(score: int) -> str:
    if score >= 100:
        return "Critical"
    if score >= 90:
        return "Blocker"
    if score >= 80:
        return "Cash Flow"
    if score >= 70:
        return "Warehouse"
    if score >= 60:
        return "SEO"
    return "Cleanup"


def add_action(actions: list[dict[str, object]], score: int, module: str, action: str, reason: str,
               minutes: int, impact: str, source_file: Path | str | None) -> None:
    actions.append({
        "priority_score": score,
        "priority_label": priority_label(score),
        "module": module,
        "action": action,
        "reason": reason,
        "estimated_time_minutes": minutes,
        "expected_impact": impact,
        "source_file": str(source_file or ""),
        "status": "open",
    })


def build_action_queue(metrics: dict[str, object], sources: dict[str, Path | None]) -> list[dict[str, object]]:
    actions: list[dict[str, object]] = []
    missing_sku = int(metrics.get("missing_user_sku_count") or 0)
    invalid_sku = int(metrics.get("invalid_user_sku_count") or 0)
    sku_total = missing_sku + invalid_sku
    if sku_total:
        add_action(
            actions,
            90,
            "Warehouse / Location",
            "Assign User SKU to listings missing warehouse location",
            f"{sku_total} listings have missing or invalid User SKU / location values.",
            max(20, min(240, round(sku_total * 0.35))),
            "Faster picking, fewer listing mistakes, cleaner bulk revise workflow.",
            sources.get("missing_sku"),
        )
    free_shipping = int(metrics.get("free_shipping_suspected_count") or 0)
    if free_shipping:
        add_action(
            actions,
            100,
            "Shipping",
            "Review suspected free-shipping listings",
            f"{free_shipping} listings may not follow buyer-paid shipping policy.",
            max(10, min(120, free_shipping)),
            "Protects profit per envelope and prevents margin leakage.",
            sources.get("free_shipping"),
        )
    price_099 = int(metrics.get("listings_at_0_99") or 0)
    under_149 = int(metrics.get("listings_under_1_49") or 0)
    if under_149:
        add_action(
            actions,
            80,
            "Pricing",
            "Review $0.99 and under-$1.49 listings",
            f"{under_149} listings are under $1.49; {price_099} are exactly $0.99.",
            max(20, min(180, round(under_149 * 0.25))),
            "Improves cash flow and validates cart-sweetener strategy.",
            sources.get("pricing"),
        )
    title_issues = int(metrics.get("title_issue_count") or 0)
    duplicate_titles = int(metrics.get("duplicate_title_rows") or 0)
    if title_issues or duplicate_titles:
        add_action(
            actions,
            60,
            "Title / SEO",
            "Fix title issues and duplicate titles",
            f"{title_issues} title audit issues and {duplicate_titles} duplicate-title rows were found.",
            max(15, min(180, round((title_issues + duplicate_titles) * 0.5))),
            "Improves search quality and reduces duplicate listing confusion.",
            sources.get("title"),
        )
    if int(metrics.get("high_price_manual_review_count") or 0):
        add_action(
            actions,
            80,
            "Pricing",
            "Review high-value listings manually",
            f"{metrics.get('high_price_manual_review_count')} high-price listings need human review.",
            30,
            "Protects high-value inventory from pricing mistakes.",
            sources.get("pricing"),
        )
    latest_export_count = int(metrics.get("latest_export_rows") or 0)
    if latest_export_count:
        add_action(
            actions,
            80,
            "Listing Pipeline",
            "Publish current prepared batch",
            f"Latest eBay-ready export has {latest_export_count} rows.",
            15,
            "Turns prepared inventory into active listings and cash-flow opportunity.",
            sources.get("latest_export"),
        )
    if not actions:
        add_action(
            actions,
            40,
            "Business Intelligence",
            "Add fresher seller audit, order, and listing reports",
            "No urgent actions were detected from available data.",
            15,
            "Improves the next BI snapshot and action queue.",
            "",
        )
    actions.sort(key=lambda row: int(row["priority_score"]), reverse=True)
    return actions


def collect_metrics() -> tuple[dict[str, object], dict[str, Path | None], list[str], list[str], list[str], dict[str, list[str]]]:
    files_used: list[str] = []
    metrics_missing: list[str] = []
    observations: list[str] = []
    column_notes: dict[str, list[str]] = {}
    sources: dict[str, Path | None] = {}
    metrics: dict[str, object] = {
        "active_listings": "",
        "orders": "",
        "items_sold": "",
        "cards_per_order": "",
        "average_order_value": "",
        "revenue_per_envelope": "",
        "missing_user_sku_count": 0,
        "free_shipping_suspected_count": 0,
        "title_issue_count": 0,
        "pricing_issue_count": 0,
        "invalid_user_sku_count": 0,
        "duplicate_title_rows": 0,
        "listings_at_0_99": 0,
        "listings_under_1_49": 0,
        "high_price_manual_review_count": 0,
        "latest_export_rows": 0,
        "listing_export_batches": 0,
        "listing_export_rows": 0,
    }

    audit_paths = INPUT_GROUPS["seller_audit_reports"]
    summary_path = latest_file(audit_paths, "putnam_seller_audit_summary.txt")
    sources["audit_summary"] = summary_path
    metrics.update(parse_summary_metrics(summary_path, files_used))
    if not summary_path:
        metrics_missing.append("Seller audit summary was not found.")

    missing_sku_path = latest_file(audit_paths, "missing_or_invalid_user_sku.csv")
    sources["missing_sku"] = missing_sku_path
    sku_rows, sku_fields = load_report(missing_sku_path, files_used, metrics_missing)
    if sku_rows:
        metrics["missing_user_sku_count"] = sum(1 for row in sku_rows if str(row.get("sku_issue", "")).lower() == "missing")
        metrics["invalid_user_sku_count"] = sum(1 for row in sku_rows if str(row.get("sku_issue", "")).lower() != "missing")
    if sku_fields and "sku_issue" not in sku_fields:
        column_notes[str(missing_sku_path)] = sku_fields

    free_shipping_path = latest_file(audit_paths, "free_shipping_listings.csv")
    sources["free_shipping"] = free_shipping_path
    free_rows, free_fields = load_report(free_shipping_path, files_used, metrics_missing)
    if free_rows and free_fields != ["note"]:
        metrics["free_shipping_suspected_count"] = len(free_rows)
    elif free_fields == ["note"]:
        observations.append("Shipping policy columns were not available in seller audit data.")

    title_path = latest_file(audit_paths, "title_audit.csv")
    duplicate_path = latest_file(audit_paths, "duplicate_titles.csv")
    sources["title"] = title_path or duplicate_path
    title_rows, title_fields = load_report(title_path, files_used, metrics_missing)
    duplicate_rows, duplicate_fields = load_report(duplicate_path, files_used, metrics_missing)
    metrics["title_issue_count"] = len(title_rows)
    metrics["duplicate_title_rows"] = len(duplicate_rows)
    if title_fields and "title_issue" not in title_fields:
        column_notes[str(title_path)] = title_fields

    pricing_path = latest_file(audit_paths, "pricing_audit.csv")
    sources["pricing"] = pricing_path
    pricing_rows, pricing_fields = load_report(pricing_path, files_used, metrics_missing)
    if pricing_rows:
        at_099, under_149, under_099 = count_price_flags(pricing_rows)
        metrics["listings_at_0_99"] = metrics.get("listings_at_0_99") or at_099
        metrics["listings_under_1_49"] = metrics.get("listings_under_1_49") or under_149
        metrics["pricing_issue_count"] = len(pricing_rows)
        if under_099:
            observations.append(f"{under_099} listings appear below the current floor price.")
    if pricing_fields and "price_under_1_49" not in pricing_fields:
        column_notes[str(pricing_path)] = pricing_fields

    export_history_path = latest_file(INPUT_GROUPS["logs"], "export_history.csv")
    sources["export_history"] = export_history_path
    export_rows, _export_fields = load_report(export_history_path, files_used, metrics_missing)
    if export_rows:
        metrics["listing_export_batches"] = len(export_rows)
        metrics["listing_export_rows"] = sum(int(float(row.get("total_listings") or 0)) for row in export_rows)

    latest_export = latest_file(INPUT_GROUPS["listing_optimizer"], "ebay_upload_ready*.csv")
    sources["latest_export"] = latest_export
    export_ready_rows, export_ready_fields = load_report(latest_export, files_used, metrics_missing)
    if export_ready_rows:
        metrics["latest_export_rows"] = len(export_ready_rows)
    if export_ready_fields:
        sku_columns = [c for c in export_ready_fields if c.lower() in {"customlabel", "*customlabel", "user sku", "inventory location", "custom label (sku)"}]
        if not sku_columns:
            column_notes[str(latest_export)] = export_ready_fields

    if metrics.get("active_listings") in ("", None):
        if sku_rows:
            metrics["active_listings"] = len(sku_rows)
            observations.append("Active listing count was estimated from SKU audit rows because no total was available.")
        else:
            metrics_missing.append("Active listings count was not available.")

    if metrics.get("orders") in ("", None):
        metrics_missing.append("Order count was not available from current reports.")
    if metrics.get("items_sold") in ("", None):
        metrics_missing.append("Sold item/card count was not available from current reports.")
    if metrics.get("average_order_value") in ("", None):
        metrics_missing.append("Average order value was not available from current reports.")
    if not latest_file(INPUT_GROUPS["listing_optimizer"], "*orders*.csv"):
        metrics_missing.append("No dedicated orders/sales export was found.")
    if not latest_file(INPUT_GROUPS["listing_optimizer"], "*offer*.csv"):
        metrics_missing.append("Offer eligibility data was not found.")
    if not latest_file(INPUT_GROUPS["listing_optimizer"], "*aging*.csv"):
        metrics_missing.append("Aging/stale inventory report was not found.")

    return metrics, sources, files_used, metrics_missing, observations, column_notes


def build_summary(metrics: dict[str, object], actions: list[dict[str, object]], files_used: list[str],
                  metrics_missing: list[str], observations: list[str], column_notes: dict[str, list[str]]) -> str:
    focus = actions[0]["action"] if actions else "No action generated"
    lines = [
        APP_NAME,
        f"Timestamp: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "Files used:",
    ]
    lines.extend([f"- {path}" for path in files_used] or ["- None"])
    lines.extend(["", "Metrics found:"])
    for key in KPI_FIELDS[1:]:
        value = metrics.get(key, "")
        if value not in ("", None):
            lines.append(f"- {key}: {value}")
    lines.extend([
        f"- invalid_user_sku_count: {metrics.get('invalid_user_sku_count', 0)}",
        f"- listings_at_0_99: {metrics.get('listings_at_0_99', 0)}",
        f"- listings_under_1_49: {metrics.get('listings_under_1_49', 0)}",
        f"- duplicate_title_rows: {metrics.get('duplicate_title_rows', 0)}",
        f"- latest_export_rows: {metrics.get('latest_export_rows', 0)}",
        f"- listing_export_batches: {metrics.get('listing_export_batches', 0)}",
        f"- listing_export_rows: {metrics.get('listing_export_rows', 0)}",
    ])
    lines.extend(["", "Metrics missing:"])
    lines.extend([f"- {item}" for item in sorted(set(metrics_missing))] or ["- None"])
    lines.extend(["", "Key observations:"])
    if int(metrics.get("missing_user_sku_count") or 0) + int(metrics.get("invalid_user_sku_count") or 0):
        lines.append("- User SKU / warehouse location cleanup is currently the largest operational blocker.")
    if int(metrics.get("listings_under_1_49") or 0):
        lines.append("- Low-price listings should be reviewed against cart-sweetener and profit-per-envelope strategy.")
    if int(metrics.get("duplicate_title_rows") or 0):
        lines.append("- Duplicate titles may indicate duplicate listings or title-quality drift.")
    lines.extend([f"- {item}" for item in observations])
    if not observations and len(lines) and lines[-1] == "Key observations:":
        lines.append("- No major observations beyond generated action queue.")
    lines.extend(["", "Available columns when expected columns were not found:"])
    if column_notes:
        for path, fields in column_notes.items():
            lines.append(f"- {path}: {', '.join(fields)}")
    else:
        lines.append("- None")
    lines.extend(["", "Recommended focus:", f"- {focus}", ""])
    return "\n".join(lines)


def write_action_summary(path: Path, actions: list[dict[str, object]]) -> None:
    lines = [
        APP_NAME,
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "Top 10 recommended actions:",
    ]
    for index, action in enumerate(actions[:10], 1):
        lines.extend([
            "",
            f"{index}. [{action['priority_label']} - {action['priority_score']}] {action['action']}",
            f"   Module: {action['module']}",
            f"   Reason: {action['reason']}",
            f"   Estimated time: {action['estimated_time_minutes']} minutes",
            f"   Expected impact: {action['expected_impact']}",
            f"   Source: {action['source_file'] or 'n/a'}",
        ])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(open_report: bool = False) -> dict[str, object]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    metrics, sources, files_used, metrics_missing, observations, column_notes = collect_metrics()
    actions = build_action_queue(metrics, sources)
    timestamp = datetime.now().isoformat(timespec="seconds")

    kpi_row = {"timestamp": timestamp}
    for field in KPI_FIELDS[1:]:
        kpi_row[field] = metrics.get(field, "")
    write_csv(REPORTS_DIR / "kpi_snapshot.csv", [kpi_row], KPI_FIELDS)
    write_csv(REPORTS_DIR / "action_queue.csv", actions, ACTION_FIELDS)
    summary_text = build_summary(metrics, actions, files_used, metrics_missing, observations, column_notes)
    (REPORTS_DIR / "business_intelligence_summary.txt").write_text(summary_text + "\n", encoding="utf-8")
    write_action_summary(REPORTS_DIR / "action_queue_summary.txt", actions)

    print(APP_NAME)
    print(VERSION)
    print("Files loaded:")
    for path in files_used:
        print(f"- {path}")
    print("Metrics calculated:")
    for key in KPI_FIELDS[1:]:
        print(f"- {key}: {metrics.get(key, '')}")
    print("Top 5 actions:")
    for action in actions[:5]:
        print(f"- [{action['priority_score']}] {action['action']}")
    print(f"Reports saved to: {REPORTS_DIR}")

    if open_report:
        report = REPORTS_DIR / "action_queue_summary.txt"
        try:
            os.startfile(report)  # type: ignore[attr-defined]
        except Exception:
            print(f"Open report manually: {report}")

    return {"metrics": metrics, "actions": actions, "reports_dir": REPORTS_DIR}


def main() -> int:
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument("--open-report", action="store_true", help="Open action_queue_summary.txt after completion.")
    args = parser.parse_args()
    run(open_report=args.open_report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
