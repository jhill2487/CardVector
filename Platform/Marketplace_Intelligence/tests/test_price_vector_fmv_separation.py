from __future__ import annotations

import inspect
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from Platform.Marketplace_Intelligence.marketplace_intelligence.config import (  # noqa: E402
    AppConfig,
)
from Platform.Marketplace_Intelligence.marketplace_intelligence.engine import (  # noqa: E402
    MarketplaceIntelligenceEngine,
)
from Platform.Marketplace_Intelligence.marketplace_intelligence.models import (  # noqa: E402
    AnalysisResult,
    Decision,
    FairMarketValue,
    Listing,
    ListingIdentity,
    MarketEvidence,
    MarketPrice,
    PriceRecommendation,
)
from Platform.Marketplace_Intelligence.marketplace_intelligence.pricing_engine import (  # noqa: E402
    PricingEngine,
    build_pricing_decision,
    fair_market_value_from_market_price,
)
from Platform.Marketplace_Intelligence.marketplace_intelligence.pricing_repository import (  # noqa: E402
    PricingDecisionRepository,
    pricing_record_from_result,
)
from Platform.Marketplace_Intelligence.marketplace_intelligence.reports import (  # noqa: E402
    result_row,
)


def pricing_profile(**overrides) -> dict[str, str]:
    profile = {
        "minimum_price": "0.99",
        "ignore_changes_under": "0.00",
        "maximum_increase_percent": "999.00",
        "maximum_decrease_percent": "999.00",
        "maximum_increase_amount": "999.00",
        "maximum_decrease_amount": "999.00",
        "shipping_assumption": "buyer_pays_shipping",
        "flat_shipping_cost": "0.00",
    }
    profile.update(overrides)
    return profile


def sample_listing(price: str = "4.00") -> Listing:
    return Listing(
        row_number=1,
        raw={},
        item_id="EBAY-1",
        title="Fixture Card",
        current_price=Decimal(price),
        sku="ETB-001-A",
    )


def sample_fmv(value: str = "5.00") -> FairMarketValue:
    evidence = MarketEvidence(
        source="fixture_ebay_sold",
        evidence_type="sold_comps_summary",
        value=Decimal(value),
        marketplace="ebay",
        condition="Near Mint",
        source_reference="fixture:sold-001",
    )
    return FairMarketValue(
        value=Decimal(value),
        confidence="85",
        reasoning="Fixture-backed sold-comps FMV.",
        evidence=(evidence,),
        evidence_reference="fixture:sold-001",
        calculated_at="2026-07-17T00:00:00+00:00",
        accepted_count=10,
    )


class ExplicitFmvPricingTests(unittest.TestCase):
    def test_fmv_recommendation_and_final_price_are_distinct_fields(self):
        engine = PricingEngine(
            pricing_profile(
                shipping_assumption="seller_pays_shipping",
                flat_shipping_cost="1.25",
            )
        )

        recommendation = engine.recommend_from_fmv(
            sample_listing(),
            sample_fmv("5.00"),
        )

        self.assertEqual(Decimal("5.00"), recommendation.fair_market_value)
        self.assertEqual(
            Decimal("6.25"),
            recommendation.recommended_listing_price,
        )
        self.assertEqual(Decimal("6.25"), recommendation.final_listing_price)
        self.assertNotEqual(
            recommendation.fair_market_value,
            recommendation.recommended_listing_price,
        )

    def test_price_vector_consumes_fmv_without_recalculating_raw_evidence(self):
        engine = PricingEngine(pricing_profile())
        with patch(
            "Platform.Marketplace_Intelligence.marketplace_intelligence."
            "pricing_engine._calculate_weighted_market_value",
            side_effect=AssertionError("Price Vector must not calculate FMV"),
        ):
            result = engine.recommend_from_fmv(sample_listing(), sample_fmv())

        self.assertEqual(Decimal("5.00"), result.recommended_listing_price)

    def test_final_price_defaults_to_recommendation(self):
        legacy = PriceRecommendation(
            recommended_price=Decimal("3.99"),
            difference=Decimal("0.00"),
            percent_change=Decimal("0.00"),
            pricing_reason="Compatibility fixture.",
        )

        self.assertEqual(Decimal("3.99"), legacy.recommended_price)
        self.assertEqual(Decimal("3.99"), legacy.recommended_listing_price)
        self.assertEqual(Decimal("3.99"), legacy.final_listing_price)

    def test_legacy_market_price_adapter_preserves_existing_result(self):
        engine = PricingEngine(
            pricing_profile(
                shipping_assumption="seller_pays_shipping",
                flat_shipping_cost="1.25",
            )
        )
        market = MarketPrice(
            matched=True,
            market_price=Decimal("5.00"),
            provider="fixture",
            source="stored_fixture",
            confidence="high",
            reason="Stored fixture.",
        )

        recommendation = engine.recommend(sample_listing(), market)

        self.assertEqual(Decimal("5.00"), recommendation.fair_market_value)
        self.assertEqual(Decimal("6.25"), recommendation.recommended_price)
        self.assertEqual(
            recommendation.recommended_price,
            recommendation.recommended_listing_price,
        )
        self.assertEqual(
            recommendation.recommended_listing_price,
            recommendation.final_listing_price,
        )

    def test_legacy_weighted_fixture_keeps_previous_recommendation(self):
        decision = build_pricing_decision(
            original_price="3.99",
            market_report={
                "accepted_count": 10,
                "confidence": 85,
                "median": "5.00",
                "last3_avg": "5.50",
                "last_sale": "4.50",
                "snapshot_id": "fixture:weighted-001",
            },
            strategy="fast_sell",
        )

        self.assertEqual(Decimal("5.10"), decision.fair_market_value)
        self.assertEqual(Decimal("4.85"), decision.recommended_listing_price)
        self.assertEqual(Decimal("4.85"), decision.final_listing_price)
        self.assertEqual(decision.market_value, decision.fair_market_value)
        self.assertEqual(
            decision.recommended_price,
            decision.recommended_listing_price,
        )
        self.assertEqual(
            "fixture:weighted-001",
            decision.market_evidence_reference,
        )

    def test_tcgplayer_active_listing_is_not_fmv(self):
        market = MarketPrice(
            matched=True,
            market_price=Decimal("4.50"),
            provider="TCGplayer",
            source="tcgplayer_live",
            confidence="high",
            reason="Lowest delivered active listing.",
            metadata={
                "evidence_type": "active_listing",
                "marketplace": "tcgplayer",
            },
        )

        fmv = fair_market_value_from_market_price(market)
        recommendation = PricingEngine(pricing_profile()).recommend_from_fmv(
            sample_listing(),
            fmv,
        )

        self.assertIsNone(fmv.value)
        self.assertFalse(fmv.evidence[0].accepted_for_fmv)
        self.assertIn("competition evidence", fmv.reasoning)
        self.assertEqual(
            sample_listing().current_price,
            recommendation.final_listing_price,
        )

    def test_pricecharting_raw_value_is_not_fmv(self):
        market = MarketPrice(
            matched=True,
            market_price=Decimal("7.00"),
            provider="PriceCharting",
            source="pricecharting",
            confidence="high",
        )

        fmv = fair_market_value_from_market_price(market)

        self.assertIsNone(fmv.value)
        self.assertFalse(fmv.evidence[0].accepted_for_fmv)
        self.assertIn("excluded", fmv.reasoning)

    def test_engine_uses_explicit_fmv_path(self):
        market = MarketPrice(
            matched=True,
            market_price=Decimal("5.00"),
            provider="fixture",
            source="fixture_sold",
            confidence="85",
            reason="Fixture market result.",
        )
        config = AppConfig(
            pricing_profile=pricing_profile(),
            business_profile={},
            market_provider={"provider": "none"},
        )
        engine = MarketplaceIntelligenceEngine(config)
        engine.provider = SimpleNamespace(get_market_price=lambda _identity: market)
        imported = SimpleNamespace(
            missing_required_fields=[],
            listings=[sample_listing()],
        )

        with (
            patch.object(
                engine.pricing_engine,
                "recommend",
                side_effect=AssertionError("Legacy recommendation path used"),
            ),
            patch.object(
                engine.pricing_engine,
                "recommend_from_fmv",
                wraps=engine.pricing_engine.recommend_from_fmv,
            ) as explicit_path,
        ):
            results = engine.analyze_import(imported)

        explicit_path.assert_called_once()
        self.assertEqual(Decimal("5.00"), results[0].fair_market_value.value)
        self.assertEqual(
            Decimal("5.00"),
            results[0].pricing.recommended_listing_price,
        )

    def test_reports_expose_new_fields_and_keep_legacy_fields(self):
        fmv = sample_fmv()
        pricing = PricingEngine(pricing_profile()).recommend_from_fmv(
            sample_listing(),
            fmv,
        )
        result = AnalysisResult(
            listing=sample_listing(),
            identity=ListingIdentity("fixture", "sku", "high"),
            market=MarketPrice(
                True,
                market_price=Decimal("5.00"),
                provider="fixture",
                source="fixture_sold",
                confidence="85",
            ),
            pricing=pricing,
            decision=Decision("Increase", "Fixture.", True),
            fair_market_value=fmv,
        )

        row = result_row(result)

        self.assertEqual("5.00", row["market_price"])
        self.assertEqual("5.00", row["fair_market_value"])
        self.assertEqual("5.00", row["recommended_price"])
        self.assertEqual("5.00", row["recommended_listing_price"])
        self.assertEqual("5.00", row["final_listing_price"])
        self.assertIn("sold_comps_summary", row["normalized_market_evidence"])

    def test_pricing_path_excludes_overlay_recognition_and_grade_vector(self):
        modules = (
            sys.modules[
                "Platform.Marketplace_Intelligence.marketplace_intelligence."
                "pricing_engine"
            ],
            sys.modules[
                "Platform.Marketplace_Intelligence.marketplace_intelligence."
                "models"
            ],
        )
        source = "\n".join(inspect.getsource(module).lower() for module in modules)
        self.assertNotIn("pokemon_lookup_overlay", source)
        self.assertNotIn("live_tcgplayer_prices", source)
        self.assertNotIn("recognition", source)
        self.assertNotIn("grade_vector", source)
        self.assertNotIn("gradevector", source)


class PricingPersistenceTests(unittest.TestCase):
    def test_migration_and_repository_round_trip_distinct_values(self):
        fmv = sample_fmv("5.00")
        pricing = PricingEngine(
            pricing_profile(
                shipping_assumption="seller_pays_shipping",
                flat_shipping_cost="1.25",
            )
        ).recommend_from_fmv(sample_listing(), fmv)
        result = AnalysisResult(
            listing=sample_listing(),
            identity=ListingIdentity("fixture", "sku", "high"),
            market=MarketPrice(
                True,
                market_price=Decimal("5.00"),
                provider="fixture",
                source="fixture_sold",
                confidence="85",
            ),
            pricing=pricing,
            decision=Decision("Increase", "Fixture.", True),
            fair_market_value=fmv,
        )

        with tempfile.TemporaryDirectory() as temporary:
            database = Path(temporary) / "price_vector.sqlite"
            repository = PricingDecisionRepository(database)
            repository.migrate()
            repository.migrate()
            record = pricing_record_from_result(
                result,
                decision_id="DECISION-001",
                created_at="2026-07-17T00:00:00+00:00",
            )
            repository.save(record)
            loaded = repository.get("DECISION-001")

            with closing(sqlite3.connect(database)) as connection:
                columns = {
                    row[1]
                    for row in connection.execute(
                        "pragma table_info(price_vector_pricing_decisions)"
                    ).fetchall()
                }

        self.assertIsNotNone(loaded)
        self.assertEqual(Decimal("5.00"), loaded.fair_market_value)
        self.assertEqual(
            Decimal("6.25"),
            loaded.recommended_listing_price,
        )
        self.assertEqual(Decimal("6.25"), loaded.final_listing_price)
        self.assertEqual("fixture:sold-001", loaded.market_evidence_reference)
        self.assertEqual(
            {
                "decision_id",
                "listing_reference",
                "fair_market_value",
                "fair_market_value_confidence",
                "recommended_listing_price",
                "final_listing_price",
                "pricing_reasoning",
                "market_evidence_reference",
                "created_at",
            },
            columns,
        )


if __name__ == "__main__":
    unittest.main()
