from __future__ import annotations

import shutil
import sys
import tempfile
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from marketplace_intelligence.config import AppConfig
from marketplace_intelligence.engine import MarketplaceIntelligenceEngine
from marketplace_intelligence.models import Listing, MarketPrice
from marketplace_intelligence.pricing_engine import PricingEngine


def run_smoke_test() -> None:
    sample = ROOT / "examples" / "ebay_active_listings_sample.csv"
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        carduploader_prices = tmp_path / "carduploader_prices.csv"
        carduploader_prices.write_text(
            "\n".join([
                "Title,Catalog SKU,Price",
                "Pokemon TCG Test Card Alpha 001,PKM-001,1.49",
                "Pokemon TCG Test Card Beta 002,PKM-002,3.99",
                "Magic The Gathering Test Spell 003,MTG-001,0.99",
            ]),
            encoding="utf-8",
        )
        config = AppConfig(
            pricing_profile={
                "minimum_price": "0.99",
                "ignore_changes_under": "0.00",
                "maximum_increase_percent": "999.00",
                "maximum_decrease_percent": "999.00",
                "maximum_increase_amount": "999.00",
                "maximum_decrease_amount": "999.00",
                "shipping_assumption": "buyer_pays_shipping",
                "flat_shipping_cost": "0.00",
            },
            business_profile={},
            market_provider={
                "provider": "composite",
                "providers": [
                    {"provider": "carduploader_inventory", "files": [str(carduploader_prices)]},
                    {
                        "provider": "tcgtracking",
                        "mode": "local_export",
                        "price_file": "examples/tcgtracking_prices_sample.json",
                        "actionable": False,
                    },
                ],
            },
        )
        output = Path(tmp) / "reports"
        engine = MarketplaceIntelligenceEngine(config)
        result = engine.analyze_file(sample, output_dir=output, analysis_only=False)
        summary = result["summary"]
        reports = result["reports"]
        assert summary.listings_imported == 4
        assert summary.listings_matched == 3
        assert summary.listings_unmatched == 1
        assert summary.changed_listings >= 1
        assert reports["analysis_report"].exists()
        assert reports["changed_listings_report"].exists()
        assert reports["bulk_revise_csv"].exists()
        assert reports["summary_file"].exists()

        analysis_output = tmp_path / "analysis_only"
        result = engine.analyze_file(sample, output_dir=analysis_output, analysis_only=True)
        assert result["reports"]["bulk_revise_csv"] is None
        assert not (analysis_output / "ebay_bulk_revise_changed_only.csv").exists()

    listing = Listing(1, {}, "1", "Shipping Test", current_price=Decimal("4.00"))
    market = MarketPrice(True, market_price=Decimal("5.00"), provider="test")
    engine = PricingEngine({
        "minimum_price": "0.99",
        "ignore_changes_under": "0.00",
        "maximum_increase_percent": "999.00",
        "maximum_decrease_percent": "999.00",
        "maximum_increase_amount": "999.00",
        "maximum_decrease_amount": "999.00",
        "shipping_assumption": "seller_pays_shipping",
        "flat_shipping_cost": "1.25",
    })
    recommendation = engine.recommend(listing, market)
    assert str(recommendation.recommended_price) == "6.25"

    print("Marketplace Intelligence smoke test passed")


if __name__ == "__main__":
    run_smoke_test()
