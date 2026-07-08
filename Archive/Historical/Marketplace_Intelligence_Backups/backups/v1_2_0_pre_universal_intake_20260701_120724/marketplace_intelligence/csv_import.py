from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .models import Listing
from .utils import decimal_money, find_column, read_csv_rows


ITEM_ID_COLUMNS = ["Item number", "ItemID", "Item ID", "item_id", "ItemId"]
TITLE_COLUMNS = ["Title", "*Title", "Item title", "ItemTitle"]
PRICE_COLUMNS = ["Start price", "StartPrice", "Current price", "CurrentPrice", "BuyItNowPrice", "Price"]
SKU_COLUMNS = ["Custom label (SKU)", "Custom Label (SKU)", "Custom Label", "CustomLabel", "SKU", "User SKU"]
QUANTITY_COLUMNS = ["Available quantity", "Quantity", "*Quantity", "Qty"]
CONDITION_COLUMNS = ["Condition", "Item condition", "ConditionName"]
CATEGORY_COLUMNS = ["Category", "Category name", "eBay category 1 name"]
SHIPPING_COLUMNS = ["Shipping service", "Shipping policy", "Domestic shipping service", "Shipping cost"]


@dataclass
class ImportResult:
    path: Path
    rows: list[dict[str, str]]
    listings: list[Listing]
    fieldnames: list[str]
    missing_required_fields: list[str]
    detected_format: str

    @property
    def ready(self) -> bool:
        return not self.missing_required_fields


def _value(row: dict[str, str], column: str | None) -> str:
    if not column:
        return ""
    return str(row.get(column, "") or "").strip()


def detect_columns(fieldnames: list[str]) -> dict[str, str | None]:
    return {
        "item_id": find_column(fieldnames, ITEM_ID_COLUMNS),
        "title": find_column(fieldnames, TITLE_COLUMNS),
        "price": find_column(fieldnames, PRICE_COLUMNS),
        "sku": find_column(fieldnames, SKU_COLUMNS),
        "quantity": find_column(fieldnames, QUANTITY_COLUMNS),
        "condition": find_column(fieldnames, CONDITION_COLUMNS),
        "category": find_column(fieldnames, CATEGORY_COLUMNS),
        "shipping": find_column(fieldnames, SHIPPING_COLUMNS),
    }


def validate_columns(fieldnames: list[str]) -> list[str]:
    columns = detect_columns(fieldnames)
    missing = []
    if not columns["item_id"]:
        missing.append("eBay item ID")
    if not columns["title"]:
        missing.append("title")
    if not columns["price"]:
        missing.append("current price")
    return missing


def import_active_listings_csv(path: Path) -> ImportResult:
    source = Path(path)
    rows = read_csv_rows(source)
    fieldnames = list(rows[0].keys()) if rows else []
    columns = detect_columns(fieldnames)
    missing = validate_columns(fieldnames)
    listings: list[Listing] = []
    if not missing:
        for index, row in enumerate(rows, start=1):
            price = decimal_money(_value(row, columns["price"]))
            if price is None:
                price = decimal_money("0.00")
            listings.append(
                Listing(
                    row_number=index,
                    raw=row,
                    item_id=_value(row, columns["item_id"]),
                    title=_value(row, columns["title"]),
                    current_price=price,
                    sku=_value(row, columns["sku"]),
                    quantity=_value(row, columns["quantity"]),
                    condition=_value(row, columns["condition"]),
                    category=_value(row, columns["category"]),
                    shipping=_value(row, columns["shipping"]),
                )
            )
    detected = "eBay Active Listings CSV" if not missing else "Unknown / incomplete CSV"
    return ImportResult(source, rows, listings, fieldnames, missing, detected)

