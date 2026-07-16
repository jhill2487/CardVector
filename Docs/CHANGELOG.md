# Changelog

## CardVector Mobile Preview-Matched Camera Capture

### Fixed

- Live camera JPEGs now use the visible centered `object-fit: cover` source
  region instead of the wider full camera sensor frame.
- Added a non-captured 63:88 card-positioning guide and bounded 1800-pixel JPEG
  output at quality 0.90.
- Improved temporary thumbnail object-URL cleanup for larger capture sessions.

### Safety

- Photo Library images remain uncropped.
- Supabase authentication, authenticated Storage upload, capture types,
  IndexedDB recovery, queue processing, atomic claims, and desktop routing are
  unchanged.

## CardVector Mobile Capture Phase 2

### Added

- Added explicit mobile workflow selection for `NEW_CAPTURE` and `PHYSICAL_INVENTORY`.
- Added a dedicated mobile capture screen with rear-camera preview, custom shutter capture, IndexedDB draft staging, thumbnail removal, photo-library fallback, and Finish Session upload.
- Added a Supabase migration for the durable `mobile_capture_sessions.capture_type` contract.

### Changed

- Kept ETB/location QR pages as informational landing pages instead of opening camera capture automatically.
- `NEW_CAPTURE` sessions stage under `Capture/MM.DD.YY`; `PHYSICAL_INVENTORY` sessions stage under `Capture/Physical_Inventory_Conversion/MM.DD.YY`.
- Existing blank capture-type sessions default to `PHYSICAL_INVENTORY` for backward-compatible desktop staging.

### Safety

- Preserved authenticated Supabase Storage upload, private bucket behavior, desktop queue atomic claim/staging, and service-role key separation.

## CardVector OS Mobile Capture Queue

### Added

- Added a first-class `Capture Queue` workspace inside CardVector OS.
- Added desktop queue visibility for pending, processing, converted, failed, cancelled, and diagnostic Mobile Capture sessions.
- Added queue actions for refresh, conservative auto-refresh, process/stage, open local folder, launch Physical Inventory Conversion, mark complete, mark failed, and retry failed.
- Added a reusable Mobile Capture queue service layer around `Platform/Putnam_OS/System/tools/mobile_capture_queue.py`.

### Changed

- Extended the queue tool with status display models, sanitized errors, retry handling, local staged-folder lookup, and a `retry-failed` CLI command.
- Mobile Capture processing now surfaces multi-workstation claim state through the desktop UI while keeping atomic Supabase claim behavior.

### Safety

- No Mobile Capture frontend, Supabase schema, CardUploader recognition, marketplace, or eBay workflow behavior was redesigned.
- The desktop queue still uses `CARDVECTOR_SUPABASE_URL` and `CARDVECTOR_SUPABASE_SERVICE_ROLE_KEY`; service-role keys are not printed or stored in tracked config.
- Original cloud images are downloaded for staging and are never automatically deleted.

## CardVector Public Site Deployment Pipeline

### Added

- Added a controlled static-site export path from private `CardVector/Docs` to public `CardVector-site`.
- Added a cross-repository deployment workflow for `cardvector.app`.
- Added public artifact validation and generated deployment manifest support.

### Changed

- Replaced the invalid private-repository GitHub Pages workflow with deployment to the public Pages repository.
- Reconciled the live public Whatnot footer link and banner asset back into `CardVector/Docs`.

### Safety

- Public deployment uses an explicit file allowlist and excludes internal reference docs, reports, runtime data, business exports, Python code, and service-role secret references.
- `CardVector-site` is deployment output only; source edits remain in `CardVector/Docs`.

## CardVector Platform v1.2.2 - UI Foundation v1

### Changed

- Applied the approved CardVector UI foundation to the existing app shell.
- Standardized the dark professional theme, bronze accent, medium left sidebar, compact top toolbar, bottom status bar, shared outlined buttons, status dots, and table styling.
- Added shared button icon text, status indicator helpers, Treeview zebra striping, hover highlight, extended selection, and sort arrows.

### Safety

- Business logic, pricing logic, CardUploader integration behavior, eBay export behavior, and the validated production flow were not modified.

## CardVector Platform v1.2.1 - Shared OBS Connection Manager

### Added

- Added a reusable OBS WebSocket connection manager for CardVector Capture Studio.
- Centralized OBS connection state as connected, disconnected, reconnecting, or error.
- Added reconnect-safe request handling so status checks and screenshots share the same OBS client path.

### Changed

- Routed Capture Studio OBS status checks and screenshot capture through the shared connection manager.
- Separated passive OBS connection status from Auto Capture paused/running status in the existing UI status path.

### Safety

- Manual capture workflow remains unchanged.
- Pricing Engine logic, CardUploader integration behavior, inventory data, and eBay export logic were not modified.

## CardVector Platform v1.2.0 - Capture Studio v2.1 Automated OBS Capture

### Added

- Added production Auto Capture mode to CardVector Capture Studio.
- Added live OBS frame comparison, stability confirmation, duplicate lockout, and same-frame duplicate prevention.
- Added Manual/Auto capture mode selection, Pause/Resume/Stop controls, and clear Auto Capture status states.
- Added configurable Auto Capture settings stored at `Platform/Putnam_OS/System/config/auto_capture_settings.json`.
- Added automatic capture logging for lifecycle events, captures, OBS disconnect/reconnect, and capture errors.

### Safety

- Manual capture workflow remains available.
- Pricing Engine logic, CardUploader integration behavior, Platform Vision, inventory data, and eBay export logic were not modified.
- Auto Capture operates on live OBS frames and continues writing into the existing Capture Studio session structure.

## CardVector Platform v1.1.1 - Production UI Regression Fixes

### Fixed

- Hardened Capture Studio right-rail thumbnail loading so real session JPEGs display when readable.
- Changed the production Capture button label to `Capture`.
- Removed the Pricing tab `Fast Path` section.
- Removed the duplicate Pricing tab CSV drop zone so Import owns CardUploader CSV intake.
- Added safe Inventory Label Center exception handling and label generation logging.

### Safety

- Pricing Engine logic, Platform Vision, CardUploader integration behavior, OBS capture implementation, eBay export logic, and inventory data were not modified.

## CardVector Platform v1.1.0 - Production Workflow + Inventory Label Center

### Added

- Added Inventory Label Center v1 for production ETB/location QR PDF labels.
- Added production Capture Studio right preview rail with recent front/back pair thumbnails and larger preview.
- Added passive OBS connection indicator with Retry only when disconnected.

### Changed

- Simplified Capture Studio v2 production workflow to one capture action: `Capture Next Card`.
- Removed manual front/back capture controls, manual OBS launch/status controls, and visible development scope text from production UI.
- Updated CardVector OS version metadata to `v1.1.0`.

### Safety

- The locked CardVector Platform architecture was preserved.
- Pricing Engine and Platform Vision were not modified.
- CardUploader remains the recognition source.
- Inventory Label Center writes PDF exports only and does not modify inventory data.

## CardVector OS Inventory Label Generator v1

### Added

- Added printable ETB/storage-location PDF label generator at `Platform/Putnam_OS/System/tools/generate_etb_qr_labels.py`.
- Added QR identity format using `https://cardvector.app/`.
- Added fallback CSV template at `Platform/Putnam_OS/System/tools/sample_etb_locations.csv`.
- Labels output to `Data/Exports/Labels/`.

### Safety

- Reads existing location registries or fallback CSV only.
- Does not modify inventory data.

## CardVector Pricing Engine v1.2 - Universal Intake + Source Profiles

### Added

- Added universal CSV intake for eBay Active Listings CSV, CardUploader Export CSV, and custom CSV source profiles.
- Added normalized Listing model fields for source type, source file, row number, title, SKU, item ID, current price, quantity, condition, set, card number, rarity, variant, finish, TCG, TCGplayer IDs, catalog SKU, status, and raw row.
- Added source-appropriate reports: eBay changed-only bulk revise export; CardUploader/custom validation and recommendation reports only.

### Safety

- Extended the existing CardVector Pricing Engine / Marketplace Intelligence path; no duplicate pricing engine or decision system was created.
- Source CSVs remain read-only.
- CardUploader/custom modes do not generate eBay bulk revise CSVs.

## CardVector Platform v1.0

### Added

- Established CardVector Platform branding while preserving Putnam Collectibles as the operating business.
- Added root `PLATFORM_VISION.md` as the stable platform vision document.
- Locked CardVector architecture and platform vision effective 2026-07-01, including product ownership questions for future feature design.
- Locked the normalized listing pipeline: CSV input, source detection, adapter mapping, normalized listing, existing Pricing Engine, reports, and source-appropriate export.
- Promoted Capture Studio to CardVector Capture Studio v2 with session metadata, front/back pairing state, scrollable recent-image filmstrip, and workflow status badges.
- Added platform responsibility guidance: Capture Studio captures, Pricing Engine prices, CardVector OS orchestrates, and CardUploader performs recognition.

### Changed

- Visible application branding now presents `CardVector OS v1.0.0`.
- Documentation now describes CardVector Platform, CardVector Capture Studio, CardVector Pricing Engine, CardVector OS, future Mobile, and future Cloud.
- Putnam Scanner is documented as Legacy Scanner Research.

### Safety

- Putnam Collectibles remains the business name.
- Existing Capture, Import, Pricing, Inventory, guided workflow, and CardUploader integration behavior is preserved.

## Putnam OS v4.1.0

### Added

- Added Acquisition Data During Intake milestone.
- Added acquisition JSON records under `Platform/Putnam_OS/System/data/acquisitions`.
- Added acquisition panels to Home, Import, and Pricing & Decisions.
- Added acquisition snapshots on work sessions, capture sessions, imports, and pricing job reports.
- Added future break-even placeholder fields without enabling revenue/order tracking.

### Safety

- Acquisition selection is optional.
- Existing capture, import, pricing, and eBay CSV column behavior is preserved.

## Marketplace Intelligence v1.1.0

### Added

- Added composite market provider support with CardUploader inventory/export prices, CardUploader/eBay sales-cache comps, and TCGtracking reference data.
- Added report evidence fields for market source, confidence, reference-only status, accepted comps, rejected comps, and pricing reason.
- Added conservative active-listing title identity parsing for rows without card-specific columns.

### Changed

- Marketplace Intelligence now prefers CardUploader evidence for actionable eBay repricing recommendations.
- TCGtracking remains reference-only by default so TCGplayer-style data does not directly create eBay bulk revise rows.

### Safety

- Reference-only data and unmatched listings are held for review and excluded from changed-only bulk revise exports.

## Marketplace Intelligence v1.0.2

### Added

- Added desktop Pricing Settings inputs for minimum price, ignored small changes, max increase percent, max decrease percent, shipping assumption, and flat shipping cost.
- Added Save Pricing Profile action that writes settings to `config/pricing_profile.json`.

### Changed

- Seller-paid shipping can now add the configured flat shipping cost into the pricing recommendation basis.
- Buyer-paid shipping remains unadjusted; mixed shipping remains conservative with no automatic shipping adjustment.

## Marketplace Intelligence v1.0.1

### Changed

- Polished the standalone desktop UI appearance with a stronger header, card-based layout, clearer primary action styling, improved spacing, styled review table, status bar, and recommendation row highlighting.
- No engine, pricing, report, or export behavior changed.

## Marketplace Intelligence v1.0.0

### Added

- Added standalone Marketplace Intelligence desktop application and reusable Python engine.
- Added eBay Active Listings CSV import, modular listing matching, local TCGtracking-style provider adapter, configurable pricing engine, separate decision engine, reports, and changed-only eBay bulk revise export.
- Added Analysis Only beta mode, sample config, sample CSV, README, launcher, and smoke test.

### Safety

- Marketplace Intelligence has no Putnam OS inventory dependency, performs no automatic uploads, and never modifies source CSV files.

## Putnam OS v4.0.0

### Added

- Added centralized UI design tokens and shared style helpers for Putnam OS.
- Added `Platform/Putnam_OS/System/app/UI_STYLE_GUIDE.md` as the UI lock developer note.

### Changed

- Polished Putnam OS typography, sidebar navigation, panels, cards, buttons, drop zones, and action rows.
- Made primary actions visually consistent while preserving existing Capture, Import, Pricing, and eBay export behavior.
- Updated Putnam OS displayed and metadata version to `v4.0.0`.

### Fixed

- Reduced sidebar duplicate-label feel by making section headers and nav items visually distinct.
- Added a horizontally scrollable quick-actions bar to prevent clipped quick-action buttons.

## Putnam OS v3.6.0

### Added

- Added Mission Control Home dashboard for guided daily workflow status and next actions.
- Added CardUploader URL setting plus Open CardUploader actions.
- Added Capture Review foundation and Inventory ETB rollups from completed sessions.
- Added `tools/validate_production_startup.py` startup validation with reports under Putnam OS Startup Logs.

### Changed

- Reorganized Putnam OS navigation into workflow sections with Home first and Shipping immediately after Orders.
- Unified the Import workflow and renamed the active pricing screen to `Pricing & Decisions`.
- Marked the legacy Listing Optimizer as retired from the active operator workflow in favor of CardUploader plus Putnam OS guidance.
- Updated Putnam OS displayed and metadata version to `v3.6.0`.

### Fixed

- Improved Decision Engine panel wrapping and production launcher logging.

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
