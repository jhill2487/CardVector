# CardVector Entry Point And Launcher Report

**Audit date:** 2026-07-17
**Scope:** Current repository entry points are primary. Archived entry points are grouped as historical rather than exhaustively promoted as runnable applications.

## Official Production Entry Point

### Observed

`Platform/Putnam_OS/Run CardVector OS Production.vbs` is the clearest current production launcher.

It launches:

`Platform/Putnam_OS/System/app/putnam_os.py`

The target defines the production `PutnamOS` Tkinter application and enters its main loop.

### Recommendation

Keep this launcher and target unchanged during early architecture work. Eventually introduce a small `Platform/main.py` bootstrap and redirect the VBS launcher only after full workflow validation. The bootstrap must initialize dependencies, not contain business logic.

## Current Desktop Application Entry Points

| Path | Purpose / current evidence | Duplicate responsibility | Recommendation |
|---|---|---|---|
| `Platform/Putnam_OS/Run CardVector OS Production.vbs` | Named CardVector production launcher; targets `putnam_os.py` and creates a startup log/temporary command | Overlaps two Putnam OS launchers | **Keep** as official current launcher |
| `Platform/Putnam_OS/Run Putnam OS Production.vbs` | Alias targeting the same production application | Duplicate production launcher | **Consolidate later** after shortcut/user validation |
| `Platform/Putnam_OS/Run Putnam OS.bat` | Portable fallback launcher using `USERENVIRONMENT`/OneDrive logic | Duplicate launcher and path logic | **Consolidate later**; may be useful for diagnostics |
| `Platform/Putnam_OS/System/app/putnam_os.py` | Production CardVector OS Tkinter UI and workflow host | Overlaps `main.py`; contains many subsystem responsibilities | **Keep**, then incrementally reduce |
| `Platform/Putnam_OS/System/app/main.py` | Separate full Tkinter Putnam OS application with import/pricing/export behavior | Major GUI and pricing workflow overlap | **Defer decision**; current uncommitted pricing tests reference it |

## Marketplace Intelligence Entry Points

| Path | Purpose / current evidence | Duplicate responsibility | Recommendation |
|---|---|---|---|
| `Platform/Marketplace_Intelligence/Run Marketplace Intelligence.bat` | Standalone desktop launcher | Separate from CardVector OS by design | **Keep** if standalone product remains supported |
| `Platform/Marketplace_Intelligence/run_marketplace_intelligence.py` | Imports and starts `marketplace_intelligence.ui.main()` | Thin launcher | **Keep** |
| `Platform/Marketplace_Intelligence/marketplace_intelligence/ui.py` | Standalone Tkinter Marketplace Intelligence UI, includes direct execution guard | UI and launcher in one module | **Keep interface**, later prefer launcher-only execution |
| `Platform/Marketplace_Intelligence/marketplace_intelligence/cli.py` | CLI execution surface | None; valid alternate interface | **Keep** |
| `Platform/Marketplace_Intelligence/business_intelligence/business_intelligence_v0_1.py` | Early business intelligence application/script | Potential reporting overlap | **Review**; versioned/prototype naming suggests noncanonical status |

## Capture Entry Points

| Path | Purpose / current evidence | Duplicate responsibility | Recommendation |
|---|---|---|---|
| `Platform/Putnam_Platform/tools/Run_Putnam_Capture.bat` | Launches legacy `Putnam_Capture.py` | Competes with current Capture Studio inside CardVector OS | **Legacy reference; defer archive** until operator usage confirmed |
| `Platform/Putnam_Platform/capture/Putnam_Capture.py` | Earlier standalone OBS capture application | Manual/session capture overlap | **Consolidate behavior, then archive** |
| `Platform/Putnam_Platform/tools/Run_OBS_AutoCrop.bat` | Intended OBS autocrop launcher | Uses a stale root path | **Obsolete/broken candidate** |
| `Platform/Putnam_Platform/capture/obs_capture_autocrop.py` | Batch/watch/auto capture preparation script | Auto-capture and image routing overlap | **Legacy reference**; retain until current Capture contracts cover required behavior |
| `Platform/Putnam_OS/System/tools/mobile_capture_queue.py` | Desktop CLI/service for cloud queue polling, claiming, download, routing, and location sync | No equivalent canonical tool found | **Keep**; move ownership only through a tested Capture extraction |

## Inventory, Orders, And Maintenance Entry Points

| Path | Purpose | Recommendation |
|---|---|---|
| `Platform/Putnam_OS/System/app/inventory_reconciliation.py` | CLI/report workflow comparing CardUploader and eBay data | **Keep**, assign future Inventory ownership |
| `Platform/Putnam_OS/System/tools/generate_etb_qr_labels.py` | PDF/QR label generation CLI | **Keep**, assign future Inventory ownership |
| `Platform/Putnam_OS/System/app/run_pricing_cli.py` | Pricing CSV CLI that executes argument parsing at module load | **Consolidate** behind Marketplace Intelligence CLI; add a guarded adapter before retirement |
| `Platform/Putnam_OS/Putnam_Seller_Tools/seller_audit/putnam_seller_audit_v1_0.py` | eBay active-listing audit CLI | **Keep as tool**, review naming/version mismatch |
| `Platform/Putnam_OS/Putnam_Seller_Tools/seller_audit/putnam_sku_repair_planner_v1_1.py` | Safe SKU repair plan CLI | **Keep as tool** |
| `Platform/Putnam_OS/Putnam_Seller_Tools/listing_optimizer/putnam_listing_optimizer_v1_1.py` | Older optimizer | **Legacy compatibility candidate** |
| `Platform/Putnam_OS/Putnam_Seller_Tools/listing_optimizer/putnam_listing_optimizer_v1_2.py` | Wrapper/newer optimizer entry | **Review and delegate to canonical pricing** |
| `Tools/export_cardvector_site.py` | Static public-site export and secret-safety boundary | **Keep** |
| `Tools/validate_production_startup.py` | Production import/startup validation | **Keep as validation tool** |
| `Tools/cardvector_mobile_capture_validation.py` | Mobile capture validation | **Keep as test/validation tool** |
| `Tools/test_mobile_capture_supabase_contract.py` | Supabase contract test | **Keep as test** |
| `Tools/test_public_storefront_contract.py` | Public storefront contract test | **Keep as test**, remove workstation-specific fixture path later |
| `Platform/Putnam_OS/cardvector_project_auditor.py` | Earlier project audit tool | **Archive candidate** after confirming no current governance workflow uses it |

## Web Entry Points

| Path | Purpose | Recommendation |
|---|---|---|
| `Docs/index.html` | Public storefront and mobile capture application entry | **Keep** |
| `Docs/404.html` | GitHub Pages deep-link fallback | **Keep** |
| `Docs/app.js` | Public route handling, capture workflow, Supabase client behavior | **Keep** |
| `Docs/mobile-capture-config.js` | Browser-safe public config | **Keep**, ensure no service-role secrets |
| `.github/workflows/pages.yml` | Exports private source and pushes artifact to `CardVector-site` | **Keep** |

The workflow name suggests Pages, but it does not deploy this private repository directly to GitHub Pages. It exports the public artifact and pushes the separate public repository.

## Directly Executable Tests And Backups

The following current source areas also contain direct `__main__` execution guards:

- Marketplace Intelligence tests under `Platform/Marketplace_Intelligence/tests`.
- Putnam OS application smoke tests under `Platform/Putnam_OS/System/app/test_*.py`.
- Mobile queue tests under `Platform/Putnam_OS/System/tools/test_mobile_capture_queue.py`.
- Public/mobile contract tests under `Tools/test_*.py`.
- Timestamped Putnam OS backup modules beside active source.
- Listing Optimizer backups under `Putnam_Seller_Tools/listing_optimizer/backups`.

These are not production application entry points. The tests are valid executable validation surfaces; the backups are archive candidates and must not be presented as supported launch targets.

## Broken Or Stale Launchers

### Confirmed by path evidence

1. `Business/Inventory/Pricing_Revisions/Run Market Validation Prototype.bat`
2. `Business/Inventory/Pricing_Revisions/Run Bulk Price Engine.bat`

Both reference `C:\Users\JaredHill\...` and pre-reorganization root locations.

3. `Platform/Putnam_Platform/tools/Run_OBS_AutoCrop.bat`

It references `Putnam_Platform\capture` at the repository root, while the current file is under `Platform\Putnam_Platform\capture`.

These are high-confidence stale launcher candidates, but this audit does not authorize deletion.

## Launcher Recommendation

### Now

- Official launcher: `Platform/Putnam_OS/Run CardVector OS Production.vbs`
- Official app target: `Platform/Putnam_OS/System/app/putnam_os.py`
- Standalone Marketplace Intelligence: retain its BAT/Python launcher pair.
- Public site: retain the export workflow.

### Later

1. Add a minimal `Platform/main.py`.
2. Have one production VBS launcher call it.
3. Preserve one documented command-line fallback.
4. Remove aliases only after desktop shortcuts and both workstations are checked.
5. Move subsystem CLIs behind canonical service APIs without removing useful operator interfaces.

## Launcher Validation Required Before Consolidation

- Start CardVector OS from the production VBS launcher.
- Start from the fallback BAT launcher.
- Confirm startup logging and environment behavior.
- Confirm Marketplace Intelligence standalone UI and CLI are intentionally supported.
- Ask the operator whether the standalone legacy capture launchers are still used.
- Search Windows shortcuts, scheduled tasks, and documentation for launcher references.
- Validate from both home and work PCs.
