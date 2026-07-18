from __future__ import annotations

from decimal import Decimal
from typing import Any

from Platform.cardvector.marketplace_intelligence import (
    pricing as canonical_pricing,
)

from .pricing_models import PricingDecision


DEFAULT_EXPORT_FLOOR = canonical_pricing.DEFAULT_EXPORT_FLOOR


def decimal_money(value: Any) -> Decimal:
    return canonical_pricing.decimal_money(value)


def calculate_market_value(market_report: dict[str, Any] | None) -> Decimal:
    return canonical_pricing.calculate_market_value(market_report)


def apply_pricing_strategy(
    market_value: Decimal,
    strategy: str = "market_match",
    export_floor: Decimal = DEFAULT_EXPORT_FLOOR,
) -> Decimal:
    return canonical_pricing.apply_pricing_strategy(
        market_value,
        strategy,
        export_floor=export_floor,
    )


def build_pricing_decision(
    original_price: Any,
    market_report: dict[str, Any] | None,
    strategy: str = "market_match",
    review_threshold: int = 60,
    auto_apply_threshold: int = 80,
    export_floor: Decimal = DEFAULT_EXPORT_FLOOR,
) -> PricingDecision:
    return canonical_pricing.build_pricing_decision(
        original_price=original_price,
        market_report=market_report,
        strategy=strategy,
        review_threshold=review_threshold,
        auto_apply_threshold=auto_apply_threshold,
        export_floor=export_floor,
    )
