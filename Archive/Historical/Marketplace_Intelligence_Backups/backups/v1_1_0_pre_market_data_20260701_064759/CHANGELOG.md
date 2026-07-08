# Changelog

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
