from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Callable

from .config import decimal_setting
from .models import (
    FairMarketValue,
    Listing,
    MarketEvidence,
    MarketPrice,
    PriceRecommendation,
    PricingDecision,
)


MONEY = Decimal("0.01")
DEFAULT_EXPORT_FLOOR = Decimal("0.99")

# Compatibility data for the existing Putnam OS exact-price revision tools.
# The canonical engine owns the values; legacy entry points only delegate here.
LEGACY_DEFAULT_LADDER = {
    "0.99": "0.99",
    "1.49": "0.99",
    "1.59": "1.09",
    "1.69": "1.19",
    "1.79": "1.29",
    "1.99": "1.49",
    "2.49": "1.99",
    "2.99": "2.49",
}

MoneyParser = Callable[[Any], Decimal]
MoneyFormatter = Callable[[Decimal], str]


def decimal_money(value: Any) -> Decimal:
    raw = str(value or "").replace("$", "").replace(",", "").strip()
    if not raw:
        return Decimal("0.00")
    try:
        return Decimal(raw)
    except InvalidOperation:
        return Decimal("0.00")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _calculate_weighted_market_value(
    market_report: dict[str, Any] | None,
) -> Decimal:
    """Marketplace Intelligence compatibility calculation for legacy reports."""

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
    return (weighted_value / total_weight).quantize(MONEY, rounding=ROUND_HALF_UP)


def fair_market_value_from_market_report(
    market_report: dict[str, Any] | None,
) -> FairMarketValue:
    """Normalize the existing weighted market report into an explicit FMV."""

    market_report = market_report or {}
    accepted_count = int(market_report.get("accepted_count") or 0)
    confidence = str(market_report.get("confidence") or "0")
    evidence_reference = str(
        market_report.get("snapshot_id")
        or market_report.get("evidence_reference")
        or market_report.get("cache_file")
        or ""
    )
    captured_at = str(
        market_report.get("captured_at")
        or market_report.get("as_of")
        or market_report.get("fetched_at")
        or ""
    )

    evidence: list[MarketEvidence] = []
    for evidence_type, key in (
        ("sold_median_summary", "median"),
        ("sold_last_three_average", "last3_avg"),
        ("sold_last_sale", "last_sale"),
    ):
        value = decimal_money(market_report.get(key))
        if value <= 0:
            continue
        evidence.append(
            MarketEvidence(
                source="legacy_market_report",
                evidence_type=evidence_type,
                value=value,
                marketplace=str(market_report.get("marketplace") or ""),
                condition=str(market_report.get("condition") or ""),
                captured_at=captured_at,
                source_reference=evidence_reference,
            )
        )

    value = _calculate_weighted_market_value(market_report)
    if value > 0:
        reasoning = (
            "Existing weighted market report: median 60%, last-three average "
            "30%, and last sale 10%, normalized over available inputs."
        )
        normalized_value: Decimal | None = value
    else:
        reasoning = "No FMV produced because fewer than three accepted comps or no usable values were available."
        normalized_value = None

    return FairMarketValue(
        value=normalized_value,
        confidence=confidence,
        reasoning=reasoning,
        evidence=tuple(evidence),
        evidence_reference=evidence_reference,
        calculated_at=captured_at or utc_now(),
        accepted_count=accepted_count,
    )


def calculate_market_value(market_report: dict[str, Any] | None) -> Decimal:
    """Backward-compatible numeric view of Marketplace Intelligence FMV."""

    fmv = fair_market_value_from_market_report(market_report)
    return fmv.value or Decimal("0.00")


def _market_evidence_type(market: MarketPrice) -> str:
    configured = str(market.metadata.get("evidence_type") or "").strip().lower()
    if configured:
        return configured
    source = f"{market.provider} {market.source}".lower()
    if "active" in source and "listing" in source:
        return "active_listing"
    if "tcgplayer_live" in source:
        return "active_listing"
    if "sold" in source or "sales_cache" in source:
        return "sold_comps_summary"
    if "inventory" in source:
        return "stored_market_price"
    if market.metadata.get("reference_only"):
        return "supporting_market_price"
    return "legacy_market_price"


def _excluded_raw_fmv_reason(
    market: MarketPrice,
    evidence_type: str,
) -> str:
    source = f"{market.provider} {market.source}".lower()
    if "pricecharting" in source:
        return "PriceCharting is excluded from raw-card FMV."
    if evidence_type == "active_listing" and (
        "tcgplayer" in source or str(market.metadata.get("marketplace") or "").lower() == "tcgplayer"
    ):
        return "TCGplayer active listings are competition evidence and are excluded from FMV."
    return ""


def fair_market_value_from_market_price(market: MarketPrice) -> FairMarketValue:
    """Compatibility adapter from the legacy provider result to explicit FMV."""

    metadata = market.metadata or {}
    evidence_type = _market_evidence_type(market)
    excluded_reason = _excluded_raw_fmv_reason(market, evidence_type)
    source_reference = str(
        metadata.get("snapshot_id")
        or metadata.get("evidence_reference")
        or metadata.get("cache_file")
        or metadata.get("source_url")
        or ""
    )
    captured_at = str(
        metadata.get("captured_at")
        or metadata.get("as_of")
        or metadata.get("fetched_at")
        or ""
    )
    has_value = bool(market.matched and market.market_price is not None)
    accepted_for_fmv = has_value and not excluded_reason

    evidence: tuple[MarketEvidence, ...] = ()
    if market.market_price is not None or market.source or market.provider:
        evidence = (
            MarketEvidence(
                source=market.source or market.provider,
                evidence_type=evidence_type,
                value=market.market_price,
                marketplace=str(metadata.get("marketplace") or ""),
                condition=str(metadata.get("condition") or ""),
                captured_at=captured_at,
                source_reference=source_reference,
                accepted_for_fmv=accepted_for_fmv,
                reason=excluded_reason or market.reason,
            ),
        )

    return FairMarketValue(
        value=market.market_price if accepted_for_fmv else None,
        confidence=market.confidence if accepted_for_fmv else "none",
        reasoning=excluded_reason or market.reason or "Legacy market-price value mapped to explicit FMV.",
        evidence=evidence,
        evidence_reference=source_reference,
        calculated_at=captured_at or utc_now(),
        accepted_count=int(metadata.get("accepted_comps") or (1 if accepted_for_fmv else 0)),
    )


def apply_pricing_strategy(
    market_value: Decimal,
    strategy: str = "market_match",
    export_floor: Decimal = DEFAULT_EXPORT_FLOOR,
) -> Decimal:
    """Apply the existing Putnam OS strategy without changing its behavior."""

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

    return max(recommended, export_floor).quantize(MONEY, rounding=ROUND_HALF_UP)


def build_pricing_decision_from_fmv(
    original_price: Any,
    fair_market_value: FairMarketValue,
    strategy: str = "market_match",
    review_threshold: int = 60,
    auto_apply_threshold: int = 80,
    export_floor: Decimal = DEFAULT_EXPORT_FLOOR,
) -> PricingDecision:
    """Apply Price Vector behavior to an explicit Marketplace Intelligence FMV."""

    original = max(decimal_money(original_price), export_floor).quantize(
        MONEY,
        rounding=ROUND_HALF_UP,
    )
    try:
        confidence = int(str(fair_market_value.confidence or "0"))
    except ValueError:
        confidence = 0
    market_value = fair_market_value.value or Decimal("0.00")

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
        accepted_count=fair_market_value.accepted_count,
        confidence=confidence,
        strategy=strategy,
        pricing_basis=pricing_basis,
        review_status=review_status,
        fair_market_value=market_value,
        fair_market_value_confidence=fair_market_value.confidence,
        fair_market_value_reasoning=fair_market_value.reasoning,
        recommended_listing_price=recommended,
        final_listing_price=recommended,
        market_evidence_reference=fair_market_value.evidence_reference,
        created_at=fair_market_value.calculated_at or utc_now(),
    )


def build_pricing_decision(
    original_price: Any,
    market_report: dict[str, Any] | None,
    strategy: str = "market_match",
    review_threshold: int = 60,
    auto_apply_threshold: int = 80,
    export_floor: Decimal = DEFAULT_EXPORT_FLOOR,
) -> PricingDecision:
    """Adapt the legacy market-report interface into the explicit FMV path."""

    return build_pricing_decision_from_fmv(
        original_price=original_price,
        fair_market_value=fair_market_value_from_market_report(market_report),
        strategy=strategy,
        review_threshold=review_threshold,
        auto_apply_threshold=auto_apply_threshold,
        export_floor=export_floor,
    )


def optimized_export_price(
    market_price: Decimal,
    export_floor: Decimal = DEFAULT_EXPORT_FLOOR,
) -> Decimal:
    """Apply the existing Listing Optimizer tier ladder."""

    price = decimal_money(market_price)
    if price <= Decimal("1.50"):
        final_price = Decimal("0.99")
    elif price <= Decimal("2.99"):
        final_price = Decimal("1.49")
    elif price <= Decimal("4.99"):
        final_price = Decimal("2.99")
    else:
        final_price = price
    return max(final_price, export_floor).quantize(MONEY, rounding=ROUND_HALF_UP)


def normalize_price_ladder(
    ladder: dict[str, str],
    *,
    parse_money: MoneyParser,
    format_money: MoneyFormatter,
) -> dict[str, str]:
    return {
        format_money(parse_money(source)): format_money(parse_money(target))
        for source, target in ladder.items()
    }


def apply_exact_price_ladder(
    records: list[dict[str, Any]],
    ladder: dict[str, str],
    *,
    parse_money: MoneyParser,
    format_money: MoneyFormatter,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Apply the legacy exact-price ladder for compatibility callers."""

    processed: list[dict[str, Any]] = []
    invalid: list[dict[str, Any]] = []
    for record in records:
        try:
            old_price = parse_money(record["old_price_raw"])
            key = format_money(old_price)
        except Exception as exc:
            invalid_record = dict(record)
            invalid_record.update(
                {
                    "status": "INVALID_PRICE",
                    "old_price": "",
                    "new_price": "",
                    "change": "",
                    "reason": str(exc),
                }
            )
            invalid.append(invalid_record)
            continue

        if key in ladder:
            new_price = parse_money(ladder[key])
            status = "CHANGE" if new_price != old_price else "UNCHANGED"
            reason = (
                f"ladder {key} -> {format_money(new_price)}"
                if status == "CHANGE"
                else "ladder leaves price unchanged"
            )
        else:
            new_price = old_price
            status = "UNCHANGED"
            reason = "price not in ladder"

        processed_record = dict(record)
        processed_record.update(
            {
                "status": status,
                "old_price": format_money(old_price),
                "new_price": format_money(new_price),
                "change": format_money(new_price - old_price),
                "reason": reason,
            }
        )
        processed.append(processed_record)
    return processed, invalid


def evaluate_new_listing_price(
    source_price: Any,
    ladder: dict[str, str],
    *,
    floor: Decimal,
    high_review_threshold: Decimal,
    parse_money: MoneyParser,
    format_money: MoneyFormatter,
) -> dict[str, Any]:
    """Apply the existing legacy new-listing guardrails."""

    old_price = parse_money(source_price)
    new_price = old_price
    status = "UNCHANGED"
    reason = "CardUploader/source price accepted"
    key = format_money(old_price)

    if key in ladder and parse_money(ladder[key]) != old_price:
        new_price = parse_money(ladder[key])
        status = "CHANGE"
        reason = f"Putnam ladder {key} -> {format_money(new_price)}"
    if new_price < floor:
        new_price = floor
        status = "CHANGE"
        reason = f"raised to minimum floor ${format_money(floor)}"

    high_review = old_price >= high_review_threshold
    if high_review:
        reason += f"; review high-value listing >= ${format_money(high_review_threshold)}"
        if status == "UNCHANGED":
            status = "REVIEW"

    return {
        "old_price": old_price,
        "new_price": new_price,
        "status": status,
        "reason": reason,
        "high_review": high_review,
    }


class PricingEngine:
    """Configurable pricing calculator reusable by Putnam OS."""

    def __init__(self, pricing_profile: dict):
        self.profile = pricing_profile

    def recommend(self, listing: Listing, market: MarketPrice) -> PriceRecommendation:
        """Backward-compatible adapter from legacy MarketPrice to explicit FMV."""

        return self.recommend_from_fmv(
            listing,
            fair_market_value_from_market_price(market),
        )

    def recommend_from_fmv(
        self,
        listing: Listing,
        fair_market_value: FairMarketValue,
    ) -> PriceRecommendation:
        """Apply pricing rules to FMV without inspecting raw market evidence."""

        current = listing.current_price
        if not fair_market_value.available:
            return PriceRecommendation(
                recommended_price=current,
                difference=Decimal("0.00"),
                percent_change=Decimal("0.00"),
                pricing_reason="No market price available.",
                review_required=True,
                review_reason="Unmatched listing.",
                fair_market_value=fair_market_value.value,
                fair_market_value_confidence=fair_market_value.confidence,
                fair_market_value_reasoning=fair_market_value.reasoning,
                recommended_listing_price=current,
                final_listing_price=current,
                market_evidence=fair_market_value.evidence,
                market_evidence_reference=fair_market_value.evidence_reference,
            )

        fmv_value = fair_market_value.value
        shipping_adjusted_market = self.apply_shipping_assumption(fmv_value)
        target = self.apply_market_strategy(current, shipping_adjusted_market)
        target = self.apply_change_limits(current, target)
        target = self.apply_minimum_price(target)
        target = self.apply_rounding(target)
        difference = (target - current).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        percent_change = Decimal("0.00")
        if current > 0:
            percent_change = ((difference / current) * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        ignore = decimal_setting(self.profile, "ignore_changes_under", "0.00")
        if abs(difference) < ignore:
            target = current
            difference = Decimal("0.00")
            percent_change = Decimal("0.00")
            reason = f"Change below ignore threshold ${ignore}."
        else:
            reason = (
                f"FMV ${fmv_value}; "
                f"{self.shipping_reason(fmv_value, shipping_adjusted_market)}; "
                f"configurable strategy target ${target}."
            )
        review_required, review_reason = self.review_check(current, target, fmv_value)
        return PriceRecommendation(
            recommended_price=target,
            difference=difference,
            percent_change=percent_change,
            pricing_reason=reason,
            review_required=review_required,
            review_reason=review_reason,
            fair_market_value=fmv_value,
            fair_market_value_confidence=fair_market_value.confidence,
            fair_market_value_reasoning=fair_market_value.reasoning,
            recommended_listing_price=target,
            final_listing_price=target,
            market_evidence=fair_market_value.evidence,
            market_evidence_reference=fair_market_value.evidence_reference,
        )

    def apply_market_strategy(self, current: Decimal, market_price: Decimal) -> Decimal:
        mode = str(self.profile.get("market_strategy", "match_market")).lower()
        if mode == "undercut_market":
            amount = decimal_setting(self.profile, "undercut_amount", "0.00")
            return market_price - amount
        if mode == "hold_if_within_band":
            band = decimal_setting(self.profile, "hold_band_percent", "5.00")
            if current > 0:
                delta = abs((market_price - current) / current) * Decimal("100")
                if delta <= band:
                    return current
        return market_price

    def apply_shipping_assumption(self, market_price: Decimal) -> Decimal:
        assumption = str(self.profile.get("shipping_assumption", "buyer_pays_shipping")).lower()
        flat_shipping_cost = decimal_setting(self.profile, "flat_shipping_cost", "0.00")
        # Seller-paid shipping means the listing price may need to absorb the configured shipping cost.
        if assumption == "seller_pays_shipping" and flat_shipping_cost > 0:
            return market_price + flat_shipping_cost
        return market_price

    def shipping_reason(self, market_price: Decimal, adjusted_market: Decimal) -> str:
        assumption = str(self.profile.get("shipping_assumption", "buyer_pays_shipping")).lower()
        flat_shipping_cost = decimal_setting(self.profile, "flat_shipping_cost", "0.00")
        labels = {
            "buyer_pays_shipping": "buyer pays shipping",
            "seller_pays_shipping": "seller pays shipping",
            "mixed_shipping": "mixed shipping",
        }
        label = labels.get(assumption, assumption.replace("_", " "))
        if adjusted_market != market_price:
            return f"{label}, added flat shipping cost ${flat_shipping_cost}"
        if assumption == "mixed_shipping":
            return "mixed shipping, no automatic shipping adjustment"
        return f"{label}, no shipping adjustment"

    def apply_minimum_price(self, value: Decimal) -> Decimal:
        minimum = decimal_setting(self.profile, "minimum_price", "0.01")
        return max(value, minimum)

    def apply_change_limits(self, current: Decimal, target: Decimal) -> Decimal:
        max_increase_pct = decimal_setting(self.profile, "maximum_increase_percent", "9999")
        max_decrease_pct = decimal_setting(self.profile, "maximum_decrease_percent", "9999")
        max_increase_amt = decimal_setting(self.profile, "maximum_increase_amount", "999999")
        max_decrease_amt = decimal_setting(self.profile, "maximum_decrease_amount", "999999")
        increase_cap = min(current + max_increase_amt, current * (Decimal("1") + (max_increase_pct / Decimal("100"))))
        decrease_floor = max(current - max_decrease_amt, current * (Decimal("1") - (max_decrease_pct / Decimal("100"))))
        if target > current:
            return min(target, increase_cap)
        if target < current:
            return max(target, decrease_floor)
        return target

    def apply_rounding(self, value: Decimal) -> Decimal:
        mode = str(self.profile.get("rounding_rule", "nearest_cent")).lower()
        if mode == "nearest_99":
            whole = int(value)
            candidate = Decimal(whole) + Decimal("0.99")
            if candidate < value:
                candidate += Decimal("1.00")
            return candidate.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if mode == "down_to_99":
            whole = int(value)
            candidate = Decimal(whole) + Decimal("0.99")
            if candidate > value and whole > 0:
                candidate -= Decimal("1.00")
            return self.apply_minimum_price(candidate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def review_check(self, current: Decimal, recommended: Decimal, market: Decimal) -> tuple[bool, str]:
        high_price = decimal_setting(self.profile, "review_price_over", "999999")
        review_delta = decimal_setting(self.profile, "review_change_percent_over", "999999")
        if recommended >= high_price:
            return True, f"Recommended price is above review threshold ${high_price}."
        if current > 0:
            delta = abs((recommended - current) / current) * Decimal("100")
            if delta >= review_delta:
                return True, f"Change exceeds review threshold {review_delta}%."
        if market <= 0:
            return True, "Invalid market price."
        return False, ""
