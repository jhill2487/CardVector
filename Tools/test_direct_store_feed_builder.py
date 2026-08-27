import csv
import json
import tempfile
import unittest
from pathlib import Path

from build_direct_store_feed import build_feed


class DirectStoreFeedBuilderTests(unittest.TestCase):
    def write_fixture(self, rows):
        handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="", suffix=".csv", delete=False)
        path = Path(handle.name)
        fieldnames = [
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
            "Image URLs",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        handle.close()
        self.addCleanup(path.unlink, missing_ok=True)
        return path

    def test_publishes_available_carduploader_rows_without_images_by_default(self):
        path = self.write_fixture([
            {
                "Title": "Pikachu 001 Test Set Pokemon English Near Mint",
                "User SKU": "ETB-001-A.1",
                "Catalog SKU": "CS-ABC123",
                "TCG": "pokemon english",
                "Set": "Test Set",
                "Card Number": "001",
                "Rarity": "Common",
                "Condition": "NM",
                "Variant": "Normal",
                "Price": "1.98",
                "Qty": "2",
                "Status": "listed",
                "Image URLs": "https://example.test/card.jpg",
            },
            {
                "Title": "Sold Card",
                "Catalog SKU": "CS-SOLD",
                "TCG": "pokemon english",
                "Price": "4.99",
                "Qty": "1",
                "Status": "sold",
            },
            {
                "Title": "Zero Qty Card",
                "Catalog SKU": "CS-ZERO",
                "TCG": "mtg",
                "Price": "2.99",
                "Qty": "0",
                "Status": "listed",
            },
        ])

        feed = build_feed(path)

        self.assertEqual("1.1", feed["schema_version"])
        self.assertEqual("hybrid_static_browse_live_availability_pending", feed["checkout_mode"])
        self.assertFalse(feed["availability"]["supabase_enabled"])
        self.assertEqual(1, feed["summary"]["published_items"])
        self.assertEqual(2, feed["summary"]["published_quantity"])
        self.assertEqual(1, feed["summary"]["skipped_zero_quantity"])
        self.assertEqual(1, feed["summary"]["skipped_status"])
        item = feed["items"][0]
        self.assertRegex(item["id"], r"^cv-[a-f0-9]{16}$")
        self.assertEqual("Pokemon", item["game"])
        self.assertEqual("Test Set", item["set_name"])
        self.assertEqual("001", item["card_number"])
        self.assertNotIn("image_url", item)
        self.assertNotIn("source_listing_id", item)
        self.assertNotIn("inventory_reference", item)

    def test_same_filename_is_irrelevant_and_same_catalog_sku_aggregates_quantity(self):
        path = self.write_fixture([
            {
                "Title": "Island MTG Near Mint",
                "Catalog SKU": "CS-LAND",
                "TCG": "mtg",
                "Price": "$1.58",
                "Qty": "1",
                "Status": "listed",
                "Image URLs": "duplicate-name.jpg",
            },
            {
                "Title": "Island MTG Near Mint",
                "Catalog SKU": "CS-LAND",
                "TCG": "mtg",
                "Price": "$1.58",
                "Qty": "1",
                "Status": "listed",
                "Image URLs": "duplicate-name.jpg",
            },
        ])

        feed = build_feed(path, include_images=True)

        self.assertEqual(1, feed["summary"]["published_items"])
        self.assertEqual(2, feed["items"][0]["quantity_available"])
        self.assertRegex(feed["items"][0]["id"], r"^cv-[a-f0-9]{16}$")

    def test_feed_json_is_serializable(self):
        path = self.write_fixture([
            {
                "Title": "Serializable Card",
                "Catalog SKU": "CS-JSON",
                "TCG": "magic",
                "Price": "2.50",
                "Qty": "3",
                "Status": "listed",
            },
        ])

        encoded = json.dumps(build_feed(path))
        self.assertIn("Magic: The Gathering", encoded)


if __name__ == "__main__":
    unittest.main()
