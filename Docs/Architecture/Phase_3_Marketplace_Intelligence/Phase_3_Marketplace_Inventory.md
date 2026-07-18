# Phase 3 Marketplace Intelligence Inventory

## Classification Key

- **Canonical implementation:** owns an active calculation today.
- **Production caller:** invokes pricing or market analysis in an operator flow.
- **Compatibility adapter:** preserves a historical import or entry surface.
- **Workflow / export owner:** handles files, confirmations, or marketplace
  records but must not own pricing mathematics.
- **Prototype / legacy:** no active production caller was found.
- **Archive:** retained evidence only; never imported by production.

## Canonical Marketplace Intelligence Package

### `Platform/Marketplace_Intelligence/marketplace_intelligence/models.py`

**Status:** Canonical implementation.

Public contracts:

- `Listing`
- `ListingIdentity`
- `MarketPrice`
- `MarketEvidence`
- `FairMarketValue`
- `PriceRecommendation`
- `PricingDecision`
- `PersistedPricingRecord`
- `Decision`
- `AnalysisResult`
- `RunSummary`

It owns normalized listing, evidence, FMV, recommendation, compatibility
decision, persistence-record, and analysis-result shapes. Compatibility fields
keep `market_value` aligned with `fair_market_value` and `recommended_price`
aligned with `recommended_listing_price`. `final_listing_price` defaults to the
recommendation.

### `Platform/Marketplace_Intelligence/marketplace_intelligence/pricing_engine.py`

**Status:** Proven canonical calculation implementation.

Public calculation surfaces:

- `decimal_money()`
- `fair_market_value_from_market_report()`
- `calculate_market_value()`
- `fair_market_value_from_market_price()`
- `apply_pricing_strategy()`
- `build_pricing_decision_from_fmv()`
- `build_pricing_decision()`
- `optimized_export_price()`
- `normalize_price_ladder()`
- `apply_exact_price_ladder()`
- `evaluate_new_listing_price()`
- `PricingEngine.recommend()`
- `PricingEngine.recommend_from_fmv()`

It owns the current weighted legacy FMV calculation, explicit-FMV Price Vector
path, configurable pricing profile behavior, low-price export tiers, exact
price ladder, listing review threshold, floors, caps, shipping assumptions,
rounding, and compatibility result mapping. Its outputs are consumed by
Putnam OS, Marketplace Intelligence, the bulk engine, and `main.py`.

### `Platform/Marketplace_Intelligence/marketplace_intelligence/engine.py`

**Status:** Canonical standalone analysis orchestrator.

`MarketplaceIntelligenceEngine` coordinates CSV import, listing identity,
market provider lookup, FMV normalization, Price Vector, decision labeling,
reports, and output directories. It passes explicit FMV into
`PricingEngine.recommend_from_fmv()`.

### `Platform/Marketplace_Intelligence/marketplace_intelligence/providers.py`

**Status:** Canonical source-normalization implementation with one overlap.

Public providers:

- `MarketProvider`
- `TCGtrackingProvider`
- `CardUploaderInventoryProvider`
- `CardUploaderSalesCacheProvider`
- `CompositeProvider`
- `NullProvider`
- `build_provider()`

The file normalizes stored CardUploader, cached eBay sold-comparable, and
reference-only TCGtracking data into `MarketPrice`. It also contains comparable
title filtering that overlaps the richer diagnostics in `putnam_os.py`.

### `Platform/Marketplace_Intelligence/marketplace_intelligence/listing_parser.py`

**Status:** Canonical identity-normalization implementation.

`ListingMatcher` converts known listing identity into lookup keys. It does not
perform card recognition.

### `Platform/Marketplace_Intelligence/marketplace_intelligence/csv_import.py`

**Status:** Canonical standalone intake adapter.

Public surfaces include eBay, CardUploader, and custom CSV detection and
normalization into `Listing`. It reads source CSVs but does not calculate
prices.

### `Platform/Marketplace_Intelligence/marketplace_intelligence/decision_engine.py`

**Status:** Canonical seller-facing recommendation labeler.

`DecisionEngine.decide()` maps market and Price Vector results to `Review`,
`No Change`, `Increase`, or `Decrease` without recalculating price.

### `Platform/Marketplace_Intelligence/marketplace_intelligence/reports.py`

**Status:** Marketplace Intelligence report renderer.

`result_row()`, `summarize()`, and `write_reports()` serialize normalized
evidence, FMV, recommended price, final price, confidence, and seller-facing
decision fields. It preserves current CSV fields and filenames.

### `Platform/Marketplace_Intelligence/marketplace_intelligence/bulk_export.py`

**Status:** Existing eBay changed-only export renderer.

`bulk_revise_rows()` and `write_bulk_revise_csv()` consume final listing prices.
They do not calculate FMV.

### `Platform/Marketplace_Intelligence/marketplace_intelligence/pricing_repository.py`

**Status:** Canonical pricing-decision persistence implementation.

Public surfaces:

- `pricing_record_from_result()`
- `PricingDecisionRepository.migrate()`
- `PricingDecisionRepository.save()`
- `PricingDecisionRepository.get()`

It writes only the database path supplied by the caller. Production use was
not found; current coverage uses temporary SQLite databases.

### `Platform/Marketplace_Intelligence/migrations/001_price_vector_pricing_decisions.sql`

**Status:** Canonical idempotent pricing-decision schema.

It creates `price_vector_pricing_decisions` with separate FMV, recommendation,
final price, reasoning, evidence reference, and timestamp fields.

### `config.py`, `utils.py`, `ui.py`, `cli.py`

**Status:** Supporting standalone application code.

- `config.py` reads and writes Marketplace Intelligence profiles and recent
  files.
- `utils.py` owns package-local money/text/CSV helpers.
- `ui.py` is a separate Tkinter presentation surface and is not part of the
  canonical pricing API.
- `cli.py` is a standalone analysis entry surface using
  `MarketplaceIntelligenceEngine`.

## Production Putnam OS Callers And Adapters

### `Platform/Putnam_OS/System/app/putnam_os.py`

**Status:** Production UI, orchestration, and compatibility caller.

Pricing calls:

- `optimized_export_price()`
- `calculate_market_value()`
- `apply_pricing_strategy()`
- `prepare_listing_export_rows()`

These currently delegate pricing math to the proven engine. The file retains
output-row mutation, eBay business-policy columns, confirmation, job folders,
logs, report files, and UI progress.

Marketplace-analysis overlap:

- `comp_match_diagnostics()`
- `comparable_reason()`
- `market_analyze()`
- token, card-number, exclusion, analytics, and confidence helpers

These are business/evidence interpretation in a UI module. The live
CardUploader HTTP/cache function `fetch_carduploader_sales()` is an external
source adapter and must remain outside core calculation code until a separately
approved integration migration.

### `Platform/Putnam_OS/System/app/bulk_price_engine.py`

**Status:** Compatibility workflow and eBay export owner.

It normalizes active-listing/bulk-template CSVs, creates review/upload/rollback
files, and writes logs. `load_ladder()` and `apply_ladder()` delegate canonical
ladder normalization/calculation. CSV and output behavior remains owned here
until the Listings migration.

### `Platform/Putnam_OS/System/app/main.py`

**Status:** Secondary application; planned deprecation candidate, not
deprecated.

Its existing-listing and new-listing workflows delegate ladder and review
calculation to the canonical pricing engine. It retains CSV, files, UI,
confirmation, and logging behavior.

### `Platform/Putnam_OS/System/MarketIntelligence/Pricing/`

**Status:** Compatibility adapter.

- `pricing_engine.py` forwards the old Putnam pricing API.
- `pricing_models.py` re-exports `PricingDecision`.
- `__init__.py` preserves historical imports.
- `test_pricing_engine.py` is a direct compatibility smoke test.

No independent formula remains in this folder.

### `Platform/Putnam_OS/Putnam_Seller_Tools/listing_optimizer/putnam_listing_optimizer_v1_1.py`

**Status:** Legacy production-compatible CLI with duplicate pricing formula.

`optimize_export_price()` repeats the same low-price tier behavior as the
canonical `optimized_export_price()`. The surrounding code owns eBay policy
validation, CSV preparation, confirmation, and export history, not pricing.

`putnam_listing_optimizer_v1_2.py` is a launcher wrapper for this file.

## Legacy Market Models

### `Platform/Putnam_OS/System/MarketIntelligence/Models/market_snapshot.py`

`MarketSnapshot` groups sold, active eBay, TCGtracking, and internal-history
facts. No active production caller was found.

### `Platform/Putnam_OS/System/MarketIntelligence/Models/market_intelligence_report.py`

`MarketIntelligenceReport` and `build_market_report()` summarize provider
presence. No active production caller was found beyond the wildcard inspector
re-export.

### `Platform/Putnam_OS/System/MarketIntelligence/Identity/identity_translator.py`

`CardUploaderIdentity` and `IdentityTranslator` format known identity for
provider queries. No active production caller was found.

### `Platform/Putnam_OS/System/MarketIntelligence/Inspector/report_builder.py`

Wildcard re-export of the legacy report model. No active production caller was
found.

These files remain retained and unmodified in Phase 3 unless a tested caller
requires forwarding. They are not selected as canonical models.

## Tests And Fixtures

### Active tests

- `Platform/Marketplace_Intelligence/tests/test_marketplace_intelligence_v1.py`
- `Platform/Marketplace_Intelligence/tests/test_price_vector_fmv_separation.py`
- `Platform/Marketplace_Intelligence/tests/test_pricing_engine_consolidation.py`
- `Platform/Putnam_OS/System/MarketIntelligence/Pricing/test_pricing_engine.py`
- `Platform/Putnam_OS/System/app/test_listing_optimizer_v1_2.py`
- `Platform/Putnam_OS/System/app/test_ebay_policy_config.py`
- `Tests/application/test_application_layer.py`

### Stored fixtures

- `Platform/Marketplace_Intelligence/examples/ebay_active_listings_sample.csv`
- `Platform/Marketplace_Intelligence/examples/carduploader_export_sample.csv`
- `Platform/Marketplace_Intelligence/examples/custom_listing_sample.csv`
- `Platform/Marketplace_Intelligence/examples/tcgtracking_prices_sample.json`
- local cached CardUploader/eBay sales JSON under the configured runtime cache
  roots

No Phase 3 test may call a live marketplace or write a production database.

## Non-Production And Deferred Areas

- `Platform/Marketplace_Intelligence/business_intelligence/` is a prototype and
  is not part of pricing consolidation.
- `Platform/Putnam_OS/Putnam_Seller_Tools/seller_audit/` audits data; it is not
  a pricing recommendation owner.
- Files with `backup`, `original`, or dated version names are historical debt.
  They are not imported by production and are deferred to the approved cleanup
  phase.
- `Data/Logs/pricing_performance_log.csv` is runtime evidence, not source.

## Ownership Decision Supported By This Inventory

The approved package `Platform/cardvector/marketplace_intelligence/` can become
the single public owner without rewriting formulas:

1. expose stable contracts and pricing operations there;
2. delegate internally to the proven historical package during migration;
3. route application and compatibility callers to the new public path;
4. relocate the pure comparable/evidence interpretation out of `putnam_os.py`
   while injecting the existing external data fetcher;
5. leave eBay CSV construction, files, confirmations, and live source mechanics
   with their present owners;
6. register every historical public path as a tested compatibility adapter.
