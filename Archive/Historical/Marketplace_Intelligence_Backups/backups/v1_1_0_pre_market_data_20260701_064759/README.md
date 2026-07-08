# Marketplace Intelligence v1.0

Marketplace Intelligence is a standalone desktop application and reusable Python
engine for analyzing eBay Active Listings CSV exports.

Primary question:

```text
Out of my active listings, which ones actually deserve attention today?
```

It does not upload to eBay. It does not require Putnam OS inventory. It does not
automatically reprice everything.

## Inputs

- eBay Active Listings CSV export.
- Configurable pricing, business, and market-provider JSON files.

## Outputs

Reports are written under:

```text
Platform/Marketplace_Intelligence/reports/
```

Each run creates:

- `analysis_report.csv`
- `changed_listings_report.csv`
- `analysis_summary.txt`
- `ebay_bulk_revise_changed_only.csv` unless Analysis Only mode is enabled

Only changed listings are included in the bulk revise CSV.

## Run The Desktop App

From the repository root:

```powershell
python Platform\Marketplace_Intelligence\run_marketplace_intelligence.py
```

Or use:

```text
Platform\Marketplace_Intelligence\Run Marketplace Intelligence.bat
```

## Run The CLI

```powershell
python -m Platform.Marketplace_Intelligence.marketplace_intelligence.cli --input Platform\Marketplace_Intelligence\examples\ebay_active_listings_sample.csv
```

Analysis-only mode:

```powershell
python -m Platform.Marketplace_Intelligence.marketplace_intelligence.cli --input Platform\Marketplace_Intelligence\examples\ebay_active_listings_sample.csv --analysis-only
```

## Configuration

Settings live outside code:

- `config/pricing_profile.json`
- `config/business_profile.json`
- `config/market_provider.json`

No business strategy should require modifying Python code.

The desktop app also exposes a Pricing Settings panel for common operator
inputs:

- Minimum price
- Ignore changes under
- Maximum increase percent
- Maximum decrease percent
- Shipping assumption
- Flat shipping cost

Use `Save Pricing Profile` to write those settings back to
`config/pricing_profile.json`.

Shipping behavior:

- `buyer_pays_shipping`: no shipping adjustment.
- `seller_pays_shipping`: adds the configured flat shipping cost into the
  recommendation basis.
- `mixed_shipping`: no automatic shipping adjustment.

## Provider Model

The pricing engine does not call providers directly.

Flow:

```text
Listing Parser -> Market Provider -> Pricing Engine -> Decision Engine -> Reports
```

v1.0 includes a TCGtracking provider adapter that reads a local
TCGtracking-style JSON/CSV export. Future providers can add TCGplayer, eBay
Sold, Whatnot, or historical pricing by implementing the same provider
interface.

## Putnam OS Integration

Putnam OS can import and reuse:

```python
from marketplace_intelligence.pricing_engine import PricingEngine
```

or call the full orchestrator:

```python
from marketplace_intelligence.engine import MarketplaceIntelligenceEngine
```

The engine has no Putnam OS inventory dependency.

## Beta Safety

- Never modifies the source CSV.
- Never uploads to eBay.
- No API login required.
- Bulk revise export is changed-only.
- Analysis Only mode skips the bulk revise CSV.
