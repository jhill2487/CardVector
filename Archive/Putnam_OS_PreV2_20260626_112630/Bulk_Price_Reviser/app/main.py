from __future__ import annotations

import csv
import json
import os
import shutil
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

VERSION = "v1.1.0"
MODULE_NAME = "Bulk Price Reviser"


def find_root() -> Path:
    env = os.environ.get("USERENVIRONMENT")
    if env and Path(env).exists():
        return Path(env)

    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".putnam_root").exists():
            return parent

    fallback = Path.home() / "OneDrive" / "PutnamCollectibles"
    if fallback.exists():
        return fallback

    raise SystemExit("Could not locate Putnam root. Set USERENVIRONMENT first.")


def money(value: str | None) -> Decimal | None:
    if value is None:
        return None
    raw = str(value).strip().replace("$", "").replace(",", "")
    if raw == "":
        return None
    try:
        return Decimal(raw).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except InvalidOperation:
        return None


def money_str(value: Decimal | None) -> str:
    if value is None:
        return ""
    return f"{value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}"


def read_csv_dict(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def latest_csv(folder: Path, pattern: str) -> Path | None:
    matches = sorted(folder.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0] if matches else None


def load_ladder(config_path: Path) -> dict[Decimal, Decimal]:
    data = json.loads(config_path.read_text(encoding="utf-8"))
    price_map = data.get("price_map", {})
    return {money(k): money(v) for k, v in price_map.items() if money(k) is not None and money(v) is not None}


def category_name(active_row: dict[str, str]) -> str:
    name = active_row.get("eBay category 1 name", "") or active_row.get("Category name", "") or ""
    num = active_row.get("eBay category 1 number", "") or ""
    if name and num:
        return f"{name} ({num})"
    return name


def build_upload_rows(changed_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows = []
    for r in changed_rows:
        rows.append({
            "Action": "Revise",
            "Category name": category_name(r),
            "Item number": r.get("Item number", ""),
            "Title": r.get("Title", ""),
            "Listing site": r.get("Listing site", "US") or "US",
            "Currency": r.get("Currency", "USD") or "USD",
            "Start price": r.get("New price", ""),
            "Buy It Now price": "",
            "Available quantity": r.get("Available quantity", ""),
            "Relationship": "",
            "Relationship details": "",
            "Custom label (SKU)": r.get("Custom label (SKU)", ""),
        })
    return rows


def write_ebay_upload(path: Path, rows: list[dict[str, str]]) -> None:
    header = [
        "Action",
        "Category name",
        "Item number",
        "Title",
        "Listing site",
        "Currency",
        "Start price",
        "Buy It Now price",
        "Available quantity",
        "Relationship",
        "Relationship details",
        "Custom label (SKU)",
    ]
    info = ["#INFO", "Version=1.0.0", "Template= eBay-active-revise-price-quantity-download_US"] + [""] * (len(header) - 3)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(info)
        writer.writerow(header)
        for r in rows:
            writer.writerow([r.get(col, "") for col in header])


def main() -> None:
    root = find_root()
    module = root / "Putnam_OS" / "modules" / "Bulk_Price_Reviser"
    input_dir = module / "input"
    output_dir = module / "output"
    logs_dir = module / "logs"
    archive_dir = module / "archive"
    config_path = module / "config" / "pricing_ladder.json"

    for d in [input_dir, output_dir, logs_dir, archive_dir]:
        d.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = logs_dir / f"bulk_price_reviser_{ts}.log"

    def log(msg: str) -> None:
        print(msg)
        with log_path.open("a", encoding="utf-8") as lf:
            lf.write(msg + "\n")

    log(f"Putnam {MODULE_NAME} {VERSION}")
    log(f"Root: {root}")
    log(f"Module: {module}")

    active_csv = latest_csv(input_dir, "eBay-all-active-listings-report*.csv") or latest_csv(input_dir, "*.csv")
    if not active_csv:
        log("")
        log("ERROR: No CSV found in input folder.")
        log(f"Place your eBay active listings export in: {input_dir}")
        input("Press Enter to close...")
        return

    log(f"Input CSV: {active_csv}")
    backup_path = archive_dir / f"{active_csv.stem}_backup_{ts}{active_csv.suffix}"
    shutil.copy2(active_csv, backup_path)
    log(f"Backup created: {backup_path}")

    ladder = load_ladder(config_path)
    log("Pricing ladder:")
    for old, new in sorted(ladder.items()):
        log(f"  {money_str(old)} -> {money_str(new)}")

    rows = read_csv_dict(active_csv)
    review_rows: list[dict[str, str]] = []
    changed_source_rows: list[dict[str, str]] = []
    unchanged_count = 0
    invalid_price_count = 0
    total_old = Decimal("0.00")
    total_new = Decimal("0.00")

    for r in rows:
        old_price = money(r.get("Current price")) or money(r.get("Start price"))
        if old_price is None:
            invalid_price_count += 1
            new_price = None
            changed = False
            reason = "invalid_or_missing_price"
        elif old_price in ladder:
            new_price = ladder[old_price]
            changed = new_price != old_price
            reason = "mapped_price_point" if changed else "mapped_no_change"
        else:
            new_price = old_price
            changed = False
            reason = "not_in_price_ladder"

        if old_price is not None:
            total_old += old_price
        if new_price is not None:
            total_new += new_price

        review = {
            "Item number": r.get("Item number", ""),
            "Title": r.get("Title", ""),
            "Custom label (SKU)": r.get("Custom label (SKU)", ""),
            "Available quantity": r.get("Available quantity", ""),
            "Category": category_name(r),
            "Old price": money_str(old_price),
            "New price": money_str(new_price),
            "Changed": "YES" if changed else "NO",
            "Reason": reason,
        }
        review_rows.append(review)

        if changed:
            source_copy = dict(r)
            source_copy["New price"] = money_str(new_price)
            changed_source_rows.append(source_copy)
        else:
            unchanged_count += 1

    review_fields = ["Item number", "Title", "Custom label (SKU)", "Available quantity", "Category", "Old price", "New price", "Changed", "Reason"]
    review_path = output_dir / f"price_revision_review_{ts}.csv"
    changed_review_path = output_dir / f"price_revision_changed_only_{ts}.csv"
    upload_path = output_dir / f"eBay_price_revision_UPLOAD_CANDIDATE_{ts}.csv"
    report_path = output_dir / f"price_revision_report_{ts}.txt"

    write_csv(review_path, review_fields, review_rows)
    write_csv(changed_review_path, review_fields, [r for r in review_rows if r["Changed"] == "YES"])
    write_ebay_upload(upload_path, build_upload_rows(changed_source_rows))

    change_count = len(changed_source_rows)
    delta = total_new - total_old

    report_lines = [
        f"Putnam {MODULE_NAME} {VERSION}",
        f"Run timestamp: {ts}",
        f"Input CSV: {active_csv}",
        "",
        f"Listings read: {len(rows)}",
        f"Listings changed: {change_count}",
        f"Listings unchanged: {unchanged_count}",
        f"Invalid/missing prices: {invalid_price_count}",
        "",
        f"Total old listed price sum: ${money_str(total_old)}",
        f"Total new listed price sum: ${money_str(total_new)}",
        f"Catalog list-price delta: ${money_str(delta)}",
        "",
        "Pricing ladder applied:",
    ]
    for old, new in sorted(ladder.items()):
        report_lines.append(f"  ${money_str(old)} -> ${money_str(new)}")
    report_lines += [
        "",
        "Output files:",
        f"  Review: {review_path}",
        f"  Changed only review: {changed_review_path}",
        f"  eBay upload candidate: {upload_path}",
        "",
        "IMPORTANT: Review the upload candidate before uploading to eBay.",
        "The generated eBay CSV only includes changed listings.",
    ]
    report_path.write_text("\n".join(report_lines), encoding="utf-8")

    log("")
    log("Run complete.")
    log(f"Listings read: {len(rows)}")
    log(f"Listings changed: {change_count}")
    log(f"Catalog list-price delta: ${money_str(delta)}")
    log("")
    log(f"Review CSV: {review_path}")
    log(f"Changed-only CSV: {changed_review_path}")
    log(f"eBay upload candidate: {upload_path}")
    log(f"Report: {report_path}")
    log("")
    input("Press Enter to close...")


if __name__ == "__main__":
    main()
