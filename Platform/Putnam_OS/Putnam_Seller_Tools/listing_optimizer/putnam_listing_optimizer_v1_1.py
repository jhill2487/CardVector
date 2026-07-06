from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Iterable

VERSION = "1.3"
APP_TITLE = "Putnam Listing Optimizer"
FLOOR_PRICE = Decimal("0.99")
SHIPPING_POLICY_DEFAULT = ""
PAYMENT_POLICY_DEFAULT = ""
RETURN_POLICY_DEFAULT = ""
PROMOTION_POLICY_DEFAULT = "Free Shipping on 3+ Cards"

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

PAYMENT_POLICY_EXACT_CANDIDATES = [
    "*PaymentProfileName",
    "PaymentProfileName",
    "Payment policy",
    "Payment Policy",
    "Payment profile",
    "Payment Profile",
]

RETURN_POLICY_EXACT_CANDIDATES = [
    "*ReturnProfileName",
    "ReturnProfileName",
    "Return policy",
    "Return Policy",
    "Return profile",
    "Return Profile",
]

FREE_SHIPPING_FLAGS = ("free shipping", "seller pays")

LOG_HEADER = [
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


def project_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if candidate.name == "PutnamCollectibles":
            return candidate
    return start


def ebay_business_policies_config_path() -> Path:
    return project_root(Path(__file__).resolve()) / "Platform" / "Putnam_OS" / "System" / "config" / "ebay_business_policies.json"


def load_ebay_business_policies() -> dict[str, str]:
    defaults = {
        "shipping_policy": SHIPPING_POLICY_DEFAULT,
        "payment_policy": PAYMENT_POLICY_DEFAULT,
        "return_policy": RETURN_POLICY_DEFAULT,
    }
    path = ebay_business_policies_config_path()
    if not path.exists():
        return defaults
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return defaults
    section = data.get("ebay_business_policies", data) if isinstance(data, dict) else {}
    if not isinstance(section, dict):
        return defaults
    for key in defaults:
        defaults[key] = str(section.get(key, defaults[key]) or "").strip()
    return defaults


def validate_ebay_business_policies(policies: dict[str, str]) -> None:
    missing = [
        label
        for key, label in [
            ("shipping_policy", "shipping policy"),
            ("payment_policy", "payment policy"),
            ("return_policy", "return policy"),
        ]
        if not str(policies.get(key, "") or "").strip()
    ]
    if missing:
        raise StopExport(
            "eBay export stopped because required business policy values are missing: "
            + ", ".join(missing)
            + f". Configure them in {ebay_business_policies_config_path()}."
        )


def export_history_path(output_path: Path) -> Path:
    return project_root(Path.cwd()) / "logs" / "export_history.csv"


def append_export_history(output_path: Path, summary: dict[str, str]) -> None:
    log_path = export_history_path(output_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    exists = log_path.exists()
    with log_path.open("a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_HEADER)
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
                "output_csv_path": str(output_path),
            }
        )


def prompt_required(prompt: str) -> str:
    value = input(prompt).strip()
    if not value:
        raise StopExport("Required value was blank.", "STOPPED", "blank required prompt")
    return value


def decimal_money(value: str) -> Decimal:
    raw = str(value or "").replace("$", "").replace(",", "").strip()
    if not raw:
        return Decimal("0.00")
    try:
        return Decimal(raw)
    except InvalidOperation:
        return Decimal("0.00")


def format_money(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def optimize_export_price(market_price: Decimal) -> Decimal:
    # Listing Optimizer v1.2 pricing rules:
    # <= $1.50 -> $0.99, $1.51-$2.99 -> $1.49,
    # $3.00-$4.99 -> $2.99, and $5.00+ keeps market-based pricing.
    if market_price <= Decimal("1.50"):
        final_price = Decimal("0.99")
    elif market_price <= Decimal("2.99"):
        final_price = Decimal("1.49")
    elif market_price <= Decimal("4.99"):
        final_price = Decimal("2.99")
    else:
        final_price = market_price
    return max(final_price, FLOOR_PRICE).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


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


def detect_payment_policy_column(fieldnames: list[str]) -> str | None:
    exact = find_exact_column(fieldnames, PAYMENT_POLICY_EXACT_CANDIDATES)
    if exact:
        return exact
    for name in fieldnames:
        norm = name.lower()
        if "payment" in norm and ("policy" in norm or "profile" in norm):
            return name
    return None


def detect_return_policy_column(fieldnames: list[str]) -> str | None:
    exact = find_exact_column(fieldnames, RETURN_POLICY_EXACT_CANDIDATES)
    if exact:
        return exact
    for name in fieldnames:
        norm = name.lower()
        if "return" in norm and ("policy" in norm or "profile" in norm):
            return name
    return None


def detect_promotion_policy_column(fieldnames: list[str]) -> str | None:
    for name in fieldnames:
        norm = name.lower()
        if "promotion" in norm and ("policy" in norm or "profile" in norm or "name" in norm):
            return name
    return None


def batch_location_columns(fieldnames: list[str], user_sku_column: str) -> list[str]:
    columns: list[str] = []
    for candidate in [user_sku_column, "Custom SKU", "User SKU", "Inventory Location", "InventoryLocation"]:
        if not candidate:
            continue
        for field in fieldnames:
            if normalize_name(field) == normalize_name(candidate) and field not in columns:
                columns.append(field)
    return columns


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


def confirm_shipping_policy(policies: dict[str, str]) -> None:
    print()
    print("eBay business policy confirmation")
    print(f"- Shipping policy: {policies['shipping_policy']}")
    print(f"- Payment policy: {policies['payment_policy']}")
    print(f"- Return policy: {policies['return_policy']}")
    print(f"- Promotion policy: {PROMOTION_POLICY_DEFAULT}")
    answer = input("Continue with these eBay policy settings? Type Y to continue: ").strip().upper()
    if answer != "Y":
        raise StopExport("Export stopped during shipping policy confirmation.", "STOPPED", "shipping confirmation declined")


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


def apply_pricing_optimizer(rows: list[dict[str, str]]) -> tuple[int, list[dict[str, str]], list[Decimal]]:
    price_col = find_exact_column(rows[0].keys() if rows else [], ["*StartPrice"])
    if not price_col:
        raise StopExport("Price logic not applied; *StartPrice column not found.", "FAILED", "missing *StartPrice")
    changed = 0
    review_rows: list[dict[str, str]] = []
    final_prices: list[Decimal] = []
    for idx, row in enumerate(rows, 1):
        original_market_price = decimal_money(row.get(price_col, ""))
        final_price = optimize_export_price(original_market_price)
        if final_price != original_market_price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP):
            changed += 1
        row[price_col] = format_money(final_price)
        cart_sweetener = final_price <= Decimal("0.99")
        review = dict(row)
        review.update(
            {
                "optimizer_row": str(idx),
                "original_market_price": format_money(original_market_price),
                "final_export_price": format_money(final_price),
                "cart_sweetener": "TRUE" if cart_sweetener else "FALSE",
            }
        )
        review_rows.append(review)
        final_prices.append(final_price)
    return changed, review_rows, final_prices


def build_export_summary(final_prices: list[Decimal], batch_location: str, policies: dict[str, str]) -> dict[str, str]:
    total = len(final_prices)
    average = (sum(final_prices, Decimal("0.00")) / Decimal(total)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return {
        "batch_location": batch_location,
        "total_listings": str(total),
        "cart_sweetener_count": str(sum(1 for price in final_prices if price <= Decimal("0.99"))),
        "average_final_price": format_money(average),
        "min_final_price": format_money(min(final_prices)),
        "max_final_price": format_money(max(final_prices)),
        "shipping_policy": policies["shipping_policy"],
        "payment_policy": policies["payment_policy"],
        "return_policy": policies["return_policy"],
        "promotion_policy": PROMOTION_POLICY_DEFAULT,
    }


def output_preview_path(output_path: Path) -> Path:
    return output_path.with_name(f"{output_path.stem}.preview{output_path.suffix or '.csv'}")


def print_final_checklist(
    input_path: Path,
    output_path: Path,
    row_count: int,
    batch_user_sku: str,
    shipping_values: list[str],
    title_standard_status: str,
    export_summary: dict[str, str],
) -> None:
    print()
    print("Pre-export checklist summary")
    print(f"- Input file: {input_path}")
    print(f"- Number of rows: {row_count}")
    print(f"- Batch/location value: {batch_user_sku}")
    print(f"- Shipping policy: {export_summary['shipping_policy']}")
    print(f"- Payment policy: {export_summary['payment_policy']}")
    print(f"- Return policy: {export_summary['return_policy']}")
    print(f"- Promotion policy: {PROMOTION_POLICY_DEFAULT}")
    print(f"- Detected source shipping policy values: {', '.join(shipping_values) if shipping_values else 'not found'}")
    print(f"- Cart sweeteners: {export_summary['cart_sweetener_count']}")
    print(f"- Average final export price: ${export_summary['average_final_price']}")
    print(f"- Minimum final export price: ${export_summary['min_final_price']}")
    print(f"- Maximum final export price: ${export_summary['max_final_price']}")
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
    policies = load_ebay_business_policies()
    validate_ebay_business_policies(policies)

    shipping_column = detect_shipping_policy_column(fieldnames)
    payment_column = detect_payment_policy_column(fieldnames)
    return_column = detect_return_policy_column(fieldnames)
    promotion_column = detect_promotion_policy_column(fieldnames)
    shipping_values = distinct_values(rows, shipping_column)
    confirm_shipping_policy(policies)
    for column_name, default_column in [
        (shipping_column, "*ShippingProfileName"),
        (payment_column, "*PaymentProfileName"),
        (return_column, "*ReturnProfileName"),
    ]:
        if not column_name and default_column not in fieldnames:
            fieldnames.append(default_column)
    shipping_column = shipping_column or "*ShippingProfileName"
    payment_column = payment_column or "*PaymentProfileName"
    return_column = return_column or "*ReturnProfileName"

    batch_columns = batch_location_columns(fieldnames, user_sku_column)
    for row in rows:
        for column in batch_columns:
            row[column] = batch_user_sku
        if shipping_column:
            row[shipping_column] = policies["shipping_policy"]
        if payment_column:
            row[payment_column] = policies["payment_policy"]
        if return_column:
            row[return_column] = policies["return_policy"]
        if promotion_column:
            row[promotion_column] = PROMOTION_POLICY_DEFAULT

    price_changes, review_rows, final_prices = apply_pricing_optimizer(rows)
    export_summary = build_export_summary(final_prices, batch_user_sku, policies)

    final_output = output_preview_path(output_path) if args.dry_run else output_path
    print_final_checklist(
        input_path=input_path,
        output_path=final_output,
        row_count=len(rows),
        batch_user_sku=batch_user_sku,
        shipping_values=shipping_values,
        title_standard_status=title_status(fieldnames, rows),
        export_summary=export_summary,
    )
    print(f"Batch/location columns to update: {', '.join(batch_columns)}")
    if args.dry_run:
        print("Dry run enabled: final upload CSV will not be created.")
    print()

    confirmation = input("Export eBay-ready CSV? Type Y to continue: ").strip().upper()
    if confirmation != "Y":
        raise StopExport("Export stopped by final checklist confirmation.", "STOPPED", "final summary declined")

    write_csv(final_output, rows, fieldnames, dialect)
    review_fields = list(fieldnames)
    for extra in ["optimizer_row", "original_market_price", "final_export_price", "cart_sweetener"]:
        if extra not in review_fields:
            review_fields.append(extra)
    write_csv(final_output.with_name(f"{final_output.stem}.optimization_review.csv"), review_rows, review_fields, dialect)
    if not args.dry_run:
        append_export_history(final_output, export_summary)

    if args.dry_run:
        print(f"Dry-run preview CSV written: {final_output}")
        print("Final upload CSV was not created.")
    else:
        print(f"Export complete: {final_output}")
        print(f"Log updated: {export_history_path(final_output)}")
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
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
