# CardVector Dead Code And Legacy Candidate Report

**Audit date:** 2026-07-17
**Safety:** This report identifies candidates only. It does not authorize deletion, movement, or archival.

## Confidence Levels

- **High:** Broken path, backup naming, no active references, or clearly superseded artifact.
- **Medium:** Appears unused but has a plausible manual or compatibility purpose.
- **Low:** Historical or obscure area with insufficient evidence.

## High-Confidence Candidates

### Tracked backup modules beside active source

Paths:

- `Platform/Putnam_OS/System/app/putnam_os_capture_v1_backup_20260629_212812.py`
- `Platform/Putnam_OS/System/app/putnam_os_comp_engine_v1_1_backup_20260629.py`
- `Platform/Putnam_OS/System/app/putnam_os_comp_ui_v1_2_0_backup_20260629.py`
- `Platform/Putnam_OS/System/app/putnam_os_import_v1_backup_20260629_222132.py`
- `Platform/Putnam_OS/System/app/putnam_os_inventory_location_foundation_backup_20260629_231122.py`
- `Platform/Putnam_OS/System/app/putnam_os_listing_workflow_backup_20260629_214810.py`
- `Platform/Putnam_OS/System/app/putnam_os_orders_v1_backup_20260629_220044.py`

Evidence:

- Timestamped backup naming.
- Located beside active production source.
- No active imports/references found.
- Git history is now available as source backup.

Recommendation: archive in one cleanup package only after current production work is committed and launcher/tests pass.

### Current untracked patch backups

Paths:

- `Platform/Putnam_OS/System/app/bulk_price_engine.py.before_ebay_patch_20260717_132121.bak`
- `Platform/Putnam_OS/System/app/main.py.before_ebay_patch_20260717_132121.bak`
- `Platform/Putnam_OS/System/app/putnam_os.py.before_active_listing_fix_20260717_135604.bak`

Evidence: explicit patch-backup suffix and current untracked state.

Recommendation: preserve until the related eBay/pricing patch is resolved; then archive or remove through an approved cleanup package.

### Broken hard-coded launchers

- `Business/Inventory/Pricing_Revisions/Run Market Validation Prototype.bat`
- `Business/Inventory/Pricing_Revisions/Run Bulk Price Engine.bat`

Evidence:

- hard-coded `C:\Users\JaredHill`,
- references to old root-level implementation paths,
- current platform code lives elsewhere.

Recommendation: verify no desktop shortcut uses them, then archive.

### Stale OBS autocrop launcher

`Platform/Putnam_Platform/tools/Run_OBS_AutoCrop.bat`

Evidence: target path does not match the current `Platform/Putnam_Platform/capture` location.

Recommendation: archive if standalone autocrop is no longer used; otherwise repair in a Capture-specific task.

## Medium-Confidence Legacy Candidates

### Secondary full GUI

`Platform/Putnam_OS/System/app/main.py`

Evidence:

- not targeted by the production launchers,
- duplicates significant application behavior,
- has a different displayed version,
- active pricing tests currently use compatibility interfaces from it.

Conclusion: likely legacy GUI, but not dead. Do not archive until tests and import callers are migrated.

### Legacy standalone capture application

- `Platform/Putnam_Platform/capture/Putnam_Capture.py`
- `Platform/Putnam_Platform/capture/obs_capture_autocrop.py`
- `Platform/Putnam_Platform/tools/Run_Putnam_Capture.bat`

Evidence:

- current CardVector OS has Capture Studio and shared OBS management,
- older tools remain separately runnable.

Conclusion: legacy/reference candidates. Operator usage must be confirmed.

### Earlier Listing Optimizer implementations

- `Platform/Putnam_OS/Putnam_Seller_Tools/listing_optimizer/putnam_listing_optimizer_v1_1.py`
- `Platform/Putnam_OS/Putnam_Seller_Tools/listing_optimizer/putnam_listing_optimizer_v1_2.py`
- older config-only optimizer area.

Evidence:

- Pricing is being consolidated under Marketplace Intelligence,
- filenames retain explicit old versions,
- acceptance tests may still exercise compatibility behavior.

Conclusion: adapters may remain; independent formulas should be retired only after parity tests.

### Older System MarketIntelligence modules

`Platform/Putnam_OS/System/MarketIntelligence/`

Evidence:

- pricing submodules are being redirected to Marketplace Intelligence,
- Models/Identity/Inspector still overlap current package concepts.

Conclusion: inspect callers and test fixtures before any archive decision.

### Project auditor

`Platform/Putnam_OS/cardvector_project_auditor.py`

Evidence: prior audit utility in active platform root; current governance uses Markdown Phase 0 reports.

Conclusion: likely archive candidate after confirming it is not part of a repeatable governance process.

### Business Intelligence v0.1

`Platform/Marketplace_Intelligence/business_intelligence/business_intelligence_v0_1.py`

Evidence: explicit `v0_1` prototype naming and separate helper logic.

Conclusion: determine whether it is a supported CLI or experiment.

## Deferred Or Not Dead

### Archived scanner and overlay

The scanner and overlay under `Archive` are already correctly classified. They are historical reference, not dead production files requiring further cleanup.

### Decision Engine

`System/decision_engine` contains placeholders and stale path assumptions, but Putnam OS still exposes related Marketplace behavior. It is incomplete/partially active, not proven dead.

### Empty or lightly populated folders

- `Collectr`
- `Platform/Pokemon_Live_Price_Lookup`
- `Shared`

Empty status does not prove safe deletion. User review is required.

### Runtime and business data

Generated captures, logs, exports, caches, audit state, and operator records are not dead code. Retention and backup policy must be decided separately.

### Migration scripts

Supabase and Marketplace Intelligence migrations are not dead after application. They are durable schema history and must remain versioned.

## Temporary Work In Current Working Tree

Current untracked items include:

- `patch_cardvector_ebay_existing_listings.py`
- pricing repository/migration/tests,
- `Docs/PriceVector`,
- an eBay business-order folder,
- `.bak` files.

These are active or operator-created changes, not cleanup targets. Resolve or commit them before architecture cleanup.

## Temporary Code Promoted Into Production

Potential examples:

- monolithic UI-local helpers that became reusable business behavior,
- versioned backup modules beside production,
- direct root/path fallback logic copied into multiple scripts,
- prototype Decision Engine checks still visible in Marketplace UI,
- old Seller Tools location semantics still available beside the physical registry.

Each requires behavior/caller tests before removal.

## Safe Investigation Sequence

1. Commit current valid work.
2. Search source, tests, launchers, docs, shortcuts, and scheduled tasks.
3. Run production workflow smoke tests.
4. Move one high-confidence group to a timestamped archive with a manifest.
5. Re-run tests and launcher validation.
6. Commit that package separately.
7. Keep rollback as a simple move back.

## Do Not Touch Yet

- `putnam_os.py`
- `main.py`
- current Price Vector modified/untracked files
- `inventory_locations.py`
- mobile queue and Supabase migrations
- operational inventory/acquisition/session JSON
- `Capture`, `Business`, and `Data` contents
- archived scanner benchmark/reference data
- any file whose only evidence is “old-looking”
