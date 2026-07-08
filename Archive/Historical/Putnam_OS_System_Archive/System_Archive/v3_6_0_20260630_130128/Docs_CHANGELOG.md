# Changelog

## Putnam OS v3.5.6

### Added

- Added local eBay business policy config at `Platform/Putnam_OS/System/config/ebay_business_policies.json` with `shipping_policy`, `payment_policy`, and `return_policy`.
- Added Settings fields for saving eBay business policy names.
- Added Capture Studio `Capture Next Photo` to automatically alternate front/back pairs while preserving manual Capture Front and Capture Back buttons.
- Added `Run Putnam OS Production.vbs` to launch Putnam OS through `pyw.exe` without a visible console.

### Changed

- Reordered main navigation to put the production workflow first: Capture, Import, Pricing, Inventory, Orders.
- Updated Putnam OS displayed and metadata version to `v3.5.6`.

### Fixed

- eBay export now stamps configured shipping, payment, and return policy names instead of using hard-coded export logic.
- eBay export now stops before writing a CSV if any required business policy value is missing.
- Aligned the standalone Listing Optimizer support tool with the same eBay business policy config and preflight.

## Putnam OS v3.5.5

### Fixed

- Updated Capture Studio to call `ReqClient.get_source_screenshot` using the installed obsws-python positional signature: `(name, img_format, width, height, quality)`.
- Removed screenshot keyword arguments from the active Capture Studio path to avoid `source_name` / `sourceName` keyword errors.
- Confirmed Capture Studio has no idle OBS status polling timer; OBS reconnects occur only on user-triggered status checks or capture actions.

### Changed

- Updated Putnam OS displayed and metadata version to `v3.5.5`.

## Putnam OS v3.5.4

### Fixed

- Removed the camelCase `get_source_screenshot` fallback from Capture Studio so obsws-python only receives Python-style snake_case arguments: `source_name`, `image_format`, and `image_compression_quality`.
- Added smoke coverage to fail if Capture Studio sends camelCase screenshot arguments such as `sourceName`, `imageFormat`, or `imageCompressionQuality`.

### Changed

- Updated Putnam OS displayed and metadata version to `v3.5.4`.

## Putnam OS v3.5.3

### Fixed

- Consolidated Capture Studio OBS client creation so OBS Status, Capture Front, and Capture Back use the same OBS host, port, password, and client setup path.
- Updated Capture Studio screenshot capture to use the current OBS program scene detected through the same OBS client path.
- Replaced the generic Capture Studio capture failure with `Failed to capture screenshot:` plus the actual OBS exception.

### Changed

- Updated Putnam OS displayed and metadata version to `v3.5.3`.

## Putnam OS v3.5.2

### Added

- Added local Putnam OS OBS WebSocket config at `Platform/Putnam_OS/System/config/obs_config.json` with exact keys `obs.host`, `obs.port`, and `obs.password`.
- Added a minimal Settings tab OBS WebSocket section so the OBS password can be saved once without editing source code.

### Fixed

- Updated Capture Studio to read the local Putnam OS OBS config before connecting to OBS, while still allowing `PUTNAM_OBS_PASSWORD` to override the saved password.

### Changed

- Updated Putnam OS displayed and metadata version to `v3.5.2`.

## Putnam OS v3.5.1

### Fixed

- Fixed Capture Studio OBS WebSocket authentication by loading the configured OBS password from Putnam OS capture settings or `PUTNAM_OBS_PASSWORD` and passing it to `obsws_python.ReqClient`.
- Added clearer Capture Studio OBS status messages for connected, auth missing, auth failed, and OBS unavailable states.
- Updated inactive Capture Studio session display so current card number shows `-` instead of `1`.

### Changed

- Updated Putnam OS displayed and metadata version to `v3.5.1`.

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
