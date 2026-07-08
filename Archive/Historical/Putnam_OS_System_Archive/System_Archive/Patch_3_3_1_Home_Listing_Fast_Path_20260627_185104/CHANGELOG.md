# Changelog

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
