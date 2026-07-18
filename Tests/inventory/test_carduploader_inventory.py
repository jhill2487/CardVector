from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from Platform.cardvector.application import InventoryApplication
from Platform.cardvector.application.runtime import EventPublisher, ExecutionContext
from Platform.cardvector.integrations.carduploader import (
    CARDUPLOADER_INVENTORY_COLUMNS,
    CardUploaderInventoryCapabilityUnavailable,
    CardUploaderInventoryService,
    InventoryQuery,
)
from Platform.Putnam_OS.System.app.inventory_reconciliation import (
    CardUploaderInventorySource,
)


ROOT = Path(__file__).resolve().parents[2]
PUTNAM_OS_SOURCE = (
    ROOT / "Platform" / "Putnam_OS" / "System" / "app" / "putnam_os.py"
).read_text(encoding="utf-8")


def write_inventory(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(CARDUPLOADER_INVENTORY_COLUMNS),
        )
        writer.writeheader()
        writer.writerows(rows)


class CardUploaderInventoryContractTests(unittest.TestCase):
    def test_repository_snapshot_remains_read_only_and_source_faithful(self):
        source = (
            ROOT
            / "Data"
            / "Imports"
            / "CardUploader_Inventory"
            / "inventory-2026-06-28.csv"
        )
        result = CardUploaderInventoryService().load_inventory(source)

        self.assertEqual(len(result.items), 308)
        self.assertEqual(result.errors, ())
        first = result.items[0]
        self.assertEqual(first.user_sku, "")
        self.assertEqual(first.location, "")
        self.assertEqual(first.inventory_id, first.catalog_sku)
        self.assertTrue(all(item.quantity_value >= 0 for item in result.items))

    def test_snapshot_contract_preserves_identity_quantity_location_and_serialization(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "inventory.csv"
            write_inventory(
                source,
                [
                    {
                        "Title": "Pikachu 025/165",
                        "User SKU": "ETB-001-A",
                        "Catalog SKU": "CAT-1",
                        "TCGplayer SKU": "TCG-1",
                        "TCGplayer Product ID": "12345",
                        "TCG": "Pokemon",
                        "Set": "151",
                        "Card Number": "025/165",
                        "Condition": "Near Mint",
                        "Price": "1.49",
                        "Qty": "2",
                        "Status": "Listed",
                    }
                ],
            )
            result = CardUploaderInventoryService().load_inventory(source)

        self.assertEqual(result.provider, "carduploader_inventory")
        self.assertEqual(result.errors, ())
        item = result.items[0]
        self.assertEqual(item.inventory_id, "ETB-001-A")
        self.assertEqual(item.location, "ETB-001-A")
        self.assertEqual(item.quantity, "2")
        self.assertEqual(item.quantity_value, 2)
        self.assertEqual(item.status, "Listed")
        serialized = result.to_dict()
        self.assertEqual(serialized["items"][0]["inventory_id"], "ETB-001-A")
        self.assertEqual(serialized["items"][0]["quantity_value"], 2)

    def test_legacy_reconciliation_source_delegates_without_output_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "inventory.csv"
            write_inventory(
                source,
                [
                    {
                        "Title": "Pikachu 025/165",
                        "User SKU": "ETB-001-A",
                        "Catalog SKU": "CAT-1",
                        "TCGplayer SKU": "TCG-1",
                        "TCGplayer Product ID": "12345",
                        "Condition": "Near Mint",
                        "Price": "1.49",
                        "Qty": "2",
                        "Status": "Listed",
                    }
                ],
            )
            canonical = CardUploaderInventoryService().load_inventory(source)
            legacy = CardUploaderInventorySource(source).load()

        item = canonical.items[0]
        record = legacy.records[0]
        self.assertEqual(record.title, item.title)
        self.assertEqual(record.carduploader_user_sku, item.user_sku)
        self.assertEqual(record.catalog_sku, item.catalog_sku)
        self.assertEqual(record.tcgplayer_sku, item.tcgplayer_sku)
        self.assertEqual(record.tcgplayer_product_id, item.tcgplayer_product_id)
        self.assertEqual(record.quantity, item.quantity)
        self.assertEqual(record.price, item.price)
        self.assertEqual(record.inventory_status, item.status)
        self.assertEqual(record.source_row_hash, item.source_row_hash)

    def test_search_is_read_only_and_uses_carduploader_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "inventory.csv"
            write_inventory(
                source,
                [
                    {
                        "Title": "Pikachu",
                        "User SKU": "ETB-001-A",
                        "TCG": "Pokemon",
                        "Status": "Listed",
                    },
                    {
                        "Title": "Luffy",
                        "User SKU": "ETB-002-B",
                        "TCG": "One Piece",
                        "Status": "Stored",
                    },
                ],
            )
            result = CardUploaderInventoryService().search_inventory(
                source,
                InventoryQuery(tcg="Pokemon", status="Listed"),
            )

        self.assertEqual([item.title for item in result.items], ["Pikachu"])

    def test_unsupported_live_mutation_capabilities_are_explicit(self):
        service = CardUploaderInventoryService()
        self.assertTrue(service.capabilities.snapshot_read)
        self.assertFalse(service.capabilities.authoritative_write)
        self.assertFalse(service.capabilities.reservations)
        self.assertFalse(service.capabilities.allocations)
        self.assertFalse(service.capabilities.pick_confirmation)
        self.assertFalse(service.capabilities.live_sync)
        with self.assertRaises(CardUploaderInventoryCapabilityUnavailable):
            service.require_capability("authoritative_write")

    def test_export_normalization_matches_legacy_shape(self):
        service = CardUploaderInventoryService()
        normalized = service.normalize_export_row(
            {
                "Title": " Pikachu ",
                "Price": "$1,234.5",
                "Qty": "-2",
                "Unexpected": "not copied",
            }
        )
        self.assertEqual(list(normalized), list(CARDUPLOADER_INVENTORY_COLUMNS))
        self.assertEqual(normalized["Title"], "Pikachu")
        self.assertEqual(normalized["Price"], "1234.50")
        self.assertEqual(normalized["Qty"], "0")
        self.assertNotIn("Unexpected", normalized)


class InventoryApplicationTests(unittest.TestCase):
    def test_application_delegates_snapshot_load_and_publishes_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "inventory.csv"
            write_inventory(source, [{"Title": "Pikachu", "Qty": "1"}])
            events = []
            publisher = EventPublisher()
            publisher.subscribe("inventory.snapshot_loaded", events.append)
            context = ExecutionContext.create(events=publisher)
            application = InventoryApplication(CardUploaderInventoryService())
            result = application.load_inventory(source, context)

        self.assertEqual(len(result.items), 1)
        self.assertEqual(events[0].name, "inventory.snapshot_loaded")
        self.assertEqual(events[0].payload["provider"], "carduploader_inventory")
        self.assertEqual(events[0].payload["item_count"], 1)

    def test_putnam_os_routes_inventory_through_application_service(self):
        self.assertIn(
            'runtime.services.register("inventory", inventory_application)',
            PUTNAM_OS_SOURCE,
        )
        self.assertIn(
            'self.application_runtime.services.resolve(\n'
            '            "inventory",\n'
            "            InventoryApplication,",
            PUTNAM_OS_SOURCE,
        )
        self.assertIn(
            "inventory_application.normalize_export_rows(rows)",
            PUTNAM_OS_SOURCE,
        )
        self.assertIn(
            "inventory_application.list_location_projection",
            PUTNAM_OS_SOURCE,
        )
        self.assertNotIn("Platform.cardvector.inventory", PUTNAM_OS_SOURCE)


if __name__ == "__main__":
    unittest.main()
