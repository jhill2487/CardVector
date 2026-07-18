# CardVector Duplicate And Overlapping Module Report

**Audit date:** 2026-07-17
**Important:** An overlap does not automatically mean one implementation is removable. Some are compatibility interfaces or represent related but distinct concepts.

## Summary Matrix

| Responsibility | Canonical owner or leading candidate | Other implementations | Risk |
|---|---|---|---|
| Desktop application | `System/app/putnam_os.py` | `System/app/main.py` | High |
| Pricing / Price Vector | `Platform/Marketplace_Intelligence` | Putnam OS pricing modules, bulk engine, Listing Optimizer | High |
| Market evidence / FMV | `Platform/Marketplace_Intelligence` | UI-local comp matching and older System MarketIntelligence models | High |
| Capture session service | `capture_studio.py` + `obs_connection_manager.py` | `Putnam_Capture.py`, autocrop script, UI capture state | High |
| Mobile capture queue | `mobile_capture_queue.py` | No direct duplicate | Medium due to app-layer import |
| ETB/location registry | `inventory_locations.py` plus documented Supabase contract | Seller Tools `location_registry.py`, legacy fallback JSON | High |
| Label generation | `generate_etb_qr_labels.py` | HTML label behavior in `inventory_locations.py` | Medium |
| Orders | `orders_fulfillment.py` | UI callbacks in `putnam_os.py` | Medium |
| Workflow context | `workflow_context.py` | UI-local state and session JSON handling | Medium |
| Path management | `Platform/putnam_paths.py` | Repeated root/path logic | Medium |
| Config loading | No complete canonical owner | Multiple JSON loaders and config roots | Medium |
| Logging | No canonical owner | Ad hoc CSV/text/JSON logs | Medium |
| CSV/file helpers | Marketplace utils plus many local helpers | Repeated functions | Low/Medium |

## Desktop GUI Overlap

### Canonical current production

`Platform/Putnam_OS/System/app/putnam_os.py`

Observed responsibilities include:

- Navigation and all primary workspaces.
- Capture and thumbnails.
- Mobile queue state.
- Import and CardUploader handoff.
- Pricing and eBay export callbacks.
- Inventory location/conversion/audit workflows.
- Orders and pick-list UI.
- Acquisition/session data.
- Configuration, paths, logging, and status.

### Other candidate

`Platform/Putnam_OS/System/app/main.py`

It defines another complete Tkinter `PutnamOS` application with overlapping CSV import, pricing, export, and configuration behavior. The production launcher does not target it, but active uncommitted pricing consolidation tests reference its interfaces.

### Recommendation

Do not delete `main.py`. First identify every imported function/test contract. Redirect useful public interfaces to application services, then retire only the second GUI construction path.

## Pricing Overlap

### Recommended canonical owner

`Platform/Marketplace_Intelligence/marketplace_intelligence/pricing_engine.py`

Supporting canonical modules:

- `engine.py`
- `models.py`
- `providers.py`
- `decision_engine.py`
- `reports.py`
- `bulk_export.py`
- current untracked `pricing_repository.py`

### Overlapping paths

- `Platform/Putnam_OS/System/MarketIntelligence/Pricing/pricing_engine.py`
- `Platform/Putnam_OS/System/MarketIntelligence/Pricing/pricing_models.py`
- `Platform/Putnam_OS/System/app/bulk_price_engine.py`
- pricing functions and callbacks in `putnam_os.py`
- pricing functions in `main.py`
- `Platform/Putnam_OS/Putnam_Seller_Tools/listing_optimizer/putnam_listing_optimizer_v1_1.py`
- `Platform/Putnam_OS/Putnam_Seller_Tools/listing_optimizer/putnam_listing_optimizer_v1_2.py`

### Current status

The working tree contains uncommitted changes that delegate several Putnam OS pricing paths to Marketplace Intelligence and introduce explicit FMV/recommended/final price persistence. That is the correct direction, but it is not yet a committed baseline.

### Recommendation

Finish and commit the current consolidation before architecture migration. Preserve adapters; remove only independent formulas after parity tests prove behavior.

## Marketplace Evidence And Matching Overlap

### Canonical owner

`Platform/Marketplace_Intelligence`

### Overlap

`putnam_os.py` contains comparison normalization and matching helpers for cached/listing data, including token, card-number, exclusion, and comparable-reason behavior similar to provider/matcher logic in Marketplace Intelligence.

`Platform/Putnam_OS/System/MarketIntelligence/Models`, `Identity`, and `Inspector` also retain earlier market-intelligence concepts.

### Risk

High. Similar names do not guarantee equivalent evidence rules. Active listings, sold evidence, CardUploader cache, FMV, and competition evidence must remain distinct.

### Recommendation

Inventory each caller and result contract. Move evidence normalization to Marketplace Intelligence only after fixture parity tests exist.

## Capture Overlap

### Current canonical path

- `System/app/capture_studio.py`
- `System/app/obs_connection_manager.py`
- Capture UI/state in `putnam_os.py`
- `System/tools/mobile_capture_queue.py`

### Legacy paths

- `Platform/Putnam_Platform/capture/Putnam_Capture.py`
- `Platform/Putnam_Platform/capture/obs_capture_autocrop.py`
- associated BAT launchers

### Duplicated concerns

- Session folder numbering.
- Front/back pairing.
- OBS connection/capture.
- Automatic capture state.
- Image routing and metadata.
- Status output.

### Recommendation

The shared OBS manager and Capture Studio service are the canonical desktop foundation. Mobile queue remains canonical for cloud claims/downloads. Compare legacy behavior against production tests before archiving legacy scripts.

## Inventory And Location Overlap

### Physical registry

`System/app/inventory_locations.py`

Format:

- ETB IDs such as `ETB-001`
- locations `A` through `J`
- 400-card ETB / 40-card location defaults
- operational state and cloud projection

### Seller Tools registry

`Platform/Putnam_OS/Putnam_Seller_Tools/location_registry.py`

Format and purpose:

- older game/batch SKU suggestions,
- examples resembling `ETB-##-Letter`,
- seller-audit/SKU-planning use.

### Supabase registry

`supabase/migrations/20260714_000004_mobile_capture_location_registry.sql`

Purpose:

- cloud-readable canonical ETB/location identity,
- authenticated reads,
- secure atomic next-location creation,
- uniqueness and RLS.

### Assessment

The local physical registry and Supabase identity registry are not necessarily competitors: current documentation defines a synchronization contract. The Seller Tools registry is a legacy batch-location concept and can conflict if treated as the physical source of truth.

### Recommendation

Define separate terms:

- Location identity.
- Operational occupancy/status.
- Capture/conversion batch assignment.
- Seller SKU repair defaults.

Then make Inventory own all adapters and synchronization.

## Label And QR Overlap

- `inventory_locations.py` produces/open HTML labels and supports registry UI actions.
- `System/tools/generate_etb_qr_labels.py` produces professional PDF QR labels.
- `putnam_os.py` dynamically calls label generation.

These are different output formats but share payload and registry logic. The payload rules must have one owner.

Recommendation: Inventory owns payload/label data models; renderers may remain separate.

## Shared Utility Duplication

Repeated helpers include:

- `money` / decimal conversion.
- column normalization and lookup.
- CSV row reading.
- safe filename generation.
- timestamp generation.
- JSON load/save.
- repository-root discovery.
- default OneDrive path construction.

Locations include:

- `putnam_os.py`
- `main.py`
- `bulk_price_engine.py`
- `orders_fulfillment.py`
- `inventory_reconciliation.py`
- Marketplace Intelligence `utils.py`, `providers.py`, and business-intelligence scripts
- Seller Tools
- label and capture utilities

### Recommendation

Do not perform a bulk utility rewrite. Promote only stable, semantics-identical helpers into `Platform/Shared`, with caller-specific tests first.

## Configuration Overlap

Configuration is stored or loaded from:

- `Data/Config`
- `Platform/Putnam_OS/config`
- `Platform/Putnam_OS/System/config`
- `Platform/Marketplace_Intelligence/config`
- environment variables
- browser-safe `Docs/mobile-capture-config.js`

These include application settings, business policy, provider config, location registry, capture settings, secrets references, and runtime state.

Recommendation: define categories before consolidation:

1. Versioned defaults.
2. Versioned schema.
3. Operator settings.
4. Workstation settings.
5. Runtime state.
6. Secrets/environment.
7. Public browser configuration.

## Logging Overlap

Logging currently includes:

- startup logs from launchers,
- UI/status logs,
- CSV performance logs,
- export logs,
- decision engine logs,
- mobile queue logs/status,
- label-generation logs,
- generated report summaries.

No canonical logging service was identified.

Recommendation: use Python logging with subsystem names and file handlers, while retaining required business CSV audit logs as explicit reports rather than generic logs.

## Filesystem And Root Discovery Overlap

Canonical candidate:

`Platform/putnam_paths.py`

Other modules independently construct `%USERPROFILE%\OneDrive\PutnamCollectibles` or use `USERENVIRONMENT`. Some scripts contain old usernames or old root layouts.

Recommendation: make path resolution a shared dependency and pass resolved data directories into services. Avoid importing UI modules to obtain paths.

## Versioned And Backup Files

Active-source folders contain timestamped backup modules:

- seven tracked `putnam_os_*backup*.py` files,
- three current untracked `.bak` files.

No active imports of the tracked backup modules were found.

Recommendation: archive after the current working tree is safely committed. Git history should become the source-code backup system.

## Canonicalization Order

1. Preserve and commit active Price Vector work.
2. Freeze the production launcher and workflow tests.
3. Establish shared path/config/log interfaces.
4. Complete Marketplace Intelligence pricing delegation.
5. Separate Putnam OS UI from application orchestration.
6. Consolidate Capture.
7. Consolidate Inventory/location ownership.
8. Consolidate Orders/reporting.
9. Archive proven-unused implementations and broken launchers.
