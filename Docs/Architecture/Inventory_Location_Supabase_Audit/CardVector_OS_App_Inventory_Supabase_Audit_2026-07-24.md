# CardVector OS and CardVector.app Inventory, Location, Storage, and Supabase Audit

Date: 2026-07-24

Status: Investigation complete. No code, schema, launcher, runtime data, inventory data, or production behavior was changed.

## 1. Current Architecture

### Application Architecture

CardVector currently has two active application surfaces:

1. CardVector.app static web/mobile surface in `Docs/`.
2. CardVector OS desktop application launched through `Platform/Putnam_OS/Run CardVector OS Production.vbs`, targeting `Platform/Putnam_OS/System/app/putnam_os.py`.

The canonical architecture through Phase 8 says:

- `Platform/cardvector/application` owns orchestration.
- `Platform/cardvector/capture` owns capture contracts.
- `Platform/cardvector/batch_workflow` owns batch milestone status only.
- `Platform/cardvector/marketplace_intelligence` owns pricing, FMV, Price Vector, Business Profile, and business rules.
- CardUploader remains the external canonical owner for managed inventory, card recognition, quantities, locations, allocation, picking, and inventory lifecycle.

That means the requested target, "Supabase is the single source of truth for inventory, ETBs, locations, storage, and captures," is not the current accepted architecture. It would supersede the current CardUploader inventory ownership decision and must be treated as a new architecture decision.

### Repository and Service Layer

| Area | Current implementation | Pattern |
| --- | --- | --- |
| Mobile capture web | `Docs/app.js` | Browser-side Supabase client and local draft cache |
| Desktop mobile queue | `Platform/Putnam_OS/System/tools/mobile_capture_queue.py` | Direct Supabase REST/Storage client plus local staging |
| Inventory facade | `Platform/cardvector/application/inventory.py` | Application facade over CardUploader snapshot service and ETB projection delegates |
| CardUploader inventory | `Platform/cardvector/integrations/carduploader/inventory.py` | Read-only CSV snapshot service |
| Batch workflow | `Platform/cardvector/batch_workflow/repository.py` | Atomic JSON repository |
| ETB registry | `Platform/Putnam_OS/System/app/inventory_locations.py` | Local JSON operational projection |
| Pricing persistence | `Platform/Marketplace_Intelligence/marketplace_intelligence/pricing_repository.py` | SQLite repository for pricing decisions, not inventory |

### Database and Store Inventory

No active `.db`, `.sqlite`, or `.sqlite3` files were found under active `Data/` or `Platform/` runtime roots during this audit. SQLite support exists for pricing decision persistence and tests, but it is not the current inventory or ETB registry source.

Active and relevant local stores:

| Store | Path or location | Current purpose | Authoritative? |
| --- | --- | --- | --- |
| Supabase Storage bucket | `mobile-capture-originals` | Mobile original photo uploads | Yes for uploaded original objects |
| Supabase capture tables | local migrations define `mobile_capture_sessions`, `mobile_capture_images` | Mobile capture queue/session metadata | Intended, but live REST check returned 404 |
| Supabase location tables | local migrations define `cardvector_etbs`, `cardvector_locations`, `cardvector_location_operators` | Cloud-visible ETB/location identity | Intended, but live REST check returned 404 |
| Browser `localStorage` | CardVector.app browser | Mobile draft session metadata | No, draft cache only |
| Browser IndexedDB | CardVector.app browser | Mobile draft image recovery | No, draft cache only |
| Current ETB registry JSON | `Platform/Putnam_OS/System/data/inventory/etb_location_registry.json` | Desktop ETB counts/status/projection | Current OS registry source, not Supabase-backed truth |
| Legacy ETB registry JSON | `Data/Config/etb_location_registry.json` | Old ETB registry fallback | Legacy/stale |
| Batch/User-SKU location registry | `Platform/Putnam_OS/System/config/location_registry.json` | Older listing/export location labels using `ETB-##-Letter` | Separate compatibility registry |
| Conversion session JSON | `Platform/Putnam_OS/System/data/inventory_conversion/sessions/*.json` | Physical inventory conversion workflow state | Local workflow state |
| Batch workflow JSON | `Platform/Putnam_OS/System/data/batch_workflows/*.json` | Batch milestone status | Local workflow status only |
| Capture session JSON | `Capture/**/capture_session.json` | Capture folder metadata | Local workflow context |
| Mobile processing manifests | `MobileCapture/Processing/**/mobile_capture_manifest.json` | Staged mobile capture metadata | Local processing artifact |
| CardUploader snapshot CSV | `Data/Exports/carduploader_inventory_snapshot.csv` | CardUploader inventory snapshot evidence | Snapshot only |
| Inventory audit/reconciliation reports | `Data/Exports/Reconciliation/*.json`, inventory audit reports | Reports and review artifacts | Generated evidence, not source of truth |
| Desktop cache folder | `Platform/Putnam_OS/System/cache` | Local cache for screen/workflow helpers | Cache only |
| Thumbnail caches | in-memory Tkinter caches in `putnam_os.py` | Capture preview performance | Cache only |

### Data Volume Observed

Relevant file counts under active roots:

| Root/type | Count |
| --- | ---: |
| `Capture` `.jpg` | 2107 |
| `Capture` `.json` | 65 |
| `MobileCapture` `.jpg` | 545 |
| `MobileCapture` `.json` | 24 |
| `Platform/Putnam_OS/System/data` `.json` | 48 |
| `Platform/Putnam_OS/System/config` `.json` | 10 |
| `Data` `.csv` | 98 |
| `Data` `.json` | 31 |
| `supabase` `.sql` migrations | 4 |

## 2. Data Flow Diagrams

### Mobile Capture Success Path

```text
CardVector.app
  -> Supabase Auth
  -> localStorage draft metadata
  -> IndexedDB draft images
  -> Supabase Storage mobile-capture-originals
  -> public.mobile_capture_sessions
  -> public.mobile_capture_images
  -> session status PENDING_CONVERSION
```

### Mobile ETB/Location Selection Path

```text
CardVector.app
  -> cardvector_location_operators authorization
  -> cardvector_etbs list
  -> cardvector_locations list
  -> optional RPC cardvector_create_next_location
  -> selected ETB/location stored on capture session
```

### Desktop Queue Processing Path

```text
CardVector OS auto queue
  -> MobileCaptureQueueService.environment_ready()
  -> process_next_pending()
  -> sync_cloud_location_registry()
  -> read PENDING_CONVERSION mobile_capture_sessions
  -> claim session atomically
  -> read mobile_capture_images
  -> download Storage objects
  -> write Capture/MM.DD.YY or Capture/Physical_Inventory_Conversion/MM.DD.YY
  -> write capture_session.json
  -> write MobileCapture/Processing manifest
  -> for PHYSICAL_INVENTORY write local conversion session as Mobile Capture Staged
```

### Desktop ETB Registry Display Path

```text
CardVector OS Inventory page
  -> inventory_refresh_etb_locations()
  -> repair_completed_inventory_conversion_registry()
  -> etb_location_rows()
  -> InventoryApplication.list_location_projection()
  -> legacy delegate
  -> Platform/Putnam_OS/System/data/inventory/etb_location_registry.json
  -> table display
```

This path does not read Supabase directly.

### CardUploader Inventory Snapshot Path

```text
CardUploader export CSV
  -> CardUploaderInventoryService.load_inventory()
  -> InventoryApplication.load_inventory()
  -> desktop inventory views/search/reports
```

The current CardUploader service is explicitly read-only and reports `authoritative_write = False`, `reservations = False`, `allocations = False`, `pick_confirmation = False`, and `live_sync = False`.

## 3. Database Schema Summary

### Local Supabase Migrations

The repository defines these Supabase objects:

| Migration | Objects |
| --- | --- |
| `20260713153000_mobile_capture.sql` | `mobile_capture_sessions`, `mobile_capture_images`, private storage bucket, capture triggers, RLS policies, storage policies |
| `20260713170000_mobile_capture_authenticated_grants.sql` | authenticated grants for capture tables |
| `20260716090000_mobile_capture_type.sql` | `mobile_capture_sessions.capture_type` and check constraint |
| `20260716130000_mobile_location_registry.sql` | `cardvector_location_operators`, `cardvector_etbs`, `cardvector_locations`, RLS, secure next-location RPC |

Foreign keys and relationships:

- `mobile_capture_images.capture_session_id` references `mobile_capture_sessions.capture_session_id`.
- `mobile_capture_sessions.operator_id` and `user_id` reference `auth.users`.
- `mobile_capture_images.user_id` references `auth.users`.
- `cardvector_location_operators.user_id` references `auth.users`.
- `cardvector_etbs.created_by` references `auth.users`.
- `cardvector_locations.etb_id` references `cardvector_etbs.etb_id`.
- `cardvector_locations.created_by` references `auth.users`.

Important missing relationship:

- `mobile_capture_sessions.etb_location_id` is not defined as a foreign key to `cardvector_locations.location_id`.

Indexes:

- `mobile_capture_sessions(status, submitted_at)`
- `mobile_capture_sessions(etb_location_id, status)`
- `mobile_capture_images(capture_session_id, sequence_number)`
- unique `mobile_capture_images(capture_session_id, coalesce(image_order, sequence_number))`
- unique `mobile_capture_images(storage_bucket, storage_path)`
- `cardvector_locations(etb_id, location_code)`

Triggers:

- `mobile_capture_sessions_normalize_before_write`
- `mobile_capture_sessions_touch_updated_at`
- `mobile_capture_images_normalize_before_write`
- `cardvector_location_operators_touch_updated_at`
- `cardvector_etbs_touch_updated_at`
- `cardvector_locations_touch_updated_at`

RLS policies:

- authenticated mobile operators can insert/read/update their own capture sessions/images under constrained policies.
- authenticated operators can read location identity only if authorized in `cardvector_location_operators`.
- direct authenticated insert/update/delete to location identity tables is revoked.
- location creation is restricted to the `cardvector_create_next_location` RPC.

Not found:

- Edge Functions
- Realtime publication setup
- database views
- materialized views
- inventory item tables
- card tables
- generic storage hierarchy tables
- photo-to-inventory linkage table
- collection metadata tables
- inventory status/history tables

### Live Supabase Verification

Configured project:

- `https://iqdpfgpkagjxzedfxrvn.supabase.co`

Read-only live verification on 2026-07-24:

| Object | Type | Result |
| --- | --- | --- |
| `mobile-capture-originals` | Storage bucket | HTTP 200, exists |
| `mobile_capture_sessions` | REST table endpoint | HTTP 404 Not Found |
| `mobile_capture_images` | REST table endpoint | HTTP 404 Not Found |
| `cardvector_etbs` | REST table endpoint | HTTP 404 Not Found |
| `cardvector_locations` | REST table endpoint | HTTP 404 Not Found |
| `cardvector_location_operators` | REST table endpoint | HTTP 404 Not Found |

No secret values were printed. This indicates the live project is only partially prepared, the migrations are not applied to the configured project, the tables are in a different schema, or the REST API schema cache/exposure does not include them.

## 4. Mobile Capture Write Trace

Starting from a successful capture in `Docs/app.js`:

1. Route `/location/<ETB-ID>/<LOCATION>`, `/etb/<ETB-ID>`, or `/capture` selects a capture destination.
2. Existing ETBs and locations are read from `cardvector_etbs` and `cardvector_locations`.
3. New locations are created only through RPC `cardvector_create_next_location`.
4. Camera capture starts only after explicit operator action.
5. Draft session metadata is stored in `localStorage`.
6. Draft image blobs are stored in IndexedDB for recovery.
7. `submitCapture()` upserts `mobile_capture_sessions`.
8. Each photo is uploaded to `mobile-capture-originals`.
9. Each photo row is upserted to `mobile_capture_images`.
10. The session is updated to `PENDING_CONVERSION`, with `original_image_locations` storing uploaded object references.

Mobile does not:

- write desktop local registry JSON;
- write CardUploader inventory;
- create card inventory records;
- update quantities;
- update card ownership;
- update order picking;
- mark ETB locations complete.

## 5. CardVector OS Data Sources by Screen/Area

| OS area | Primary data source | Reads Supabase directly? | Notes |
| --- | --- | --- | --- |
| Mobile Capture Queue | Supabase REST and Storage through `mobile_capture_queue.py` | Yes | Reads pending sessions/images, claims/stages sessions |
| Capture workspace | local capture folders, workflow context, queue service | Partially | Queue yes; thumbnails/folders local |
| Inventory conversion panel | local ETB registry JSON and local conversion-session JSON | No | Uses `etb_location_rows()` and current conversion session |
| ETB Location Registry | local ETB registry JSON plus completed local rollups | No | Does not read Supabase before rendering |
| Inventory Label Center | local ETB registry JSON | No | Generates labels from local registry/projection |
| Inventory review/audit | eBay active listing CSV and local audit session JSON | No | Not CardUploader live inventory |
| Inventory statistics | local audit/conversion session functions | No | Local session-derived stats |
| Reports | generated local CSV/JSON/text artifacts | No | Reports are outputs, not authoritative state |
| CardUploader inventory search/import | CardUploader export CSV snapshot | No | Snapshot adapter only |
| Batch workflow | local JSON batch workflow repository | No | Batch milestones only, no card-level inventory |
| Collection dashboard | no canonical Supabase collection table found | No | Any counts are local workflow/report derived |

## 6. Duplicate Models, Tables, Services, APIs, and Sync Logic

### Duplicate or Overlapping Concepts

| Concept | Implementations found | Assessment |
| --- | --- | --- |
| Inventory | CardUploader CSV snapshot, inventory audit sessions, reconciliation reports | CardUploader is documented owner; CardVector stores snapshots/reports only |
| ETBs | Supabase `cardvector_etbs`, local `etb_location_registry.json`, legacy `Data/Config/etb_location_registry.json` | Duplicate projections exist |
| Locations | Supabase `cardvector_locations`, local ETB child slots, old Seller Tools batch registry | Multiple concepts share ETB-like names but different semantics |
| Storage hierarchy | ETB A-J slots only; no generic Room/Shelf/Box/Binder/Cabinet model found | Target architecture not implemented |
| Capture history | Supabase sessions/images, local capture folders, mobile processing manifests, conversion sessions | Multiple lifecycle artifacts by design, but no canonical unified capture ledger |
| Collection metadata | reports, CSVs, CardUploader snapshot evidence | No canonical collection metadata table found |
| Sync | mobile queue cloud/local sync, CardUploader CSV snapshot import, local repair from completed sessions | Sync paths are fragmented and not a Supabase SOT model |

### ETB Format Split

Two ETB-like location formats exist:

- Modern capture/location format: `ETB-###-A`, for example `ETB-002-G`.
- Legacy batch/User-SKU format: `ETB-##-Letter`, for example `ETB-02-A`.

This is a source of operator confusion and future data-join risk.

### Services and Repositories

| Service/repository | Source of truth claim | Current behavior |
| --- | --- | --- |
| `MobileCaptureQueueService` | none for inventory | Supabase queue and local staging |
| `InventoryApplication` | facade only | Routes to CardUploader snapshot service and ETB projection delegates |
| `CardUploaderInventoryService` | CardUploader external | Read-only exported CSV snapshot parser |
| `JsonBatchWorkflowRepository` | batch milestone JSON only | Atomic JSON persistence, not inventory |
| `inventory_locations.py` | desktop operational projection | Local ETB registry JSON plus cloud identity merge |
| `PricingDecisionRepository` | pricing decisions | SQLite pricing records, unrelated to location registry |

## 7. Synchronization Flow

### Mobile Capture Sync

Mobile writes directly to Supabase and Storage. Desktop queue reads from Supabase, claims sessions, downloads images, stages files, and updates queue status.

This is cloud-to-local for capture processing.

### Location Registry Sync

`sync_cloud_location_registry()`:

1. Builds a snapshot from the local ETB registry.
2. Upserts local ETBs into `cardvector_etbs`.
3. Upserts local provisioned/used locations into `cardvector_locations`.
4. Reads cloud ETBs and locations back.
5. Merges cloud-created identities into local JSON as `cloud_provisioned` metadata.

This is two-way for identity only. It does not synchronize managed inventory or mark physical locations complete.

### Inventory Sync

No live two-way inventory sync was found.

Current inventory integration is snapshot based:

```text
CardUploader export CSV -> CardUploaderInventoryService -> CardVector views/reports
```

### Failed or Weak Sync Paths

1. Live Supabase expected table endpoints returned 404.
2. Inventory registry screen does not read Supabase directly.
3. Registry refresh does not run strict location sync before display.
4. Mobile-staged sessions remain `Mobile Capture Staged` and are skipped by registry repair.
5. Settings sync message appears to read result keys that do not match queue result names, making sync status easy to misread.
6. No canonical reconciliation joins cloud sessions, local staged sessions, local registry, and CardUploader inventory snapshot.

## 8. Root Cause Analysis

The primary root cause is split authority, not a single broken query.

CardVector.app mobile captures prove image/session work happened, but that work lands in Supabase capture tables/storage and then local staging artifacts. CardVector OS Inventory / ETB Location Registry reads local ETB registry JSON and completed conversion rollups. It does not use Supabase as the registry source and it does not treat `Mobile Capture Staged` as completed inventory.

Observed local conversion session state:

| Status | Count |
| --- | ---: |
| `Location Complete` | 10 |
| `Mobile Capture Staged` | 7 |
| `Ready for Capture` | 3 |
| `Waiting for Capture` | 1 |

Mobile-origin staged sessions observed:

| Session file | ETB/location | Cards | Mobile session |
| --- | --- | ---: | --- |
| `conversion_20260713_135913.json` | `ETB-001-C` | 2 | `19242ab2-47c6-4292-984d-a32a033a7da3` |
| `conversion_20260713_234422.json` | `ETB-005-A` | 34 | `0853bb7a-660e-41cb-a498-a05a0d0db1ca` |
| `conversion_20260713_234423.json` | `ETB-005-A` | 34 | `0853bb7a-660e-41cb-a498-a05a0d0db1ca` |
| `conversion_20260716_000208.json` | `ETB-002-G` | 80 | `3e83d3c2-c5bb-47e0-a077-3adf86ac5f43` |
| `conversion_20260716_000329.json` | `ETB-002-G` | 80 | `3e83d3c2-c5bb-47e0-a077-3adf86ac5f43` |
| `conversion_20260716_002720.json` | `ETB-002-G` | 5 | `7dcbb601-3284-4796-a6b9-0df257c1fb70` |
| `conversion_20260716_072818.json` | `ETB-005-B` | 27 | `326fd837-c515-4f81-8999-e0863e80a098` |

The registry repair code only updates the local registry when a conversion session status is `Location Complete`. That is correct for the current architecture, but it explains why mobile-staged work is invisible as completed inventory.

## 9. Location Architecture Findings

Current canonical ID support is limited to ETB A-J child slots:

- ETB: `ETB-###`
- Location code: `A` through `J`
- Location ID: `ETB-###-A`

No generic location model was found for:

- Room
- Closet
- Shelf
- Drawer
- Cabinet
- Storage Box
- Bin
- Binder
- arbitrary nested hierarchy

Current relationships:

| Relationship | Exists? | Notes |
| --- | --- | --- |
| Capture -> ETB/location | Yes | Stored in Supabase session fields and local `capture_session.json` |
| Photo -> Capture | Yes | Supabase image rows reference session; local capture records include image paths |
| ETB -> Location | Yes | Supabase `cardvector_locations.etb_id`; local nested JSON |
| Inventory -> Location | Partially | CardUploader snapshot uses `User SKU` as location-like field |
| Inventory -> ETB | Not canonical | Derivable only from user SKU/location conventions |
| Photo -> Inventory item | No canonical link found | Requires recognition/import handoff |
| Capture -> Inventory item | No canonical link found | Current workflow stages for CardUploader |

Everything does not reference one canonical Location ID today.

## 10. Proposed Final Architecture

To meet the desired end state, Supabase must become the authoritative database for:

- users/operators;
- cards/card identities;
- managed inventory items;
- canonical storage locations;
- ETBs as storage location nodes;
- photos and capture sessions;
- capture-to-inventory links;
- collection metadata;
- inventory status/history;
- sync state and conflict metadata.

Recommended high-level model:

```text
auth.users
  -> operators/profiles

cards
  -> inventory_items
      -> location_id
      -> inventory_status
      -> marketplace/listing references

locations
  -> parent_location_id
  -> location_type
  -> display_code
  -> canonical_path

captures
  -> capture_images
  -> capture_inventory_links

sync_events
  -> source system
  -> conflict status
  -> applied timestamp
```

Future flow:

```text
CardVector.app
  -> Supabase Auth
  -> Supabase reads/writes
  -> offline cache with sync state

CardVector OS
  -> Supabase repositories
  -> local cache only
  -> no independent registry authority

CardUploader
  -> either writes inventory to Supabase through an approved integration
  -> or remains external with a durable Supabase mirror contract
```

## 11. Recommended Migration Plan

### Phase A: Supabase Reality Check

1. In Supabase dashboard, verify whether the expected tables exist in `public`.
2. If absent, apply the four migrations in `supabase/migrations`.
3. If present but REST returns 404, reload PostgREST schema cache and verify API exposure.
4. Verify one authorized operator exists in `cardvector_location_operators`.
5. Run a read-only smoke check from desktop.

### Phase B: Repair Visibility Without Changing Authority

1. Fix the desktop Settings sync result message to display `etbs_received`, `locations_received`, `etbs_published`, and `locations_published`.
2. Add a registry-side "staged mobile captures" indicator so mobile work is visible without pretending it is completed inventory.
3. Add a reconciliation report comparing:
   - Supabase capture sessions/images;
   - Supabase ETB/location identity;
   - local ETB registry JSON;
   - local conversion session JSON;
   - CardUploader inventory snapshot.

### Phase C: Architecture Decision for Supabase SOT

Create an ADR deciding whether:

1. Supabase becomes the true inventory source of truth and CardUploader becomes an integration client; or
2. CardUploader remains the true inventory source of truth and Supabase becomes the shared operational mirror/cache.

This must explicitly supersede or amend the current CardUploader ownership decision.

### Phase D: Supabase Canonical Schema

Add migrations for:

- `locations` hierarchy;
- `cards`;
- `inventory_items`;
- `inventory_item_photos`;
- `captures`;
- `capture_images`;
- `capture_inventory_links`;
- `collection_metadata`;
- `inventory_status_history`;
- `sync_events`;
- RLS/RPC policies for safe browser and desktop writes.

### Phase E: Repository Layer

Create Supabase-backed repositories under the approved integration/infrastructure boundary, then route:

- CardVector.app through Supabase tables/RPCs;
- CardVector OS through application services backed by Supabase repositories;
- CardUploader import/sync through an explicit integration contract.

### Phase F: Demote Local Stores

Convert local JSON/CSV stores to:

- offline cache;
- performance cache;
- generated reports;
- migration compatibility only.

Do not remove local registry writes until every caller has migrated and equivalence is proven.

## 12. Files Requiring Modification Later

No files were modified in this audit except this report.

Likely future files:

| File | Reason |
| --- | --- |
| `Docs/Architecture/CardVector_Architecture_Manifest.md` | Supabase SOT would change inventory ownership |
| `Docs/Architecture/CardVector_Subsystem_Ownership_Matrix.md` | Ownership matrix must reflect final source of truth |
| `Docs/Architecture/CardVector_Architecture_Decision_Log.md` | New ADR required |
| `Docs/Reference/MOBILE_LOCATION_SYNC.md` | Current projection contract would be superseded |
| `supabase/migrations/*.sql` | Add canonical inventory/location hierarchy schema |
| `Docs/app.js` | Link captures/photos to canonical Supabase location/inventory model |
| `Platform/Putnam_OS/System/tools/mobile_capture_queue.py` | Route capture/location sync through canonical repositories |
| `Platform/Putnam_OS/System/app/inventory_locations.py` | Demote local JSON to cache/projection |
| `Platform/Putnam_OS/System/app/putnam_os.py` | Inventory/registry screens should read canonical application services |
| `Platform/cardvector/application/inventory.py` | Replace legacy projection delegates with canonical repository calls |
| `Platform/cardvector/integrations/carduploader/inventory.py` | Add supported live/sync path or durable mirror contract |
| `Platform/Putnam_OS/Putnam_Seller_Tools/location_registry.py` | Retire or map legacy `ETB-##` batch labels |
| `Tools/architecture/check_architecture.py` | Add guardrails against duplicate registries |

## 13. Risk Assessment

| Risk | Severity | Notes |
| --- | --- | --- |
| Live Supabase tables missing/unavailable | Critical | Storage bucket exists, table endpoints 404 |
| Supabase SOT conflicts with current CardUploader inventory ownership | High | Requires ADR and migration plan |
| Local ETB registry contains operational data not in Supabase | High | Direct replacement risks losing counts/status/history |
| Mobile staged captures duplicated by mobile session ID | Medium | Some local conversion-session pairs reference same mobile session |
| `Mobile Capture Staged` could be misread as inventory complete | High | Must not update counts until workflow semantics are approved |
| No canonical photo-to-inventory link | High | Photos are tied to captures, not recognized inventory items |
| No generic storage hierarchy | Medium | Current model only supports ETB A-J |
| Legacy `ETB-##` and current `ETB-###` formats coexist | Medium | Can confuse inventory/listing joins |
| Local caches and reports are numerous | Medium | Need strict cache/report/source classification before migration |

## 14. Final Finding

CardVector OS does not reflect CardVector.app mobile capture work in the ETB Location Registry because the registry is not backed by Supabase and the mobile capture workflow does not create completed inventory records. It creates capture sessions, image records, uploaded photo objects, and local staged conversion artifacts after desktop queue processing.

The shortest safe path is:

1. fix the live Supabase schema mismatch;
2. expose staged mobile capture visibility in CardVector OS;
3. add a reconciliation report;
4. make a formal architecture decision on Supabase versus CardUploader inventory authority;
5. then migrate toward Supabase as the single source of truth if that decision is approved.

No refactoring should begin until the Supabase table mismatch and inventory ownership decision are resolved.
