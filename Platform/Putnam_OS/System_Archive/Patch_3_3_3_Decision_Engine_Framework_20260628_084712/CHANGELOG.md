# Changelog

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
