from __future__ import annotations

import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from Platform.cardvector.integrations.carduploader.inventory import InventoryItem
from Platform.cardvector.integrations.carduploader.price_updates import (
    CardUploaderPriceUpdateError,
    CardUploaderPriceUpdatePolicy,
    build_price_update_plan,
    ebay_sold_search_query,
    require_apply_ready,
    write_price_update_plan_csv,
    write_price_update_plan_json,
)
from Platform.cardvector.marketplace_intelligence.models import (
    ExistingListingEvaluation,
    PricingExplanation,
)


def sample_item(**overrides):
    values = {
        "row_number": 7,
        "title": "Pikachu 025/025 Celebrations Holo Near Mint",
        "user_sku": "ETB-001-A.1",
        "catalog_sku": "CU-PIKA-025",
        "tcgplayer_sku": "12345",
        "tcgplayer_product_id": "67890",
        "tcg": "Pokemon",
        "set_name": "Celebrations",
        "card_number": "025/025",
        "condition": "Near Mint",
        "variant": "Holo",
        "finish": "Holo",
        "price": "3.00",
        "quantity": "2",
        "status": "Listed",
        "source_file": "carduploader.csv",
    }
    values.update(overrides)
    return InventoryItem(**values)


def sample_evaluation(**overrides):
    explanation = PricingExplanation(
        recommended_price=Decimal("3.50"),
        confidence="high",
        primary_market="ebay_sold",
        comparable_count=8,
        median_sold=Decimal("3.45"),
        average_sold=Decimal("3.52"),
        market_trend="stable",
        price_range_low=Decimal("3.00"),
        price_range_high=Decimal("4.00"),
        outliers_removed=1,
        review_required=False,
        review_decision="auto_approve",
        review_priority="normal",
        reason_codes=("HIGH_CONFIDENCE",),
        summary="Fixture sold comps support the price.",
        evidence_reference="fixture:sold-pikachu",
    )
    values = {
        "marketplace": "ebay",
        "listing_reference": "carduploader:CU-PIKA-025",
        "matched_card": "Pikachu 025/025 Celebrations",
        "match_confidence": "high",
        "recommended_price": Decimal("3.50"),
        "price_delta": Decimal("0.50"),
        "review_priority": "normal",
        "review_decision": "auto_approve",
        "reason_codes": ("HIGH_CONFIDENCE",),
        "explanation": explanation,
        "recommendation": "Increase Price",
    }
    values.update(overrides)
    return ExistingListingEvaluation(**values)


class CardUploaderPriceUpdateTests(unittest.TestCase):
    def test_carduploader_identity_builds_usable_ebay_sold_query(self):
        query = ebay_sold_search_query(sample_item())
        self.assertIn("Pikachu", query)
        self.assertIn("Celebrations", query)
        self.assertIn("025/025", query)
        self.assertIn("Near Mint", query)
        self.assertEqual(query.count("Holo"), 1)

    def test_dry_run_plan_is_not_apply_ready(self):
        plan = build_price_update_plan(sample_item(), sample_evaluation())
        self.assertEqual(plan.status, "dry_run")
        self.assertFalse(plan.is_apply_ready)
        self.assertEqual(plan.current_price, Decimal("3.00"))
        self.assertEqual(plan.recommended_price, Decimal("3.50"))
        self.assertEqual(plan.price_delta, Decimal("0.50"))
        self.assertEqual(plan.percent_delta, Decimal("16.67"))

    def test_approved_safe_plan_is_apply_ready(self):
        plan = build_price_update_plan(sample_item(), sample_evaluation(), approved=True)
        self.assertEqual(plan.status, "approved")
        self.assertTrue(plan.is_apply_ready)
        self.assertEqual(require_apply_ready([plan]), (plan,))

    def test_unapproved_or_blocked_plan_blocks_apply(self):
        dry_run = build_price_update_plan(sample_item(), sample_evaluation())
        blocked = build_price_update_plan(
            sample_item(price="3.00"),
            sample_evaluation(recommended_price=Decimal("6.00")),
            approved=True,
            policy=CardUploaderPriceUpdatePolicy(max_percent_move=Decimal("25.00")),
        )
        self.assertEqual(blocked.status, "blocked")
        self.assertIn("exceeds_max_percent_move", blocked.notes)
        with self.assertRaises(CardUploaderPriceUpdateError):
            require_apply_ready([dry_run, blocked])

    def test_review_required_plan_blocks_apply(self):
        plan = build_price_update_plan(
            sample_item(),
            sample_evaluation(match_confidence="medium", review_decision="manual_review"),
            approved=True,
        )
        self.assertEqual(plan.status, "blocked")
        self.assertIn("match_confidence_requires_review", plan.notes)
        self.assertIn("marketplace_intelligence_requires_review", plan.notes)

    def test_plan_writers_create_review_artifacts(self):
        plan = build_price_update_plan(sample_item(), sample_evaluation(), approved=True)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            csv_path = write_price_update_plan_csv(root / "plan.csv", [plan])
            json_path = write_price_update_plan_json(root / "plan.json", [plan])
            self.assertTrue(csv_path.exists())
            self.assertTrue(json_path.exists())
            self.assertIn("recommended_price", csv_path.read_text(encoding="utf-8"))
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(payload[0]["inventory_id"], "CU-PIKA-025")
            self.assertTrue(payload[0]["apply_ready"])


if __name__ == "__main__":
    unittest.main()
