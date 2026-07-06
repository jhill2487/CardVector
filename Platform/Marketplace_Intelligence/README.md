# CardVector Pricing Engine v1.2

CardVector Pricing Engine / Marketplace Intelligence is a standalone desktop
application and reusable Python engine for analyzing listing CSVs through a
universal intake pipeline.

Primary question:

```text
Out of my active listings, which ones actually deserve attention today?
```

It does not upload to eBay. It does not require Putnam OS inventory. It does not
automatically reprice everything.

## Universal Intake

- eBay Active Listings CSV export.
- CardUploader export CSV.
- Custom CSV with a saved source profile mapping.
- Configurable pricing, business, and market-provider JSON files.

Locked flow:

```text
CSV Input
v
Source Detection
v
Column Mapping / Adapter Profile
v
Normalized Listing
v
Existing Pricing Engine
v
Reports / Recommendations
v
Source-appropriate export
```

## Outputs

Reports are written under:

```text
Platform/Marketplace_Intelligence/reports/
```

Each run creates:

- `analysis_report.csv`
- `changed_listings_report.csv`
- `analysis_summary.txt`
- eBay mode: `ebay_bulk_revise_changed_only.csv` unless Analysis Only mode is enabled
- CardUploader/custom modes: validation and recommendation CSVs only

Only changed listings are included in the bulk revise CSV.

CardUploader mode never creates an eBay bulk revise CSV.

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
- `config/source_profiles/*.json`

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

Custom source profile example:

```json
{
  "name": "custom_example",
  "mapping": {
    "title": "Listing Name",
    "sku": "My SKU",
    "current_price": "My Price",
    "quantity": "Count",
    "condition": "Grade",
    "set_name": "Expansion",
    "card_number": "Number",
    "finish": "Foil Type"
  }
}
```

## Provider Model

The pricing engine does not call providers directly.

Flow:

```text
Listing Parser -> Market Provider -> Pricing Engine -> Decision Engine -> Reports
```

v1.2 uses a composite provider by default.

Default provider priority:

1. CardUploader inventory/export CSV prices
2. CardUploader/eBay sales cache with conservative comp validation
3. TCGtracking local export as reference-only context

CardUploader evidence is allowed to drive recommendations. TCGtracking is
reference-only by default so TCGplayer-style figures do not directly reprice
eBay listings. A reference-only match can appear in `analysis_report.csv`, but
it will be marked for manual review and excluded from the bulk revise CSV.

Provider settings live in:

```text
config/market_provider.json
```

The pricing engine still does not call providers directly. Future providers can
add TCGplayer, eBay Sold, Whatnot, live TCGtracking, or historical pricing by
implementing the same provider interface.

## Report Evidence Fields

`analysis_report.csv` includes:

- `market_source`
- `market_confidence`
- `reference_only`
- `accepted_comps`
- `rejected_comps`
- `pricing_reason`

Use these fields to decide whether a recommendation deserves action today.

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
- Bulk revise export is eBay-source only.
- CardUploader and custom CSV modes produce reports/recommendations only.
- Analysis Only mode skips the bulk revise CSV.
- Reference-only market data never creates revise rows.
