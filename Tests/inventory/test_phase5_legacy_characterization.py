from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from Platform.Putnam_OS.System.app.inventory_locations import (
    create_etb_location,
    etb_location_rows,
    mark_location_complete,
)
from Platform.Putnam_OS.System.app.inventory_reconciliation import (
    CardUploaderInventorySource,
    EbayActiveListingsSource,
    reconcile,
)
from Platform.Putnam_OS.System.app.orders_fulfillment import generate_pick_slips


CARDUPLOADER_FIELDS = [
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


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


class Phase5LegacyCharacterizationTests(unittest.TestCase):
    def test_carduploader_snapshot_identity_quantity_and_source_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "inventory.csv"
            write_csv(
                source,
                CARDUPLOADER_FIELDS,
                [
                    {
                        "Title": "Pikachu 025/165",
                        "User SKU": "ETB-001-A",
                        "Catalog SKU": "CAT-1",
                        "TCGplayer SKU": "TCG-SKU-1",
                        "TCGplayer Product ID": "12345",
                        "TCG": "Pokemon",
                        "Set": "Pikachu 025 151",
                        "Card Number": "025/165",
                        "Condition": "Near Mint",
                        "Price": "1.49",
                        "Qty": "2",
                        "Status": "Listed",
                    }
                ],
            )
            imported = CardUploaderInventorySource(source).load()

        self.assertEqual(imported.provider, "carduploader_inventory")
        self.assertEqual(imported.errors, [])
        self.assertEqual(len(imported.records), 1)
        record = imported.records[0]
        self.assertEqual(record.title, "Pikachu 025/165")
        self.assertEqual(record.carduploader_user_sku, "ETB-001-A")
        self.assertEqual(record.catalog_sku, "CAT-1")
        self.assertEqual(record.tcgplayer_sku, "TCG-SKU-1")
        self.assertEqual(record.tcgplayer_product_id, "12345")
        self.assertEqual(record.quantity, "2")
        self.assertEqual(record.price, "1.49")
        self.assertEqual(record.inventory_status, "Listed")
        self.assertEqual(len(record.source_row_hash), 64)

    def test_reconciliation_result_and_quantity_mismatch_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            carduploader = root / "carduploader.csv"
            ebay = root / "ebay.csv"
            write_csv(
                carduploader,
                CARDUPLOADER_FIELDS,
                [
                    {
                        "Title": "Pikachu 025/165 151",
                        "TCGplayer Product ID": "12345",
                        "Set": "Pikachu 025 151",
                        "Card Number": "025/165",
                        "Condition": "Near Mint",
                        "Qty": "2",
                    }
                ],
            )
            write_csv(
                ebay,
                [
                    "Item number",
                    "Title",
                    "Available quantity",
                    "Condition",
                    "TCGplayer Product ID",
                ],
                [
                    {
                        "Item number": "999",
                        "Title": "Pikachu 025/165 151",
                        "Available quantity": "1",
                        "Condition": "Near Mint",
                        "TCGplayer Product ID": "12345",
                    }
                ],
            )
            result = reconcile(
                CardUploaderInventorySource(carduploader).load(),
                EbayActiveListingsSource(ebay).load(),
            )

        self.assertEqual(result["summary"]["quantity_mismatches"], 1)
        self.assertEqual(result["summary"]["needs_review"], 1)
        self.assertEqual(result["matches"][0].match_status, "needs_review")
        self.assertEqual(result["matches"][0].confidence, "low")

    def test_local_etb_projection_preserves_capacity_and_completion_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = Path(tmp) / "registry.json"
            created = create_etb_location(registry)
            updated = mark_location_complete(
                "ETB-001",
                "A",
                path=registry,
                captured_count=12,
            )
            rows = etb_location_rows(registry)

        self.assertEqual(created["location_code"], "ETB-001")
        self.assertEqual(len(created["locations"]), 10)
        self.assertEqual(updated["stored_count"], 12)
        self.assertEqual(rows[0]["total_capacity"], 400)
        self.assertEqual(rows[0]["locations"][0]["stored_count"], 12)
        self.assertEqual(rows[0]["locations"][0]["status"], "Needs Review")

    def test_pick_slip_generation_is_file_only_and_preserves_ordering(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "orders.csv"
            write_csv(
                source,
                [
                    "Order Number",
                    "Item Title",
                    "Quantity",
                    "Custom Label",
                ],
                [
                    {
                        "Order Number": "ORDER-2",
                        "Item Title": "Second",
                        "Quantity": "1",
                        "Custom Label": "ETB-001-B",
                    },
                    {
                        "Order Number": "ORDER-1",
                        "Item Title": "First",
                        "Quantity": "2",
                        "Custom Label": "ETB-001-A",
                    },
                ],
            )
            result = generate_pick_slips(source, root / "Pick_Lists")
            first_lines = Path(result["txt_files"][0]).read_text(encoding="utf-8")

        self.assertEqual(result["order_count"], 2)
        self.assertEqual(result["line_count"], 2)
        self.assertIn("Order number: ORDER-2", first_lines)
        self.assertIn("Location: ETB-001-B", first_lines)


if __name__ == "__main__":
    unittest.main()
