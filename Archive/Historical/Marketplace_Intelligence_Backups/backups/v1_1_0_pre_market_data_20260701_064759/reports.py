from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path

from .bulk_export import write_bulk_revise_csv
from .models import AnalysisResult, RunSummary
from .utils import money_text, write_csv


ANALYSIS_FIELDS = [
    "row_number",
    "item_id",
    "title",
    "sku",
    "match_method",
    "match_confidence",
    "current_price",
    "market_price",
    "recommended_price",
    "difference",
    "percent_change",
    "recommendation",
    "changed",
    "review_required",
    "reason",
    "provider",
]


def result_row(result: AnalysisResult) -> dict[str, str]:
    return {
        "row_number": str(result.listing.row_number),
        "item_id": result.listing.item_id,
        "title": result.listing.title,
        "sku": result.listing.sku,
        "match_method": result.identity.match_method,
        "match_confidence": result.identity.confidence,
        "current_price": money_text(result.listing.current_price),
        "market_price": money_text(result.market.market_price),
        "recommended_price": money_text(result.pricing.recommended_price),
        "difference": money_text(result.pricing.difference),
        "percent_change": str(result.pricing.percent_change),
        "recommendation": result.decision.recommendation,
        "changed": "TRUE" if result.decision.changed else "FALSE",
        "review_required": "TRUE" if result.decision.review_required else "FALSE",
        "reason": result.decision.reason,
        "provider": result.market.provider,
    }


def summarize(input_file: Path, output_dir: Path, results: list[AnalysisResult]) -> RunSummary:
    summary = RunSummary(input_file=input_file, output_dir=output_dir, listings_imported=len(results))
    for result in results:
        if result.market.matched:
            summary.listings_matched += 1
        else:
            summary.listings_unmatched += 1
        if result.decision.recommendation == "Increase":
            summary.price_increases += 1
        elif result.decision.recommendation == "Decrease":
            summary.price_decreases += 1
        elif result.decision.recommendation == "No Change":
            summary.no_changes += 1
        if result.decision.review_required:
            summary.review_required += 1
        if result.decision.changed:
            summary.changed_listings += 1
            summary.potential_revenue_impact += result.pricing.difference
    summary.potential_revenue_impact = summary.potential_revenue_impact.quantize(Decimal("0.01"))
    return summary


def summary_text(summary: RunSummary, analysis_only: bool) -> str:
    return "\n".join([
        "Marketplace Intelligence v1.0",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        f"Input file: {summary.input_file}",
        f"Output folder: {summary.output_dir}",
        f"Mode: {'Analysis Only' if analysis_only else 'Reports + Bulk Revise Export'}",
        "",
        f"Listings Imported: {summary.listings_imported}",
        f"Listings Matched: {summary.listings_matched}",
        f"Listings Unmatched: {summary.listings_unmatched}",
        f"Price Increases: {summary.price_increases}",
        f"Price Decreases: {summary.price_decreases}",
        f"No Changes: {summary.no_changes}",
        f"Review Required: {summary.review_required}",
        f"Changed Listings: {summary.changed_listings}",
        f"Potential Revenue Impact: ${money_text(summary.potential_revenue_impact)}",
        "",
        "Recommendation:",
        "Review changed listings first. Marketplace Intelligence does not upload or revise listings automatically.",
    ])


def write_reports(
    output_dir: Path,
    input_file: Path,
    results: list[AnalysisResult],
    analysis_only: bool = False,
) -> dict[str, Path | None]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = [result_row(result) for result in results]
    changed = [row for row in rows if row["changed"] == "TRUE"]
    analysis_csv = write_csv(output_dir / "analysis_report.csv", rows, ANALYSIS_FIELDS)
    changed_csv = write_csv(output_dir / "changed_listings_report.csv", changed, ANALYSIS_FIELDS)
    bulk_csv = None
    if not analysis_only:
        bulk_csv = write_bulk_revise_csv(output_dir / "ebay_bulk_revise_changed_only.csv", results)
    summary = summarize(input_file, output_dir, results)
    summary_file = output_dir / "analysis_summary.txt"
    summary_file.write_text(summary_text(summary, analysis_only), encoding="utf-8")
    return {
        "analysis_report": analysis_csv,
        "changed_listings_report": changed_csv,
        "bulk_revise_csv": bulk_csv,
        "summary_file": summary_file,
    }
