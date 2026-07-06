# Changelog

## Putnam OS v3.5.0

### Added

- Established the current Putnam OS build as the baseline workflow testing release.
- Included Capture Studio v1 for front/back card photo capture.
- Included Import Module v1 for CardUploader CSV import and handoff to Listings/Pricing.
- Included Orders / Pick Slip v1 for eBay orders CSV import and printable pick slips.
- Included Inventory Location Foundation for ETB container registry and printable ETB labels.

### Changed

- Included Listing Workflow Polish: visible workflow stages, handled busy-state cleanup, $0.99 minimum fixed-price export floor, and pricing performance logging.
- Updated Putnam OS displayed and metadata version to `v3.5.0`.

### Known Issues

- This is a workflow testing baseline; full daily-production validation is still recommended before relying on every module for live operations.

## Putnam OS v3.4.1

### Added

- Added Inventory Audit v2 quick location assignment.
- Added resumable audit session files under `Data/Logs/inventory_audit_sessions/`.
- Added location update logging at `Data/Logs/location_update_log.csv`.
- Added audit event logging at `Data/Logs/inventory_audit_event_log.csv`.
- Added explicit audit statuses for Pending, Confirmed, Needs Review, Missing, and Location Updated.

### Changed

- Updated Inventory Audit UI labels and controls for faster audit work.
- Updated Putnam OS visible version to `v3.4.1`.

### Fixed

- Updated Latest eBay inventory source search to include `Business/eBay_Store_Items`.

### Known Issues

- Inventory Audit v2 updates session/report data only; it does not directly edit source inventory CSVs.
- Full manual UI testing is still recommended on the next live audit session.

## Putnam OS v3.4.0

### Added

- Added fulfillment profile config foundation at `Data/Config/fulfillment_profiles.json`.
- Added fulfillment profile documentation for future Profit per Envelope reporting.
- Added backlog records for Inventory Audit v2, Profit Dashboard, Bulk Sales Performance Report, Offer Analytics Dashboard, Promotion Performance Dashboard, and Module Completeness Pass.

### Changed

- Retired the legacy `$0.89` cart sweetener export rule.
- Updated the Listing Optimizer cart sweetener floor to `$0.99`.
- Updated Putnam OS visible version to `v3.4.0`.

### Fixed

- Aligned active pricing workflow docs with the eBay-safe `$0.99` minimum export price.

### Known Issues

- Fulfillment profiles are config-only and are not connected to live profit calculations yet.
- Profit, offer, promotion, and bulk sales dashboards remain backlog/planned items.

## Putnam OS v3.3.5

Initial tracked release.

Future releases should follow:

### Added

### Changed

### Fixed

### Known Issues
