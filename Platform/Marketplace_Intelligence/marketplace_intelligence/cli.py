from __future__ import annotations

import argparse
import os
from pathlib import Path

from . import __version__
from .config import remember_recent_file
from .csv_import import SOURCE_CARDUPLOADER, SOURCE_CUSTOM, SOURCE_EBAY
from .engine import MarketplaceIntelligenceEngine


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=f"CardVector Pricing Engine v{__version__}")
    parser.add_argument("--input", required=True, help="Path to listing CSV.")
    parser.add_argument("--output", help="Output report folder. Defaults to reports/<input>_<timestamp>.")
    parser.add_argument("--analysis-only", action="store_true", help="Generate reports only; no bulk revise CSV.")
    parser.add_argument(
        "--source-type",
        choices=["auto", SOURCE_EBAY, SOURCE_CARDUPLOADER, SOURCE_CUSTOM],
        default="auto",
        help="Override source detection.",
    )
    parser.add_argument("--source-profile", help="Custom CSV source profile name or JSON path.")
    parser.add_argument("--open-report", action="store_true", help="Open output folder after completion.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    engine = MarketplaceIntelligenceEngine()
    output = Path(args.output) if args.output else None
    result = engine.analyze_file(
        Path(args.input),
        output_dir=output,
        analysis_only=args.analysis_only,
        source_type=args.source_type,
        source_profile=args.source_profile,
    )
    remember_recent_file(Path(args.input))
    summary = result["summary"]
    reports = result["reports"]
    imported = result["import"]
    print(f"CardVector Pricing Engine v{__version__}")
    print(f"Input file: {args.input}")
    print(f"Detected source: {imported.detected_format}")
    print(f"Source type: {imported.source_type}")
    print(f"Listings imported: {summary.listings_imported}")
    print(f"Listings normalized: {summary.listings_normalized}")
    print(f"Listings matched: {summary.listings_matched}")
    print(f"Listings unmatched: {summary.listings_unmatched}")
    print(f"Changed listings: {summary.changed_listings}")
    print(f"Review required: {summary.review_required}")
    print(f"Potential revenue impact: ${summary.potential_revenue_impact}")
    print(f"Analysis report: {reports['analysis_report']}")
    print(f"Changed listings report: {reports['changed_listings_report']}")
    if reports.get("bulk_revise_csv"):
        print(f"Bulk revise CSV: {reports['bulk_revise_csv']}")
    elif imported.source_type != SOURCE_EBAY:
        print("Bulk revise CSV: skipped for non-eBay source mode")
    else:
        print("Bulk revise CSV: skipped by Analysis Only mode")
    if reports.get("pricing_recommendations"):
        print(f"Pricing recommendations: {reports['pricing_recommendations']}")
    if args.open_report:
        try:
            os.startfile(result["output_dir"])
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
