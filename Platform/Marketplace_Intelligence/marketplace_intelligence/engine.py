from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .config import AppConfig, REPORTS_DIR, load_app_config
from .csv_import import ImportResult, import_listing_csv
from .decision_engine import DecisionEngine
from .listing_parser import ListingMatcher
from .models import AnalysisResult
from .pricing_engine import PricingEngine
from .providers import build_provider
from .reports import summarize, write_reports
from .utils import safe_filename


class MarketplaceIntelligenceEngine:
    def __init__(self, config: AppConfig | None = None):
        self.config = config or load_app_config()
        self.matcher = ListingMatcher()
        self.provider = build_provider(self.config.market_provider)
        self.pricing_engine = PricingEngine(self.config.pricing_profile)
        self.decision_engine = DecisionEngine(self.config.business_profile)

    def import_csv(
        self,
        path: Path,
        source_type: str | None = None,
        custom_mapping: dict[str, str] | None = None,
        source_profile: str | Path | None = None,
    ) -> ImportResult:
        return import_listing_csv(Path(path), source_type=source_type, custom_mapping=custom_mapping, source_profile=source_profile)

    def analyze_import(self, imported: ImportResult) -> list[AnalysisResult]:
        if imported.missing_required_fields:
            raise ValueError("Missing required columns: " + ", ".join(imported.missing_required_fields))
        results: list[AnalysisResult] = []
        for listing in imported.listings:
            identity = self.matcher.identify(listing)
            market = self.provider.get_market_price(identity)
            pricing = self.pricing_engine.recommend(listing, market)
            decision = self.decision_engine.decide(listing, market, pricing)
            results.append(AnalysisResult(listing, identity, market, pricing, decision))
        return results

    def analyze_file(
        self,
        path: Path,
        output_dir: Path | None = None,
        analysis_only: bool = False,
        source_type: str | None = None,
        custom_mapping: dict[str, str] | None = None,
        source_profile: str | Path | None = None,
    ) -> dict:
        imported = self.import_csv(path, source_type=source_type, custom_mapping=custom_mapping, source_profile=source_profile)
        results = self.analyze_import(imported)
        target_dir = output_dir or self.default_output_dir(Path(path))
        reports = write_reports(target_dir, Path(path), results, analysis_only=analysis_only, source_type=imported.source_type)
        summary = summarize(Path(path), target_dir, results, source_type=imported.source_type)
        return {
            "import": imported,
            "results": results,
            "summary": summary,
            "reports": reports,
            "output_dir": target_dir,
        }

    def default_output_dir(self, path: Path) -> Path:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = safe_filename(Path(path).stem)
        return REPORTS_DIR / f"{name}_{stamp}"
