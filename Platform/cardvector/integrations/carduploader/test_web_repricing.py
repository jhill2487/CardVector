from __future__ import annotations

import unittest
from decimal import Decimal

from Platform.cardvector.integrations.carduploader.price_updates import (
    CardUploaderPriceUpdateError,
    build_price_update_plan,
)
from Platform.cardvector.integrations.carduploader.test_price_updates import (
    sample_evaluation,
    sample_item,
)
from Platform.cardvector.integrations.carduploader.web_repricing import (
    CARDUPLOADER_AUTOMATIC_INVENTORY_URL,
    SAVE_MODE_AUTOSAVE,
    SAVE_MODE_MANUAL,
    SAVE_MODE_UNKNOWN,
    CardUploaderWebInventoryRow,
    CardUploaderWebPageSnapshot,
    CardUploaderWebSafetyPolicy,
    build_web_price_edits,
    carduploader_inventory_snapshot_script,
    normalize_carduploader_web_snapshot,
    require_web_apply_ready,
)


def visible_row(**overrides):
    values = {
        "row_key": "row-1",
        "title": "Pikachu 025/025 Celebrations Holo Near Mint",
        "current_price": "3.00",
        "quantity": "2",
        "inventory_id": "CU-PIKA-025",
        "catalog_sku": "CU-PIKA-025",
        "user_sku": "ETB-001-A.1",
        "price_input_selector": "[data-row='row-1'] input[name='price']",
    }
    values.update(overrides)
    return CardUploaderWebInventoryRow.from_mapping(values)


def snapshot(**overrides):
    values = {
        "url": CARDUPLOADER_AUTOMATIC_INVENTORY_URL,
        "rows": (visible_row(),),
        "save_mode": SAVE_MODE_MANUAL,
    }
    values.update(overrides)
    return CardUploaderWebPageSnapshot(**values)


class CardUploaderWebRepricingTests(unittest.TestCase):
    def test_snapshot_script_is_read_only(self):
        script = carduploader_inventory_snapshot_script()
        forbidden_tokens = (
            ".click(",
            ".fill(",
            ".type(",
            "dispatchEvent",
            "submit(",
            "fetch(",
            "XMLHttpRequest",
        )
        for token in forbidden_tokens:
            self.assertNotIn(token, script)
        self.assertIn("querySelectorAll('table')", script)

    def test_normalizes_carduploader_automatic_inventory_table(self):
        payload = {
            "url": CARDUPLOADER_AUTOMATIC_INVENTORY_URL,
            "captured_at": "2026-08-09T12:00:00Z",
            "controls": [{"text": "Set price"}],
            "tables": [
                {
                    "headers": [
                        "CARD",
                        "STATUS",
                        "PLATFORM",
                        "USER SKU",
                        "CATALOG SKU",
                        "CONDITION",
                        "VARIANT",
                        "TCG",
                        "PRICE",
                        "MARKET",
                        "QTY",
                        "ADDED",
                    ],
                    "rows": [
                        {
                            "row_index": 0,
                            "cells": [
                                "CARD",
                                "STATUS",
                                "PLATFORM",
                                "USER SKU",
                                "CATALOG SKU",
                                "CONDITION",
                                "VARIANT",
                                "TCG",
                                "PRICE",
                                "MARKET",
                                "QTY",
                                "ADDED",
                            ],
                        },
                        {
                            "row_index": 1,
                            "text": (
                                "King of the Pride (Retro Frame) Modern Horizons x1 "
                                "Listed ETB-007-H CS-WAVED9 NM Foil Mtg $1.98 $0.71 1 8/7/2026"
                            ),
                            "cells": [
                                "King of the Pride (Retro Frame)",
                                "Listed",
                                "eBay",
                                "ETB-007-H",
                                "CS-WAVED9",
                                "NM",
                                "Foil",
                                "Mtg",
                                "$1.98",
                                "$0.71",
                                "1",
                                "8/7/2026",
                            ],
                        },
                    ],
                }
            ],
        }
        page = normalize_carduploader_web_snapshot(payload)
        self.assertEqual(page.url, CARDUPLOADER_AUTOMATIC_INVENTORY_URL)
        self.assertEqual(page.save_mode, SAVE_MODE_UNKNOWN)
        self.assertEqual(len(page.rows), 1)
        self.assertEqual(page.rows[0].row_key, "CS-WAVED9")
        self.assertEqual(page.rows[0].title, "King of the Pride (Retro Frame)")
        self.assertEqual(page.rows[0].current_price, Decimal("1.98"))
        self.assertEqual(page.rows[0].quantity, 1)
        self.assertEqual(page.rows[0].catalog_sku, "CS-WAVED9")
        self.assertEqual(page.rows[0].user_sku, "ETB-007-H")
        self.assertIn("price inputs were not visible", page.operator_note)

    def test_read_only_table_snapshot_is_not_apply_ready(self):
        plan = build_price_update_plan(
            sample_item(price="1.98", catalog_sku="CS-WAVED9"),
            sample_evaluation(recommended_price="2.25"),
            approved=True,
        )
        page = CardUploaderWebPageSnapshot(
            url=CARDUPLOADER_AUTOMATIC_INVENTORY_URL,
            rows=(
                CardUploaderWebInventoryRow.from_mapping(
                    {
                        "row_key": "CS-WAVED9",
                        "catalog_sku": "CS-WAVED9",
                        "current_price": "$1.98",
                        "quantity": "1",
                    }
                ),
            ),
            save_mode=SAVE_MODE_UNKNOWN,
        )
        edits = build_web_price_edits(page, [plan])
        self.assertIn("price_input_selector_missing", edits[0].safety_notes)
        with self.assertRaisesRegex(CardUploaderPriceUpdateError, "carduploader_save_mode_unknown"):
            require_web_apply_ready(page, edits, confirm_live_sync=True)

    def test_builds_edit_from_visible_carduploader_row(self):
        plan = build_price_update_plan(sample_item(), sample_evaluation(), approved=True)
        edits = build_web_price_edits(snapshot(), [plan])
        self.assertEqual(len(edits), 1)
        self.assertEqual(edits[0].row_key, "row-1")
        self.assertEqual(edits[0].current_price, Decimal("3.00"))
        self.assertEqual(edits[0].recommended_price, Decimal("3.50"))
        self.assertTrue(edits[0].is_apply_ready)

    def test_wrong_page_blocks_apply(self):
        plan = build_price_update_plan(sample_item(), sample_evaluation(), approved=True)
        edits = build_web_price_edits(snapshot(), [plan])
        with self.assertRaisesRegex(CardUploaderPriceUpdateError, "not_carduploader_automatic_inventory_page"):
            require_web_apply_ready(
                snapshot(url="https://carduploader.com/dashboard/history"),
                edits,
                confirm_live_sync=True,
            )

    def test_unknown_save_mode_blocks_apply(self):
        plan = build_price_update_plan(sample_item(), sample_evaluation(), approved=True)
        page = snapshot(save_mode=SAVE_MODE_UNKNOWN)
        edits = build_web_price_edits(page, [plan])
        with self.assertRaisesRegex(CardUploaderPriceUpdateError, "carduploader_save_mode_unknown"):
            require_web_apply_ready(page, edits, confirm_live_sync=True)

    def test_autosave_blocks_apply_by_default(self):
        plan = build_price_update_plan(sample_item(), sample_evaluation(), approved=True)
        page = snapshot(save_mode=SAVE_MODE_AUTOSAVE)
        edits = build_web_price_edits(page, [plan])
        with self.assertRaisesRegex(CardUploaderPriceUpdateError, "autosave_page_blocked"):
            require_web_apply_ready(page, edits, confirm_live_sync=True)

    def test_explicit_live_sync_confirmation_is_required(self):
        plan = build_price_update_plan(sample_item(), sample_evaluation(), approved=True)
        page = snapshot()
        edits = build_web_price_edits(page, [plan])
        with self.assertRaisesRegex(CardUploaderPriceUpdateError, "live_sync_confirmation_required"):
            require_web_apply_ready(page, edits)

    def test_visible_price_mismatch_blocks_row(self):
        plan = build_price_update_plan(sample_item(price="3.00"), sample_evaluation(), approved=True)
        page = snapshot(rows=(visible_row(current_price="2.50"),))
        edits = build_web_price_edits(page, [plan])
        self.assertIn("visible_price_does_not_match_plan", edits[0].safety_notes)
        with self.assertRaisesRegex(CardUploaderPriceUpdateError, "unsafe_or_unapproved_rows"):
            require_web_apply_ready(page, edits, confirm_live_sync=True)

    def test_missing_price_input_selector_blocks_row(self):
        plan = build_price_update_plan(sample_item(), sample_evaluation(), approved=True)
        page = snapshot(rows=(visible_row(price_input_selector=""),))
        edits = build_web_price_edits(page, [plan])
        self.assertIn("price_input_selector_missing", edits[0].safety_notes)

    def test_unapproved_plan_blocks_apply(self):
        plan = build_price_update_plan(sample_item(), sample_evaluation(), approved=False)
        page = snapshot()
        edits = build_web_price_edits(page, [plan])
        self.assertFalse(edits[0].is_apply_ready)
        with self.assertRaisesRegex(CardUploaderPriceUpdateError, "unsafe_or_unapproved_rows"):
            require_web_apply_ready(page, edits, confirm_live_sync=True)

    def test_max_rows_per_apply_blocks_bulk_apply(self):
        plans = [
            build_price_update_plan(
                sample_item(row_number=index, catalog_sku=f"CU-PIKA-{index:03d}"),
                sample_evaluation(),
                approved=True,
            )
            for index in range(3)
        ]
        rows = tuple(
            visible_row(row_key=f"row-{index}", catalog_sku=f"CU-PIKA-{index:03d}")
            for index in range(3)
        )
        page = snapshot(rows=rows)
        edits = build_web_price_edits(page, plans)
        with self.assertRaisesRegex(CardUploaderPriceUpdateError, "too_many_rows_for_single_apply"):
            require_web_apply_ready(
                page,
                edits,
                policy=CardUploaderWebSafetyPolicy(max_rows_per_apply=2),
                confirm_live_sync=True,
            )


if __name__ == "__main__":
    unittest.main()
