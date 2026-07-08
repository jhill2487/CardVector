# Changelog

## v3.5.6 - Production Workflow Hardening
- Added local eBay business policy config at Platform/Putnam_OS/System/config/ebay_business_policies.json with shipping_policy, payment_policy, and return_policy.
- Added Settings fields for saving eBay business policy names.
- eBay export now stamps configured shipping, payment, and return policy names instead of using hard-coded export logic.
- eBay export now stops before writing a CSV if any required business policy value is missing.
- Aligned the standalone Listing Optimizer support tool with the same eBay business policy config and preflight.
- Added Capture Studio Capture Next Photo to automatically alternate front/back pairs while preserving manual Capture Front and Capture Back buttons.
- Reordered main navigation to put the production workflow first: Capture, Import, Pricing, Inventory, Orders.
- Added Run Putnam OS Production.vbs to launch Putnam OS through pyw.exe without a visible console.
- Updated Putnam OS displayed and metadata version to v3.5.6.

## v3.5.5 - obsws-python Positional Screenshot Fix
- Updated Capture Studio to call ReqClient.get_source_screenshot using the installed obsws-python positional signature: name, img_format, width, height, quality.
- Removed screenshot keyword arguments from the active Capture Studio path to avoid source_name / sourceName keyword errors.
- Confirmed Capture Studio has no idle OBS status polling timer; OBS reconnects occur only on user-triggered status checks or capture actions.
- Updated Putnam OS displayed and metadata version to v3.5.5.

## v3.5.4 - obsws-python Screenshot Argument Fix
- Removed the camelCase get_source_screenshot fallback from Capture Studio so obsws-python only receives snake_case arguments: source_name, image_format, and image_compression_quality.
- Added smoke coverage to fail if Capture Studio sends camelCase screenshot arguments such as sourceName, imageFormat, or imageCompressionQuality.
- Updated Putnam OS displayed and metadata version to v3.5.4.

## v3.5.3 - Capture Studio Screenshot Path Fix
- Consolidated Capture Studio OBS client creation so OBS Status, Capture Front, and Capture Back use the same OBS host, port, password, and client setup path.
- Updated Capture Studio screenshot capture to use the current OBS program scene detected through the same OBS client path.
- Replaced the generic Capture Studio capture failure with Failed to capture screenshot plus the actual OBS exception.
- Updated Putnam OS displayed and metadata version to v3.5.3.

## v3.5.2 - Local OBS Config Fix
- Added local Putnam OS OBS WebSocket config at Platform/Putnam_OS/System/config/obs_config.json with exact keys obs.host, obs.port, and obs.password.
- Added a minimal Settings tab OBS WebSocket section so the OBS password can be saved once without editing source code.
- Updated Capture Studio to read the local Putnam OS OBS config before connecting to OBS, while still allowing PUTNAM_OBS_PASSWORD to override the saved password.
- Updated Putnam OS displayed and metadata version to v3.5.2.

## v3.5.1 - Capture Studio OBS Auth Validation Fix
- Fixed Capture Studio OBS WebSocket authentication by loading the configured OBS password from capture settings or `PUTNAM_OBS_PASSWORD` and passing it into `obsws_python.ReqClient`.
- Added clear OBS status outcomes for connected, auth missing, auth failed, and OBS unavailable states.
- Updated inactive Capture Studio session display so current card number shows `-` instead of `1`.
- Updated Putnam OS displayed and metadata version to v3.5.1.

## v3.5.0 - Baseline Workflow Testing Release
- Established the current Putnam OS build as the baseline workflow testing release.
- Included Capture Studio v1 for front/back card photo capture.
- Included Import Module v1 for CardUploader CSV import and handoff to Listings/Pricing.
- Included Listing Workflow Polish with visible workflow stages, handled busy-state cleanup, $0.99 minimum fixed-price export floor, and pricing performance logging.
- Included Orders / Pick Slip v1 for eBay orders CSV import and printable pick slips.
- Included Inventory Location Foundation for ETB container registry and printable ETB labels.
- Updated Putnam OS displayed and metadata version to v3.5.0.
- No new workflow functionality was added in this release checkpoint beyond versioning, metadata, and release documentation.

## v3.4.1 - Inventory Audit v2
- Added quick location assignment inside Inventory Audit Mode.
- Added audit statuses for Pending, Confirmed, Needs Review, Missing, and Location Updated.
- Added resumable audit session files under Data/Logs/inventory_audit_sessions.
- Added location update logging at Data/Logs/location_update_log.csv.
- Added audit event logging at Data/Logs/inventory_audit_event_log.csv.
- Added Save Progress, Resume Audit, Start New Audit, and Audit Progress UI labels.
- Updated Inventory Audit pause/completion summaries to include status counts and session save path.
- Preserved existing pricing rules, eBay export logic, and confirmed-only bulk revise behavior.

## v3.4.0 - Workflow Confidence and Cart Sweetener Floor
- Retired the legacy $0.89 cart sweetener export floor.
- Updated Listing Optimizer pricing so no fixed-price eBay export is below $0.99.
- Added progress feedback and pricing performance telemetry for Listing Optimizer runs.
- Added fulfillment profile config foundation for future Profit per Envelope reporting.
- Documented analytics, promotion, offer, bulk-sales, and module-completeness backlog items.

## v3.3.6 - Inventory Audit Mode v1.0
- Added Inventory Audit Mode inside the existing Putnam OS Inventory workspace.
- Added source-agnostic inventory normalization with v1.0 support for eBay Active Listings reports.
- Added persistent audit sessions, resume support, audit event history, and internal verification image attachment.
- Added audit actions: Confirm, Already Correct, Missing Card, Needs Review, Skip, Next, and Previous.
- Added reports: inventory_location_audit.csv, inventory_location_summary.txt, and ebay_bulk_revise_location_confirmed.csv.
- Bulk revise output includes confirmed rows only; missing, needs-review, skipped, and already-correct rows are excluded.
- Reused Capture Studio as an optional internal verification-image source without OCR, scanner identification, CardUploader recognition, or eBay modification.

## v3.3.5 - Embedded Batch Location Management
- Added shared batch location registry for the rule `User SKU = Batch Location`.
- Embedded game/location prompts into Putnam OS work-session intake instead of creating a separate Location Manager tab.
- Listing Optimizer export now suggests batch locations from the registry, allows override, validates ETB format, and records successful export locations.
- SKU Repair Planner now uses registry suggestions for game-specific repair planning while preserving `CS-*` identifiers.
- Seller audit reports now include location audit and location registry summary outputs.

## v3.3.4 - Listing Optimizer v1.2
- Added required batch/location prompt before eBay-ready CSV export.
- Added shipping policy confirmation for Buyer Pays Shipping and Free Shipping on 3+ Cards promotion.
- Added Decimal-based pricing optimizer, now superseded by the v3.4.0 $0.99 cart-sweetener floor.
- Added cart_sweetener internal review tagging for low-value cart-sweetener listings.
- Added final export summary confirmation before writing CSV output.
- Added success-only export history at logs/export_history.csv.
- Preserved eBay upload CSV columns while writing internal optimization review details separately.

## v3.3.3 - Decision Engine Framework
- Added read-only Decision Engine framework under System\decision_engine.
- Added Recommendation model and module interface for future recommendation modules.
- Added production modules for pricing summary awareness, CardUploader inventory snapshot reading, and default marketplace.
- Added placeholder modules for promotion, velocity, market signals, and content.
- Added business_profile.json config with cash-flow/profit goals and low-risk defaults.
- Added Home Decision Engine status panel and Run Decision Engine Check button.
- Decision Engine checks generate logs under System\logs.
- Did not change pricing CSV output, market intelligence logic, inventory adapter behavior, or capture module.

## v3.3.2 - CardUploader Inventory Adapter
- Added Home quick action: Import CardUploader Inventory Export.
- Accepts CardUploader inventory CSV exports as the operational inventory source.
- Writes lightweight inventory snapshot to System\data\carduploader_inventory_snapshot.csv.
- Copies original inventory exports to Imports\CardUploader_Inventory without deleting originals.
- Generates Inventory_Import reports with row totals, listed value, TCG/status counts, duplicate IDs/SKUs, and repeated-card summaries.
- Added Home folder buttons for Collectr, Imports, and Inventory Snapshot.
- Did not add a new inventory database or change pricing logic.

## v3.3.1 - Home Listing Fast Path
- Added Home quick action: Analyze Latest CardUploader Export.
- Searches Imports, Putnam_OS Incoming Files, and Downloads for the newest preferred CSV export.
- Added Home drop zone labeled Drop CardUploader CSV Here.
- Added Home quick folder buttons for Imports, Exports, Completed Jobs, and Work Sessions.
- Routes completed job folders to Putnam_OS\Completed Jobs while copying eBay-ready exports to Exports.
- Copies source CSVs into Imports\Processed without deleting originals.
- Integrated canonical root folders created by Audit_And_Clean_Root.ps1.
- Kept the existing Pricing page workflow intact and added Home fast-path guidance.

## v2.5.0
- Moved market validation into the Putnam OS Pricing Workspace.
- Removed standalone prototype workflow from the user-facing release.
- Added Comparable Validation Engine output with rejected comparable reasons.
- Added explicit rejection rules for World Championship/deck variants and other non-comparable products.
- Preserved existing Pricing Workspace drag-and-drop workflow.

## 3.2.1 - Platform + Brand + Guided Pricing Patch
- Fixed canonical launcher to use USERENVIRONMENT and remove hard-coded user paths.
- Added Putnam Collectibles brand standard config under System\config.
- Applied dark navy/black, electric blue, and gold UI brand refresh.
- Reworked Pricing Workspace around one primary action: Analyze & Prepare eBay CSV.
- Kept Market Intelligence and Comparable Validation inside the Pricing workflow.
- Added persistent status ribbon with root/version/loaded-file diagnostics.
- Preserved existing data folders and backed up changed files to System_Archive.

## v3.3.0 - Platform Session Manager
- Added Work Sessions workspace inside Putnam OS.
- Added active session tracking with session JSON and notes.
- Added home-page quick actions for CSV analysis, work sessions, completed jobs, and video splitting.
- Added Putnam Platform tools folder integration.
- Added Split_Putnam_Work_Session.ps1 and Backup_Putnam_OS.ps1 platform tools.
- Maintained USERENVIRONMENT-based portability and no hard-coded user paths.
