from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
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
