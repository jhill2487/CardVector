# CardVector Phase 0 Project Audit

Generated: 2026-07-06

Scope: inspection-only consolidation audit for `C:\Users\user\OneDrive\PutnamCollectibles`.

No files were moved, deleted, renamed, or refactored as part of this audit.

## Executive Summary

The repository has a mostly clear target structure:

- `Platform/` for applications and reusable code.
- `Business/` for operating files.
- `Data/` for imports, exports, logs, media, processed outputs, and generated data.
- `Docs/` for governance and project documentation.
- `Tools/` for standalone helper utilities.
- `Archive/` for old versions and historical experiments.
- `Work_Sessions/` for work-session records and temporary development notes.

The main consolidation issue is not the core application layout. It is root-level drift: one-off audit scripts, audit reports, old root folders, duplicate platform folders, and runtime media now sit beside the canonical folders. The highest-risk cleanup area is active-looking duplicate code in and near `Platform/Putnam_OS/System/app/`, especially old backup copies of `putnam_os.py`. Those should be compared and archived later, not deleted blindly.

The likely canonical source of truth for repository paths is `Platform/putnam_paths.py`. Older tools still use `USERENVIRONMENT` directly or refer to pre-reorganization folders. That is acceptable for legacy tools, but new code should use the path manager.

## Current Root Folder Map

| Root Item | Classification | Notes |
|---|---:|---|
| `.putnam_root` | Documentation / marker | Canonical root marker. Keep. |
| `AGENTS.md` | Documentation | Root stub pointing agents into `Docs/`. Keep. |
| `PLATFORM_VISION.md` | Documentation | Canonical platform vision. Keep at root unless governance changes. |
| `Platform/` | Application | Canonical application and reusable-code owner. |
| `Business/` | Business Operations | Canonical operating business files. |
| `Data/` | Data | Canonical generated data, imports, exports, logs, media, processed outputs. |
| `Docs/` | Documentation | Canonical governance/project documentation owner. |
| `Tools/` | Tools | Canonical standalone helper/tool folder. |
| `Archive/` | Archive | Historical code, backups, experiments, datasets. Do not flatten without review. |
| `Work_Sessions/` | Work Sessions | Work-session records and development artifacts. |
| `Capture/` | Data / Runtime | Active capture output. Treat as runtime data, not source. |
| `Putnam_Content/` | Business Operations | Content/media workflow. Consider whether this belongs under `Business/` later. |
| `Shared/` | Tools / Documentation / Templates | Shared templates/utilities. Needs owner decision. |
| `Collectr/` | Unknown / Needs Review | Present at root; purpose not clear from shallow inspection. Do not move yet. |
| `Putnam_Platform/` | Duplicate / Needs Review | Appears to overlap with `Platform/Putnam_Platform/`. |
| `Putnam_Seller_Tools/` | Duplicate / Needs Review | Appears to overlap with `Platform/Putnam_OS/Putnam_Seller_Tools/`. |
| `ScreenRecording_06-30-2026 14-42-57_1.MP4` | Runtime / Media | Large root-level media file. Should not be source. |
| `cardvector_*_auditor.py` and related `CARDVECTOR_*_REPORT.txt` | Work Sessions / Tools / Reports | Root-level audit artifacts from prior work. Likely candidates for archival after review. |
| `FOLDER_INSPECTION_Putnam_OS.txt` | Work Sessions / Report | Root-level inspection output. Likely archive candidate. |

## Likely Authoritative Entry Points

### CardVector OS

- Application script: `Platform/Putnam_OS/System/app/putnam_os.py`
- Production launcher: `Platform/Putnam_OS/Run CardVector OS Production.vbs`
- Legacy/alias launcher: `Platform/Putnam_OS/Run Putnam OS Production.vbs`
- Older batch launcher: `Platform/Putnam_OS/Run Putnam OS.bat`

### CardVector Capture / OBS Bridge

- Current Capture Studio service used by CardVector OS: `Platform/Putnam_OS/System/app/capture_studio.py`
- Shared OBS connection foundation: `Platform/Putnam_OS/System/app/obs_connection_manager.py`
- Older/separate capture tools: `Platform/Putnam_Platform/capture/Putnam_Capture.py`
- OBS autocrop bridge: `Platform/Putnam_Platform/capture/obs_capture_autocrop.py`

### Marketplace Intelligence

- Launcher script: `Platform/Marketplace_Intelligence/run_marketplace_intelligence.py`
- Batch launcher: `Platform/Marketplace_Intelligence/Run Marketplace Intelligence.bat`
- Package root: `Platform/Marketplace_Intelligence/marketplace_intelligence/`

### Seller Tools

- Likely canonical location: `Platform/Putnam_OS/Putnam_Seller_Tools/`
- Root duplicate location needing review: `Putnam_Seller_Tools/`

### Path Management

- Canonical path manager: `Platform/putnam_paths.py`

## Duplicate / Overlapping Files

High-count duplicate filenames were found. Many are intentional backups/checkpoints, but several are too close to active source to ignore.

### Active App Backups in Source Folder

These files live beside active app code in `Platform/Putnam_OS/System/app/`:

- `putnam_os_capture_v1_backup_20260629_212812.py`
- `putnam_os_comp_engine_v1_1_backup_20260629.py`
- `putnam_os_comp_ui_v1_2_0_backup_20260629.py`
- `putnam_os_import_v1_backup_20260629_222132.py`
- `putnam_os_inventory_location_foundation_backup_20260629_231122.py`
- `putnam_os_listing_workflow_backup_20260629_214810.py`
- `putnam_os_orders_v1_backup_20260629_220044.py`

Recommendation: compare once against current `putnam_os.py`, then move to archive/checkpoint storage if confirmed obsolete. Do not delete in Phase 0.

### Root-Level Audit Scripts and Reports

Root contains many one-off audit scripts and outputs:

- `cardvector_workspace_auditor.py`
- `cardvector_production_path_auditor.py`
- `cardvector_production_path_auditor_v2.py`
- `cardvector_production_module_auditor.py`
- `cardvector_production_reference_auditor.py`
- `cardvector_root_cleanup_auditor.py`
- `cardvector_folder_inspector.py`
- `cardvector_batch_folder_inspector.py`
- `cardvector_config_reference_finder.py`
- Matching `CARDVECTOR_*_REPORT.txt` files.

Recommendation: after this report is accepted, archive these as prior audit artifacts or consolidate into one canonical audit tool under `Tools/`.

### Repeated README / CHANGELOG / PROJECT_STATUS Copies

Many duplicate documentation filenames exist because release checkpoints copy current docs into `System_Archive`. This is expected. The likely authoritative docs are:

- `Docs/README.md`
- `Docs/CHANGELOG.md`
- `Docs/PROJECT_STATUS.md`
- `Platform/Putnam_OS/README.md`
- `Platform/Putnam_OS/CHANGELOG.md`
- `Platform/Marketplace_Intelligence/README.md`
- `Platform/Marketplace_Intelligence/CHANGELOG.md`

Do not treat checkpoint copies as active documentation.

## Duplicate / Overlapping Folders

### `Putnam_Platform/` vs `Platform/Putnam_Platform/`

There is both a root-level `Putnam_Platform/` and a canonical-looking `Platform/Putnam_Platform/`.

Risk: tools, docs, and capture scripts may point to either path.

Recommendation: identify which folder has active launchers/configuration before any move. Prefer `Platform/Putnam_Platform/` as canonical if current docs remain unchanged.

### `Putnam_Seller_Tools/` vs `Platform/Putnam_OS/Putnam_Seller_Tools/`

There is both a root-level seller-tools folder and a nested CardVector OS seller-tools folder.

Risk: business intelligence reports and README references mention both locations.

Recommendation: make `Platform/Putnam_OS/Putnam_Seller_Tools/` canonical for CardVector OS-adjacent seller tools, then archive or migrate the root folder after comparing outputs.

### Capture Outputs

Root `Capture/` holds session folders such as `06.30.26`, `07.01.26`, `07.02.26`, and `07.03.26`.

Recommendation: treat as active runtime data. Do not move until Capture Studio has a configured migration path.

### Processed OBS Test Outputs

`Data/Processed/` contains several `obs_autocrop_*` smoke/acceptance folders.

Recommendation: treat as generated test output. Later cleanup should archive or purge only after confirming no benchmark images are needed.

### Archive Density

`Archive/` contains historical scanner, overlay, OCR, Kaggle, release-checkpoint, and root-cleanup folders.

Recommendation: leave intact until a dedicated archive inventory is performed. Archive is already the correct high-level owner for old work.

## Hard-Coded Path Findings

### Active Source / Tool Findings

These should be reviewed before production reliance:

- `Business/Inventory/Pricing_Revisions/Run Market Validation Prototype.bat` hard-codes `C:\Users\JaredHill\OneDrive\PutnamCollectibles`.
- `Business/Inventory/Pricing_Revisions/Run Bulk Price Engine.bat` hard-codes `C:\Users\JaredHill\OneDrive\PutnamCollectibles`.
- `Platform/Putnam_Platform/docs/platform_initializer_report_*.txt` contain old absolute path reports. These are generated historical reports, not live code.
- `Platform/Putnam_OS/System/app/putnam_os.py` defines `DOWNLOADS = ROOT / "Downloads"`. That is portable relative to root, but may be semantically stale if the intended folder is the Windows user Downloads folder.

### Runtime / Data Path Records

Several data/history files contain old absolute paths. These should not be rewritten casually:

- `Data/Config/import_module_state.json`
- `Platform/Putnam_OS/System/data/inventory_audit/inventory_audit_history.csv`
- `Platform/Putnam_OS/System/app/test_artifacts/...`
- `Platform/Putnam_OS/System/logs/Startup Logs/...`
- Seller/business-intelligence generated reports under root `Putnam_Seller_Tools/`.

Recommendation: future code should resolve paths portably, but historical logs should remain historical unless there is a specific migration reason.

## USERENVIRONMENT Issues

The current canonical path layer is `Platform/putnam_paths.py`. It checks `PUTNAM_ROOT`, `USERENVIRONMENT`, current working directory, and repository markers.

Older tools still rely on `USERENVIRONMENT` directly:

- `Platform/Putnam_Platform/tools/putnam_platform_initializer_v1_0.py`
- `Platform/Putnam_Platform/engines/Bulk_Price_Engine/app/bulk_price_engine.py`
- `Platform/Putnam_Platform/engines/Market_Intelligence/app/market_validation.py`
- `Platform/Putnam_Platform/Decision_Engine/decision_engine.py`
- Some PowerShell and batch launchers in `Platform/Putnam_Platform/tools/`.

This is not necessarily broken, but it is no longer the preferred standard. Future consolidation should migrate reusable tools to `Platform/putnam_paths.py` or an equivalent shared resolver.

## Documentation Consolidation Findings

Likely canonical governance hierarchy:

1. `Docs/Putnam_Standards/PUTNAM_PRINCIPLES.md`
2. `PLATFORM_VISION.md`
3. `Docs/Putnam_Standards/PUTNAM_PLATFORM_STANDARDS.md`
4. `Docs/AGENTS.md`
5. `Docs/PROJECT_STATUS.md`
6. `Docs/ROADMAP.md`
7. `Docs/CHANGELOG.md`
8. `Docs/README.md`

Other docs are useful but may overlap:

- `Docs/GOVERNANCE.md`
- `Docs/GOVERNANCE_OVERVIEW.md`
- `Docs/PROJECT_MANUAL.md`
- `Docs/PUTNAM_MANIFESTO.md`
- `Docs/PROJECT_INDEX.md`
- `Docs/PATH_MANAGER.md`
- `Docs/*_REPORT.md`

Recommendation: do not delete any docs yet. Later consolidation should define:

- one canonical project manual/reference,
- one canonical roadmap,
- one canonical status file,
- one canonical governance overview,
- one report archive location.

## Runtime / Temp / Cache Findings

The following should not be treated as source code:

- `Capture/`
- `Data/Exports/`
- `Data/Imports/`
- `Data/Logs/`
- `Data/Processed/`
- `Platform/Marketplace_Intelligence/reports/`
- `Platform/Marketplace_Intelligence/backups/`
- `Platform/Putnam_OS/Completed Jobs/`
- `Platform/Putnam_OS/Incoming Files/`
- `Platform/Putnam_OS/System/cache/`
- `Platform/Putnam_OS/System/logs/`
- `Platform/Putnam_OS/System/data/`
- `Platform/Putnam_OS/System_Archive/`
- `Platform/Putnam_OS/System/app/test_artifacts/`
- all `__pycache__/` folders,
- root `ScreenRecording_06-30-2026 14-42-57_1.MP4`.

Recommendation: future cleanup should use a runtime-data policy before moving or deleting anything from these locations.

## Recommended Canonical Folder Owners

| Purpose | Recommended Owner |
|---|---|
| CardVector OS application | `Platform/Putnam_OS/` |
| CardVector OS Tk app source | `Platform/Putnam_OS/System/app/` |
| CardVector OS data/cache/config/log internals | `Platform/Putnam_OS/System/` |
| Marketplace Intelligence app/engine | `Platform/Marketplace_Intelligence/` |
| Legacy/support capture utilities | `Platform/Putnam_Platform/capture/` until folded into a clearer Capture Studio package |
| Shared path resolution | `Platform/putnam_paths.py` |
| Business operations CSVs/files | `Business/` |
| Generated imports/exports/logs/media/processed data | `Data/` |
| Project docs/governance | `Docs/` |
| Standalone utilities | `Tools/` |
| Old versions/checkpoints/experiments | `Archive/` and `Platform/Putnam_OS/System_Archive/` |
| Work-session records | `Work_Sessions/` |
| Content workflow | Needs review: currently `Putnam_Content/` |

## Recommended Cleanup Order

1. Confirm canonical entry points:
   - `Platform/Putnam_OS/Run CardVector OS Production.vbs`
   - `Platform/Putnam_OS/System/app/putnam_os.py`
   - `Platform/Marketplace_Intelligence/run_marketplace_intelligence.py`

2. Archive root audit artifacts:
   - move root `cardvector_*_auditor.py`, `cardvector_*_inspector.py`, and `CARDVECTOR_*_REPORT.txt` into an approved archive/report location.
   - Do this only after user review.

3. Decide owner for root duplicate folders:
   - `Putnam_Platform/`
   - `Putnam_Seller_Tools/`
   - `Collectr/`
   - `Shared/`
   - `Putnam_Content/`

4. Compare and archive active-folder backup Python files:
   - especially backup copies beside `Platform/Putnam_OS/System/app/putnam_os.py`.

5. Resolve hard-coded active launcher paths:
   - particularly `Business/Inventory/Pricing_Revisions/*.bat`.

6. Migrate legacy `USERENVIRONMENT`-only tools to `Platform/putnam_paths.py` where they remain active.

7. Define runtime retention rules:
   - captures,
   - completed jobs,
   - logs,
   - reports,
   - processed smoke outputs,
   - cache.

8. Consolidate documentation concepts after code/folder owners are clear.

## Do Not Touch Yet

Do not touch these until the next cleanup phase has explicit approval:

- `Archive/`
- `Platform/Putnam_OS/System_Archive/`
- `Capture/`
- `Business/`
- `Data/`
- `Platform/Putnam_OS/System/data/`
- `Platform/Putnam_OS/System/logs/`
- `Platform/Marketplace_Intelligence/reports/`
- `Platform/Putnam_OS/Completed Jobs/`
- current app source: `Platform/Putnam_OS/System/app/putnam_os.py`
- current path manager: `Platform/putnam_paths.py`
- all databases, CSV history files, logs, media, and capture images.

## Questions for User Review

1. Should `Platform/Putnam_OS/Run CardVector OS Production.vbs` be the only official CardVector OS launcher?
2. Should `Run Putnam OS Production.vbs` remain as a compatibility alias, or be archived after the CardVector name is fully adopted?
3. Is root `Putnam_Platform/` still used by anything, or can it be compared against `Platform/Putnam_Platform/` for archival?
4. Is root `Putnam_Seller_Tools/` still active, or should `Platform/Putnam_OS/Putnam_Seller_Tools/` become the only seller-tools owner?
5. What is `Collectr/` used for, and should it remain at root?
6. Should `Putnam_Content/` remain root-level for content operations, or move under `Business/Content/` in a future cleanup?
7. Should `Shared/` remain root-level, move under `Docs/`, or become `Tools/Templates/`?
8. Should root audit scripts/reports be archived as one batch after this report is reviewed?
9. How long should `Capture/`, `Completed Jobs/`, logs, generated reports, and processed smoke outputs be retained?
10. Should historical CSV/log paths be left untouched forever, or should future reports store portable relative paths only?
