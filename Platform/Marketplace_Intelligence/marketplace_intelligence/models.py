from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


@dataclass
class Listing:
    row_number: int
    raw: dict[str, str]
    item_id: str
    title: str
    current_price: Decimal
    source_type: str = "ebay_active_listings"
    source_file: str = ""
    sku: str = ""
    quantity: str = ""
    condition: str = ""
    category: str = ""
    shipping: str = ""
    set_name: str = ""
    card_number: str = ""
    rarity: str = ""
    variant: str = ""
    finish: str = ""
    tcg: str = ""
    tcgplayer_product_id: str = ""
    tcgplayer_sku: str = ""
    catalog_sku: str = ""
    status: str = ""
    warnings: list[str] = field(default_factory=list)

    @property
    def raw_row(self) -> dict[str, str]:
        return self.raw


@dataclass
class ListingIdentity:
    lookup_key: str
    match_method: str
    confidence: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class MarketPrice:
    matched: bool
    market_price: Decimal | None = None
    provider: str = ""
    source: str = ""
    confidence: str = "none"
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MarketEvidence:
    """One normalized market observation owned by Marketplace Intelligence."""

    source: str
    evidence_type: str
    value: Decimal | None
    marketplace: str = ""
    condition: str = ""
    captured_at: str = ""
    source_reference: str = ""
    accepted_for_fmv: bool = True
    reason: str = ""


@dataclass(frozen=True)
class FairMarketValue:
    """Marketplace Intelligence output consumed by Price Vector."""

    value: Decimal | None
    confidence: str = "none"
    reasoning: str = ""
    evidence: tuple[MarketEvidence, ...] = ()
    evidence_reference: str = ""
    calculated_at: str = ""
    currency: str = "USD"
    card_type: str = "raw"
    accepted_count: int = 0

    @property
    def available(self) -> bool:
        return self.value is not None and self.value > 0


@dataclass(frozen=True)
class ReviewThresholds:
    """Configurable advisory thresholds that do not alter Price Vector math."""

    auto_approve_confidence: int = 80
    manual_review_below_confidence: int = 60
    warning_below_confidence: int = 70
    insufficient_data_comps: int = 3
    stale_market_days: int = 30
    price_spike_percent: Decimal = Decimal("40.00")
    price_collapse_percent: Decimal = Decimal("40.00")
    high_variance_percent: Decimal = Decimal("35.00")
    review_price_over: Decimal = Decimal("100.00")

    @classmethod
    def from_profile(cls, profile: dict[str, Any] | None) -> "ReviewThresholds":
        values = profile or {}

        def integer(key: str, default: int) -> int:
            try:
                return int(str(values.get(key, default)))
            except (TypeError, ValueError):
                return default

        def decimal(key: str, default: str) -> Decimal:
            try:
                return Decimal(str(values.get(key, default)))
            except (InvalidOperation, TypeError, ValueError):
                return Decimal(default)

        return cls(
            auto_approve_confidence=integer("auto_approve_confidence", 80),
            manual_review_below_confidence=integer(
                "manual_review_below_confidence",
                60,
            ),
            warning_below_confidence=integer("warning_below_confidence", 70),
            insufficient_data_comps=integer("insufficient_data_comps", 3),
            stale_market_days=integer("stale_market_days", 30),
            price_spike_percent=decimal("price_spike_percent", "40.00"),
            price_collapse_percent=decimal("price_collapse_percent", "40.00"),
            high_variance_percent=decimal("high_variance_percent", "35.00"),
            review_price_over=decimal("review_price_over", "100.00"),
        )


@dataclass(frozen=True)
class PricingExplanation:
    """Human- and machine-readable evidence for one recommendation."""

    recommended_price: Decimal
    confidence: str
    primary_market: str
    comparable_count: int
    median_sold: Decimal | None
    average_sold: Decimal | None
    market_trend: str
    price_range_low: Decimal | None
    price_range_high: Decimal | None
    outliers_removed: int
    review_required: bool
    review_decision: str
    review_priority: str
    reason_codes: tuple[str, ...]
    summary: str
    evidence_reference: str = ""

    def to_dict(self) -> dict[str, Any]:
        def money(value: Decimal | None) -> str:
            return "" if value is None else str(value)

        return {
            "recommended_price": money(self.recommended_price),
            "confidence": self.confidence,
            "primary_market": self.primary_market,
            "comparable_count": self.comparable_count,
            "median_sold": money(self.median_sold),
            "average_sold": money(self.average_sold),
            "market_trend": self.market_trend,
            "price_range_low": money(self.price_range_low),
            "price_range_high": money(self.price_range_high),
            "outliers_removed": self.outliers_removed,
            "review_required": self.review_required,
            "review_decision": self.review_decision,
            "review_priority": self.review_priority,
            "reason_codes": list(self.reason_codes),
            "summary": self.summary,
            "evidence_reference": self.evidence_reference,
        }


@dataclass(frozen=True)
class ExistingListingRequest:
    """Read-only existing-listing evaluation input."""

    marketplace: str
    listing_title: str
    current_price: Decimal
    quantity: str = ""
    sku: str = ""
    condition: str = ""
    listing_id: str = ""
    set_name: str = ""
    card_number: str = ""
    variant: str = ""
    finish: str = ""


@dataclass(frozen=True)
class ExistingListingEvaluation:
    """Read-only readiness result; it never mutates a marketplace listing."""

    marketplace: str
    listing_reference: str
    matched_card: str
    match_confidence: str
    recommended_price: Decimal
    price_delta: Decimal
    review_priority: str
    review_decision: str
    reason_codes: tuple[str, ...]
    explanation: PricingExplanation

    def to_dict(self) -> dict[str, Any]:
        return {
            "marketplace": self.marketplace,
            "listing_reference": self.listing_reference,
            "matched_card": self.matched_card,
            "match_confidence": self.match_confidence,
            "recommended_price": str(self.recommended_price),
            "price_delta": str(self.price_delta),
            "review_priority": self.review_priority,
            "review_decision": self.review_decision,
            "reason_codes": list(self.reason_codes),
            "explanation": self.explanation.to_dict(),
        }


@dataclass
class PriceRecommendation:
    recommended_price: Decimal
    difference: Decimal
    percent_change: Decimal
    pricing_reason: str
    review_required: bool = False
    review_reason: str = ""
    fair_market_value: Decimal | None = None
    fair_market_value_confidence: str = "none"
    fair_market_value_reasoning: str = ""
    recommended_listing_price: Decimal | None = None
    final_listing_price: Decimal | None = None
    market_evidence: tuple[MarketEvidence, ...] = ()
    market_evidence_reference: str = ""
    reason_codes: tuple[str, ...] = ()
    explanation: PricingExplanation | None = None

    def __post_init__(self) -> None:
        # recommended_price remains the compatibility name for existing callers.
        recommendation = self.recommended_listing_price
        if recommendation is None:
            recommendation = self.recommended_price
        self.recommended_listing_price = recommendation
        self.recommended_price = recommendation
        if self.final_listing_price is None:
            self.final_listing_price = recommendation


@dataclass(frozen=True)
class PricingDecision:
    """Backward-compatible Putnam OS market-report pricing result."""

    original_price: Decimal
    market_value: Decimal
    recommended_price: Decimal
    accepted_count: int
    confidence: int
    strategy: str
    pricing_basis: str
    review_status: str
    fair_market_value: Decimal | None = None
    fair_market_value_confidence: str = ""
    fair_market_value_reasoning: str = ""
    recommended_listing_price: Decimal | None = None
    final_listing_price: Decimal | None = None
    market_evidence_reference: str = ""
    created_at: str = ""

    def __post_init__(self) -> None:
        # market_value and recommended_price are retained compatibility names.
        fair_market_value = (
            self.market_value
            if self.fair_market_value is None
            else self.fair_market_value
        )
        recommendation = (
            self.recommended_price
            if self.recommended_listing_price is None
            else self.recommended_listing_price
        )
        object.__setattr__(self, "fair_market_value", fair_market_value)
        object.__setattr__(self, "market_value", fair_market_value)
        object.__setattr__(self, "recommended_listing_price", recommendation)
        object.__setattr__(self, "recommended_price", recommendation)
        object.__setattr__(
            self,
            "final_listing_price",
            recommendation if self.final_listing_price is None else self.final_listing_price,
        )
        if not self.fair_market_value_confidence:
            object.__setattr__(self, "fair_market_value_confidence", str(self.confidence))


@dataclass(frozen=True)
class PersistedPricingRecord:
    decision_id: str
    listing_reference: str
    fair_market_value: Decimal | None
    fair_market_value_confidence: str
    recommended_listing_price: Decimal
    final_listing_price: Decimal
    pricing_reasoning: str
    market_evidence_reference: str = ""
    created_at: str = ""


@dataclass
class Decision:
    recommendation: str
    reason: str
    changed: bool
    review_required: bool = False


@dataclass
class AnalysisResult:
    listing: Listing
    identity: ListingIdentity
    market: MarketPrice
    pricing: PriceRecommendation
    decision: Decision
    fair_market_value: FairMarketValue | None = None
    explanation: PricingExplanation | None = None


@dataclass
class RunSummary:
    input_file: Path
    output_dir: Path
    source_type: str = ""
    listings_imported: int = 0
    listings_normalized: int = 0
    listings_matched: int = 0
    listings_unmatched: int = 0
    price_increases: int = 0
    price_decreases: int = 0
    no_changes: int = 0
    review_required: int = 0
    changed_listings: int = 0
    zero_99_review_candidates: int = 0
    reference_only_evidence: int = 0
    potential_revenue_impact: Decimal = Decimal("0.00")
