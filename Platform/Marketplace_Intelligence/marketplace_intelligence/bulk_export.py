from __future__ import annotations

from pathlib import Path

from .models import AnalysisResult
from .utils import money_text, write_csv


BULK_REVISE_FIELDS = [
    "Action",
    "ItemID",
    "StartPrice",
    "Title",
    "CustomLabel",
    "MarketplaceIntelligenceReason",
]


def bulk_revise_rows(results: list[AnalysisResult]) -> list[dict[str, str]]:
    rows = []
    for result in results:
        if not result.decision.changed:
            continue
        rows.append({
            "Action": "Revise",
            "ItemID": result.listing.item_id,
            "StartPrice": money_text(result.pricing.recommended_price),
            "Title": result.listing.title,
            "CustomLabel": result.listing.sku,
            "MarketplaceIntelligenceReason": result.decision.reason,
        })
    return rows


def write_bulk_revise_csv(path: Path, results: list[AnalysisResult]) -> Path:
    return write_csv(path, bulk_revise_rows(results), BULK_REVISE_FIELDS)

