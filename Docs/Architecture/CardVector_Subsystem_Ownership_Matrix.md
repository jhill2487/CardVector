# CardVector Subsystem Ownership Matrix

**Status:** Proposed
**Evidence:** `Module_Ownership.md`, `Duplicate_Module_Report.md`, and current source paths

## Matrix

| Responsibility | Current implementation(s) | Canonical target package | Migration | Adapter |
|---|---|---|---|---|
| Application startup | Production VBS -> `putnam_os.py` | `cardvector.__main__`, `cardvector.bootstrap` | Required | Launcher redirect |
| Desktop shell | `putnam_os.py`, overlapping `main.py` | `cardvector.presentation.desktop` | Required | Existing classes remain during extraction |
| Navigation | `PutnamOS.build_ui`, `show_page` | `cardvector.presentation.desktop.navigation` | Required | No external adapter expected |
| Cross-workflow orchestration | `putnam_os.py`, `workflow_context.py` | `cardvector.application.workflows` | Required | Existing UI methods delegate |
| Background jobs | UI threads/callbacks, mobile queue loops | `cardvector.application.background_jobs` plus subsystem workers | Required | Existing scheduling methods delegate |
| Capture domain | UI functions, `capture_studio.py` | `cardvector.capture` | Required | Old module forwards |
| OBS connection | `obs_connection_manager.py` | `cardvector.integrations.obs` implementing Capture port | Required | Old import path forwards |
| Mobile capture queue | `System/tools/mobile_capture_queue.py` | `cardvector.capture.application` with Supabase adapter | Required | CLI wrapper remains |
| Thumbnails/pairs | `capture_pair_rows`, UI preview methods | `cardvector.capture` metadata service; UI renders | Required | Current functions delegate |
| Scanner recognition | CardUploader external; archived scanner research | External CardUploader; future `cardvector.scanner` only by approval | No current migration | CardUploader adapter |
| Card identification model | CSV/provider fields, CardUploader data | `cardvector.shared.domain.cards` if shared contract is proven | Discovery required | External identity adapter |
| Marketplace Intelligence | `Platform/Marketplace_Intelligence` | `cardvector.marketplace_intelligence` | Package migration required | Old package forwards |
| Market evidence | MI providers plus UI comp helpers | `cardvector.marketplace_intelligence` | Required | UI helper wrappers temporarily |
| Fair Market Value | MI/active Price Vector work | `cardvector.marketplace_intelligence` | Required | Legacy market-price mapping |
| Price Vector | MI pricing engine | `cardvector.marketplace_intelligence` | Required | Putnam OS/optimizer adapters |
| Bulk repricing | MI plus `bulk_price_engine.py`, `main.py` | MI pricing; Listings owns export preparation | Required | Preserve CLI/UI result shapes |
| Pricing persistence | Active untracked MI repository/migration | `cardvector.marketplace_intelligence` ports + infrastructure repository | Required | Existing API adapter |
| Inventory domain | `inventory_locations.py`, UI conversion/audit | `cardvector.inventory` | Required | Old functions/classes forward |
| Location cloud sync | `mobile_capture_queue.py`, Supabase migration | Inventory application + Supabase integration | Required | Queue command compatibility |
| Conversion sessions | `putnam_os.py`, runtime JSON | `cardvector.inventory.application` | Required | Current UI/session functions delegate |
| Reconciliation | `inventory_reconciliation.py` | `cardvector.inventory` | Required | CLI wrapper |
| QR payloads/labels | Inventory module and label tool | Inventory owns payload/data; Reporting renderer outputs | Required | Existing tool wrapper |
| Listings | UI/export helpers, bulk engine, Listing Optimizer | `cardvector.listings` | Required | Existing export functions delegate |
| eBay CSV preservation | `prepare_listing_export_rows`, MI bulk export | Listings + eBay integration | Required | Legacy function wrapper |
| Orders | `orders_fulfillment.py`, UI callbacks | `cardvector.orders` | Required | Existing module wrapper |
| Shipping | eBay policies in `putnam_os.py`/config | `cardvector.shipping` | Required | Current policy functions delegate |
| Content | `content_page`, `Putnam_Content` business data | `cardvector.content` if retained | Decision required | None until approved |
| Analytics | performance logs, MI business-intelligence prototype | `cardvector.analytics` | Required after definitions approved | Existing reports remain |
| Reports | many subsystem-specific writers | Subsystem semantics + `cardvector.reporting` renderers | Required incrementally | Preserve output filenames/formats |
| Configuration | multiple JSON roots/loaders | `cardvector.infrastructure.configuration` | Required | Legacy config facade |
| Logging | ad hoc files and UI logs | `cardvector.infrastructure.logging` | Required | Preserve business audit logs |
| Database access | Supabase, JSON, active MI SQLite plan | Owner ports + `cardvector.infrastructure.persistence` | Required | Repository adapters |
| Filesystem access | direct `Path` operations throughout | `cardvector.infrastructure.filesystem` | Required | Path facade |
| Runtime paths | `Platform/putnam_paths.py` plus duplicates | `cardvector.infrastructure.filesystem.paths` | Required | `putnam_paths.py` forwarding module |
| Imports | UI/CLI CSV readers | Owning subsystem importer | Required | Existing function signatures |
| Exports | UI, MI, Orders, labels | Owning subsystem + Reporting renderer | Required | Existing output contracts |
| CardUploader API/handoff | URL, CSV, caches, reconciliation | `cardvector.integrations.carduploader` | Required | Current URL/config names preserved |
| eBay integration | CSV input/export and browser handoff | `cardvector.integrations.ebay` | Required | Existing actions preserved |
| TCGplayer integration | MI providers/config | `cardvector.integrations.tcgplayer` | Required when live/stored provider matures | Provider adapter |
| Supabase integration | Docs app and desktop queue | `cardvector.integrations.supabase` desktop; public JS remains separate | Required | Queue wrapper |
| Error handling | exceptions, message boxes, text logs | domain/app errors + presentation mapping | Required | Legacy exception translation |
| Validation | scattered functions | Owning domain/application plus shared primitives | Required | Existing function wrappers |
| Shared models | duplicated dicts/dataclasses | `cardvector.shared.domain` only for proven cross-owner concepts | Discovery required | Shape adapters |
| Public website | `Docs` and export tool | Static source/export boundary remains | No desktop package migration | Existing deployment workflow |

## Ownership Clarifications

### Scanner And Recognition

Known:

- current production recognition is CardUploader,
- scanner/OCR source is archived,
- CardVector production does not import recognition code.

Decision:

- `cardvector.scanner` is a reserved future owner, not an implementation authorization.
- Card identity used across imports/listings may become a shared domain contract only after field semantics are documented.

### Listings Versus Marketplace Intelligence

Marketplace Intelligence answers:

- what market evidence exists,
- what FMV is,
- what listing price is recommended.

Listings answers:

- what listing record is valid,
- which business policies and marketplace columns are required,
- how a reviewed result becomes an eBay-ready export.

Listings must never recalculate FMV or Price Vector.

### Inventory Versus Capture

Capture records where and how images were acquired. Inventory owns ETB/location identity, occupancy, and conversion completion. Cross-subsystem assignment is orchestrated by the application layer using IDs, not imports between infrastructure modules.

### Reports Versus Analytics

Reporting renders and catalogs outputs. Analytics defines metrics and computes insight. A report may present analytics, but rendering must not become a competing analytics implementation.

## Public API Expectations

Each canonical package should eventually expose:

- command/query input models,
- result models,
- service interfaces,
- domain errors,
- explicitly stable constants.

Internal repositories, parsers, widgets, and vendor clients are not public imports.

## Migration Priority

1. Startup, paths, configuration, logging.
2. Marketplace Intelligence compatibility consolidation.
3. Application workflow context.
4. Capture.
5. Inventory.
6. Listings/shipping.
7. Orders.
8. Analytics/reporting/content decisions.
9. Scanner only through separate approval.
