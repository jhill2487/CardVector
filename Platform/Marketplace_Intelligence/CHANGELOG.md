# Changelog

## v1.2.0 - CardVector Pricing Engine Universal Intake + Source Profiles

### Added

- Added universal CSV intake with source detection, adapter mapping, normalized listings, existing Pricing Engine analysis, reports, and source-appropriate exports.
- Added eBay Active Listings, CardUploader Export, and custom CSV adapter support.
- Added custom source profile JSON support under `config/source_profiles/`.
- Added CardUploader validation reports, underpriced candidate reports, and pricing recommendation CSV output.
- Added source type override support in CLI/UI.

### Changed

- Updated visible version to `v1.2.0`.
- Updated configurable minimum price in `config/pricing_profile.json` to `1.49`.
- eBay Active Listings mode continues to generate changed-only bulk revise CSVs.

### Safety

- Source CSVs are read only and never overwritten.
- CardUploader/custom modes do not generate eBay bulk revise CSVs.
- The existing pricing, provider, and decision engines are reused instead of duplicated.

## v1.1.0

### Added

- Added composite market provider support.
- Added actionable CardUploader inventory/export CSV price provider.
- Added CardUploader/eBay sales-cache provider with conservative comp validation.
- Added market source, market confidence, reference-only, accepted comp, rejected comp, and pricing reason fields to analysis reports.
- Added title identity parsing for active-listing rows that do not include card-specific columns.

### Changed

- Changed default market provider config to prefer CardUploader evidence first.
- Kept TCGtracking as reference-only by default so TCGplayer-style figures do not directly drive eBay repricing.
- Updated the desktop review table to show market source and confidence.

### Safety

- Reference-only market data can appear in analysis reports but cannot create changed bulk revise rows.
- Listings without usable market evidence remain review/unmatched.

## v1.0.2

### Added

- Added desktop Pricing Settings inputs for minimum price, ignored small changes, max increase percent, max decrease percent, shipping assumption, and flat shipping cost.
- Added Save Pricing Profile action that writes settings to `config/pricing_profile.json`.

### Changed

- Seller-paid shipping can now add the configured flat shipping cost into the pricing recommendation basis.
- Buyer-paid shipping remains unadjusted; mixed shipping remains conservative with no automatic shipping adjustment.

## v1.0.1

### Changed

- Polished the desktop UI with a stronger header, card-based layout, clearer primary action styling, improved spacing, styled review table, status bar, and recommendation row highlighting.
- No engine, pricing, report, or export behavior changed.

## v1.0.0

### Added

- Added standalone Marketplace Intelligence desktop application.
- Added reusable Python engine with separate CSV import, listing parser, market provider, pricing engine, decision engine, report generator, and bulk revise export layers.
- Added configurable pricing, business, and market-provider JSON profiles.
- Added local TCGtracking-style provider adapter.
- Added eBay Active Listings CSV import with column validation and listing count.
- Added changed-only review screen with filters.
- Added analysis report, changed listings report, analysis summary, and changed-only eBay bulk revise CSV export.
- Added Analysis Only mode that skips bulk revise CSV generation.
- Added README, launcher, sample config, sample CSV, sample market data, and smoke test.

### Safety

- No Putnam OS inventory dependency.
- No automatic uploads.
- No API login required.
- Source CSV files are never modified.
