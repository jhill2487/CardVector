# CardVector Repository Inventory

**Audit date:** 2026-07-17
**Classification basis:** Current files, imports, launchers, documentation, Git tracking, and prior Phase 0 evidence.

## Classification Definitions

- **Production:** Used by the validated daily CardVector workflow.
- **Development:** Active source, tests, migrations, or work in progress.
- **Test:** Fixtures, test runners, and validation artifacts.
- **Archive:** Intentionally retained historical material.
- **Legacy:** Superseded or stale implementation still outside the archive.
- **Business Data:** Operator-owned business records or external inputs.
- **Generated Runtime:** Outputs, logs, caches, captures, or resumable state.
- **Unknown:** Purpose or current usage is not sufficiently proven.

## Root Folder Map

| Folder | Observed purpose | Classification | Long-term architecture | Notes |
|---|---|---|---|---|
| `.agents/` | Historical session/agent support files | Legacy / Work Sessions | No at root | Keep until reviewed; do not treat as production source |
| `.git/` | Git repository metadata | Production infrastructure | Yes | Never modify manually |
| `.github/` | GitHub Actions deployment workflow | Production infrastructure | Yes | `pages.yml` exports the public site to `CardVector-site` |
| `Archive/` | Historical projects, scanners, backups, reports, and experiments | Archive | Yes | Correct owner for non-production reference code |
| `Business/` | eBay store files, inventory business records, pricing revisions | Business Data | Yes | Contains two stale hard-coded launcher scripts |
| `Capture/` | Dated desktop/mobile capture outputs and physical-inventory sessions | Generated Runtime / Business Data | Yes as runtime data | Must remain outside source ownership |
| `Collectr/` | No tracked implementation found during this audit | Unknown | Review | Do not remove without operator confirmation |
| `Data/` | Config, imports, exports, logs, media, processed data | Generated Runtime / Business Data | Yes | Some tracked config coexists with ignored runtime output |
| `Docs/` | Governance, current documentation, Price Vector docs, public site source | Production documentation / Development | Yes | Also serves as private public-site source for export |
| `MobileCapture/` | Converted, failed, and processing queues | Generated Runtime | Yes as runtime data | Not source code |
| `Platform/` | Active CardVector applications and reusable code | Production / Development | Yes | Primary source root |
| `Putnam_Content/` | Content and media workflow material | Business Data | Yes, if actively used | Not part of CardVector application architecture |
| `Shared/` | Templates and utilities directories | Development / Unknown | Consolidate intentionally | Nearly empty; not yet a canonical shared-code owner |
| `supabase/` | Versioned database migrations and capture/location contracts | Production infrastructure | Yes | Correct source owner for Supabase schema |
| `Tools/` | Deployment, validation, contract tests, helper utilities | Development / Test | Yes | Must not become a business-logic owner |
| `Work_Sessions/` | Temporary validation exports and development work products | Generated Runtime / Work Sessions | Yes | Should remain ignored and disposable after review |

## Root Files

| File | Purpose | Classification | Long-term |
|---|---|---|---|
| `.env.example` | Environment-variable template | Production documentation | Keep |
| `.gitattributes` | Git behavior | Production infrastructure | Keep |
| `.gitignore` | Runtime/output exclusion rules | Production infrastructure | Keep and refine carefully |
| `.putnam_root` | Repository-root marker used by path resolution | Production infrastructure | Keep unless replaced by a documented equivalent |
| `AGENTS.md` | Agent entry-point stub | Production governance, currently stale | Keep, correct links later |
| `PLATFORM_VISION.md` | High-level platform vision | Production governance | Keep or cross-link into canonical docs |
| `patch_cardvector_ebay_existing_listings.py` | Untracked patch script from active work | Development / Temporary | Do not classify as permanent until current work is resolved |

## Platform Inventory

### `Platform/Marketplace_Intelligence`

**Purpose:** Canonical market evidence, FMV, pricing recommendation, decision, report, bulk export, UI, and CLI package.

**Classification:** Production / Active Development.

**Long-term:** Yes. This is the recommended canonical Marketplace and Price Vector owner.

Major areas:

- `marketplace_intelligence/engine.py`: orchestration.
- `pricing_engine.py`: FMV/strategy/price calculation and compatibility interfaces.
- `models.py`: listing, evidence, recommendation, and result models.
- `providers.py`: provider abstraction and stored-data adapters.
- `decision_engine.py`: recommendation classification.
- `csv_import.py`, `listing_parser.py`: active-listing input.
- `reports.py`, `bulk_export.py`: outputs.
- `ui.py`, `cli.py`: standalone entry surfaces.
- `config.py`, `utils.py`: subsystem configuration and helpers.
- `business_intelligence/`: separate early business-intelligence tool.
- `migrations/`: currently untracked Price Vector persistence migration.
- `tests/`: Marketplace Intelligence and Price Vector tests.

Current caution: several files are modified and new pricing persistence/test files are untracked. They represent active work, not audit artifacts.

### `Platform/Putnam_OS`

**Purpose:** CardVector OS desktop workflow and associated operational modules.

**Classification:** Production / Active Development.

**Long-term:** Yes, but internal responsibilities should be separated.

Major areas:

- Root launchers and README.
- `System/app/`: production UI plus focused capture, inventory, orders, reconciliation, and workflow modules.
- `System/tools/`: mobile queue and label tools.
- `System/MarketIntelligence/`: older/compatibility market models, pricing, identity, and inspection modules.
- `System/decision_engine/`: rule/check framework with active and placeholder checks.
- `System/config/`: application and business settings.
- `System/data/`: inventory, acquisition, session, audit, and cache state.
- `System/cache/`, `System/logs/`: generated runtime.
- `Putnam_Seller_Tools/`: seller audit, SKU planning, and older location registry.
- `Putnam_Listing_Optimizer/`: listing optimizer configuration and compatibility area.
- `Completed Jobs/`, `Incoming Files/`, `config/`: operational folders.

### `Platform/Putnam_Platform`

**Purpose:** Earlier OBS capture/autocrop implementation and launchers.

**Classification:** Legacy Reference with some runnable code.

**Long-term:** No as a parallel platform. Reusable behavior should migrate to canonical Capture ownership only after validation.

Major files:

- `capture/Putnam_Capture.py`
- `capture/obs_capture_autocrop.py`
- `capture/README.md`
- `tools/Run_Putnam_Capture.bat`
- `tools/Run_OBS_AutoCrop.bat`

### `Platform/Pokemon_Live_Price_Lookup`

**Purpose:** No current tracked implementation found.

**Classification:** Unknown / Empty legacy location.

**Long-term:** No unless a future approved subsystem is placed here.

### `Platform/putnam_paths.py`

**Purpose:** Repository and standard path resolution.

**Classification:** Production shared infrastructure.

**Long-term:** Yes, as the starting point for canonical filesystem ownership.

## Business Inventory

### `Business/eBay_Store_Items`

**Purpose:** eBay reports, exports, branding, order/business records, pricing revisions, and operator data.

**Classification:** Business Data.

**Long-term:** Yes.

Concern: `Pricing_Revisions` contains launchers hard-coded to an old username and old pre-reorganization code locations.

### `Business/Inventory`

**Purpose:** Inventory business records.

**Classification:** Business Data.

**Long-term:** Yes.

## Data Inventory

| Area | Purpose | Classification |
|---|---|---|
| `Data/Config` | Shared operational configuration and legacy registry fallback | Mixed versioned config / runtime |
| `Data/Imports` | Imported external files | Generated / Business Data |
| `Data/Exports` | eBay exports, reports, pick lists, labels | Generated Runtime |
| `Data/Logs` | Performance and operational logs | Generated Runtime |
| `Data/Media` | Generated or working media | Generated Runtime |
| `Data/Processed` | Processed artifacts | Generated Runtime |
| `Data/Completed_Jobs` | Completed workflow output | Generated Runtime |

Long-term recommendation: retain this root but define which files are versioned samples/defaults versus operator state. `.gitignore` does not untrack files that were already committed.

## Documentation Inventory

Current active documents include:

- `Docs/PROJECT_MANUAL.md`
- `Docs/PROJECT_INDEX.md`
- `Docs/PROJECT_ROADMAP.md`
- `Docs/DEVELOPMENT_LOG.md`
- `Docs/CHANGELOG.md`
- `Docs/README.md`
- `Docs/PriceVector/*`
- `Docs/Reference/Putnam_Standards/*`
- `Docs/Reports/*`

Public static site source includes:

- `Docs/index.html`
- `Docs/404.html`
- `Docs/app.js`
- `Docs/styles.css`
- `Docs/mobile-capture-config.js`
- `Docs/CNAME`
- `Docs/assets/*`

Historical governance and Phase 0 reports are under:

- `Archive/Documentation/`
- `Archive/Reports/reports/`

Observed issue: root `AGENTS.md` refers to older document paths that are no longer present.

## Archive Inventory

Major archive areas:

- `Archive/Historical/`: historical application and business-development material.
- `Archive/Projects/`: retired or reference projects, including the Pokemon Lookup Overlay.
- `Archive/Scanner_Development/`: scanner, OCR, recognition, benchmark, and image-processing history.
- `Archive/Documentation/`: archived constitution/governance.
- `Archive/Reports/`: Phase 0 and other audit reports.
- Historical backups and experiments.

**Classification:** Archive.

**Long-term:** Yes. Archive is the correct destination, but production imports and launchers must never reference it.

## Scanner And Overlay Status

### Observed

- Scanner/OCR/recognition implementations are under `Archive/Scanner_Development`.
- The Putnam Pokemon Lookup Overlay is under `Archive/Projects/Putnam_Pokemon_Lookup_Overlay_v0.9.3`.
- No active `Platform/Scanner` implementation exists.
- CardVector production documentation explicitly keeps recognition outside the current platform workflow.

### Recommendation

Treat these as historical reference, not current dependencies. If scanner work resumes, create one approved canonical owner rather than restoring multiple versioned scripts.

## Runtime And Tracking Findings

The repository contains generated runtime areas that are correctly ignored now, including Capture, MobileCapture, exports, logs, caches, and work sessions. However, tracked files remain in some operational areas:

- ETB/location configuration or registry data.
- Current session and audit JSON.
- Acquisition records.
- Market cache snapshots.
- Application configuration containing workstation-local paths.

Do not remove them from Git without:

1. identifying the authoritative operational store,
2. backing up business state,
3. creating sample/default files,
4. documenting workstation synchronization,
5. validating startup with missing runtime state.

## Long-Term Disposition Summary

| Area | Disposition |
|---|---|
| `Platform/Marketplace_Intelligence` | Keep and strengthen as canonical Marketplace/Price Vector |
| `Platform/Putnam_OS` | Keep; incrementally separate UI and application services |
| `Platform/Putnam_Platform` | Consolidate reusable capture behavior, then archive |
| `Archive` | Keep isolated |
| `Business` | Keep as operator-owned business area |
| `Data` | Keep as runtime/data area with explicit retention rules |
| `Docs` | Keep; repair governance entry points |
| `Tools` | Keep for maintenance/deployment/tests, not business logic |
| `supabase` | Keep as schema/migration source |
| `Capture`, `MobileCapture`, `Work_Sessions` | Keep as ignored runtime areas |
| `Shared` | Promote only through an approved shared-infrastructure migration |
| `Collectr`, empty platform folders | Needs user review |
