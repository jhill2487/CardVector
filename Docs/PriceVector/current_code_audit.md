# Price Vector Current Code Audit

Audit date: 2026-07-17

Repository: `jhill2487/CardVector`

Audited baseline: `main` at `0fe2475d4b72c9a3251cbed0d2bd4890b0ceec85`

Scope: inspection only. No production code was changed for this audit.

## Executive Summary

CardVector already has reusable listing normalization, provider abstraction,
configurable recommendation calculations, decision labels, reports, and eBay
bulk-revise output. The project standard in
`Docs/Reference/Putnam_Standards/PUTNAM_PLATFORM_STANDARDS.md` identifies
`Platform/Marketplace_Intelligence` as the canonical reusable CardVector
Pricing Engine.

Two additional pricing implementations overlap that owner:

1. `Platform/Putnam_OS/System/MarketIntelligence/Pricing` calculates a weighted
   market value and an integrated Putnam OS recommendation.
2. `Platform/Putnam_OS/System/app/putnam_os.py`,
   `Platform/Putnam_OS/System/app/bulk_price_engine.py`, and
   `Platform/Putnam_OS/System/app/main.py` retain embedded or legacy pricing
   ladders and export behavior.

The approved Price Vector model is not present as a complete contract. In
particular, there is no first-class Fair Market Value object, no approved
value-tier approval matrix, no internal quality-review flag, and no durable
manual-override record. There is also no pricing database or repository layer;
pricing state is currently JSON configuration plus CSV/JSON/TXT reports.

Card recognition is not implemented by these pricing components. CardUploader
identity fields are translated or normalized after recognition, which is
consistent with the fixed scope.

## Canonical Ownership

| Responsibility | Current owner or candidate | Finding |
| --- | --- | --- |
| Reusable Pricing Engine | `Platform/Marketplace_Intelligence/marketplace_intelligence` | Named by platform standards and README as reusable by Putnam OS. Best direct reuse target for Price Vector. |
| Market evidence inside Putnam OS | `Platform/Putnam_OS/System/MarketIntelligence` | Contains useful evidence and weighted-market-value models, but duplicates part of the canonical engine boundary. |
| CardVector OS orchestration/export | `Platform/Putnam_OS/System/app/putnam_os.py` | Production workflow owner. It should consume pricing results, not become the new Price Vector owner. |
| Legacy eBay price ladder | `Platform/Putnam_OS/System/app/bulk_price_engine.py` and `main.py` | Still callable but overlaps the canonical Pricing Engine. Preserve for compatibility during Phase 1. |
| Card recognition | CardUploader, external to this repository responsibility | No Price Vector recognition work is required or appropriate. |

## 1. Business And Seller Profiles

### Canonical pricing-engine profile

`Platform/Marketplace_Intelligence/config/business_profile.json`

- Stores `business_name`, `primary_goal`, current recommendation labels, and
  future recommendation labels.
- Current `business_name` is `Community Seller`, not `Putnam Collectibles`.
- Does not record ownership, active/inactive marketplaces, acquisition policy,
  or the Competitive Turnover strategy.

`Platform/Marketplace_Intelligence/marketplace_intelligence/config.py`

- `AppConfig` groups pricing, business, and provider dictionaries.
- `load_app_config()` loads the three JSON profiles.
- `load_json()` and `save_json()` are reusable configuration helpers.

### Putnam OS profile

`Platform/Putnam_OS/System/config/business_profile.json`

- Stores `primary_goal`, `secondary_goal`, `risk_tolerance`,
  `minimum_profit`, and `default_marketplace`.
- Does not contain the approved complete Price Vector business profile.

`Platform/Putnam_OS/System/decision_engine/business_profile.py`

- `DEFAULT_BUSINESS_PROFILE` supplies the same small Putnam OS defaults.
- `business_profile_path()` points at a legacy `Putnam_OS/System` path relative
  to a supplied root rather than the current `Platform/Putnam_OS/System` owner.
- `load_business_profile()` merges file values over defaults.

Direct reuse: the standalone `AppConfig` and JSON helpers.

Conflict: two business-profile files and loaders represent different schemas.

## 2. Pricing Configuration And Rules

### Canonical standalone configuration

`Platform/Marketplace_Intelligence/config/pricing_profile.json`

- Configures minimum price, market strategy, hold band, increase/decrease
  limits, ignored small changes, rounding, review thresholds, and shipping.
- Current profile is `Community Beta Conservative`, not Competitive Turnover.
- Current high-price review threshold is `$100`, not the approved `$20`.

`Platform/Marketplace_Intelligence/marketplace_intelligence/pricing_engine.py`

- `PricingEngine.recommend()` accepts a normalized `Listing` and `MarketPrice`.
- `apply_market_strategy()` supports market match, undercut, and hold band.
- `apply_shipping_assumption()` supports buyer-paid, seller-paid, and mixed
  shipping assumptions.
- `apply_change_limits()`, `apply_minimum_price()`, `apply_rounding()`, and
  `review_check()` are reusable calculation helpers.
- The engine currently treats `MarketPrice.market_price` as the input target;
  it does not consume a first-class FMV object.

### Integrated Putnam OS market-pricing package

`Platform/Putnam_OS/System/MarketIntelligence/Pricing/pricing_engine.py`

- `calculate_market_value()` requires at least three accepted comps and uses
  median at 60%, last-three average at 30%, and last sale at 10%.
- `apply_pricing_strategy()` supports `market_match`, `fast_sell`, and `profit`.
- `build_pricing_decision()` keeps source price when data is missing or
  confidence is below the configured threshold.

`Platform/Putnam_OS/System/MarketIntelligence/Pricing/pricing_models.py`

- `PricingDecision` keeps `original_price`, `market_value`,
  `recommended_price`, accepted-comp count, confidence, strategy, basis, and
  review status.
- This is the closest current representation of separate market value and
  recommendation, but it lacks evidence records, override history, and the
  approved tiered approval policy.

### Embedded and legacy rules

`Platform/Putnam_OS/System/app/putnam_os.py`

- `optimized_export_price()` contains the legacy cart-sweetener ladder.
- `calculate_market_value()` and `apply_pricing_strategy()` duplicate the
  integrated package functions.
- `prepare_listing_export_rows()` calls the integrated
  `build_pricing_decision()` and writes review metadata.
- `validate_export_price_floor()` enforces the `$0.99` floor.

`Platform/Putnam_OS/System/app/bulk_price_engine.py`

- `load_ladder()`, `apply_ladder()`, `preview_file()`, and `run_revision()`
  implement exact-price ladder revisions and rollback output.

`Platform/Putnam_OS/System/app/main.py`

- `load_rules()`, `normalized_ladder()`, and `apply_existing_ladder()` contain
  another legacy implementation.

Conflicting configuration files:

- `Platform/Putnam_OS/System/config/pricing_rules.json`
- `Platform/Putnam_OS/config/pricing_ladder.json`
- `Platform/Putnam_OS/System/config/pricing_ladder.json`

They contain similar ladders with different versions and field names.

## 3. Inventory Records

`Platform/Putnam_OS/System/app/inventory_reconciliation.py`

- `InventoryCandidate` is the broadest normalized inventory record currently
  present. It contains CardVector inventory ID/status, acquisition lot ID,
  ETB/location, title/card fields, condition, quantity, price, CardUploader
  IDs, eBay IDs, source provider/file, import timestamp, and row hash.
- `CardUploaderInventorySource.load()` and `EbayActiveListingsSource.load()`
  normalize source CSV rows.
- `SourceImport`, `MatchResult`, `reconcile()`, and `write_report()` provide a
  report-only reconciliation pipeline.
- No database repository persists `InventoryCandidate` objects.

Operational data sources include:

- `Data/Imports/CardUploader_Inventory/inventory-2026-06-28.csv`
- `Data/Exports/carduploader_inventory_snapshot.csv`
- `Data/Exports/Reconciliation/*.csv`
- `Data/Exports/Reconciliation/*.json`

`Platform/Putnam_OS/System/app/inventory_locations.py` and
`Data/Config/etb_location_registry.json` own storage-location state, not
per-card price records.

Direct reuse: `InventoryCandidate` field vocabulary and the source adapters.

## 4. Card And Product Identity Records

`Platform/Marketplace_Intelligence/marketplace_intelligence/models.py`

- `Listing` is the canonical normalized listing input. It includes marketplace
  item ID, title, current price, SKU, condition, set, card number, variant,
  finish, TCG, TCGplayer product/SKU, catalog SKU, and source data.
- `ListingIdentity` stores lookup key, match method, confidence, and details.

`Platform/Marketplace_Intelligence/marketplace_intelligence/listing_parser.py`

- `ListingMatcher.identify()` prefers SKU, then item specifics, then
  conservative title normalization.
- It adapts known identity; it does not perform card recognition.

`Platform/Putnam_OS/System/MarketIntelligence/Identity/identity_translator.py`

- `CardUploaderIdentity` stores CardUploader-provided card identity.
- `IdentityTranslator.tcgtracking()` and `.ebay()` translate that identity into
  provider-specific query formats.
- Its docstring explicitly prohibits card identification.

Direct reuse: normalized `Listing`, `ListingIdentity`, and identity translation.

## 5. Acquisition Cost And Provenance

`Platform/Putnam_OS/System/app/putnam_os.py`

- `default_acquisition_record()`, `create_acquisition()`, `load_acquisition()`,
  `save_acquisition()`, and `list_acquisitions()` manage JSON records.
- `acquisition_snapshot()` attaches acquisition ID/name and purchase-price
  snapshot to a session.
- `record_import_acquisition_metadata()` and
  `write_acquisition_job_metadata()` attach optional acquisition information
  to imports and pricing jobs.

Storage:

- `Platform/Putnam_OS/System/data/acquisitions/records/ACQ-*.json`
- `Platform/Putnam_OS/System/data/acquisitions/current_acquisition.json`

Existing records support purchase price, source, seller, platform, notes,
status, and work-session/import/pricing-job associations. Acquisition selection
is optional.

Missing:

- Explicit `acquisition_method`.
- Explicit acquisition-cost confidence.
- Per-listing allocation of lot cost.
- A Price Vector input contract for acquisition provenance.

## 6. Marketplace Accounts And Marketplace-Specific Settings

`Platform/Putnam_OS/System/config/ebay_business_policies.json`

- Stores configured eBay shipping, payment, and return policy names.

`Platform/Putnam_OS/System/config/putnam_os_config.json`

- Supports CardUploader, mobile capture, eBay Seller Hub, and eBay upload URLs,
  plus integrated pricing strategy/confidence thresholds.
- A pre-existing uncommitted change to this file was present during the audit
  and was not modified.

`Platform/Marketplace_Intelligence/config/market_provider.json`

- Selects provider adapters and local source paths.

`Platform/Marketplace_Intelligence/config/source_profiles/*.json`

- Maps eBay, CardUploader, and custom CSV columns into normalized listings.

`Data/Config/fulfillment_profiles.json`

- Stores packaging-cost foundations. It is explicitly not connected to current
  profit calculations.

There is no marketplace-account model, credential repository, TCGplayer seller
configuration, or Whatnot/direct-site activation state. No secrets are stored
by the pricing engine.

## 7. Market-Price Data And External Providers

`Platform/Marketplace_Intelligence/marketplace_intelligence/providers.py`

- `MarketProvider` is the reusable provider interface.
- `CardUploaderInventoryProvider` uses local CardUploader/export prices.
- `CardUploaderSalesCacheProvider` reads cached CardUploader/eBay sold results,
  rejects graded and non-single-card titles, requires accepted comps, calculates
  a median, and emits confidence/comp metadata.
- `TCGtrackingProvider` reads a local JSON/CSV export and is reference-only by
  default.
- `CompositeProvider` chooses the first actionable match while retaining
  reference-only context.
- `NullProvider` safely represents no configured provider.
- `build_provider()` constructs providers from JSON configuration.

Stored evidence and fixtures:

- `Platform/Putnam_OS/System/data/market_cache/carduploader_sales_*.json`
- `Platform/Marketplace_Intelligence/examples/tcgtracking_prices_sample.json`
- `Platform/Marketplace_Intelligence/examples/ebay_active_listings_sample.csv`
- `Platform/Marketplace_Intelligence/examples/carduploader_export_sample.csv`

`Platform/Putnam_OS/System/MarketIntelligence/Models/market_snapshot.py`

- `MarketSnapshot` groups facts under `sold`, `ebay_active`, `tcgtracking`, and
  `internal_history`.

`Platform/Putnam_OS/System/MarketIntelligence/Models/market_intelligence_report.py`

- `MarketIntelligenceReport` and `build_market_report()` summarize provider
  presence and confidence.

Important limitations:

- No live TCGplayer, eBay sold, Card Ladder, or Alt client exists.
- Cached eBay comparable filtering does not enforce an explicit
  condition-to-condition equality check.
- TCGtracking is not equivalent to a verified TCGplayer recent-sales feed.
- Active eBay listings are imported as listings, not implemented as a
  competition-evidence provider.
- No PriceCharting provider or usage was found.

## 8. Price Recommendations

`Platform/Marketplace_Intelligence/marketplace_intelligence/models.py`

- `MarketPrice` stores matched value, provider, source, confidence, reason, and
  metadata.
- `PriceRecommendation` stores recommended price, difference, percent change,
  pricing reason, and review fields.
- `Decision` stores `No Change`, `Increase`, `Decrease`, or `Review`.
- `AnalysisResult` joins listing, identity, market, pricing, and decision.

`Platform/Marketplace_Intelligence/marketplace_intelligence/engine.py`

- `MarketplaceIntelligenceEngine` orchestrates import, identity, provider,
  pricing, decision, and report output.

`Platform/Marketplace_Intelligence/marketplace_intelligence/reports.py`

- `result_row()` exposes current price, market price/source/confidence,
  accepted/rejected comps, recommendation, and reasoning.
- `write_reports()` creates analysis, changed-only, validation, recommendation,
  and summary reports.

`Platform/Marketplace_Intelligence/marketplace_intelligence/bulk_export.py`

- `bulk_revise_rows()` and `write_bulk_revise_csv()` emit changed-only eBay
  revision rows.

Reusable foundation: orchestration, result joins, report generation, and
changed-only export.

## 9. Approval And Review Workflows

`Platform/Marketplace_Intelligence/marketplace_intelligence/decision_engine.py`

- `DecisionEngine.decide()` routes unmatched, reference-only, or
  threshold-triggered results to `Review`.
- It otherwise labels price direction or no change.

`Platform/Marketplace_Intelligence/marketplace_intelligence/pricing_engine.py`

- `review_check()` uses configurable absolute-price and percentage-change
  thresholds.
- It does not implement the approved under-$5, $5-$20, and over-$20 matrix.

`Platform/Putnam_OS/System/MarketIntelligence/Pricing/pricing_engine.py`

- `build_pricing_decision()` uses confidence thresholds of 60/80 by default.
- It does not vary approval by recommended-price tier.

`Platform/Putnam_OS/System/app/putnam_os.py`

- `prepare_listing_export_rows()` writes review status into
  `optimization_review.csv`.
- `audit_new_listing()` requires shipping-policy and final-summary
  confirmation before writing output.
- `PutnamOS.pricing_page()`, `auto_run()`, `finish_pricing_success()`, and
  `finish_pricing_failure()` implement the current desktop review/export flow.

There is no internal quality-review state separate from marketplace condition.

## 10. Manual Price Overrides

No durable Price Vector manual-price override model or workflow was found.

The repository contains unrelated uses of the word `override`, such as CSV
source-type override, OBS password override, and batch-location override. None
preserve an original recommendation, final listing price, override reason,
operator, and timestamp as one pricing record.

## 11. Database Models, Migrations, And Repositories

No pricing database, pricing ORM model, or pricing repository was found.

Existing Supabase migrations are limited to mobile capture and location
management:

- `supabase/migrations/20260713153000_mobile_capture.sql`
- `supabase/migrations/20260713170000_mobile_capture_authenticated_grants.sql`
- `supabase/migrations/20260716090000_mobile_capture_type.sql`
- `supabase/migrations/20260716130000_mobile_location_registry.sql`

Existing tables include `mobile_capture_sessions`, `mobile_capture_images`,
`cardvector_location_operators`, `cardvector_etbs`, and
`cardvector_locations`. None stores pricing recommendations or overrides.

Current pricing persistence is:

- JSON configuration.
- Local market-cache JSON.
- CSV analysis/review/export reports.
- TXT summaries.
- CSV performance and export-history logs.

## 12. Pricing API, Services, UI, And CLI

### Services

- `Platform/Marketplace_Intelligence/marketplace_intelligence/engine.py`:
  `MarketplaceIntelligenceEngine`.
- `Platform/Marketplace_Intelligence/marketplace_intelligence/pricing_engine.py`:
  `PricingEngine`.
- `Platform/Marketplace_Intelligence/marketplace_intelligence/decision_engine.py`:
  `DecisionEngine`.
- `Platform/Marketplace_Intelligence/marketplace_intelligence/providers.py`:
  provider services.

### Desktop UI

`Platform/Marketplace_Intelligence/marketplace_intelligence/ui.py`

- `MarketplaceIntelligenceApp` is the standalone pricing desktop application.
- Relevant methods: `browse()`, `analyze()`, `_analyze_worker()`,
  `display_result()`, `populate_tree()`, `profile_from_settings()`,
  `apply_pricing_settings()`, and `save_pricing_settings()`.

`Platform/Putnam_OS/System/app/putnam_os.py`

- `PutnamOS.processing_page()` is the production CardVector OS handoff.
- `PutnamOS.pricing_page()` remains a compatibility view.
- Pricing execution and review methods include `load()`, `auto_run()`,
  `update_pricing_progress()`, `set_pricing_busy()`,
  `finish_pricing_success()`, `finish_pricing_failure()`,
  `open_pricing_report()`, and `open_current_output_folder()`.

### CLI

- `Platform/Marketplace_Intelligence/marketplace_intelligence/cli.py`:
  `build_parser()` and `main()`.
- `Platform/Marketplace_Intelligence/run_marketplace_intelligence.py`:
  standalone launcher.
- `Platform/Putnam_OS/System/app/run_pricing_cli.py`:
  legacy ladder preview/revision CLI.

### API routes

No HTTP API routes associated with pricing were found.

## 13. Tests And Fixtures

Pricing-specific tests:

- `Platform/Marketplace_Intelligence/tests/test_marketplace_intelligence_v1.py`
  exercises eBay, CardUploader, custom CSV, provider priority, reports, bulk
  export, analysis-only mode, and shipping adjustment.
- `Platform/Putnam_OS/System/MarketIntelligence/Pricing/test_pricing_engine.py`
  verifies weighted market value and integrated recommendation status.
- `Platform/Putnam_OS/System/app/test_listing_optimizer_v1_2.py` checks the
  older low-price ladder, confirmations, output columns, SKU/location, and
  export logging.
- `Platform/Putnam_OS/System/app/test_ebay_policy_config.py` checks required
  policy validation and policy-column population.

Relevant source fixtures:

- `Platform/Marketplace_Intelligence/examples/ebay_active_listings_sample.csv`
- `Platform/Marketplace_Intelligence/examples/carduploader_export_sample.csv`
- `Platform/Marketplace_Intelligence/examples/custom_listing_sample.csv`
- `Platform/Marketplace_Intelligence/examples/tcgtracking_prices_sample.json`
- `Platform/Putnam_OS/System/data/market_cache/carduploader_sales_*.json`

No tests currently cover:

- A first-class FMV input contract.
- Competitive Turnover.
- The approved value-tier approval matrix.
- Internal quality review over `$20`.
- Acquisition method/cost confidence.
- Manual override preservation.
- A guarantee that Price Vector never calls a provider directly.

## Duplicate And Conflicting Pricing Logic

| Overlap | Files | Impact |
| --- | --- | --- |
| Reusable recommendation calculator | Standalone `pricing_engine.py` versus Putnam OS MarketIntelligence `pricing_engine.py` | Different models, strategies, thresholds, and ownership. |
| Market-value calculation | Putnam OS MarketIntelligence `calculate_market_value()` and duplicate in `putnam_os.py` | Same weighted formula exists twice. |
| Low-price business rules | `optimized_export_price()`, `bulk_price_engine.py`, `main.py`, and three ladder JSON files | Multiple rule sources can produce different output. |
| Review policy | Standalone price/change thresholds, integrated confidence thresholds, and high-value JSON fields | No single approved policy implementation. |
| Business profile | Standalone and Putnam OS JSON/loaders | Schemas and defaults do not agree. |
| Decision terminology | Standalone listing Decision Engine and Putnam OS portfolio Decision Engine | Same class name, unrelated responsibilities. |

## Automated Test Results

The bundled Python runtime was used:

`C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`

### Combined unittest run

Command:

```powershell
python -m unittest Platform.Putnam_OS.System.tools.test_mobile_capture_queue Tools.test_mobile_capture_supabase_contract Tools.test_mobile_location_contract Tools.test_public_storefront_contract
```

Result: **65 tests run, 64 passed, 1 failed**.

Existing failure:
`Tools.test_mobile_location_contract.MobileLocationDatabaseContractTests.test_etb_and_no_qr_flows_preserve_capture_type_and_canonical_location`
still expects the pre-photo-mode
`captureRoute(state.etbId, state.location, state.captureType)` signature.

### Pricing and desktop smoke tests

| Command | Result |
| --- | --- |
| `python Platform/Marketplace_Intelligence/tests/test_marketplace_intelligence_v1.py` | Passed. |
| `python -m Platform.Putnam_OS.System.MarketIntelligence.Pricing.test_pricing_engine` | Passed. |
| `python Platform/Putnam_OS/System/app/test_desktop_workflow_ui.py` | 5 tests passed. |
| `python Platform/Putnam_OS/System/app/test_mobile_capture_thumbnail_pairs.py` | 3 tests passed. |
| `python Platform/Putnam_OS/System/app/test_workflow_context.py` | 3 tests passed. |
| `python Platform/Putnam_OS/System/app/test_auto_capture_v2_1.py` | Passed. |
| `python Platform/Putnam_OS/System/app/test_capture_studio_v1.py` | Passed. |
| `python Platform/Putnam_OS/System/app/test_obs_connection_manager_v1.py` | Passed. |
| `python Platform/Putnam_OS/System/app/test_orders_v1.py` | Passed. |
| `python Platform/Putnam_OS/System/app/test_ebay_policy_config.py` | Passed. |
| `python Platform/Putnam_OS/System/app/test_inventory_audit_mode_v1_0.py` | Failed before assertions because Windows/OneDrive denied removal of the existing `test_artifacts/inventory_audit_v1_0/audit_images` directory. |
| `python Platform/Putnam_OS/System/app/test_listing_optimizer_v1_2.py` | Failed at `changes == 7`; current integrated no-market behavior retained more source prices than the stale ladder expectation. |
| `python -m compileall -q Platform/Marketplace_Intelligence Platform/Putnam_OS/System/MarketIntelligence Platform/Putnam_OS/System/decision_engine` | Passed. |
| `node --check Docs/app.js` | Passed. |

A preliminary direct-file execution of
`Platform/Putnam_OS/System/MarketIntelligence/Pricing/test_pricing_engine.py`
failed to import `Platform`; running the same test as a module passed.

All tracked test-generated state was restored after testing. The pre-existing
`Platform/Putnam_OS/System/config/putnam_os_config.json` modification was left
untouched.
