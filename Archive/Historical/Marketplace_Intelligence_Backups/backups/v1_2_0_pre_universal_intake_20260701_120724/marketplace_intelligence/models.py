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
    sku: str = ""
    quantity: str = ""
    condition: str = ""
    category: str = ""
    shipping: str = ""


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


@dataclass
class PriceRecommendation:
    recommended_price: Decimal
    difference: Decimal
    percent_change: Decimal
    pricing_reason: str
    review_required: bool = False
    review_reason: str = ""


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


@dataclass
class RunSummary:
    input_file: Path
    output_dir: Path
    listings_imported: int = 0
    listings_matched: int = 0
    listings_unmatched: int = 0
    price_increases: int = 0
    price_decreases: int = 0
    no_changes: int = 0
    review_required: int = 0
    changed_listings: int = 0
    potential_revenue_impact: Decimal = Decimal("0.00")

