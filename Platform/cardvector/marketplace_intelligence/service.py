"""Dependency-injectable Marketplace Intelligence pricing service."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from . import pricing
from .models import ExistingListingRequest, FairMarketValue, Listing, MarketPrice


class PricingService:
    """Stable service facade; all calculations delegate to the proven engine."""

    def decimal_money(self, value: Any) -> Decimal:
        return pricing.decimal_money(value)

    def fair_market_value_from_market_report(
        self,
        market_report: dict[str, Any] | None,
    ):
        return pricing.fair_market_value_from_market_report(market_report)

    def fair_market_value_from_market_price(self, market: MarketPrice):
        return pricing.fair_market_value_from_market_price(market)

    def calculate_market_value(
        self,
        market_report: dict[str, Any] | None,
    ) -> Decimal:
        return pricing.calculate_market_value(market_report)

    def apply_pricing_strategy(
        self,
        market_value: Decimal,
        strategy: str = "market_match",
        export_floor: Decimal = pricing.DEFAULT_EXPORT_FLOOR,
    ) -> Decimal:
        return pricing.apply_pricing_strategy(
            market_value,
            strategy,
            export_floor=export_floor,
        )

    def build_pricing_decision_from_fmv(
        self,
        original_price: Any,
        fair_market_value: FairMarketValue,
        strategy: str = "market_match",
        review_threshold: int = 60,
        auto_apply_threshold: int = 80,
        export_floor: Decimal = pricing.DEFAULT_EXPORT_FLOOR,
    ):
        return pricing.build_pricing_decision_from_fmv(
            original_price=original_price,
            fair_market_value=fair_market_value,
            strategy=strategy,
            review_threshold=review_threshold,
            auto_apply_threshold=auto_apply_threshold,
            export_floor=export_floor,
        )

    def build_pricing_decision(
        self,
        original_price: Any,
        market_report: dict[str, Any] | None,
        strategy: str = "market_match",
        review_threshold: int = 60,
        auto_apply_threshold: int = 80,
        export_floor: Decimal = pricing.DEFAULT_EXPORT_FLOOR,
    ):
        return pricing.build_pricing_decision(
            original_price=original_price,
            market_report=market_report,
            strategy=strategy,
            review_threshold=review_threshold,
            auto_apply_threshold=auto_apply_threshold,
            export_floor=export_floor,
        )

    def recommend_from_fmv(
        self,
        listing: Listing,
        fair_market_value: FairMarketValue,
        pricing_profile: dict[str, Any],
    ):
        return pricing.PricingEngine(pricing_profile).recommend_from_fmv(
            listing,
            fair_market_value,
        )

    def optimized_export_price(
        self,
        market_price: Decimal,
        export_floor: Decimal = pricing.DEFAULT_EXPORT_FLOOR,
    ) -> Decimal:
        return pricing.optimized_export_price(
            market_price,
            export_floor=export_floor,
        )

    def normalize_price_ladder(self, ladder, *, parse_money, format_money):
        return pricing.normalize_price_ladder(
            ladder,
            parse_money=parse_money,
            format_money=format_money,
        )

    def apply_exact_price_ladder(
        self,
        records,
        ladder,
        *,
        parse_money,
        format_money,
    ):
        return pricing.apply_exact_price_ladder(
            records,
            ladder,
            parse_money=parse_money,
            format_money=format_money,
        )

    def evaluate_new_listing_price(
        self,
        source_price,
        ladder,
        *,
        floor,
        high_review_threshold,
        parse_money,
        format_money,
    ):
        return pricing.evaluate_new_listing_price(
            source_price,
            ladder,
            floor=floor,
            high_review_threshold=high_review_threshold,
            parse_money=parse_money,
            format_money=format_money,
        )

    def evaluate_existing_listing(
        self,
        request: ExistingListingRequest,
        *,
        engine=None,
    ):
        """Evaluate an existing listing without performing marketplace writes."""

        if engine is None:
            from Platform.Marketplace_Intelligence.marketplace_intelligence.engine import (
                MarketplaceIntelligenceEngine,
            )

            engine = MarketplaceIntelligenceEngine()
        return engine.evaluate_existing_listing(request)


PRICING_SERVICE = PricingService()

__all__ = ["PRICING_SERVICE", "PricingService"]
