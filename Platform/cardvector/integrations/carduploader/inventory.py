from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


PROVIDER_CARDUPLOADER = "carduploader_inventory"

CARDUPLOADER_INVENTORY_COLUMNS = (
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
)

CARDUPLOADER_COLUMN_ALIASES = {
    "title": ("Title", "Listing Title", "Name"),
    "custom_sku": ("Custom SKU", "Custom label (SKU)", "Custom Label", "CustomLabel"),
    "user_sku": ("User SKU", "UserSKU", "SKU"),
    "catalog_sku": ("Catalog SKU", "CatalogSKU"),
    "tcgplayer_sku": ("TCGplayer SKU", "TCGPlayer SKU", "TCGplayerSKU"),
    "tcgplayer_product_id": (
        "TCGplayer Product ID",
        "TCGPlayer Product ID",
        "Product ID",
    ),
    "tcg": ("TCG", "Game"),
    "set_name": ("Set", "Set Name"),
    "card_number": ("Card Number", "Number", "Card #"),
    "rarity": ("Rarity",),
    "variant": ("Variant", "Printing"),
    "finish": ("Finish", "Foil"),
    "condition": ("Condition",),
    "quantity": ("Qty", "Quantity"),
    "price": ("Price", "Listing Price", "Current Price"),
    "status": ("Status",),
    "grading_company": ("Grading Company",),
    "cert_number": ("Cert Number",),
    "grade": ("Grade",),
    "source_id": ("CardUploader ID", "Source ID", "Inventory ID", "ID"),
}


class CardUploaderInventoryError(RuntimeError):
    """Base error for the CardUploader inventory integration."""


class CardUploaderInventoryCapabilityUnavailable(CardUploaderInventoryError):
    """Raised when a live CardUploader capability is not available."""


@dataclass(frozen=True)
class InventoryCapabilities:
    snapshot_read: bool = True
    snapshot_search: bool = True
    authoritative_write: bool = False
    reservations: bool = False
    allocations: bool = False
    pick_confirmation: bool = False
    live_sync: bool = False


@dataclass(frozen=True)
class InventoryQuery:
    text: str = ""
    status: str = ""
    tcg: str = ""
    location: str = ""


@dataclass(frozen=True)
class InventoryItem:
    row_number: int
    title: str = ""
    custom_sku: str = ""
    user_sku: str = ""
    catalog_sku: str = ""
    tcgplayer_sku: str = ""
    tcgplayer_product_id: str = ""
    tcg: str = ""
    set_name: str = ""
    card_number: str = ""
    rarity: str = ""
    condition: str = ""
    variant: str = ""
    finish: str = ""
    price: str = ""
    quantity: str = ""
    status: str = ""
    grading_company: str = ""
    cert_number: str = ""
    grade: str = ""
    source_id: str = ""
    source_file: str = ""
    imported_at: str = ""
    source_row_hash: str = ""
    raw: Mapping[str, str] = field(default_factory=dict)

    @property
    def inventory_id(self) -> str:
        return (
            self.source_id
            or self.user_sku
            or self.catalog_sku
            or self.tcgplayer_sku
            or self.source_row_hash
        )

    @property
    def location(self) -> str:
        return self.user_sku

    @property
    def quantity_value(self) -> int:
        try:
            return max(0, int(float(str(self.quantity or "0").replace(",", ""))))
        except (TypeError, ValueError):
            return 0

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["inventory_id"] = self.inventory_id
        payload["location"] = self.location
        payload["quantity_value"] = self.quantity_value
        return payload


@dataclass(frozen=True)
class InventoryResult:
    provider: str
    source_file: str
    items: tuple[InventoryItem, ...]
    fieldnames: tuple[str, ...]
    errors: tuple[str, ...] = ()
    loaded_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "source_file": self.source_file,
            "items": [item.to_dict() for item in self.items],
            "fieldnames": list(self.fieldnames),
            "errors": list(self.errors),
            "loaded_at": self.loaded_at,
        }


def normalize_column_name(value: str) -> str:
    return "".join(ch for ch in str(value or "").lower().strip() if ch.isalnum())


def find_column(fieldnames: list[str], candidates: tuple[str, ...]) -> str | None:
    normalized = {normalize_column_name(name): name for name in fieldnames}
    for candidate in candidates:
        found = normalized.get(normalize_column_name(candidate))
        if found:
            return found
    return None


def read_csv_rows(path: str | Path) -> tuple[list[dict[str, str]], list[str]]:
    source = Path(path)
    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            with source.open("r", encoding=encoding, newline="") as handle:
                sample = handle.read(4096)
                handle.seek(0)
                try:
                    dialect = csv.Sniffer().sniff(sample)
                except csv.Error:
                    dialect = csv.excel
                reader = csv.DictReader(handle, dialect=dialect)
                return list(reader), list(reader.fieldnames or [])
        except UnicodeDecodeError:
            continue
    with source.open(
        "r",
        encoding="utf-8-sig",
        errors="replace",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)
        return list(reader), list(reader.fieldnames or [])


def source_row_hash(row: Mapping[str, str]) -> str:
    payload = json.dumps(dict(row), sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def normalize_export_row(row: Mapping[str, Any]) -> dict[str, str]:
    normalized = {
        column: str(row.get(column, "") or "").strip()
        for column in CARDUPLOADER_INVENTORY_COLUMNS
    }
    raw_price = normalized.get("Price", "").replace("$", "").replace(",", "").strip()
    try:
        price = float(raw_price or 0)
    except (TypeError, ValueError):
        price = 0.0
    normalized["Price"] = f"{price:.2f}"
    try:
        quantity = int(float(str(normalized.get("Qty") or "0").replace(",", "").strip()))
    except (TypeError, ValueError):
        quantity = 0
    normalized["Qty"] = str(max(0, quantity))
    return normalized


class CardUploaderInventoryService:
    """Read-only CardUploader inventory contract over exported snapshots.

    CardUploader remains authoritative. This service does not create a second
    inventory store and does not claim unsupported live mutation capabilities.
    """

    provider = PROVIDER_CARDUPLOADER

    def __init__(self) -> None:
        self.capabilities = InventoryCapabilities()

    def load_inventory(self, path: str | Path) -> InventoryResult:
        source = Path(path)
        rows, fieldnames = read_csv_rows(source)
        mapping = {
            field: find_column(fieldnames, aliases)
            for field, aliases in CARDUPLOADER_COLUMN_ALIASES.items()
        }
        loaded_at = datetime.now().isoformat(timespec="seconds")
        errors = []
        if not mapping.get("title"):
            errors.append("CardUploader file is missing a title/name column.")

        def value(row: Mapping[str, str], field: str) -> str:
            column = mapping.get(field)
            return str(row.get(column, "") or "").strip() if column else ""

        items = []
        for index, row in enumerate(rows, start=1):
            items.append(
                InventoryItem(
                    row_number=index,
                    title=value(row, "title"),
                    custom_sku=value(row, "custom_sku"),
                    user_sku=value(row, "user_sku"),
                    catalog_sku=value(row, "catalog_sku"),
                    tcgplayer_sku=value(row, "tcgplayer_sku"),
                    tcgplayer_product_id=value(row, "tcgplayer_product_id"),
                    tcg=value(row, "tcg"),
                    set_name=value(row, "set_name"),
                    card_number=value(row, "card_number"),
                    rarity=value(row, "rarity"),
                    condition=value(row, "condition"),
                    variant=value(row, "variant"),
                    finish=value(row, "finish"),
                    price=value(row, "price"),
                    quantity=value(row, "quantity"),
                    status=value(row, "status"),
                    grading_company=value(row, "grading_company"),
                    cert_number=value(row, "cert_number"),
                    grade=value(row, "grade"),
                    source_id=value(row, "source_id"),
                    source_file=str(source),
                    imported_at=loaded_at,
                    source_row_hash=source_row_hash(row),
                    raw=dict(row),
                )
            )
        return InventoryResult(
            provider=self.provider,
            source_file=str(source),
            items=tuple(items),
            fieldnames=tuple(fieldnames),
            errors=tuple(errors),
            loaded_at=loaded_at,
        )

    def search_inventory(
        self,
        path: str | Path,
        query: InventoryQuery | None = None,
    ) -> InventoryResult:
        result = self.load_inventory(path)
        criteria = query or InventoryQuery()
        text = str(criteria.text or "").strip().lower()
        status = str(criteria.status or "").strip().lower()
        tcg = str(criteria.tcg or "").strip().lower()
        location = str(criteria.location or "").strip().lower()
        items = tuple(
            item
            for item in result.items
            if (
                not text
                or text
                in " ".join(
                    (
                        item.title,
                        item.catalog_sku,
                        item.tcgplayer_sku,
                        item.tcgplayer_product_id,
                    )
                ).lower()
            )
            and (not status or item.status.lower() == status)
            and (not tcg or item.tcg.lower() == tcg)
            and (not location or item.location.lower() == location)
        )
        return InventoryResult(
            provider=result.provider,
            source_file=result.source_file,
            items=items,
            fieldnames=result.fieldnames,
            errors=result.errors,
            loaded_at=result.loaded_at,
        )

    def get_inventory_item(
        self,
        path: str | Path,
        inventory_id: str,
    ) -> InventoryItem | None:
        identifier = str(inventory_id or "").strip()
        if not identifier:
            return None
        return next(
            (
                item
                for item in self.load_inventory(path).items
                if item.inventory_id == identifier
            ),
            None,
        )

    def normalize_export_row(self, row: Mapping[str, Any]) -> dict[str, str]:
        return normalize_export_row(row)

    def normalize_export_rows(
        self,
        rows: list[Mapping[str, Any]],
    ) -> list[dict[str, str]]:
        return [self.normalize_export_row(row) for row in rows]

    def require_export_columns(self, rows: list[Mapping[str, Any]]) -> None:
        if not rows:
            raise ValueError("Inventory CSV is empty.")
        available = set(rows[0].keys())
        missing = [
            column
            for column in CARDUPLOADER_INVENTORY_COLUMNS
            if column not in available
        ]
        if missing:
            raise ValueError(
                "Missing CardUploader inventory columns: " + ", ".join(missing)
            )

    def require_capability(self, capability: str) -> None:
        if not bool(getattr(self.capabilities, capability, False)):
            raise CardUploaderInventoryCapabilityUnavailable(
                f"CardUploader inventory capability is not available: {capability}"
            )


__all__ = [
    "CARDUPLOADER_COLUMN_ALIASES",
    "CARDUPLOADER_INVENTORY_COLUMNS",
    "PROVIDER_CARDUPLOADER",
    "CardUploaderInventoryCapabilityUnavailable",
    "CardUploaderInventoryError",
    "CardUploaderInventoryService",
    "InventoryCapabilities",
    "InventoryItem",
    "InventoryQuery",
    "InventoryResult",
    "find_column",
    "normalize_column_name",
    "normalize_export_row",
    "read_csv_rows",
    "source_row_hash",
]
