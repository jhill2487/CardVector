# CardVector Module Ownership

**Audit date:** 2026-07-17
**Purpose:** Define current owners and recommended permanent owners without authorizing file moves.

## Ownership Principles

1. One canonical implementation per responsibility.
2. UI presents and delegates; it does not own business rules.
3. External systems retain their real responsibilities.
4. Runtime data ownership is distinct from source-code ownership.
5. Compatibility adapters may remain while callers migrate, but they do not calculate independently.

## Responsibility Matrix

| Responsibility | Current owner(s) | Recommended permanent owner | Confidence |
|---|---|---|---|
| Production bootstrap | VBS launcher -> `putnam_os.py` | `Platform/main.py` with one production launcher | High |
| Desktop GUI | `System/app/putnam_os.py` | `Platform/Putnam_OS/app` | High |
| Workflow orchestration | `putnam_os.py`, `workflow_context.py` | `Platform/Putnam_OS/application` | High |
| Market evidence | Marketplace Intelligence, some UI matching | `Platform/Marketplace_Intelligence` | High |
| FMV | Marketplace Intelligence / active Price Vector work | `Platform/Marketplace_Intelligence` | High |
| Pricing recommendation | Marketplace Intelligence plus compatibility callers | `Platform/Marketplace_Intelligence` | High |
| Marketplace decisions | Marketplace Intelligence and older Decision Engine | Marketplace Intelligence for listing-price decisions | Medium |
| Capture sessions | Capture Studio, UI, legacy capture | `Platform/Capture` | High |
| OBS connection | `obs_connection_manager.py` | `Platform/Capture` | High |
| Mobile capture queue | `mobile_capture_queue.py` | `Platform/Capture` | High |
| Inventory locations | `inventory_locations.py`, Supabase contract | `Platform/Inventory` | High |
| Conversion sessions | `putnam_os.py` plus runtime JSON | `Platform/Inventory` | High |
| Inventory reconciliation | `inventory_reconciliation.py` | `Platform/Inventory` | High |
| SKU repair planning | Seller Tools | Inventory adapter/tool, preserving audit use | Medium |
| Orders/pick lists | `orders_fulfillment.py` and UI | `Platform/Orders` | High |
| Reporting | Per-subsystem renderers | Each subsystem; shared rendering utilities only | High |
| Paths/filesystem | `Platform/putnam_paths.py` plus duplicates | `Platform/Shared` | High |
| Configuration | Multiple config roots/loaders | `Platform/Shared` contracts; subsystem-owned schemas | Medium |
| Logging | Ad hoc across modules | `Platform/Shared` logging infrastructure | High |
| CSV/money/file helpers | Repeated local helpers | `Platform/Shared` after semantic review | Medium |
| Public site export | `Tools/export_cardvector_site.py` | `Tools` | High |
| Supabase schema | `supabase/migrations` | `supabase` | High |
| Recognition | CardUploader external; archived scanner history | CardUploader external in current product | High |
| Scanner research | Archive | No production owner until approved | High |
| Business data | `Business` and external services | Operator/business, not Platform | High |
| Runtime output | `Data`, `Capture`, `MobileCapture`, Work Sessions | Runtime data roots, not source modules | High |

## GUI Ownership

### Current

`putnam_os.py` owns both presentation and substantial application behavior.

### Permanent

`Platform/Putnam_OS/app` should own:

- windows, frames, dialogs, status indicators,
- presentation models,
- event binding,
- background task presentation,
- operator navigation.

It must not own:

- pricing formulas,
- location mutation rules,
- queue claim semantics,
- order parsing,
- CSV schema discovery,
- direct business-data persistence.

## Workflow Orchestration Ownership

`Platform/Putnam_OS/application` should own:

- pending-work aggregation,
- exact job context,
- Capture -> CardUploader handoff,
- CSV import -> pricing handoff,
- pricing -> eBay export handoff,
- actionable alerts,
- background task coordination.

`workflow_context.py` is the strongest current seed for this ownership.

## Marketplace And Pricing Ownership

`Platform/Marketplace_Intelligence` owns:

- normalized market evidence,
- provider adapters,
- Fair Market Value,
- FMV confidence/reasoning,
- Price Vector strategy,
- recommended listing price,
- final listing-price persistence,
- approval/decision outputs when implemented,
- marketplace-specific pricing/export analysis.

Putnam OS may expose UI and compatibility adapters but must not calculate prices independently.

## Capture Ownership

`Platform/Capture` should own:

- capture session model,
- front-only and front/back pairing,
- OBS connection and capture,
- mobile queue polling and claiming,
- authenticated image download,
- dated folder routing,
- capture manifests,
- thumbnails and pair metadata,
- capture-specific status and errors.

It must not own recognition, pricing, inventory valuation, or CardUploader internals.

## Inventory Ownership

`Platform/Inventory` should own:

- ETB and location identity,
- location validation and sequence,
- occupancy and capacity,
- active location,
- conversion session state,
- local/cloud synchronization,
- location QR payloads,
- inventory reconciliation,
- label data contracts.

Rendering PDF/HTML labels may use separate renderers, but payload and identity rules belong here.

## Orders Ownership

`Platform/Orders` should own:

- eBay order CSV normalization,
- order/line-item grouping,
- fulfillment models,
- pick-list rendering,
- order report outputs.

It must not duplicate CardUploader managed-inventory picking or purchase shipping labels unless a future approved integration is added.

## Reporting Ownership

Reports should stay close to the subsystem that defines their meaning:

- Marketplace reports -> Marketplace Intelligence.
- Inventory reconciliation/location reports -> Inventory.
- Pick lists -> Orders.
- Capture manifests -> Capture.
- Cross-workflow operator summary -> Putnam OS application.

Shared code may provide CSV, text, HTML, or PDF primitives but not report business semantics.

## Shared Infrastructure Ownership

`Platform/Shared` should own:

- root and portable path resolution,
- atomic file write helpers,
- safe filenames,
- common timestamp parsing,
- structured application logging,
- configuration source loading,
- common CSV primitives,
- common decimal serialization.

Subsystem-specific column matching or business rounding must remain in the subsystem.

## Configuration Ownership Contract

Recommended categories:

| Category | Owner | Git |
|---|---|---|
| Default settings | Subsystem source/config | Versioned |
| Schema/validation | Subsystem | Versioned |
| Operator preferences | Data/config runtime | Usually not versioned |
| Workstation paths/devices | Data/config runtime or environment | Not versioned |
| Secrets | Environment/secret manager | Never versioned |
| Public browser config | Public site source | Versioned, no private secrets |
| Session/resume state | Runtime data | Not versioned |

## External Ownership Boundaries

### CardUploader

Owns card recognition and its managed marketplace inventory behavior. CardVector owns handoff context and supported import/reconciliation adapters.

### eBay

Owns listing publication, marketplace inventory, orders, and fulfillment platform behavior. CardVector owns supported CSV analysis/export and browser handoff.

### Supabase

Provides cloud persistence, authentication, storage, and RPC execution. CardVector owns versioned schema/migrations and client contracts.

### OBS

Provides image capture. CardVector Capture owns connection management and session handling.

## Ownership Decisions Still Required

1. Is standalone Marketplace Intelligence a permanent product surface or only a reusable engine plus diagnostics?
2. Is `main.py` used by any operator shortcut or only by tests/development?
3. Are legacy standalone OBS capture tools still used?
4. Should Seller Tools remain a named product area or become Inventory/Marketplace maintenance tools?
5. Which current operational JSON files must synchronize across workstations?
6. Is the older Decision Engine a future Marketplace feature, a Putnam OS alert service, or a deferred prototype?
