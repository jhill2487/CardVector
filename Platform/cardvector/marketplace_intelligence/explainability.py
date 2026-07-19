"""Deterministic explanation policy for Marketplace Intelligence results."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from enum import Enum
from typing import Any

from .models import (
    Decision,
    FairMarketValue,
    Listing,
    ListingIdentity,
    MarketPrice,
    PriceRecommendation,
    PricingExplanation,
    ReviewThresholds,
)


MONEY = Decimal("0.01")


class PricingReasonCode(str, Enum):
    NO_MARKET_DATA = "NO_MARKET_DATA"
    LOW_DATA = "LOW_DATA"
    HIGH_VARIANCE = "HIGH_VARIANCE"
    NO_RECENT_SALES = "NO_RECENT_SALES"
    STALE_MARKET = "STALE_MARKET"
    PROMO_VARIANT = "PROMO_VARIANT"
    VARIANT_UNVERIFIED = "VARIANT_UNVERIFIED"
    REFERENCE_ONLY = "REFERENCE_ONLY"
    HIGH_CONFIDENCE = "HIGH_CONFIDENCE"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    PRICE_SPIKE = "PRICE_SPIKE"
    PRICE_COLLAPSE = "PRICE_COLLAPSE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    MARKET_ALIGNED = "MARKET_ALIGNED"


def confidence_score(value: Any) -> int:
    raw = str(value or "").strip().lower()
    try:
        return max(0, min(100, int(Decimal(raw))))
    except (InvalidOperation, ValueError):
        return {
            "high": 85,
            "medium": 70,
            "low": 50,
            "reference": 40,
            "none": 0,
        }.get(raw, 0)


def _money(value: Any) -> Decimal | None:
    raw = str(value or "").replace("$", "").replace(",", "").strip()
    if not raw:
        return None
    try:
        return Decimal(raw).quantize(MONEY, rounding=ROUND_HALF_UP)
    except InvalidOperation:
        return None


def _integer(value: Any, default: int = 0) -> int:
    try:
        return int(str(value or default))
    except (TypeError, ValueError):
        return default


def _captured_at(market: MarketPrice, fmv: FairMarketValue) -> str:
    metadata = market.metadata or {}
    captured = str(
        metadata.get("captured_at")
        or metadata.get("sold_at")
        or metadata.get("as_of")
        or metadata.get("fetched_at")
        or ""
    )
    if captured:
        return captured
    for item in fmv.evidence:
        if item.captured_at:
            return item.captured_at
    return ""


def _age_days(value: str, now: datetime | None) -> int | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        captured = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if captured.tzinfo is None:
        captured = captured.replace(tzinfo=timezone.utc)
    reference = now or datetime.now(timezone.utc)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)
    return max(0, (reference - captured.astimezone(timezone.utc)).days)


def _primary_market(market: MarketPrice, fmv: FairMarketValue) -> str:
    metadata = market.metadata or {}
    configured = str(metadata.get("marketplace") or "").strip()
    if configured:
        return configured
    for item in fmv.evidence:
        if item.marketplace:
            return item.marketplace
    return market.provider or market.source or "unknown"


def _has_promo_identity(listing: Listing, identity: ListingIdentity) -> bool:
    identity_text = " ".join(
        [
            listing.title,
            listing.variant,
            listing.set_name,
            listing.card_number,
            str(identity.details.get("parsed_set") or ""),
            str(identity.details.get("parsed_card_number") or ""),
        ]
    ).lower()
    return "promo" in identity_text


def _variant_unverified(listing: Listing, market: MarketPrice) -> bool:
    expected = " ".join([listing.variant, listing.finish]).strip().lower()
    if not expected:
        return False
    metadata = market.metadata or {}
    observed = " ".join(
        [
            str(metadata.get("variant") or ""),
            str(metadata.get("finish") or ""),
        ]
    ).strip().lower()
    return not observed or expected != observed


def _percent_change(current: Decimal, recommended: Decimal) -> Decimal:
    if current <= 0:
        return Decimal("0.00")
    return (
        ((recommended - current) / current) * Decimal("100")
    ).quantize(MONEY, rounding=ROUND_HALF_UP)


def build_pricing_explanation(
    *,
    listing: Listing,
    identity: ListingIdentity,
    market: MarketPrice,
    fair_market_value: FairMarketValue,
    pricing: PriceRecommendation,
    decision: Decision,
    thresholds: ReviewThresholds,
    now: datetime | None = None,
) -> PricingExplanation:
    """Build additive evidence without changing recommendation calculations."""

    metadata = market.metadata or {}
    comparable_count = _integer(
        metadata.get("accepted_comps"),
        fair_market_value.accepted_count,
    )
    median_sold = _money(metadata.get("median")) or fair_market_value.value
    average_sold = _money(
        metadata.get("average")
        or metadata.get("average_sold")
        or metadata.get("last3_avg")
    )
    price_range_low = _money(metadata.get("price_low") or metadata.get("minimum"))
    price_range_high = _money(metadata.get("price_high") or metadata.get("maximum"))
    outliers_removed = _integer(metadata.get("outliers_removed"))
    score = confidence_score(
        fair_market_value.confidence or market.confidence
    )
    age_days = _age_days(_captured_at(market, fair_market_value), now)

    trend = str(
        metadata.get("market_trend")
        or metadata.get("trend")
        or "unknown"
    ).strip().lower()
    if trend not in {"rising", "falling", "stable", "unknown"}:
        trend = "unknown"

    codes: list[str] = list(pricing.reason_codes)
    if not fair_market_value.available:
        codes.append(PricingReasonCode.NO_MARKET_DATA.value)
    if comparable_count < thresholds.insufficient_data_comps:
        codes.append(PricingReasonCode.LOW_DATA.value)
    if comparable_count > 0 and age_days is None:
        codes.append(PricingReasonCode.NO_RECENT_SALES.value)
    if age_days is not None and age_days > thresholds.stale_market_days:
        codes.append(PricingReasonCode.STALE_MARKET.value)
    if _has_promo_identity(listing, identity):
        codes.append(PricingReasonCode.PROMO_VARIANT.value)
    if _variant_unverified(listing, market):
        codes.append(PricingReasonCode.VARIANT_UNVERIFIED.value)
    if metadata.get("reference_only"):
        codes.append(PricingReasonCode.REFERENCE_ONLY.value)

    if (
        median_sold
        and price_range_low is not None
        and price_range_high is not None
        and median_sold > 0
    ):
        spread = ((price_range_high - price_range_low) / median_sold) * Decimal("100")
        if spread >= thresholds.high_variance_percent:
            codes.append(PricingReasonCode.HIGH_VARIANCE.value)

    if score >= thresholds.auto_approve_confidence:
        codes.append(PricingReasonCode.HIGH_CONFIDENCE.value)
    elif score < thresholds.warning_below_confidence:
        codes.append(PricingReasonCode.LOW_CONFIDENCE.value)

    recommended = pricing.final_listing_price or pricing.recommended_listing_price
    recommended = recommended or pricing.recommended_price
    price_delta_percent = _percent_change(listing.current_price, recommended)
    if price_delta_percent >= thresholds.price_spike_percent:
        codes.append(PricingReasonCode.PRICE_SPIKE.value)
    if price_delta_percent <= -thresholds.price_collapse_percent:
        codes.append(PricingReasonCode.PRICE_COLLAPSE.value)

    inherited_review = bool(decision.review_required or pricing.review_required)
    advisory_review = any(
        code
        in {
            PricingReasonCode.NO_MARKET_DATA.value,
            PricingReasonCode.LOW_DATA.value,
            PricingReasonCode.HIGH_VARIANCE.value,
            PricingReasonCode.NO_RECENT_SALES.value,
            PricingReasonCode.STALE_MARKET.value,
            PricingReasonCode.VARIANT_UNVERIFIED.value,
            PricingReasonCode.REFERENCE_ONLY.value,
            PricingReasonCode.PRICE_SPIKE.value,
            PricingReasonCode.PRICE_COLLAPSE.value,
        }
        for code in codes
    )
    review_required = inherited_review or advisory_review
    if review_required:
        codes.append(PricingReasonCode.REVIEW_REQUIRED.value)

    if PricingReasonCode.NO_MARKET_DATA.value in codes:
        review_decision = "INSUFFICIENT_DATA"
        review_priority = "high"
    elif any(
        code
        in {
            PricingReasonCode.HIGH_VARIANCE.value,
            PricingReasonCode.STALE_MARKET.value,
            PricingReasonCode.VARIANT_UNVERIFIED.value,
            PricingReasonCode.REFERENCE_ONLY.value,
        }
        for code in codes
    ) or score < thresholds.manual_review_below_confidence:
        review_decision = "MANUAL_REVIEW"
        review_priority = "high"
    elif any(
        code
        in {
            PricingReasonCode.PRICE_SPIKE.value,
            PricingReasonCode.PRICE_COLLAPSE.value,
            PricingReasonCode.LOW_CONFIDENCE.value,
            PricingReasonCode.LOW_DATA.value,
            PricingReasonCode.NO_RECENT_SALES.value,
        }
        for code in codes
    ):
        review_decision = "PRICING_WARNING"
        review_priority = "medium"
    elif score >= thresholds.auto_approve_confidence and not inherited_review:
        review_decision = "AUTO_APPROVE"
        review_priority = "low"
    else:
        review_decision = "REVIEW_RECOMMENDED"
        review_priority = "medium"

    if not codes:
        codes.append(PricingReasonCode.MARKET_ALIGNED.value)

    unique_codes = tuple(dict.fromkeys(codes))
    primary_market = _primary_market(market, fair_market_value)
    summary = (
        f"Recommended ${recommended}; confidence {fair_market_value.confidence or market.confidence}; "
        f"primary market {primary_market}; {comparable_count} comparable(s); "
        f"{review_decision}; reason codes {', '.join(unique_codes)}."
    )
    return PricingExplanation(
        recommended_price=recommended,
        confidence=fair_market_value.confidence or market.confidence or "none",
        primary_market=primary_market,
        comparable_count=comparable_count,
        median_sold=median_sold,
        average_sold=average_sold,
        market_trend=trend,
        price_range_low=price_range_low,
        price_range_high=price_range_high,
        outliers_removed=outliers_removed,
        review_required=review_required,
        review_decision=review_decision,
        review_priority=review_priority,
        reason_codes=unique_codes,
        summary=summary,
        evidence_reference=fair_market_value.evidence_reference,
    )


__all__ = [
    "PricingReasonCode",
    "build_pricing_explanation",
    "confidence_score",
]
