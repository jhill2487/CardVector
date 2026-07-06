# CardVector Phase 0 Canonical Responsibility & Dependency Audit

Generated: 2026-07-06

Scope: inspection-only architectural audit for `C:\Users\user\OneDrive\PutnamCollectibles`.

This audit does not authorize cleanup. No files were moved, renamed, deleted,
refactored, or behavior-changed while producing this report.

## 1 Executive Summary

CardVector has a workable canonical direction, but several responsibilities are
currently split between a large orchestrator file, small service modules, legacy
tools, archived backups, and generated/runtime folders.

The strongest canonical owners are:

- CardVector OS shell and workflow orchestration:
  `Platform/Putnam_OS/System/app/putnam_os.py`
- Production launcher:
  `Platform/Putnam_OS/Run CardVector OS Production.vbs`
- Shared path management:
  `Platform/putnam_paths.py`
- Capture session and manual capture service:
  `Platform/Putnam_OS/System/app/capture_studio.py`
- Shared OBS WebSocket connection:
  `Platform/Putnam_OS/System/app/obs_connection_manager.py`
- Marketplace Intelligence reusable pricing package:
  `Platform/Marketplace_Intelligence/marketplace_intelligence/`
- ETB location registry:
  `Platform/Putnam_OS/System/app/inventory_locations.py`
- Batch/game location registry:
  `Platform/Putnam_OS/Putnam_Seller_Tools/location_registry.py`
- Label PDF generator:
  `Platform/Putnam_OS/System/tools/generate_etb_qr_labels.py`
- Orders pick slips:
  `Platform/Putnam_OS/System/app/orders_fulfillment.py`

The highest-risk overlaps are:

- Pricing logic appears in CardVector OS, Marketplace Intelligence, legacy Bulk
  Price Engine, legacy Decision Engine, and Listing Optimizer.
- Capture/OBS responsibilities appear in current Capture Studio plus older
  `Platform/Putnam_Platform/capture/Putnam_Capture.py` and autocrop scripts.
- Inventory/location responsibilities are split between ETB registry,
  batch/location registry, audit mode, acquisition metadata, and seller tools.
- The main app file owns both UI and substantial business logic. This makes it
  authoritative, but risky to clean up without tests.

Cleanup should not begin by deleting files. It should begin by confirming the
canonical owners below, then marking every non-owner as either integrated,
legacy-reference, runtime output, or archive candidate.

## 2 Responsibility Matrix

| Responsibility | Canonical Owner | Other Candidates | Confidence | Cleanup Risk |
|---|---|---|---:|---:|
| CardVector OS entry point | `Platform/Putnam_OS/System/app/putnam_os.py` | `Platform/Putnam_OS/System/app/main.py`; backup `putnam_os_*backup*.py` files | High | High |
| Production launcher | `Platform/Putnam_OS/Run CardVector OS Production.vbs` | `Run Putnam OS Production.vbs`; `Run Putnam OS.bat` | High | Medium |
| Shared application initialization | `Platform/putnam_paths.py` plus bootstrap blocks in active app modules | Legacy `find_root()` / `resolve_root()` implementations | High | Medium |
| Capture Studio | `Platform/Putnam_OS/System/app/capture_studio.py` with UI in `putnam_os.py` | `Platform/Putnam_Platform/capture/Putnam_Capture.py`; `Putnam_Capture_v0_1_backup.py` | High | High |
| OBS integration | `capture_studio.py` using `OBSConnectionManager` | `Putnam_Capture.py`; `obs_capture_autocrop.py`; archived capture backups | High | High |
| OBS connection manager | `Platform/Putnam_OS/System/app/obs_connection_manager.py` | `Putnam_Capture.py` internal `ObsConnection` | High | High |
| Auto capture | UI/state in `putnam_os.py`; capture bytes through `CaptureStudioService` | `Putnam_Capture.py` frame signatures/auto capture helpers | Medium | High |
| Manual capture | `CaptureStudioService.capture_next()` and Capture tab methods in `putnam_os.py` | `Putnam_Capture.py` CLI/manual flow | High | High |
| Thumbnail generation | `putnam_os.py` functions `build_capture_thumbnail_image`, `capture_thumbnail`, `refresh_capture_preview_rail` | `Putnam_Capture.py` `LastCapturePreview` | Medium | Medium |
| Thumbnail cache | Tkinter image references held in Capture UI state in `putnam_os.py` | No separate cache service found | Medium | Medium |
| Image session management | `CaptureStudioService` and root `Capture/` session folders | Legacy `Putnam_Capture.py`; `Incoming Files/Capture_Sessions` docs/legacy paths | High | High |
| Inventory database | `Platform/Putnam_OS/System/data/` files, especially inventory snapshot and audit data | Root/Business inventory CSVs; seller audit reports | Medium | High |
| Inventory locations | `inventory_locations.py` using `Data/Config/etb_location_registry.json` | Seller tools `location_registry.py`; OS audit functions | Medium | High |
| ETB management | `inventory_locations.py` plus Inventory UI methods in `putnam_os.py` | Label generator location readers | High | Medium |
| Batch management | `Putnam_Seller_Tools/location_registry.py` for game/batch location suggestions | `putnam_os.py` batch assignment/export functions; seller repair planner | Medium | High |
| Acquisition management | Acquisition functions inside `putnam_os.py`; data under `Platform/Putnam_OS/System/data/acquisitions/` | None obvious | High | Medium |
| QR generation | `generate_etb_qr_labels.py` | `inventory_locations.py` HTML labels do not generate QR | High | Low |
| Label generation | `generate_etb_qr_labels.py` for production PDF/QR labels | `inventory_locations.py` HTML label files | Medium | Medium |
| Marketplace Intelligence | `Platform/Marketplace_Intelligence/marketplace_intelligence/engine.py` and package modules | Legacy `Platform/Putnam_Platform/engines/Market_Intelligence/app/market_validation.py`; OS comp search functions | High | High |
| Pricing | `Platform/Marketplace_Intelligence/marketplace_intelligence/pricing_engine.py` for reusable engine; `putnam_os.py` for listing export floor/optimizer | `bulk_price_engine.py`; legacy Bulk Price Engine; Listing Optimizer; Decision Engine pricing | Medium | High |
| eBay export | `putnam_os.py` listing/export functions | Listing Optimizer CLI; Marketplace Intelligence bulk export for repricing only | High | High |
| CardUploader integration | `putnam_os.py` Import/Pricing workflow and CardUploader import helpers | Marketplace Intelligence CSV import supports CardUploader mode | High | Medium |
| Marketplace synchronization | No production canonical owner found | Marketplace Intelligence future roadmap; legacy Market Intelligence | Low | High |
| Duplicate listing detection | Seller audit/title duplicate reports under Seller Tools | Marketplace Intelligence matching/reports; OS import validation | Medium | Medium |
| Path management | `Platform/putnam_paths.py` | Module-local bootstrap/find_root functions | High | Medium |
| Configuration management | Mixed: OS config in `Platform/Putnam_OS/System/config/`, Data config in `Data/Config/`, Marketplace config in `Platform/Marketplace_Intelligence/config/` | Legacy configs under `Platform/Putnam_Platform/*/config` | Medium | High |
| Logging | Mixed: `Data/Logs/`, `Platform/Putnam_OS/System/logs/`, app-specific reports/logs | Runtime report folders | Medium | Medium |
| Runtime data | `Data/` for shared generated data; `Platform/Putnam_OS/System/data/` for OS internal state | Capture root; app-specific reports | Medium | High |
| Cache | `Platform/Putnam_OS/System/cache/`; Marketplace report/cache inputs; legacy market cache | Root/generated cache folders | Medium | Medium |
| Temporary files | No single owner; runtime folders and `__pycache__` appear throughout | Test artifact folders and generated reports | Low | Medium |
| Settings | OS config JSONs and Marketplace config JSONs | Legacy capture settings in `Platform/Putnam_Platform/capture/capture_settings.json` | Medium | Medium |
| Main window | `PutnamOS` class in `putnam_os.py` | `main.py` older app shell | High | High |
| Navigation | `PutnamOS.build_ui()` / `show_page()` in `putnam_os.py` | `main.py` older shell | High | High |
| Shared widgets | Methods in `PutnamOS`: `card`, `label`, `action_button`, `make_drop_zone`, table helpers | No separate widget module found | Medium | Medium |
| Theme | Constants and `build_styles()` in `putnam_os.py`; `UI_STYLE_GUIDE.md` | `main.py` older theme | High | Medium |
| Design system | `putnam_os.py` constants plus `UI_STYLE_GUIDE.md` | Docs/README design notes | Medium | Medium |
| Status bar | `PutnamOS` UI/status variables and `status_indicator()` in `putnam_os.py` | Marketplace Intelligence standalone UI status | High | Low |
| Toolbar | `PutnamOS.build_ui()` in `putnam_os.py` | Older `main.py` | High | Low |

## 3 Dependency Tree

```text
CardVector OS production launcher
`-- Platform/Putnam_OS/System/app/putnam_os.py
    |-- Platform.putnam_paths
    |   |-- PUTNAM_ROOT / USERENVIRONMENT / cwd / repo markers
    |   `-- Platform, Business, Data, Docs, Tools, Archive, Work_Sessions paths
    |-- Tkinter / ttk / tkinterdnd2
    |-- Capture subsystem
    |   |-- capture_studio.CaptureStudioService
    |   |   |-- obs_connection_manager.OBSConnectionManager
    |   |   |-- obsws-python
    |   |   |-- Platform/Putnam_OS/System/config/obs_config.json
    |   |   |-- Platform/Putnam_Platform/capture/capture_settings.json
    |   |   `-- root Capture/ session folders
    |   |-- capture thumbnails in putnam_os.py
    |   `-- auto capture state in putnam_os.py
    |-- Inventory subsystem
    |   |-- inventory_locations.py
    |   |   |-- Data/Config/etb_location_registry.json
    |   |   `-- Data/Exports/Inventory_Location_Labels/
    |   |-- Putnam_Seller_Tools.location_registry
    |   |   `-- Platform/Putnam_OS/System/config/location_registry.json
    |   |-- acquisition helpers in putnam_os.py
    |   |   `-- Platform/Putnam_OS/System/data/acquisitions/
    |   |-- inventory audit helpers in putnam_os.py
    |   |   `-- Platform/Putnam_OS/System/data/inventory_audit/
    |   `-- label generator subprocess/import path
    |       `-- Platform/Putnam_OS/System/tools/generate_etb_qr_labels.py
    |-- Pricing and listing/export subsystem
    |   |-- CardUploader CSV import helpers in putnam_os.py
    |   |-- listing optimizer/export functions in putnam_os.py
    |   |-- bulk_price_engine.py for existing listing price revisions
    |   |-- Platform/Putnam_Platform/Decision_Engine (legacy/referenced check)
    |   `-- Data/Logs/pricing_performance_log.csv
    |-- Orders subsystem
    |   `-- orders_fulfillment.generate_pick_slips()
    |       `-- Data/Exports/Pick_Lists/
    |-- Seller tools
    |   |-- seller audit
    |   |-- SKU repair planner
    |   `-- listing optimizer reference CLI
    `-- Runtime output
        |-- Platform/Putnam_OS/Completed Jobs/
        |-- Platform/Putnam_OS/Incoming Files/
        |-- Data/Imports/
        |-- Data/Exports/
        |-- Data/Logs/
        `-- Data/Media/

Marketplace Intelligence
`-- run_marketplace_intelligence.py / package CLI / desktop UI
    |-- marketplace_intelligence.engine.MarketplaceIntelligenceEngine
    |   |-- csv_import.import_listing_csv
    |   |-- listing_parser.ListingMatcher
    |   |-- providers.build_provider
    |   |-- pricing_engine.PricingEngine
    |   |-- decision_engine.DecisionEngine
    |   `-- reports.write_reports
    |-- Platform/Marketplace_Intelligence/config/
    `-- Platform/Marketplace_Intelligence/reports/
```

### Modules Depending On OBS

- `Platform/Putnam_OS/System/app/capture_studio.py`
- `Platform/Putnam_OS/System/app/obs_connection_manager.py`
- `Platform/Putnam_OS/System/app/putnam_os.py` through `CaptureStudioService`
- Legacy candidate: `Platform/Putnam_Platform/capture/Putnam_Capture.py`
- OBS/autocrop bridge: `Platform/Putnam_Platform/capture/obs_capture_autocrop.py`

### Modules Depending On Inventory

- `putnam_os.py`
- `inventory_locations.py`
- `Putnam_Seller_Tools/location_registry.py`
- `seller_audit/putnam_seller_audit_v1_0.py`
- `seller_audit/putnam_sku_repair_planner_v1_1.py`
- `generate_etb_qr_labels.py`

### Modules Depending On Pricing

- `putnam_os.py`
- `Platform/Marketplace_Intelligence/marketplace_intelligence/pricing_engine.py`
- `Platform/Marketplace_Intelligence/marketplace_intelligence/decision_engine.py`
- `Platform/Putnam_OS/System/app/bulk_price_engine.py`
- Legacy: `Platform/Putnam_Platform/engines/Bulk_Price_Engine/app/bulk_price_engine.py`
- Legacy: `Platform/Putnam_Platform/Decision_Engine/pricing.py`
- Reference/legacy: `Putnam_Seller_Tools/listing_optimizer/putnam_listing_optimizer_v1_1.py`

### Modules Depending On Shared Configuration

- `putnam_os.py` reads/writes OS config JSONs.
- `capture_studio.py` reads OBS and capture settings.
- `inventory_locations.py` uses `Data/Config/etb_location_registry.json`.
- `location_registry.py` uses `Platform/Putnam_OS/System/config/location_registry.json`.
- Marketplace Intelligence package uses `Platform/Marketplace_Intelligence/config/`.
- Legacy Putnam Platform engines use their own config folders.

### Modules Depending On Path Manager

- `putnam_os.py`
- `capture_studio.py`
- `inventory_locations.py`
- `orders_fulfillment.py`
- `Platform/Putnam_OS/System/app/bulk_price_engine.py`
- `Platform/Putnam_OS/System/app/main.py`
- `Platform/Putnam_OS/Putnam_Seller_Tools/location_registry.py`
- `Platform/putnam_paths.py` itself is the canonical source.

## 4 Shared Services

| Shared Service | Current Owner | Consumers | Notes |
|---|---|---|---|
| Repository path resolution | `Platform/putnam_paths.py` | OS app, capture, inventory, orders, seller tools | Strongest shared service. New code should extend this. |
| OBS WebSocket connection | `obs_connection_manager.py` | `capture_studio.py`, Capture UI via service | Canonical for current and future OBS features. |
| Capture session service | `capture_studio.py` | Capture tab in `putnam_os.py`, tests | Owns session folder creation, pairing filenames, retakes, finish state. |
| ETB registry service | `inventory_locations.py` | Inventory tab, labels | Owns ETB-style storage container state. |
| Batch/game location registry | `Putnam_Seller_Tools/location_registry.py` | OS export/intake, seller audit, SKU repair | Owns game-aware batch location suggestions and preservation of CS values. |
| Orders pick slip generator | `orders_fulfillment.py` | Orders tab | Owns eBay orders CSV parsing and pick slip output. |
| Marketplace pricing engine | `Marketplace_Intelligence/marketplace_intelligence/pricing_engine.py` | Marketplace Intelligence engine | Intended reusable pricing owner, but OS export still has local pricing rules. |
| Marketplace decision engine | `Marketplace_Intelligence/marketplace_intelligence/decision_engine.py` | Marketplace Intelligence engine | Separate from price calculation. |
| Label PDF generator | `System/tools/generate_etb_qr_labels.py` | Inventory Label Center | Owns QR/PDF labels; reads registries but does not modify inventory. |
| UI style/design constants | `putnam_os.py`; `UI_STYLE_GUIDE.md` | CardVector OS shell | Shared only inside current monolithic UI. |

## 5 Overlapping Implementations

| Overlap | Implementations Found | Risk | Notes |
|---|---|---:|---|
| Capture/OBS capture | Current `capture_studio.py`; `obs_connection_manager.py`; legacy `Putnam_Capture.py`; `Putnam_Capture_v0_1_backup.py`; capture backups | HIGH | Wrong cleanup could break validated manual/auto capture or old recovery path. |
| OBS connection handling | `obs_connection_manager.py`; `Putnam_Capture.py` internal `ObsConnection`; older backup code | HIGH | Canonical owner is clear, but legacy code may still be useful reference. |
| Auto capture logic | `putnam_os.py` auto-capture state; `Putnam_Capture.py` frame signature/distance helpers | HIGH | Current production UI likely depends on OS implementation. |
| Thumbnail preview | `putnam_os.py`; `Putnam_Capture.py` `LastCapturePreview` | MEDIUM | Legacy preview can likely be retired later if not referenced, but verify first. |
| Listing/pricing/export | `putnam_os.py`; `System/app/bulk_price_engine.py`; Marketplace Intelligence; legacy Bulk Price Engine; Listing Optimizer CLI | HIGH | Pricing responsibility has historically shifted. Do not remove without behavioral comparison. |
| Market comp/cache logic | `putnam_os.py` CardUploader sales/cache helpers; Marketplace Intelligence providers; legacy Market Intelligence | HIGH | Some data sources are reference-only by design. Cleanup could change recommendation behavior. |
| Location registries | `inventory_locations.py`; `Putnam_Seller_Tools/location_registry.py`; config files in both `Data/Config` and `System/config` | HIGH | These may represent different concepts: ETB container registry vs batch/game location registry. |
| Label generation | `generate_etb_qr_labels.py`; `inventory_locations.py` HTML labels | MEDIUM | PDF/QR generator appears production owner; HTML label generation may be older/fallback. |
| App shell | `putnam_os.py`; `main.py`; backup `putnam_os_*` files | HIGH | `main.py` may be old, but file is active-looking. Confirm launcher paths and imports first. |
| Path resolution | `Platform/putnam_paths.py`; many local `find_root()` / `resolve_root()` functions | MEDIUM | Migrate only active code; leave archives/report history alone. |
| Seller tools | `Platform/Putnam_OS/Putnam_Seller_Tools/`; root `Putnam_Seller_Tools/` | MEDIUM | Root folder contains business intelligence/branding, not a direct duplicate of all nested tools. Needs owner decision. |
| Documentation concepts | `PROJECT_STATUS`, `ROADMAP`, `PROJECT_MANUAL`, `GOVERNANCE`, `GOVERNANCE_OVERVIEW`, `PUTNAM_MANIFESTO`, standards docs | MEDIUM | Governance hierarchy exists; avoid consolidating until concepts are explicitly mapped. |
| Reports/output | `Data/Exports`, `Data/Logs`, Marketplace `reports`, Seller Tools `reports`, OS `Completed Jobs` | LOW/MEDIUM | Generated outputs should be retention-managed, not treated as source. |

## 6 Recommended Canonical Owners

These recommendations are for review only and do not authorize cleanup.

| Area | Recommended Canonical Owner | Rationale |
|---|---|---|
| CardVector OS application shell | `Platform/Putnam_OS/System/app/putnam_os.py` | Current production launcher targets this file. |
| CardVector OS launch | `Platform/Putnam_OS/Run CardVector OS Production.vbs` | Rebranded production launcher. |
| Shared path system | `Platform/putnam_paths.py` | Already documented as the path rule and used by active modules. |
| Capture Studio service | `Platform/Putnam_OS/System/app/capture_studio.py` | Current service used by OS Capture UI. |
| OBS connection | `Platform/Putnam_OS/System/app/obs_connection_manager.py` | Explicit shared manager with status/reconnect. |
| Capture UI and thumbnails | `PutnamOS.capture_page()` and related methods in `putnam_os.py` | Current UI owner; later extraction can extend this rather than replacing. |
| Marketplace Intelligence app | `Platform/Marketplace_Intelligence/` | Standalone package with README, config, examples, reports, CLI/UI. |
| Reusable market pricing engine | `Platform/Marketplace_Intelligence/marketplace_intelligence/pricing_engine.py` | Designed as reusable engine. |
| CardVector OS eBay listing export | `putnam_os.py` until extracted | Owns eBay-ready CSV workflow and export history today. |
| ETB location registry | `inventory_locations.py` | Owns ETB codes/status/capacity. |
| Game/batch location registry | `Putnam_Seller_Tools/location_registry.py` | Owns game-aware suggested next batch locations. |
| Acquisition tracking | `putnam_os.py` acquisition helpers | No separate owner found. |
| Orders/pick slips | `orders_fulfillment.py` | Small focused module already exists. |
| QR/PDF labels | `generate_etb_qr_labels.py` | Production QR label generator. |
| Seller audit/SKU repair | `Platform/Putnam_OS/Putnam_Seller_Tools/seller_audit/` | Current seller tools path used by docs and imports. |
| UI design system | `putnam_os.py` constants plus `UI_STYLE_GUIDE.md` | Current centralized place for OS UI tokens. |

## 7 High Risk Areas

1. `Platform/Putnam_OS/System/app/putnam_os.py`

   This is the production app entry point and contains UI, pricing/export,
   capture UI, inventory audit, acquisition, import, and workflow orchestration.
   It is canonical but monolithic. Cleanup here should be test-first and very
   incremental.

2. Backup files beside active app code

   Files like `putnam_os_capture_v1_backup_20260629_212812.py` and related
   `putnam_os_*backup*.py` contain large older implementations. They should be
   compared and moved only after confirming no launcher/import references.

3. Pricing ownership

   Marketplace Intelligence is the intended reusable pricing engine, but
   CardVector OS still contains listing/export pricing rules and older engines
   remain present. Removing the wrong implementation could alter eBay export
   behavior.

4. Capture ownership

   Current Capture Studio is split across `capture_studio.py`,
   `obs_connection_manager.py`, and Capture UI methods in `putnam_os.py`.
   Legacy `Putnam_Capture.py` still contains substantial OBS/capture logic and
   should not be deleted without reference checks.

5. Location registry split

   `Data/Config/etb_location_registry.json` and
   `System/config/location_registry.json` appear to serve related but distinct
   purposes. Treat as separate concepts until explicitly unified.

6. Runtime folders with business data

   `Capture/`, `Business/`, `Data/`, `Completed Jobs/`, `System/data/`,
   Marketplace reports, seller audit reports, and logs may contain business
   evidence or generated output. Do not delete in cleanup passes.

## 8 Safe Cleanup Candidates

These are candidates only. Cleanup still requires explicit approval.

| Candidate | Why It Looks Safer | Required Check Before Cleanup |
|---|---|---|
| Root `CARDVECTOR_*_REPORT.txt` files | Generated audit/report artifacts | Confirm they are superseded by `Docs/Reports` reports. |
| Root `cardvector_*_auditor.py` scripts | One-off audit scripts from prior phases | Confirm no scheduled launcher or workflow uses them. |
| `__pycache__/` folders | Python bytecode caches | Safe only if cleanup policy allows generated cache removal. |
| Marketplace Intelligence `backups/` | Explicit backups | Retention decision needed; do not delete blindly. |
| Old `putnam_os_*backup*.py` in app folder | Explicit backup filenames | High verification required because they sit beside app code. |
| `Platform/Putnam_Platform/capture/*backup*` | Explicit backup folders/files | Confirm current Capture Studio does not import them. |
| Generated smoke-test folders in `Data/Processed/obs_autocrop_*` | Test outputs | Confirm no benchmark expectation depends on them. |
| Root screen recording MP4 | Runtime/media artifact | Confirm owner wants it archived or retained. |

## 9 Questions For User

1. Should `Platform/Putnam_OS/Run CardVector OS Production.vbs` be the only
   official launcher going forward?

2. Should `Platform/Putnam_OS/System/app/main.py` be treated as legacy once
   `putnam_os.py` is confirmed as the only launched app?

3. Should Marketplace Intelligence become the single canonical pricing engine
   for recommendations, while CardVector OS keeps only eBay export formatting
   and workflow confirmation?

4. Should `Platform/Putnam_OS/System/app/bulk_price_engine.py` remain active,
   or become a compatibility wrapper around Marketplace Intelligence later?

5. Should `Platform/Putnam_Platform/engines/Bulk_Price_Engine/` and
   `Platform/Putnam_Platform/Decision_Engine/` be considered legacy reference
   after pricing ownership is confirmed?

6. Are `Data/Config/etb_location_registry.json` and
   `Platform/Putnam_OS/System/config/location_registry.json` intentionally
   separate concepts: ETB containers vs game/batch locations?

7. Should `inventory_locations.py` own all ETB/container state and
   `location_registry.py` own all game/batch assignment state?

8. Should `Putnam_Capture.py` remain available as a fallback CLI capture tool,
   or should Capture Studio inside CardVector OS be the only active capture
   owner?

9. Should root `Putnam_Seller_Tools/` be kept for business intelligence and
   branding, or reviewed for consolidation under `Platform/Putnam_OS/`?

10. Should future cleanup create a formal "legacy reference" label in docs
    before anything is archived, so daily production files are never confused
    with historical work?

