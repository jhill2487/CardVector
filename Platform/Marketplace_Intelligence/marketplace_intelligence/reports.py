from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path

from . import __version__
from .bulk_export import write_bulk_revise_csv
from .csv_import import SOURCE_CARDUPLOADER, SOURCE_CUSTOM, SOURCE_EBAY
from .models import AnalysisResult, RunSummary
from .utils import money_text, write_csv


ANALYSIS_FIELDS = [
    "row_number",
    "source_type",
    "source_file",
    "item_id",
    "title",
    "sku",
    "quantity",
    "condition",
    "set_name",
    "card_number",
    "rarity",
    "variant",
    "finish",
    "tcg",
    "tcgplayer_product_id",
    "tcgplayer_sku",
    "catalog_sku",
    "status",
    "match_method",
    "match_confidence",
    "current_price",
    "market_price",
    "market_source",
    "market_confidence",
    "reference_only",
    "accepted_comps",
    "rejected_comps",
    "recommended_price",
    "difference",
    "percent_change",
    "recommendation",
    "changed",
    "review_required",
    "reason",
    "pricing_reason",
    "provider",
]


def result_row(result: AnalysisResult) -> dict[str, str]:
    return {
        "row_number": str(result.listing.row_number),
        "source_type": result.listing.source_type,
        "source_file": result.listing.source_file,
        "item_id": result.listing.item_id,
        "title": result.listing.title,
        "sku": result.listing.sku,
        "quantity": result.listing.quantity,
        "condition": result.listing.condition,
        "set_name": result.listing.set_name,
        "card_number": result.listing.card_number,
        "rarity": result.listing.rarity,
        "variant": result.listing.variant,
        "finish": result.listing.finish,
        "tcg": result.listing.tcg,
        "tcgplayer_product_id": result.listing.tcgplayer_product_id,
        "tcgplayer_sku": result.listing.tcgplayer_sku,
        "catalog_sku": result.listing.catalog_sku,
        "status": result.listing.status,
        "match_method": result.identity.match_method,
        "match_confidence": result.identity.confidence,
        "current_price": money_text(result.listing.current_price),
        "market_price": money_text(result.market.market_price),
        "market_source": result.market.source,
        "market_confidence": result.market.confidence,
        "reference_only": "TRUE" if result.market.metadata.get("reference_only") else "FALSE",
        "accepted_comps": str(result.market.metadata.get("accepted_comps", "")),
        "rejected_comps": str(result.market.metadata.get("rejected_comps", "")),
        "recommended_price": money_text(result.pricing.recommended_price),
        "difference": money_text(result.pricing.difference),
        "percent_change": str(result.pricing.percent_change),
        "recommendation": result.decision.recommendation,
        "changed": "TRUE" if result.decision.changed else "FALSE",
        "review_required": "TRUE" if result.decision.review_required else "FALSE",
        "reason": result.decision.reason,
        "pricing_reason": result.pricing.pricing_reason,
        "provider": result.market.provider,
    }


def summarize(input_file: Path, output_dir: Path, results: list[AnalysisResult], source_type: str = "") -> RunSummary:
    summary = RunSummary(input_file=input_file, output_dir=output_dir, source_type=source_type, listings_imported=len(results), listings_normalized=len(results))
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
        if result.listing.current_price == Decimal("0.99"):
            summary.zero_99_review_candidates += 1
        if result.market.metadata.get("reference_only"):
            summary.reference_only_evidence += 1
        if result.decision.changed:
            summary.changed_listings += 1
            summary.potential_revenue_impact += result.pricing.difference
    summary.potential_revenue_impact = summary.potential_revenue_impact.quantize(Decimal("0.01"))
    return summary


def summary_text(summary: RunSummary, analysis_only: bool) -> str:
    return "\n".join([
        f"CardVector Pricing Engine v{__version__}",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        f"Input file: {summary.input_file}",
        f"Detected source type: {summary.source_type or 'unknown'}",
        f"Output folder: {summary.output_dir}",
        f"Mode: {'Reports / Validation Only' if analysis_only else 'Reports + Bulk Revise Export'}",
        "",
        f"Listings Imported: {summary.listings_imported}",
        f"Listings Normalized: {summary.listings_normalized}",
        f"Listings Matched: {summary.listings_matched}",
        f"Listings Unmatched: {summary.listings_unmatched}",
        f"Price Increases: {summary.price_increases}",
        f"Price Decreases: {summary.price_decreases}",
        f"No Changes: {summary.no_changes}",
        f"Review Required: {summary.review_required}",
        f"0.99 Review Candidates: {summary.zero_99_review_candidates}",
        f"Reference-only Evidence Count: {summary.reference_only_evidence}",
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
    source_type: str = SOURCE_EBAY,
) -> dict[str, Path | None]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = [result_row(result) for result in results]
    changed = [row for row in rows if row["changed"] == "TRUE"]
    analysis_csv = write_csv(output_dir / "analysis_report.csv", rows, ANALYSIS_FIELDS)
    changed_csv = write_csv(output_dir / "changed_listings_report.csv", changed, ANALYSIS_FIELDS)
    bulk_csv = None
    validation_report = None
    carduploader_validation = None
    underpriced = None
    pricing_recommendations = None
    if source_type == SOURCE_EBAY and not analysis_only:
        bulk_csv = write_bulk_revise_csv(output_dir / "ebay_bulk_revise_changed_only.csv", results)
    if source_type in {SOURCE_CARDUPLOADER, SOURCE_CUSTOM}:
        underpriced_rows = [
            row for row, result in zip(rows, results)
            if result.listing.current_price <= Decimal("0.99")
            or result.pricing.recommended_price > result.listing.current_price
            or result.decision.review_required
        ]
        recommendation_rows = [row for row in rows if row["recommendation"] != "No Change" or row["review_required"] == "TRUE"]
        validation_name = "carduploader_validation_report.csv" if source_type == SOURCE_CARDUPLOADER else "custom_validation_report.csv"
        validation_report = write_csv(output_dir / validation_name, rows, ANALYSIS_FIELDS)
        if source_type == SOURCE_CARDUPLOADER:
            carduploader_validation = validation_report
        underpriced = write_csv(output_dir / "underpriced_candidates_report.csv", underpriced_rows, ANALYSIS_FIELDS)
        pricing_recommendations = write_csv(output_dir / "pricing_recommendations.csv", recommendation_rows, ANALYSIS_FIELDS)
    summary = summarize(input_file, output_dir, results, source_type=source_type)
    summary_file = output_dir / "analysis_summary.txt"
    mode_analysis_only = analysis_only or source_type != SOURCE_EBAY
    summary_file.write_text(summary_text(summary, mode_analysis_only), encoding="utf-8")
    return {
        "analysis_report": analysis_csv,
        "changed_listings_report": changed_csv,
        "bulk_revise_csv": bulk_csv,
        "validation_report": validation_report,
        "carduploader_validation_report": carduploader_validation,
        "underpriced_candidates_report": underpriced,
        "pricing_recommendations": pricing_recommendations,
        "summary_file": summary_file,
    }
