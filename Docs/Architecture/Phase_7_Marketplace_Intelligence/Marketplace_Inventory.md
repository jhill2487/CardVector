# Phase 7 Marketplace Intelligence Inventory

## Canonical Public Owner

| Path | Responsibility | Decision |
| --- | --- | --- |
| `Platform/cardvector/marketplace_intelligence/__init__.py` | Approved public imports | Extend |
| `Platform/cardvector/marketplace_intelligence/models.py` | Aliases proven contracts; avoids duplicate dataclasses | Extend aliases only |
| `Platform/cardvector/marketplace_intelligence/pricing.py` | Canonical pricing facade over proven formulas | Preserve math |
| `Platform/cardvector/marketplace_intelligence/evidence.py` | Pure comparable diagnostics and legacy sales-row analysis | Reuse |
| `Platform/cardvector/marketplace_intelligence/service.py` | Dependency-injectable pricing facade | Extend |
| `Platform/cardvector/marketplace_intelligence/persistence.py` | Pricing-decision repository facade | Preserve |
| `Platform/cardvector/marketplace_intelligence/adapters/__init__.py` | Provider normalization facade | Preserve |

## Proven Implementation Behind The Canonical API

| Path | Responsibility | Inputs and outputs | Decision |
| --- | --- | --- | --- |
| `Platform/Marketplace_Intelligence/marketplace_intelligence/engine.py` | CSV analysis sequence | `ImportResult` to `AnalysisResult` and reports | Delegate sequencing to canonical pipeline |
| `pricing_engine.py` | FMV adapters and Price Vector calculations | market report or explicit FMV to recommendation | Preserve formulas exactly |
| `models.py` | Listing, evidence, FMV, recommendation, decision, persistence models | Python dataclasses | Add backward-compatible explanation contracts |
| `providers.py` | Local CardUploader inventory, sold-cache, and TCGtracking providers | `ListingIdentity` to `MarketPrice` | Preserve source behavior |
| `listing_parser.py` | SKU, item-specifics, and title identity | `Listing` to `ListingIdentity` | Preserve matching behavior |
| `decision_engine.py` | Seller-facing Increase/Decrease/Review/No Change | pricing result to `Decision` | Preserve |
| `reports.py` | Analysis, validation, recommendation, and summary files | `AnalysisResult` to CSV/text | Append explainability columns |
| `bulk_export.py` | Existing changed-only eBay revise contract | changed results to six-column CSV | Preserve exactly |
| `pricing_repository.py` | SQLite persistence for FMV/recommendation/final price | `PersistedPricingRecord` | Preserve schema and behavior |
| `csv_import.py` | eBay, CardUploader, and custom CSV normalization | CSV to `Listing` | Preserve |
| `config/*.json` | Pricing, provider, and business settings | Versioned defaults | Add advisory explanation thresholds only |

## Compatibility Callers

| Path | Current use | Decision |
| --- | --- | --- |
| `Platform/cardvector/application/pricing.py` | Application orchestration | Add existing-listing evaluation forwarding |
| `Platform/Putnam_OS/System/app/putnam_os.py` | Production pricing and export UI | Preserve behavior |
| `Platform/Putnam_OS/System/app/main.py` | Secondary compatibility pricing UI | Preserve |
| `Platform/Putnam_OS/System/app/bulk_price_engine.py` | Exact ladder compatibility | Preserve |
| `Platform/Putnam_OS/System/MarketIntelligence/Pricing/` | Historical import adapter | Preserve |
| `Platform/Marketplace_Intelligence/marketplace_intelligence/ui.py` | Standalone desktop UI | Preserve visible behavior |
| `Platform/Marketplace_Intelligence/marketplace_intelligence/cli.py` | Standalone CLI | Preserve |

## Data Sources And Cache

- CardUploader inventory/export CSV values are loaded into an in-memory key to
  price map.
- CardUploader/eBay sold-cache JSON is selected by normalized query filename,
  filtered by the existing comparable matcher, and summarized by median and
  last-three average.
- TCGtracking sample/local export is reference-only by default.
- No live API provider is part of the production pipeline.
- Pricing persistence is a separate SQLite decision repository; Phase 7 does
  not change its migration or write to a production database.

## Duplicate And Split Logic

- Price calculations have one implementation in historical
  `pricing_engine.py`; canonical imports delegate to it.
- Provider comparable matching and canonical diagnostics contain overlapping
  match rules. Phase 7 will preserve matching output and document the split;
  it will not silently change accepted comparables.
- `putnam_os.py`, `main.py`, and `bulk_price_engine.py` are forwarding
  compatibility callers, not independent pricing engines.
- Listing Optimizer retains a separately registered future Listings
  compatibility surface and is not part of this phase.

## Current Accuracy Limits

Observed comparable filtering validates name tokens, collector number, a weak
set-title signal, and exclusions for graded, lot, pack, deck, sealed, and
similar listings. It does not reliably validate structured language, finish,
promo, first-edition, shadowless, seller quality, sale date, condition, or
duplicate sale identity. The sold-cache path does not perform statistical
outlier removal. These gaps must be exposed as uncertainty before any future
change to matching or pricing mathematics.
