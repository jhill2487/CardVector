from __future__ import annotations

import inspect
import sys
import tempfile
import unittest
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[3]
APP_DIR = REPO_ROOT / "Platform" / "Putnam_OS" / "System" / "app"
for import_path in (REPO_ROOT, APP_DIR):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from Platform.cardvector.marketplace_intelligence import (  # noqa: E402
    pricing as canonical_pricing,
)
from Platform.cardvector.marketplace_intelligence.models import (  # noqa: E402
    PricingDecision,
)
from Platform.Putnam_OS.System.MarketIntelligence.Pricing import (  # noqa: E402
    pricing_engine as putnam_pricing_adapter,
)
from Platform.Putnam_OS.System.app import bulk_price_engine, main as legacy_main  # noqa: E402
import putnam_os  # noqa: E402


def strict_money(value) -> Decimal:
    if value is None:
        raise InvalidOperation("None")
    raw = str(value).strip().replace("$", "").replace(",", "")
    if not raw:
        raise InvalidOperation("blank")
    return Decimal(raw).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def money_text(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}"


class CanonicalPricingBehaviorTests(unittest.TestCase):
    REPORT = {
        "accepted_count": 10,
        "confidence": 85,
        "median": "5.00",
        "last3_avg": "5.50",
        "last_sale": "4.50",
    }

    def test_weighted_market_report_result_is_unchanged(self):
        decision = canonical_pricing.build_pricing_decision(
            original_price="3.99",
            market_report=self.REPORT,
            strategy="market_match",
        )

        self.assertEqual(Decimal("5.10"), decision.market_value)
        self.assertEqual(Decimal("5.10"), decision.recommended_price)
        self.assertEqual("AUTO_APPLIED", decision.review_status)

    def test_existing_strategy_and_no_market_behaviors_are_unchanged(self):
        fast_sell = canonical_pricing.build_pricing_decision(
            original_price="3.99",
            market_report=self.REPORT,
            strategy="fast_sell",
        )
        no_market = canonical_pricing.build_pricing_decision(
            original_price="3.99",
            market_report={"accepted_count": 2, "confidence": 100},
        )

        self.assertEqual(Decimal("4.85"), fast_sell.recommended_price)
        self.assertEqual(Decimal("3.99"), no_market.recommended_price)
        self.assertEqual("NO_MARKET_DATA", no_market.review_status)

    def test_listing_optimizer_boundaries_are_unchanged(self):
        cases = {
            "0.50": "0.99",
            "1.50": "0.99",
            "1.51": "1.49",
            "2.99": "1.49",
            "3.00": "2.99",
            "4.99": "2.99",
            "5.00": "5.00",
        }

        for source, expected in cases.items():
            with self.subTest(source=source):
                self.assertEqual(
                    Decimal(expected),
                    canonical_pricing.optimized_export_price(Decimal(source)),
                )

    def test_exact_ladder_and_new_listing_guardrails_are_unchanged(self):
        records = [
            {"old_price_raw": "1.49", "title": "Changed"},
            {"old_price_raw": "3.99", "title": "Unchanged"},
            {"old_price_raw": "", "title": "Invalid"},
        ]
        processed, invalid = canonical_pricing.apply_exact_price_ladder(
            records,
            canonical_pricing.LEGACY_DEFAULT_LADDER,
            parse_money=strict_money,
            format_money=money_text,
        )
        review = canonical_pricing.evaluate_new_listing_price(
            "20.00",
            canonical_pricing.LEGACY_DEFAULT_LADDER,
            floor=Decimal("0.99"),
            high_review_threshold=Decimal("20.00"),
            parse_money=strict_money,
            format_money=money_text,
        )

        self.assertEqual(("CHANGE", "0.99"), (processed[0]["status"], processed[0]["new_price"]))
        self.assertEqual(("UNCHANGED", "3.99"), (processed[1]["status"], processed[1]["new_price"]))
        self.assertEqual("INVALID_PRICE", invalid[0]["status"])
        self.assertEqual("REVIEW", review["status"])
        self.assertTrue(review["high_review"])


class PutnamPricingDelegationTests(unittest.TestCase):
    def test_integrated_pricing_package_delegates_to_canonical_engine(self):
        expected = PricingDecision(
            original_price=Decimal("3.99"),
            market_value=Decimal("5.10"),
            recommended_price=Decimal("5.10"),
            accepted_count=10,
            confidence=85,
            strategy="market_match",
            pricing_basis="weighted_market_value",
            review_status="AUTO_APPLIED",
        )
        with patch.object(
            putnam_pricing_adapter.canonical_pricing,
            "build_pricing_decision",
            return_value=expected,
        ) as delegated:
            actual = putnam_pricing_adapter.build_pricing_decision("3.99", {})

        self.assertIs(expected, actual)
        delegated.assert_called_once()

    def test_putnam_os_export_path_delegates_to_canonical_engine(self):
        expected = PricingDecision(
            original_price=Decimal("3.99"),
            market_value=Decimal("5.10"),
            recommended_price=Decimal("5.10"),
            accepted_count=10,
            confidence=85,
            strategy="market_match",
            pricing_basis="weighted_market_value",
            review_status="AUTO_APPLIED",
        )
        policies = {
            "shipping_policy": "Buyer Pays Shipping",
            "payment_policy": "Payment Policy",
            "return_policy": "Return Policy",
        }
        with (
            patch.object(
                putnam_os.pricing_application,
                "build_pricing_decision",
                return_value=expected,
            ) as delegated,
            patch.object(
                putnam_os,
                "load_app_config",
                return_value={
                    "pricing_strategy": "market_match",
                    "pricing_review_threshold": 60,
                    "pricing_auto_apply_threshold": 80,
                },
            ),
        ):
            result = putnam_os.prepare_listing_export_rows(
                [{"*Title": "Test Card", "*StartPrice": "3.99"}],
                "ETB-001-A",
                policies=policies,
                market_reports=[{"row": 1, "accepted_count": 10}],
            )

        self.assertEqual("5.10", result[0][0]["*StartPrice"])
        delegated.assert_called_once()

    def test_legacy_ladder_entry_points_delegate_to_canonical_engine(self):
        sentinel = ([{"status": "UNCHANGED"}], [])
        with patch.object(
            bulk_price_engine.canonical_pricing,
            "apply_exact_price_ladder",
            return_value=sentinel,
        ) as bulk_delegate:
            self.assertIs(sentinel, bulk_price_engine.apply_ladder([], {}))
        with patch.object(
            legacy_main.canonical_pricing,
            "apply_exact_price_ladder",
            return_value=sentinel,
        ) as main_delegate:
            self.assertIs(sentinel, legacy_main.apply_existing_ladder([], {}))

        bulk_delegate.assert_called_once()
        main_delegate.assert_called_once()

    def test_legacy_new_listing_review_delegates_to_canonical_engine(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "carduploader.csv"
            source.write_text("Title,Price\nTest Card,1.49\n", encoding="utf-8")
            with (
                patch.object(legacy_main, "COMPLETED_DIR", root / "completed"),
                patch.object(legacy_main, "log_run"),
                patch.object(
                    legacy_main,
                    "load_rules",
                    return_value={
                        "minimum_new_listing_price": "0.99",
                        "high_value_review_threshold": "20.00",
                        "price_ladder": canonical_pricing.LEGACY_DEFAULT_LADDER,
                    },
                ),
                patch.object(
                    legacy_main.canonical_pricing,
                    "evaluate_new_listing_price",
                    wraps=canonical_pricing.evaluate_new_listing_price,
                ) as delegated,
            ):
                _job, summary = legacy_main.review_new_listing_prices(source)

        self.assertEqual(1, summary["changed"])
        delegated.assert_called_once()

    def test_duplicate_formulas_are_absent_from_putnam_compatibility_modules(self):
        modules = (
            putnam_pricing_adapter,
            putnam_os,
            bulk_price_engine,
            legacy_main,
        )
        forbidden = (
            'Decimal("0.60")',
            'Decimal("0.30")',
            'Decimal("0.10")',
            'Decimal("0.95")',
            'Decimal("1.05")',
        )
        for module in modules:
            source = inspect.getsource(module)
            for formula in forbidden:
                with self.subTest(module=module.__name__, formula=formula):
                    self.assertNotIn(formula, source)

    def test_pricing_path_does_not_import_recognition_or_grade_vector(self):
        source = inspect.getsource(canonical_pricing).lower()
        self.assertNotIn("recognition", source)
        self.assertNotIn("grade_vector", source)
        self.assertNotIn("gradevector", source)


if __name__ == "__main__":
    unittest.main()
