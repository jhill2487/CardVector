from __future__ import annotations

import argparse
import csv
from datetime import datetime
from pathlib import Path
from typing import Iterable

VERSION = "1.1"
APP_TITLE = "Putnam Listing Optimizer"
FLOOR_PRICE = 0.99

USER_SKU_COLUMN_CANDIDATES = [
    "*CustomLabel",
    "Custom label (SKU)",
    "Custom Label (SKU)",
    "Custom Label",
    "CustomLabel",
    "Custom SKU",
    "User SKU",
    "UserSKU",
    "Seller SKU",
    "Merchant SKU",
]

CARDUPLOADER_INTERNAL_SKU_COLUMNS = [
    "CardUploader SKU",
    "Card Uploader SKU",
    "CardUploaderSKU",
    "Internal SKU",
    "InternalSKU",
    "Source SKU",
    "Card SKU",
    "SKU",
]

SHIPPING_POLICY_EXACT_CANDIDATES = [
    "*ShippingProfileName",
    "ShippingProfileName",
    "Shipping policy",
    "Shipping Policy",
    "Shipping profile",
    "Shipping Profile",
    "Business policy",
    "Business Policy",
]

FREE_SHIPPING_FLAGS = ("free shipping", "seller pays")

LOG_HEADER = [
    "timestamp",
    "input_file",
    "output_file",
    "row_count",
    "batch_user_sku",
    "shipping_policy_values",
    "export_status",
    "notes",
]


class StopExport(RuntimeError):
    def __init__(self, message: str, status: str = "STOPPED", notes: str = ""):
        super().__init__(message)
        self.status = status
        self.notes = notes or message


def print_checkpoint() -> None:
    print(f"{APP_TITLE} v{VERSION}")
    print("Pre-Export Safety Checklist enabled")
    print()


def normalize_name(value: str) -> str:
    return "".join(ch for ch in value.lower().strip() if ch.isalnum())


def find_exact_column(fieldnames: list[str], candidates: Iterable[str]) -> str | None:
    by_norm = {normalize_name(name): name for name in fieldnames}
    for candidate in candidates:
        found = by_norm.get(normalize_name(candidate))
        if found:
            return found
    return None


def read_csv(path: Path) -> tuple[list[dict[str, str]], list[str], csv.Dialect]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        sample = f.read(4096)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample)
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(f, dialect=dialect)
        if not reader.fieldnames:
            raise StopExport("Input CSV has no header row.", "FAILED", "missing header")
        fieldnames = [str(name).strip() for name in reader.fieldnames]
        rows = [{str(k).strip(): (v if v is not None else "") for k, v in row.items()} for row in reader]
    return rows, fieldnames, dialect


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str], dialect: csv.Dialect) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, dialect=dialect, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def append_log(
    output_path: Path,
    input_path: Path,
    row_count: int,
    batch_user_sku: str,
    shipping_values: list[str],
    export_status: str,
    notes: str,
) -> None:
    log_path = output_path.parent / "putnam_listing_optimizer_export_log.csv"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    exists = log_path.exists()
    with log_path.open("a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_HEADER)
        if not exists:
            writer.writeheader()
        writer.writerow(
            {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "input_file": str(input_path),
                "output_file": str(output_path),
                "row_count": row_count,
                "batch_user_sku": batch_user_sku,
                "shipping_policy_values": " | ".join(shipping_values),
                "export_status": export_status,
                "notes": notes,
            }
        )


def prompt_required(prompt: str) -> str:
    value = input(prompt).strip()
    if not value:
        raise StopExport("Required value was blank.", "STOPPED", "blank required prompt")
    return value


def resolve_user_sku_column(fieldnames: list[str], configured_column: str | None) -> str:
    if configured_column:
        for field in fieldnames:
            if field == configured_column:
                return field
        raise StopExport(
            f'Configured User SKU column "{configured_column}" was not found.',
            "FAILED",
            "configured user sku column not found",
        )

    target = find_exact_column(fieldnames, USER_SKU_COLUMN_CANDIDATES)
    if target:
        return target

    print("Could not identify the correct User SKU / Custom Label column.")
    print("Available column names:")
    for name in fieldnames:
        print(f"- {name}")
    print()
    configured = input("Enter User SKU / Custom Label column name exactly, or press Enter to stop: ").strip()
    if not configured:
        raise StopExport("User SKU / Custom Label column was not configured.", "STOPPED", "user sku column not configured")
    return resolve_user_sku_column(fieldnames, configured)


def detect_shipping_policy_column(fieldnames: list[str]) -> str | None:
    exact = find_exact_column(fieldnames, SHIPPING_POLICY_EXACT_CANDIDATES)
    if exact:
        return exact
    for name in fieldnames:
        norm = name.lower()
        if "shipping" in norm and ("policy" in norm or "profile" in norm):
            return name
    return None


def distinct_values(rows: list[dict[str, str]], column: str | None) -> list[str]:
    if not column:
        return []
    seen: list[str] = []
    for row in rows:
        value = str(row.get(column, "")).strip()
        if value and value not in seen:
            seen.append(value)
    return seen


def shipping_value_is_free(value: str) -> bool:
    norm = value.lower().strip()
    compact = "".join(ch for ch in norm if ch.isalnum())
    try:
        if float(norm.replace("$", "").replace(",", "")) == 0:
            return True
    except ValueError:
        pass
    return (
        compact in {"free", "freeshipping", "sellerpays", "sellerpaid", "sellerpaidshipping"}
        or any(flag in norm for flag in FREE_SHIPPING_FLAGS)
    )


def enforce_shipping_policy(shipping_values: list[str]) -> None:
    if not any(shipping_value_is_free(value) for value in shipping_values):
        return
    print("WARNING: Shipping policy appears to be Free Shipping.")
    print("Putnam standard is Buyer Paid Shipping.")
    override = input("Do you want to continue? Type YES to override: ").strip()
    if override != "YES":
        raise StopExport("Export stopped because shipping policy appears to be Free Shipping.", "STOPPED", "free shipping policy not overridden")


def title_status(fieldnames: list[str], rows: list[dict[str, str]]) -> str:
    status_col = None
    for name in fieldnames:
        norm = name.lower()
        if "title" in norm and ("status" in norm or "standard" in norm):
            status_col = name
            break
    if status_col:
        values = distinct_values(rows, status_col)
        return f'{status_col}: {", ".join(values) if values else "blank"}'
    title_col = find_exact_column(fieldnames, ["*Title", "Title", "Listing title", "Item title"])
    if title_col:
        return f"{title_col} present (not modified)"
    return "not available"


def apply_existing_price_guardrails(rows: list[dict[str, str]]) -> tuple[int, str]:
    price_col = find_exact_column(rows[0].keys() if rows else [], ["*StartPrice"])
    if not price_col:
        return 0, "price logic not applied; *StartPrice column not found"
    changed = 0
    for row in rows:
        raw = str(row.get(price_col, "")).replace("$", "").replace(",", "").strip()
        try:
            price = float(raw)
        except ValueError:
            continue
        if price < FLOOR_PRICE:
            row[price_col] = f"{FLOOR_PRICE:.2f}"
            changed += 1
    return changed, f"existing floor-price guardrail applied to {changed} row(s)"


def output_preview_path(output_path: Path) -> Path:
    return output_path.with_name(f"{output_path.stem}.preview{output_path.suffix or '.csv'}")


def print_final_checklist(
    input_path: Path,
    output_path: Path,
    row_count: int,
    batch_user_sku: str,
    shipping_values: list[str],
    title_standard_status: str,
) -> None:
    print()
    print("Pre-export checklist summary")
    print(f"- Input file: {input_path}")
    print(f"- Number of rows: {row_count}")
    print(f"- Batch/User SKU value: {batch_user_sku}")
    print(f"- Detected shipping policy values: {', '.join(shipping_values) if shipping_values else 'not found'}")
    print(f"- Title standard status: {title_standard_status}")
    print(f"- Output file path: {output_path}")
    print()


def run(args: argparse.Namespace) -> int:
    print_checkpoint()
    input_path = Path(args.input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    rows, fieldnames, dialect = read_csv(input_path)
    if not rows:
        raise StopExport("Input CSV has no data rows.", "FAILED", "no data rows")

    batch_user_sku = prompt_required("Enter warehouse location / User SKU for this batch:")
    user_sku_column = resolve_user_sku_column(fieldnames, args.user_sku_column)

    shipping_column = detect_shipping_policy_column(fieldnames)
    shipping_values = distinct_values(rows, shipping_column)
    notes: list[str] = []
    if shipping_column:
        enforce_shipping_policy(shipping_values)
    else:
        print("WARNING: Shipping policy column not found.")
        notes.append("shipping policy column not found")

    for row in rows:
        row[user_sku_column] = batch_user_sku

    price_changes, price_note = apply_existing_price_guardrails(rows)
    notes.append(price_note)

    final_output = output_preview_path(output_path) if args.dry_run else output_path
    print_final_checklist(
        input_path=input_path,
        output_path=final_output,
        row_count=len(rows),
        batch_user_sku=batch_user_sku,
        shipping_values=shipping_values,
        title_standard_status=title_status(fieldnames, rows),
    )
    print(f"User SKU / Custom Label column to update: {user_sku_column}")
    print("Promo note: Free shipping on 3+ items is handled by eBay promotion, not by setting individual listings to free shipping.")
    if args.dry_run:
        print("Dry run enabled: final upload CSV will not be created.")
    print()

    confirmation = input("Export eBay-ready CSV? Type EXPORT to continue:").strip()
    if confirmation != "EXPORT":
        raise StopExport("Export stopped by final checklist confirmation.", "STOPPED", "final EXPORT confirmation not provided")

    write_csv(final_output, rows, fieldnames, dialect)
    status = "DRY_RUN_PREVIEW" if args.dry_run else "EXPORTED"
    note_text = "; ".join(notes + [f"user sku column: {user_sku_column}", f"price changes: {price_changes}"])
    append_log(output_path, input_path, len(rows), batch_user_sku, shipping_values, status, note_text)

    if args.dry_run:
        print(f"Dry-run preview CSV written: {final_output}")
        print("Final upload CSV was not created.")
    else:
        print(f"Export complete: {final_output}")
    print(f"Log updated: {output_path.parent / 'putnam_listing_optimizer_export_log.csv'}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=f"{APP_TITLE} v{VERSION}")
    parser.add_argument("--input", required=True, help="Input CardUploader/eBay CSV path.")
    parser.add_argument("--output", required=True, help="Output eBay-ready CSV path.")
    parser.add_argument("--dry-run", action="store_true", help="Run checks and write a preview CSV without creating the final upload CSV.")
    parser.add_argument("--user-sku-column", help="Exact User SKU / Custom Label column name when auto-detection is not possible.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        return run(args)
    except StopExport as exc:
        print(str(exc))
        try:
            input_path = Path(args.input).expanduser().resolve()
            output_path = Path(args.output).expanduser().resolve()
            append_log(output_path, input_path, 0, "", [], exc.status, exc.notes)
        except Exception:
            pass
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
