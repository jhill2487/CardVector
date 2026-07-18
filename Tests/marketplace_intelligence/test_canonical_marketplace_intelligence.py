from __future__ import annotations

import inspect
import sys
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock, patch


REPO_ROOT = Path(__file__).resolve().parents[2]
APP_DIR = REPO_ROOT / "Platform" / "Putnam_OS" / "System" / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from Platform.cardvector.application import PricingApplication
from Platform.cardvector.marketplace_intelligence import (
    PRICING_SERVICE,
    adapters,
    evidence,
    models,
    persistence,
    pricing,
)
from Platform.Marketplace_Intelligence.marketplace_intelligence import (
    models as proven_models,
    pricing_engine as proven_pricing,
)
from Platform.Marketplace_Intelligence.marketplace_intelligence import providers
from Platform.Putnam_OS.System.app import bulk_price_engine, main as legacy_main
from Platform.Putnam_OS.System.MarketIntelligence.Pricing import (
    pricing_engine as putnam_pricing_adapter,
)
import putnam_os


class CanonicalApiTests(unittest.TestCase):
    def test_public_models_are_aliases_not_duplicate_dataclasses(self):
        self.assertIs(models.FairMarketValue, proven_models.FairMarketValue)
        self.assertIs(models.PricingDecision, proven_models.PricingDecision)
        self.assertIs(models.PriceRecommendation, proven_models.PriceRecommendation)

    def test_public_pricing_api_reuses_proven_implementation(self):
        self.assertIs(
            pricing.calculate_market_value,
            proven_pricing.calculate_market_value,
        )
        self.assertIs(
            pricing.build_pricing_decision,
            proven_pricing.build_pricing_decision,
        )

    def test_pricing_service_forwards_to_canonical_pricing_module(self):
        with patch.object(
            pricing,
            "optimized_export_price",
            return_value=Decimal("2.99"),
        ) as delegated:
            actual = PRICING_SERVICE.optimized_export_price(
                Decimal("4.99"),
                Decimal("0.99"),
            )
        self.assertEqual(Decimal("2.99"), actual)
        delegated.assert_called_once_with(
            Decimal("4.99"),
            export_floor=Decimal("0.99"),
        )

    def test_application_layer_uses_injected_pricing_operations(self):
        service = Mock()
        service.calculate_market_value.return_value = Decimal("5.10")
        application = PricingApplication(service)

        actual = application.calculate_market_value({"accepted_count": 10})

        self.assertEqual(Decimal("5.10"), actual)
        service.calculate_market_value.assert_called_once_with(
            {"accepted_count": 10}
        )

    def test_application_runtime_registers_canonical_pricing_service(self):
        runtime = putnam_os.build_application_runtime()

        self.assertIs(runtime.services.resolve("pricing"), putnam_os.pricing_application)

    def test_persistence_contract_is_canonical_alias(self):
        from Platform.Marketplace_Intelligence.marketplace_intelligence import (
            pricing_repository as proven_repository,
        )

        self.assertIs(
            persistence.PricingDecisionRepository,
            proven_repository.PricingDecisionRepository,
        )
        self.assertEqual(
            persistence.MIGRATION_PATH,
            proven_repository.MIGRATION_PATH,
        )

    def test_adapter_contract_reuses_proven_provider_implementations(self):
        self.assertIs(
            adapters.CardUploaderSalesCacheProvider,
            providers.CardUploaderSalesCacheProvider,
        )
        self.assertIs(adapters.TCGtrackingProvider, providers.TCGtrackingProvider)


class ExactEquivalenceTests(unittest.TestCase):
    REPORTS = (
        None,
        {},
        {"accepted_count": 1, "confidence": 100, "median": "5.00"},
        {
            "accepted_count": 10,
            "confidence": 85,
            "median": "5.00",
            "last3_avg": "5.50",
            "last_sale": "4.50",
        },
        {
            "accepted_count": 3,
            "confidence": 59,
            "median": "5.00",
            "last_sale": "4.00",
        },
    )

    def test_fmv_and_price_vector_outputs_are_exact(self):
        for report in self.REPORTS:
            with self.subTest(report=report):
                self.assertEqual(
                    proven_pricing.fair_market_value_from_market_report(report),
                    pricing.fair_market_value_from_market_report(report),
                )
                self.assertEqual(
                    proven_pricing.build_pricing_decision("3.99", report),
                    PRICING_SERVICE.build_pricing_decision("3.99", report),
                )

    def test_putnam_helpers_route_through_application_and_match_canonical(self):
        report = {
            "accepted_count": 10,
            "confidence": 85,
            "median": "5.00",
            "last3_avg": "5.50",
            "last_sale": "4.50",
        }

        self.assertEqual(
            pricing.calculate_market_value(report),
            putnam_os.calculate_market_value(report),
        )
        self.assertEqual(
            pricing.apply_pricing_strategy(Decimal("5.00")),
            putnam_os.apply_pricing_strategy(Decimal("5.00")),
        )
        self.assertEqual(
            pricing.optimized_export_price(Decimal("4.99")),
            putnam_os.optimized_export_price(Decimal("4.99")),
        )

    def test_provider_strategy_is_exact_after_delegation(self):
        cases = (
            ("Fixture Card Test Set 001", "Fixture Card", "Test Set", "001"),
            ("Fixture Card Test Set 001 PSA 10", "Fixture Card", "Test Set", "001"),
            ("Different Card Test Set 001", "Fixture Card", "Test Set", "001"),
            ("Fixture Card Test Set 999", "Fixture Card", "Test Set", "001"),
        )
        for title, name, set_name, number in cases:
            with self.subTest(title=title):
                self.assertEqual(
                    evidence.provider_comparable_reason(
                        title,
                        name,
                        set_name,
                        number,
                    ),
                    providers.comparable_reason(
                        title,
                        name,
                        set_name,
                        number,
                    ),
                )


class CallerAndBoundaryTests(unittest.TestCase):
    def test_production_pricing_callers_use_canonical_public_path(self):
        modules = (
            bulk_price_engine,
            legacy_main,
            putnam_pricing_adapter,
        )
        for module in modules:
            with self.subTest(module=module.__name__):
                self.assertIs(module.canonical_pricing, pricing)

    def test_putnam_comparable_helpers_delegate_to_canonical_evidence(self):
        with patch.object(
            evidence,
            "comparable_reason",
            return_value=(True, "accepted", {"fixture": True}),
        ) as delegated:
            actual = putnam_os.comparable_reason(
                "Fixture Card",
                "Fixture Card",
                "",
                "",
            )

        self.assertEqual((True, "accepted", {"fixture": True}), actual)
        delegated.assert_called_once()

    def test_canonical_pricing_path_has_no_ui_recognition_or_grade_vector(self):
        sources = "\n".join(
            inspect.getsource(module).lower()
            for module in (pricing, evidence, models, persistence)
        )
        self.assertNotIn("tkinter", sources)
        self.assertNotIn("filedialog", sources)
        self.assertNotIn("recognition", sources)
        self.assertNotIn("grade_vector", sources)
        self.assertNotIn("gradevector", sources)


if __name__ == "__main__":
    unittest.main()
