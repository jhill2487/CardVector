from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .config import CONFIG_DIR, load_json, save_json
from .models import Listing
from .utils import decimal_money, find_column, read_csv_rows


SOURCE_EBAY = "ebay_active_listings"
SOURCE_CARDUPLOADER = "carduploader_export"
SOURCE_CUSTOM = "custom_csv"

SOURCE_LABELS = {
    SOURCE_EBAY: "eBay Active Listings CSV",
    SOURCE_CARDUPLOADER: "CardUploader Export CSV",
    SOURCE_CUSTOM: "Custom CSV",
}

ITEM_ID_COLUMNS = ["Item number", "ItemID", "Item ID", "item_id", "ItemId"]
TITLE_COLUMNS = ["Title", "*Title", "Item title", "ItemTitle"]
PRICE_COLUMNS = ["Start price", "StartPrice", "Current price", "CurrentPrice", "BuyItNowPrice", "Price"]
SKU_COLUMNS = ["Custom label (SKU)", "Custom Label (SKU)", "Custom Label", "CustomLabel", "SKU", "User SKU"]
QUANTITY_COLUMNS = ["Available quantity", "Quantity", "*Quantity", "Qty"]
CONDITION_COLUMNS = ["Condition", "Item condition", "ConditionName"]
CATEGORY_COLUMNS = ["Category", "Category name", "eBay category 1 name"]
SHIPPING_COLUMNS = ["Shipping service", "Shipping policy", "Domestic shipping service", "Shipping cost"]

CARDUPLOADER_COLUMNS = {
    "title": ["Title", "Listing Title", "Name"],
    "sku": ["User SKU", "SKU"],
    "catalog_sku": ["Catalog SKU", "CatalogSKU"],
    "tcgplayer_sku": ["TCGplayer SKU", "TCGPlayer SKU", "TCGplayerSKU"],
    "tcgplayer_product_id": ["TCGplayer Product ID", "TCGPlayer Product ID", "Product ID"],
    "tcg": ["TCG", "Game"],
    "set_name": ["Set", "Set Name"],
    "card_number": ["Card Number", "Number"],
    "rarity": ["Rarity"],
    "condition": ["Condition"],
    "variant": ["Variant"],
    "finish": ["Finish", "Foil"],
    "current_price": ["Price", "Listing Price", "Current Price"],
    "quantity": ["Qty", "Quantity"],
    "status": ["Status"],
}

PROFILE_DIR = CONFIG_DIR / "source_profiles"


@dataclass
class SourceDetection:
    source_type: str
    label: str
    confidence: str
    reason: str


@dataclass
class ImportResult:
    path: Path
    rows: list[dict[str, str]]
    listings: list[Listing]
    fieldnames: list[str]
    missing_required_fields: list[str]
    detected_format: str
    source_type: str = SOURCE_EBAY
    source_profile: str = ""
    warnings: list[str] = field(default_factory=list)

    @property
    def ready(self) -> bool:
        return not self.missing_required_fields


def _value(row: dict[str, str], column: str | None) -> str:
    if not column:
        return ""
    return str(row.get(column, "") or "").strip()


def _mapped_value(row: dict[str, str], mapping: dict[str, str | None], field: str) -> str:
    return _value(row, mapping.get(field))


def _money(row: dict[str, str], mapping: dict[str, str | None], field: str = "current_price"):
    return decimal_money(_mapped_value(row, mapping, field), decimal_money("0.00"))


def detect_ebay_columns(fieldnames: list[str]) -> dict[str, str | None]:
    return {
        "item_id": find_column(fieldnames, ITEM_ID_COLUMNS),
        "title": find_column(fieldnames, TITLE_COLUMNS),
        "current_price": find_column(fieldnames, PRICE_COLUMNS),
        "sku": find_column(fieldnames, SKU_COLUMNS),
        "quantity": find_column(fieldnames, QUANTITY_COLUMNS),
        "condition": find_column(fieldnames, CONDITION_COLUMNS),
        "category": find_column(fieldnames, CATEGORY_COLUMNS),
        "shipping": find_column(fieldnames, SHIPPING_COLUMNS),
    }


def detect_carduploader_columns(fieldnames: list[str]) -> dict[str, str | None]:
    return {field: find_column(fieldnames, candidates) for field, candidates in CARDUPLOADER_COLUMNS.items()}


def detect_columns(fieldnames: list[str]) -> dict[str, str | None]:
    return detect_ebay_columns(fieldnames)


def validate_columns(fieldnames: list[str]) -> list[str]:
    columns = detect_ebay_columns(fieldnames)
    missing = []
    if not columns["item_id"]:
        missing.append("eBay item ID")
    if not columns["title"]:
        missing.append("title")
    if not columns["current_price"]:
        missing.append("current price")
    return missing


def detect_source(fieldnames: list[str]) -> SourceDetection:
    ebay = detect_ebay_columns(fieldnames)
    carduploader = detect_carduploader_columns(fieldnames)
    ebay_score = sum(1 for field in ["item_id", "title", "current_price"] if ebay.get(field))
    carduploader_score = sum(
        1
        for field in [
            "title",
            "sku",
            "catalog_sku",
            "tcgplayer_sku",
            "tcgplayer_product_id",
            "tcg",
            "set_name",
            "card_number",
            "condition",
            "current_price",
        ]
        if carduploader.get(field)
    )
    if carduploader_score >= 5 and carduploader.get("title") and carduploader.get("current_price"):
        return SourceDetection(
            SOURCE_CARDUPLOADER,
            SOURCE_LABELS[SOURCE_CARDUPLOADER],
            "high" if carduploader_score >= 7 else "medium",
            f"Matched {carduploader_score} CardUploader-style columns.",
        )
    if ebay_score == 3:
        return SourceDetection(
            SOURCE_EBAY,
            SOURCE_LABELS[SOURCE_EBAY],
            "high",
            "Matched eBay item ID, title, and price columns.",
        )
    return SourceDetection(SOURCE_CUSTOM, SOURCE_LABELS[SOURCE_CUSTOM], "low", "No known source profile matched confidently.")


def _required_missing(mapping: dict[str, str | None], required: list[str], label: str) -> list[str]:
    return [f"{label} {field.replace('_', ' ')}" for field in required if not mapping.get(field)]


def ebay_active_listings_adapter(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> ImportResult:
    mapping = detect_ebay_columns(fieldnames)
    missing = _required_missing(mapping, ["item_id", "title", "current_price"], "eBay")
    listings: list[Listing] = []
    if not missing:
        for index, row in enumerate(rows, start=1):
            listings.append(
                Listing(
                    row_number=index,
                    raw=row,
                    item_id=_mapped_value(row, mapping, "item_id"),
                    title=_mapped_value(row, mapping, "title"),
                    current_price=_money(row, mapping),
                    source_type=SOURCE_EBAY,
                    source_file=str(path),
                    sku=_mapped_value(row, mapping, "sku"),
                    quantity=_mapped_value(row, mapping, "quantity"),
                    condition=_mapped_value(row, mapping, "condition"),
                    category=_mapped_value(row, mapping, "category"),
                    shipping=_mapped_value(row, mapping, "shipping"),
                )
            )
    return ImportResult(path, rows, listings, fieldnames, missing, SOURCE_LABELS[SOURCE_EBAY], SOURCE_EBAY)


def carduploader_export_adapter(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> ImportResult:
    mapping = detect_carduploader_columns(fieldnames)
    missing = _required_missing(mapping, ["title", "current_price"], "CardUploader")
    listings: list[Listing] = []
    warnings: list[str] = []
    if not missing:
        for index, row in enumerate(rows, start=1):
            row_warnings = []
            if _mapped_value(row, mapping, "current_price") in {"", "0", "0.00"}:
                row_warnings.append("Missing or zero CardUploader price.")
            listing = Listing(
                row_number=index,
                raw=row,
                item_id="",
                title=_mapped_value(row, mapping, "title"),
                current_price=_money(row, mapping),
                source_type=SOURCE_CARDUPLOADER,
                source_file=str(path),
                sku=_mapped_value(row, mapping, "sku"),
                quantity=_mapped_value(row, mapping, "quantity"),
                condition=_mapped_value(row, mapping, "condition"),
                set_name=_mapped_value(row, mapping, "set_name"),
                card_number=_mapped_value(row, mapping, "card_number"),
                rarity=_mapped_value(row, mapping, "rarity"),
                variant=_mapped_value(row, mapping, "variant"),
                finish=_mapped_value(row, mapping, "finish"),
                tcg=_mapped_value(row, mapping, "tcg"),
                tcgplayer_product_id=_mapped_value(row, mapping, "tcgplayer_product_id"),
                tcgplayer_sku=_mapped_value(row, mapping, "tcgplayer_sku"),
                catalog_sku=_mapped_value(row, mapping, "catalog_sku"),
                status=_mapped_value(row, mapping, "status"),
                warnings=row_warnings,
            )
            listings.append(listing)
            warnings.extend(f"Row {index}: {warning}" for warning in row_warnings)
    return ImportResult(path, rows, listings, fieldnames, missing, SOURCE_LABELS[SOURCE_CARDUPLOADER], SOURCE_CARDUPLOADER, warnings=warnings)


def load_source_profile(name_or_path: str | Path) -> dict:
    raw = str(name_or_path or "").strip()
    if not raw:
        return {}
    path = Path(raw)
    if not path.suffix:
        path = PROFILE_DIR / f"{raw}.json"
    return load_json(path)


def save_source_profile(name: str, mapping: dict[str, str]) -> Path:
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in str(name or "custom_profile")).strip("_")
    return save_json(PROFILE_DIR / f"{safe or 'custom_profile'}.json", {"name": safe or "custom_profile", "mapping": mapping})


def custom_csv_adapter(
    path: Path,
    rows: list[dict[str, str]],
    fieldnames: list[str],
    mapping: dict[str, str] | None = None,
    profile_name: str = "",
) -> ImportResult:
    mapping = dict(mapping or {})
    missing = _required_missing(mapping, ["title", "current_price"], "Custom CSV")
    listings: list[Listing] = []
    if not mapping:
        missing = ["custom source profile mapping"]
    if not missing:
        for index, row in enumerate(rows, start=1):
            listings.append(
                Listing(
                    row_number=index,
                    raw=row,
                    item_id=_mapped_value(row, mapping, "item_id"),
                    title=_mapped_value(row, mapping, "title"),
                    current_price=_money(row, mapping),
                    source_type=SOURCE_CUSTOM,
                    source_file=str(path),
                    sku=_mapped_value(row, mapping, "sku"),
                    quantity=_mapped_value(row, mapping, "quantity"),
                    condition=_mapped_value(row, mapping, "condition"),
                    set_name=_mapped_value(row, mapping, "set_name"),
                    card_number=_mapped_value(row, mapping, "card_number"),
                    variant=_mapped_value(row, mapping, "variant"),
                    finish=_mapped_value(row, mapping, "finish"),
                    status=_mapped_value(row, mapping, "status"),
                )
            )
    warnings = []
    if missing:
        warnings.append("Custom CSV requires a saved source profile JSON with a mapping object.")
    return ImportResult(path, rows, listings, fieldnames, missing, SOURCE_LABELS[SOURCE_CUSTOM], SOURCE_CUSTOM, profile_name, warnings)


def import_listing_csv(
    path: Path,
    source_type: str | None = None,
    custom_mapping: dict[str, str] | None = None,
    source_profile: str | Path | None = None,
) -> ImportResult:
    source = Path(path)
    rows = read_csv_rows(source)
    fieldnames = list(rows[0].keys()) if rows else []
    detection = detect_source(fieldnames)
    selected_source = source_type or detection.source_type
    if selected_source == "auto":
        selected_source = detection.source_type
    if selected_source == SOURCE_EBAY:
        result = ebay_active_listings_adapter(source, rows, fieldnames)
    elif selected_source == SOURCE_CARDUPLOADER:
        result = carduploader_export_adapter(source, rows, fieldnames)
    elif selected_source == SOURCE_CUSTOM:
        profile = load_source_profile(source_profile) if source_profile else {}
        mapping = custom_mapping or profile.get("mapping") or profile
        result = custom_csv_adapter(source, rows, fieldnames, mapping=mapping, profile_name=str(source_profile or ""))
    else:
        result = custom_csv_adapter(source, rows, fieldnames, mapping=custom_mapping, profile_name=str(source_profile or ""))
        result.missing_required_fields.append(f"unknown source type: {selected_source}")
    result.warnings.insert(0, f"Detected source: {detection.label} ({detection.confidence}) - {detection.reason}")
    if source_type and source_type not in {"auto", detection.source_type}:
        result.warnings.insert(1, f"Source override applied: {source_type}")
    return result


def import_active_listings_csv(path: Path) -> ImportResult:
    return import_listing_csv(path, source_type=SOURCE_EBAY)
