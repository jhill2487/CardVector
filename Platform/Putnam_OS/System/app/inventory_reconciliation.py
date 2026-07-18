from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from Platform.cardvector.integrations.carduploader import (
    CardUploaderInventoryService,
)
from Platform.putnam_paths import DATA_EXPORTS_DIR


PROVIDER_CARDUPLOADER = "carduploader_inventory"
PROVIDER_EBAY = "ebay_active_listings"
RECONCILIATION_EXPORT_DIR = DATA_EXPORTS_DIR / "Reconciliation"


EBAY_COLUMNS = {
    "ebay_item_id": ["Item number", "Item Number", "Item ID", "ItemID", "ItemId"],
    "ebay_listing_title": ["Title", "*Title", "Listing title", "Item title", "ItemTitle"],
    "available_quantity": ["Available quantity", "Available Quantity", "Quantity Available", "Quantity", "Qty"],
    "sold_quantity": ["Sold quantity", "Sold Quantity", "Quantity sold", "Sold"],
    "listing_status": ["Listing status", "Status", "Format"],
    "listing_price": ["Current price", "Start price", "StartPrice", "Price", "BuyItNowPrice"],
    "condition": ["Condition", "Item condition", "ConditionName", "CD:Card Condition - (ID: 40001)"],
    "category": ["eBay category 1 name", "Category", "Category name"],
    "ebay_product_id": ["eBay Product ID(ePID)", "ePID", "Product ID"],
    "source_sku": ["Custom label (SKU)", "Custom Label (SKU)", "Custom Label", "CustomLabel", "SKU"],
}

REPORT_FIELDS = [
    "match_status",
    "confidence",
    "review_reason",
    "carduploader_row",
    "ebay_row",
    "carduploader_title",
    "ebay_listing_title",
    "tcgplayer_product_id",
    "tcgplayer_sku",
    "catalog_sku",
    "ebay_item_id",
    "condition",
    "variant",
    "carduploader_quantity",
    "ebay_available_quantity",
    "carduploader_user_sku_source_ref",
    "ebay_custom_label_source_ref",
]


@dataclass
class InventoryCandidate:
    row_number: int
    raw: dict[str, str]
    cardvector_inventory_id: str = ""
    inventory_status: str = ""
    acquisition_lot_id: str = ""
    etb_id: str = ""
    location_code: str = ""
    audit_status: str = ""
    mobile_published: str = ""
    title: str = ""
    card_name: str = ""
    set_name: str = ""
    card_number: str = ""
    variant: str = ""
    finish: str = ""
    condition: str = ""
    quantity: str = ""
    price: str = ""
    tcgplayer_product_id: str = ""
    tcgplayer_sku: str = ""
    catalog_sku: str = ""
    carduploader_source_id: str = ""
    carduploader_custom_sku: str = ""
    carduploader_user_sku: str = ""
    ebay_item_id: str = ""
    ebay_listing_title: str = ""
    ebay_available_quantity: str = ""
    ebay_sold_quantity: str = ""
    ebay_listing_status: str = ""
    ebay_listing_price: str = ""
    ebay_category: str = ""
    ebay_product_id: str = ""
    ebay_source_sku: str = ""
    source_provider: str = ""
    source_file: str = ""
    import_timestamp: str = ""
    source_row_hash: str = ""

    def title_for_matching(self) -> str:
        return self.ebay_listing_title or self.title or self.card_name


@dataclass
class SourceImport:
    provider: str
    source_file: Path
    records: list[InventoryCandidate]
    fieldnames: list[str]
    errors: list[str] = field(default_factory=list)


@dataclass
class MatchResult:
    match_status: str
    confidence: str
    review_reason: str
    carduploader: InventoryCandidate | None = None
    ebay: InventoryCandidate | None = None

    def to_report_row(self) -> dict[str, str]:
        carduploader = self.carduploader
        ebay = self.ebay
        return {
            "match_status": self.match_status,
            "confidence": self.confidence,
            "review_reason": self.review_reason,
            "carduploader_row": str(carduploader.row_number if carduploader else ""),
            "ebay_row": str(ebay.row_number if ebay else ""),
            "carduploader_title": carduploader.title if carduploader else "",
            "ebay_listing_title": ebay.ebay_listing_title if ebay else "",
            "tcgplayer_product_id": carduploader.tcgplayer_product_id if carduploader else "",
            "tcgplayer_sku": carduploader.tcgplayer_sku if carduploader else "",
            "catalog_sku": carduploader.catalog_sku if carduploader else "",
            "ebay_item_id": ebay.ebay_item_id if ebay else "",
            "condition": carduploader.condition if carduploader else (ebay.condition if ebay else ""),
            "variant": carduploader.variant or carduploader.finish if carduploader else "",
            "carduploader_quantity": carduploader.quantity if carduploader else "",
            "ebay_available_quantity": ebay.ebay_available_quantity if ebay else "",
            "carduploader_user_sku_source_ref": carduploader.carduploader_user_sku if carduploader else "",
            "ebay_custom_label_source_ref": ebay.ebay_source_sku if ebay else "",
        }


def read_csv_rows(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    for encoding in ["utf-8-sig", "utf-8", "cp1252"]:
        try:
            with path.open("r", encoding=encoding, newline="") as handle:
                sample = handle.read(4096)
                handle.seek(0)
                try:
                    dialect = csv.Sniffer().sniff(sample)
                except csv.Error:
                    dialect = csv.excel
                reader = csv.DictReader(handle, dialect=dialect)
                rows = list(reader)
                return rows, list(reader.fieldnames or [])
        except UnicodeDecodeError:
            continue
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        return rows, list(reader.fieldnames or [])


def normalize_column_name(value: str) -> str:
    return "".join(ch for ch in str(value or "").lower().strip() if ch.isalnum())


def find_column(fieldnames: list[str], candidates: list[str]) -> str | None:
    normalized = {normalize_column_name(name): name for name in fieldnames}
    for candidate in candidates:
        found = normalized.get(normalize_column_name(candidate))
        if found:
            return found
    return None


def value(row: dict[str, str], column: str | None) -> str:
    if not column:
        return ""
    return str(row.get(column, "") or "").strip()


def row_hash(row: dict[str, str]) -> str:
    payload = json.dumps(row, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def parse_int(value_text: str) -> int | None:
    raw = str(value_text or "").replace(",", "").strip()
    if not raw:
        return None
    try:
        return int(float(raw))
    except ValueError:
        return None


def normalize_text(text: str) -> str:
    text = str(text or "").lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def token_set(text: str) -> set[str]:
    stop_words = {"the", "and", "or", "a", "an", "of", "pokemon", "card", "cards"}
    return {token for token in normalize_text(text).split() if len(token) > 1 and token not in stop_words}


def token_overlap(left: str, right: str) -> float:
    left_tokens = token_set(left)
    right_tokens = token_set(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / max(len(left_tokens), len(right_tokens))


def compatible_condition(left: str, right: str) -> bool:
    if not left or not right:
        return True
    aliases = {
        "near mint": "nm",
        "nm": "nm",
        "lightly played": "lp",
        "lp": "lp",
        "moderately played": "mp",
        "mp": "mp",
        "heavily played": "hp",
        "hp": "hp",
        "damaged": "dmg",
        "dmg": "dmg",
    }
    return aliases.get(normalize_text(left), normalize_text(left)) == aliases.get(normalize_text(right), normalize_text(right))


def compatible_variant(carduploader: InventoryCandidate, ebay: InventoryCandidate) -> bool:
    variant = normalize_text(carduploader.variant or carduploader.finish)
    if not variant:
        return True
    ebay_text = normalize_text(ebay.ebay_listing_title)
    variant_tokens = token_set(variant)
    if not variant_tokens:
        return True
    return bool(variant_tokens & token_set(ebay_text))


def has_card_number_match(carduploader: InventoryCandidate, ebay: InventoryCandidate) -> bool:
    card_number = normalize_text(carduploader.card_number)
    if not card_number:
        return False
    ebay_title = normalize_text(ebay.ebay_listing_title)
    return bool(re.search(rf"(^|\s|#){re.escape(card_number)}($|\s|/|-)", ebay_title))


class CardUploaderInventorySource:
    provider = PROVIDER_CARDUPLOADER

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load(self) -> SourceImport:
        result = CardUploaderInventoryService().load_inventory(self.path)
        records = [
            InventoryCandidate(
                row_number=item.row_number,
                raw=dict(item.raw),
                title=item.title,
                card_name=item.title,
                set_name=item.set_name,
                card_number=item.card_number,
                variant=item.variant or item.rarity,
                finish=item.finish,
                condition=item.condition,
                quantity=item.quantity,
                price=item.price,
                tcgplayer_product_id=item.tcgplayer_product_id,
                tcgplayer_sku=item.tcgplayer_sku,
                catalog_sku=item.catalog_sku,
                carduploader_source_id=item.source_id,
                # External SKU fields remain source references, never CardVector IDs.
                carduploader_custom_sku=item.custom_sku,
                carduploader_user_sku=item.user_sku,
                inventory_status=item.status,
                source_provider=self.provider,
                source_file=item.source_file,
                import_timestamp=item.imported_at,
                source_row_hash=item.source_row_hash,
            )
            for item in result.items
        ]
        return SourceImport(
            self.provider,
            self.path,
            records,
            list(result.fieldnames),
            list(result.errors),
        )


class EbayActiveListingsSource:
    provider = PROVIDER_EBAY

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load(self) -> SourceImport:
        rows, fieldnames = read_csv_rows(self.path)
        mapping = {field: find_column(fieldnames, candidates) for field, candidates in EBAY_COLUMNS.items()}
        timestamp = datetime.now().isoformat(timespec="seconds")
        records = []
        errors = []
        if not mapping.get("ebay_item_id"):
            errors.append("eBay file is missing Item number / Item ID.")
        if not mapping.get("ebay_listing_title"):
            errors.append("eBay file is missing listing title.")
        for index, row in enumerate(rows, start=1):
            title = value(row, mapping.get("ebay_listing_title"))
            records.append(
                InventoryCandidate(
                    row_number=index,
                    raw=row,
                    title=title,
                    condition=value(row, mapping.get("condition")),
                    ebay_item_id=value(row, mapping.get("ebay_item_id")),
                    ebay_listing_title=title,
                    ebay_available_quantity=value(row, mapping.get("available_quantity")),
                    ebay_sold_quantity=value(row, mapping.get("sold_quantity")),
                    ebay_listing_status=value(row, mapping.get("listing_status")),
                    ebay_listing_price=value(row, mapping.get("listing_price")),
                    ebay_category=value(row, mapping.get("category")),
                    ebay_product_id=value(row, mapping.get("ebay_product_id")),
                    # eBay Custom Label is preserved as a source reference, not a CardVector master key.
                    ebay_source_sku=value(row, mapping.get("source_sku")),
                    source_provider=self.provider,
                    source_file=str(self.path),
                    import_timestamp=timestamp,
                    source_row_hash=row_hash(row),
                )
            )
        return SourceImport(self.provider, self.path, records, fieldnames, errors)


def duplicate_key_count(records: list[InventoryCandidate], key_name: str) -> int:
    seen: dict[str, int] = {}
    for record in records:
        key = str(getattr(record, key_name, "") or "").strip()
        if key:
            seen[key] = seen.get(key, 0) + 1
    return sum(1 for count in seen.values() if count > 1)


def quantity_mismatch(carduploader: InventoryCandidate, ebay: InventoryCandidate) -> bool:
    carduploader_qty = parse_int(carduploader.quantity)
    ebay_qty = parse_int(ebay.ebay_available_quantity)
    if carduploader_qty is None or ebay_qty is None:
        return False
    return carduploader_qty != ebay_qty


def strong_matches(carduploader_records: list[InventoryCandidate], ebay: InventoryCandidate) -> list[InventoryCandidate]:
    candidates = []
    for record in carduploader_records:
        if not compatible_condition(record.condition, ebay.condition):
            continue
        if not compatible_variant(record, ebay):
            continue
        if ebay.tcgplayer_product_id and record.tcgplayer_product_id == ebay.tcgplayer_product_id:
            candidates.append(record)
        elif ebay.tcgplayer_sku and record.tcgplayer_sku == ebay.tcgplayer_sku:
            candidates.append(record)
    return candidates


def medium_matches(carduploader_records: list[InventoryCandidate], ebay: InventoryCandidate) -> list[InventoryCandidate]:
    candidates = []
    for record in carduploader_records:
        if not compatible_condition(record.condition, ebay.condition):
            continue
        if not compatible_variant(record, ebay):
            continue
        if not has_card_number_match(record, ebay):
            continue
        set_overlap = token_overlap(record.set_name, ebay.ebay_listing_title)
        title_overlap = token_overlap(record.title, ebay.ebay_listing_title)
        if set_overlap >= 0.60 and title_overlap >= 0.35:
            candidates.append(record)
    return candidates


def low_review_candidates(carduploader_records: list[InventoryCandidate], ebay: InventoryCandidate) -> list[InventoryCandidate]:
    scored = []
    for record in carduploader_records:
        score = token_overlap(record.title, ebay.ebay_listing_title)
        if score >= 0.50:
            scored.append((score, record))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [record for _, record in scored[:5]]


def reconcile(carduploader_import: SourceImport, ebay_import: SourceImport) -> dict[str, Any]:
    carduploader_records = carduploader_import.records
    ebay_records = ebay_import.records
    matches: list[MatchResult] = []
    matched_carduploader_rows: set[int] = set()
    matched_ebay_rows: set[int] = set()
    quantity_mismatch_count = 0

    for ebay in ebay_records:
        strong = strong_matches(carduploader_records, ebay)
        if len(strong) == 1:
            record = strong[0]
            reason = "Matched by external product identifier."
            if quantity_mismatch(record, ebay):
                quantity_mismatch_count += 1
                reason += " Quantity differs and needs review."
                status = "needs_review"
                confidence = "low"
            else:
                status = "matched"
                confidence = "high"
            matches.append(MatchResult(status, confidence, reason, record, ebay))
            matched_carduploader_rows.add(record.row_number)
            matched_ebay_rows.add(ebay.row_number)
            continue
        if len(strong) > 1:
            matches.append(MatchResult("needs_review", "low", "Multiple CardUploader records share a strong identifier.", strong[0], ebay))
            matched_ebay_rows.add(ebay.row_number)
            continue

        medium = medium_matches(carduploader_records, ebay)
        if len(medium) == 1:
            record = medium[0]
            reason = "Matched by title/set/card number with compatible condition and variant."
            if quantity_mismatch(record, ebay):
                quantity_mismatch_count += 1
                reason += " Quantity differs and needs review."
                status = "needs_review"
                confidence = "low"
            else:
                status = "matched"
                confidence = "medium"
            matches.append(MatchResult(status, confidence, reason, record, ebay))
            matched_carduploader_rows.add(record.row_number)
            matched_ebay_rows.add(ebay.row_number)
            continue
        if len(medium) > 1:
            matches.append(MatchResult("needs_review", "low", "Multiple medium-confidence candidates found.", medium[0], ebay))
            matched_ebay_rows.add(ebay.row_number)
            continue

        low = low_review_candidates(carduploader_records, ebay)
        if low:
            matches.append(MatchResult("needs_review", "low", "Title appears similar, but no stronger identifier matched.", low[0], ebay))
            matched_ebay_rows.add(ebay.row_number)

    for record in carduploader_records:
        if record.row_number not in matched_carduploader_rows:
            matches.append(MatchResult("carduploader_only", "none", "No high or medium eBay match found.", record, None))

    for ebay in ebay_records:
        if ebay.row_number not in matched_ebay_rows:
            matches.append(MatchResult("ebay_only", "none", "No CardUploader candidate found.", None, ebay))

    summary = {
        "carduploader_records": len(carduploader_records),
        "ebay_listings": len(ebay_records),
        "high_confidence_matches": sum(1 for item in matches if item.match_status == "matched" and item.confidence == "high"),
        "medium_confidence_matches": sum(1 for item in matches if item.match_status == "matched" and item.confidence == "medium"),
        "needs_review": sum(1 for item in matches if item.match_status == "needs_review"),
        "carduploader_only": sum(1 for item in matches if item.match_status == "carduploader_only"),
        "ebay_only": sum(1 for item in matches if item.match_status == "ebay_only"),
        "quantity_mismatches": quantity_mismatch_count,
        "duplicate_candidates": duplicate_key_count(carduploader_records, "tcgplayer_product_id")
        + duplicate_key_count(carduploader_records, "tcgplayer_sku"),
        "errors": len(carduploader_import.errors) + len(ebay_import.errors),
    }
    return {
        "summary": summary,
        "errors": carduploader_import.errors + ebay_import.errors,
        "carduploader_source": str(carduploader_import.source_file),
        "ebay_source": str(ebay_import.source_file),
        "matches": matches,
    }


def write_report(result: dict[str, Any], output_dir: Path | None = None) -> dict[str, Path]:
    target_dir = output_dir or RECONCILIATION_EXPORT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = target_dir / f"inventory_reconciliation_{stamp}.json"
    csv_path = target_dir / f"inventory_reconciliation_{stamp}.csv"
    report_rows = [match.to_report_row() for match in result["matches"]]
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "summary": result["summary"],
        "errors": result["errors"],
        "carduploader_source": result["carduploader_source"],
        "ebay_source": result["ebay_source"],
        "authority_rules": {
            "cardvector_location_authority": "ETB/location workflows only",
            "carduploader_sku_use": "source reference only",
            "ebay_item_id_use": "external listing reference",
        },
        "matches": report_rows,
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REPORT_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(report_rows)
    return {"json": json_path, "csv": csv_path}


def run_reconciliation(carduploader_csv: str | Path, ebay_csv: str | Path, output_dir: str | Path | None = None) -> dict[str, Any]:
    carduploader_import = CardUploaderInventorySource(carduploader_csv).load()
    ebay_import = EbayActiveListingsSource(ebay_csv).load()
    result = reconcile(carduploader_import, ebay_import)
    paths = write_report(result, Path(output_dir) if output_dir else None)
    return {
        "summary": result["summary"],
        "errors": result["errors"],
        "report_paths": {name: str(path) for name, path in paths.items()},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a conservative CardVector inventory reconciliation report.")
    parser.add_argument("--carduploader", required=True, help="Path to CardUploader inventory export CSV.")
    parser.add_argument("--ebay", required=True, help="Path to eBay active listings report CSV.")
    parser.add_argument("--output-dir", default="", help="Optional report output directory. Defaults to Data/Exports/Reconciliation.")
    args = parser.parse_args(argv)

    result = run_reconciliation(args.carduploader, args.ebay, args.output_dir or None)
    print(json.dumps(result, indent=2))
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
