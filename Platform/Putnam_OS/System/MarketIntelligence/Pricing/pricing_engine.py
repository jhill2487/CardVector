from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

from .pricing_models import PricingDecision


MONEY = Decimal("0.01")
DEFAULT_EXPORT_FLOOR = Decimal("0.99")


def decimal_money(value: Any) -> Decimal:
    raw = str(value or "").replace("$", "").replace(",", "").strip()
    if not raw:
        return Decimal("0.00")
    try:
        return Decimal(raw)
    except InvalidOperation:
        return Decimal("0.00")


def calculate_market_value(market_report: dict[str, Any] | None) -> Decimal:
    market_report = market_report or {}
    accepted_count = int(market_report.get("accepted_count") or 0)
    if accepted_count < 3:
        return Decimal("0.00")

    median = decimal_money(market_report.get("median"))
    last3_avg = decimal_money(market_report.get("last3_avg"))
    last_sale = decimal_money(market_report.get("last_sale"))

    weighted_parts: list[tuple[Decimal, Decimal]] = []
    if median > 0:
        weighted_parts.append((median, Decimal("0.60")))
    if last3_avg > 0:
        weighted_parts.append((last3_avg, Decimal("0.30")))
    if last_sale > 0:
        weighted_parts.append((last_sale, Decimal("0.10")))

    if not weighted_parts:
        return Decimal("0.00")

    total_weight = sum((weight for _value, weight in weighted_parts), Decimal("0.00"))
    weighted_value = sum((value * weight for value, weight in weighted_parts), Decimal("0.00"))

    return (weighted_value / total_weight).quantize(
        MONEY,
        rounding=ROUND_HALF_UP,
    )


def apply_pricing_strategy(
    market_value: Decimal,
    strategy: str = "market_match",
    export_floor: Decimal = DEFAULT_EXPORT_FLOOR,
) -> Decimal:
    value = max(decimal_money(market_value), export_floor)
    normalized = str(strategy or "market_match").strip().lower()

    if normalized == "market_match":
        recommended = value
    elif normalized == "fast_sell":
        recommended = value * Decimal("0.95")
    elif normalized == "profit":
        recommended = value * Decimal("1.05")
    else:
        raise ValueError(f"Unknown pricing strategy: {strategy}")

    return max(recommended, export_floor).quantize(
        MONEY,
        rounding=ROUND_HALF_UP,
    )


def build_pricing_decision(
    original_price: Any,
    market_report: dict[str, Any] | None,
    strategy: str = "market_match",
    review_threshold: int = 60,
    auto_apply_threshold: int = 80,
    export_floor: Decimal = DEFAULT_EXPORT_FLOOR,
) -> PricingDecision:
    market_report = market_report or {}
    original = max(decimal_money(original_price), export_floor).quantize(
        MONEY,
        rounding=ROUND_HALF_UP,
    )
    accepted_count = int(market_report.get("accepted_count") or 0)
    confidence = int(market_report.get("confidence") or 0)
    market_value = calculate_market_value(market_report)

    if market_value <= 0:
        recommended = original
        pricing_basis = "carduploader_price_retained"
        review_status = "NO_MARKET_DATA"
    elif confidence < int(review_threshold):
        recommended = original
        pricing_basis = "low_confidence_source_retained"
        review_status = "MANUAL_REVIEW_REQUIRED"
    else:
        recommended = apply_pricing_strategy(
            market_value,
            strategy,
            export_floor=export_floor,
        )
        pricing_basis = "weighted_market_value"
        review_status = (
            "AUTO_APPLIED"
            if confidence >= int(auto_apply_threshold)
            else "APPLIED_REVIEW_RECOMMENDED"
        )

    return PricingDecision(
        original_price=original,
        market_value=market_value,
        recommended_price=recommended,
        accepted_count=accepted_count,
        confidence=confidence,
        strategy=strategy,
        pricing_basis=pricing_basis,
        review_status=review_status,
    )
