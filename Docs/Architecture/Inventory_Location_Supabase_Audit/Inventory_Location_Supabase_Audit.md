# Inventory, Location, Storage, and Supabase Architecture Audit

Date: 2026-07-22

Scope: CardVector OS desktop application, CardVector.app mobile/public site, ETB/location registry, inventory registry, storage, synchronization, and Supabase integration.

Status: Investigation only. No application code, schema, launcher, inventory, or production behavior was changed.

## Executive Summary

The registry inconsistency is real and comes from a split current architecture:

1. CardVector.app writes mobile capture sessions, image metadata, and cloud ETB/location identity to Supabase.
2. CardVector OS displays the Inventory / ETB Location Registry from a local JSON operational projection at `Platform/Putnam_OS/System/data/inventory/etb_location_registry.json`.
3. CardVector OS does not read that registry screen directly from Supabase.
4. The desktop queue sync adapter merges Supabase ETB/location identities into the local projection, but it does not make Supabase the card inventory source of truth.
5. Successful mobile captures staged by the desktop queue become local capture folders and, for physical inventory conversion, local conversion-session JSON files with status `Mobile Capture Staged`.
6. The local ETB registry is only repaired from conversion sessions whose status is exactly `Location Complete`.
7. Therefore, mobile captures can be successfully uploaded and staged while the desktop ETB/location registry still does not show completed occupancy, stored counts, or actual inventory changes.

There is also a live Supabase verification concern. The configured project URL matches `Docs/mobile-capture-config.js`, and the storage bucket `mobile-capture-originals` exists, but read-only REST checks for the expected tables returned `404 Not Found` for:

- `mobile_capture_sessions`
- `mobile_capture_images`
- `cardvector_etbs`
- `cardvector_locations`
- `cardvector_location_operators`

That means the live Supabase schema currently reachable from this workstation does not match the local migrations, or the tables are absent/not exposed in the expected schema. This should be verified in the Supabase dashboard before any synchronization refactor.

## Current Architecture

### Approved Ownership Baseline

Observed architecture documents establish these current owners:

| Responsibility | Current documented owner | Evidence |
| --- | --- | --- |
| Managed card inventory, quantities, card-level locations, allocation, picking | CardUploader | `Docs/Architecture/CV-ADR-021-carduploader-inventory-ownership.md`, `Docs/Architecture/CardVector_Subsystem_Ownership_Matrix.md` |
| Capture and image intake | CardVector Capture | `Docs/Architecture/Phase_4_Capture_and_Recognition/` |
| Mobile capture cloud queue | Supabase plus CardVector OS queue worker | `supabase/migrations/20260713153000_mobile_capture.sql`, `Platform/Putnam_OS/System/tools/mobile_capture_queue.py` |
| Cloud-visible ETB/location identity | Supabase | `Docs/Reference/MOBILE_LOCATION_SYNC.md`, `supabase/migrations/20260716130000_mobile_location_registry.sql` |
| Desktop ETB operational projection | Local JSON | `Platform/Putnam_OS/System/app/inventory_locations.py` |
| CardVector OS workflow orchestration | CardVector Application layer and `putnam_os.py` compatibility | `Platform/cardvector/application/inventory.py`, `Platform/Putnam_OS/System/app/putnam_os.py` |

Important conflict with the requested target: current accepted architecture says CardUploader owns managed inventory. The requested end state says Supabase should become the single source of truth for all inventory and location data. Implementing that target requires a new architecture decision that supersedes or amends ADR-021.

## Data Flow Diagrams

### CardVector.app Mobile Capture

```text
CardVector.app Docs/app.js
  -> browser auth via Supabase JS
  -> localStorage session metadata and IndexedDB draft images
  -> Supabase table mobile_capture_sessions
  -> Supabase table mobile_capture_images
  -> Supabase Storage bucket mobile-capture-originals
  -> status PENDING_CONVERSION
```

Location selection and creation:

```text
CardVector.app Docs/app.js
  -> cardvector_location_operators authorization check
  -> cardvector_etbs list
  -> cardvector_locations list
  -> RPC cardvector_create_next_location
  -> cardvector_locations insert through server-side validation
```

### Desktop Queue Processing

```text
CardVector OS queue service
  -> sync local ETB projection to Supabase identity tables
  -> read pending mobile_capture_sessions
  -> atomically claim session
  -> read mobile_capture_images
  -> download objects from mobile-capture-originals
  -> stage files under Capture/MM.DD.YY or Capture/Physical_Inventory_Conversion/MM.DD.YY
  -> write capture_session.json
  -> write mobile_capture_manifest.json
  -> for PHYSICAL_INVENTORY write inventory_conversion session JSON
```

### Desktop ETB Registry Screen

```text
CardVector OS putnam_os.py
  -> inventory_refresh_etb_locations()
  -> repair_completed_inventory_conversion_registry()
  -> etb_location_rows()
  -> InventoryApplication.list_location_projection()
  -> legacy local JSON delegate
  -> Platform/Putnam_OS/System/data/inventory/etb_location_registry.json
```

This screen does not read Supabase directly.

### Inventory Snapshot Flow

```text
CardUploader export CSV
  -> Platform/cardvector/integrations/carduploader/inventory.py
  -> InventoryApplication
  -> CardVector OS views/reports/search
```

The current CardUploader inventory adapter is snapshot based and read-only. It does not provide live inventory writes, reservations, allocation, or live sync.

## Databases and Stores Found

### Supabase Project

Configured project URL:

- `https://iqdpfgpkagjxzedfxrvn.supabase.co`

Local public configuration:

- `Docs/mobile-capture-config.js`

Environment variables present on workstation:

- `CARDVECTOR_SUPABASE_URL`: set
- `CARDVECTOR_SUPABASE_SERVICE_ROLE_KEY`: set
- `SUPABASE_URL`: not set
- `SUPABASE_SERVICE_ROLE_KEY`: not set

Live read-only check:

| Object | Result |
| --- | --- |
| Storage bucket `mobile-capture-originals` | Exists, HTTP 200 |
| `mobile_capture_sessions` | HTTP 404 Not Found |
| `mobile_capture_images` | HTTP 404 Not Found |
| `cardvector_etbs` | HTTP 404 Not Found |
| `cardvector_locations` | HTTP 404 Not Found |
| `cardvector_location_operators` | HTTP 404 Not Found |

No secrets were printed during this check.

### Supabase Tables From Local Migrations

Defined by `supabase/migrations/20260713153000_mobile_capture.sql`:

| Table | Purpose |
| --- | --- |
| `mobile_capture_sessions` | Mobile capture session queue state, ETB/location metadata, capture type, user/operator, device, image count, status, conversion status, errors |
| `mobile_capture_images` | Per-image metadata, storage path, ordering, upload status, dimensions, removed marker |

Defined by `supabase/migrations/20260716130000_mobile_location_registry.sql`:

| Table | Purpose |
| --- | --- |
| `cardvector_location_operators` | Authenticated operator authorization for location listing/creation |
| `cardvector_etbs` | Cloud-visible ETB identity and high-level status/capacity fields |
| `cardvector_locations` | Cloud-visible ETB A-J child location identity and capacity/status/count fields |

### Supabase Storage Buckets

| Bucket | Purpose | Evidence |
| --- | --- | --- |
| `mobile-capture-originals` | Private original image storage for mobile uploads | Local migration and live bucket check |

### Local JSON Stores

| Path | Purpose | Authority Status |
| --- | --- | --- |
| `Platform/Putnam_OS/System/data/inventory/etb_location_registry.json` | Current desktop ETB operational projection: counts, status, active slot, QR labels, CardUploader references | Operational projection, not Supabase-backed truth |
| `Data/Config/etb_location_registry.json` | Legacy ETB registry copied only when the current system-data registry does not exist | Legacy/stale |
| `Platform/Putnam_OS/System/config/location_registry.json` | Older batch/User-SKU registry with `ETB-##-Letter` format | Separate listing/export batch label registry |
| `Platform/Putnam_OS/System/data/inventory_conversion/sessions/*.json` | Physical inventory conversion workflow state | Local workflow state |
| `Platform/Putnam_OS/System/data/inventory_conversion/current_inventory_conversion.json` | Current active conversion pointer | Local workflow state |
| `MobileCapture/Processing/<session>/mobile_capture_manifest.json` | Desktop-staged mobile session manifest | Local processing artifact |
| `Capture/**/capture_session.json` | Capture folder metadata, image records, ETB/location/capture type | Local workflow context |
| `Capture/**/cardvector_workflow.json` | Capture-to-CardUploader workflow context | Local workflow context |

### Local CSV / Snapshot Stores

| Path | Purpose | Authority Status |
| --- | --- | --- |
| `Data/Exports/carduploader_inventory_snapshot.csv` | CardUploader inventory export snapshot used by CardVector adapter | Snapshot of CardUploader-owned inventory |
| `Data/Exports/Reconciliation/*.json` | Reconciliation report outputs | Generated reports |

### Browser Cache Stores

| Store | Purpose | Authority Status |
| --- | --- | --- |
| `localStorage` | Mobile draft session metadata | Offline/draft cache only |
| IndexedDB capture database | Mobile draft image recovery | Offline/draft cache only |

## Supabase Schema Summary

### Mobile Capture Tables

`mobile_capture_sessions` fields include:

- `capture_session_id` primary key
- `etb_location`
- `etb_location_id`
- `created_at`, `updated_at`, `submitted_at`
- `status`
- `source`
- `operator`, `operator_id`, `user_id`
- `device`, `source_device`
- `image_count`
- `original_image_locations`
- `conversion_status`
- `conversion_workstation`
- `error_message`
- `schema_version`
- `capture_type` added by `20260716090000_mobile_capture_type.sql`

`mobile_capture_images` fields include:

- `image_id` primary key
- `capture_session_id` foreign key to `mobile_capture_sessions`
- `image_order`, `sequence_number`
- `storage_bucket`, `storage_path`
- `original_filename`, `content_type`, `byte_size`
- `upload_status`
- `sha256`, `width`, `height`
- `created_at`, `removed_at`
- `user_id`

Indexes:

- sessions by status/submitted time
- sessions by location/status
- images by session/order
- unique session image order
- unique storage bucket/path

### Location Tables

`cardvector_etbs`:

- `etb_id` primary key, format `ETB-###`
- status in `Empty`, `Active`, `Full`, `Needs Review`, `Archived`
- capacity default 400
- `active_location_code` A-J
- `source_updated_at`
- `created_by`
- timestamps

`cardvector_locations`:

- `location_id` primary key, must equal `etb_id || '-' || location_code`
- `etb_id` foreign key to `cardvector_etbs`
- `location_code` A-J
- status in `Empty`, `Active`, `Full`, `Location Complete`, `Needs Review`, `Archived`
- capacity default 40
- `stored_count`
- `assigned_batch`
- `source_updated_at`
- `created_by`
- timestamps
- unique `(etb_id, location_code)`

### RLS, RPC, and Triggers

RLS is enabled on all local migration tables.

Read access:

- Authenticated users can read their own location operator record.
- Authenticated users can read ETBs/locations only if present in `cardvector_location_operators` with `can_manage_locations`.
- Authenticated mobile operators can insert/read/update their own mobile capture session and image records under the policies in the capture migration.

Write access:

- Browser direct insert/update/delete to location tables is revoked.
- Mobile location creation uses RPC `cardvector_create_next_location`.
- Service role can select/insert/update location tables for desktop sync.

RPC `cardvector_create_next_location`:

- requires authentication
- requires location-management authorization
- validates ETB ID and expected A-J code
- locks the ETB row with `FOR UPDATE`
- computes the next missing location A-J inside the transaction
- rejects stale proposals and exhausted ETBs
- inserts one canonical `ETB-###-A` row

Triggers:

- `cardvector_mobile_capture_touch_updated_at`
- `cardvector_mobile_capture_normalize_session`
- `cardvector_mobile_capture_normalize_image`
- touch triggers for location/operator tables

Not found in repository migrations:

- Edge Functions
- database views
- materialized views
- Realtime subscription setup
- card inventory tables
- generic storage hierarchy tables
- inventory-photo linkage table
- inventory status table

## Mobile Capture Write Trace

Starting from a successful mobile capture in `Docs/app.js`:

1. The operator reaches `/location/<ETB-ID>/<LOCATION>`, `/etb/<ETB-ID>`, or `/capture`.
2. ETB/location lists are read from `cardvector_etbs` and `cardvector_locations`.
3. Optional next location creation calls RPC `cardvector_create_next_location`.
4. The operator explicitly starts camera capture.
5. Draft metadata is stored in `localStorage`.
6. Draft/recovery images are stored in IndexedDB.
7. On submit, `submitCapture()` upserts a row into `mobile_capture_sessions`.
8. Each image is uploaded to `mobile-capture-originals/{user_id}/{etb_location}/{capture_session_id}/...`.
9. Each image row is upserted into `mobile_capture_images`.
10. The session is updated to `PENDING_CONVERSION`.

Mobile writes:

| Object | Written by mobile? | Notes |
| --- | --- | --- |
| `mobile_capture_sessions` | Yes | Session, status, capture type, ETB/location metadata |
| `mobile_capture_images` | Yes | Image metadata and storage paths |
| `mobile-capture-originals` | Yes | Original image objects |
| `cardvector_locations` | Yes, only through RPC | Next-location creation only |
| `cardvector_etbs` | No direct browser insert | Read by mobile; desktop/service role publishes local ETBs |
| Card inventory | No | Not implemented |
| Desktop local registry | No | Browser cannot write local OS JSON |
| CardUploader inventory | No | CardUploader remains external |

## CardVector OS Read and Write Trace

### Mobile Queue

`Platform/Putnam_OS/System/tools/mobile_capture_queue.py`:

- reads `mobile_capture_sessions`
- reads `mobile_capture_images`
- downloads from `mobile-capture-originals`
- writes local capture folders
- writes local processing manifests
- writes local inventory conversion session JSON for physical inventory captures
- updates Supabase session status through queue lifecycle calls
- syncs local ETB projection with `cardvector_etbs` and `cardvector_locations`

### Inventory / ETB Location Registry Screen

`Platform/Putnam_OS/System/app/putnam_os.py`:

- `inventory_refresh_etb_locations()` calls `repair_completed_inventory_conversion_registry()`.
- `repair_completed_inventory_conversion_registry()` only marks local locations complete from sessions with status `Location Complete`.
- `etb_location_rows()` delegates to the Application inventory facade.
- The facade calls legacy local JSON projection functions in `inventory_locations.py`.
- The table is populated from local rows and local completed-session rollups.

The screen does not call `mobile_capture_queue.sync_locations()` and does not query Supabase directly.

### Settings Sync Locations

`sync_locations_ui()` calls the queue service location sync, but the completion dialog expects keys named `cloud_etb_count` and `cloud_location_count` or `etb_count` and `location_count`.

The queue result uses names such as:

- `etbs_received`
- `locations_received`
- `etbs_published`
- `locations_published`

This likely causes the desktop sync success message to show zero or misleading counts even when sync worked.

## Duplicate Concepts and Implementations

### Inventory

| Concept | Current implementations |
| --- | --- |
| Managed card inventory | CardUploader export snapshot via `Platform/cardvector/integrations/carduploader/inventory.py` |
| Inventory projection in OS | `Platform/cardvector/application/inventory.py` delegates to local ETB projection |
| Reconciliation data | `Data/Exports/Reconciliation/*.json` |

No CardVector-owned live inventory database was found in the Supabase migrations.

### ETBs and Locations

| Concept | Implementation | Format | Status |
| --- | --- | --- | --- |
| Cloud ETB/location identity | Supabase `cardvector_etbs`, `cardvector_locations` | `ETB-###`, A-J | Intended cloud identity source |
| Desktop ETB operational projection | `Platform/Putnam_OS/System/data/inventory/etb_location_registry.json` | `ETB-###-A` | Current OS registry source |
| Legacy ETB registry | `Data/Config/etb_location_registry.json` | mixed older ETB projection | Legacy/stale |
| Batch/User-SKU location registry | `Platform/Putnam_OS/System/config/location_registry.json` | `ETB-##-Letter` | Separate listing/export label registry |

### Capture History

| Concept | Implementation |
| --- | --- |
| Cloud queue history | `mobile_capture_sessions`, `mobile_capture_images` |
| Desktop processing manifest | `MobileCapture/Processing/<session>/mobile_capture_manifest.json` |
| Capture folder context | `Capture/**/capture_session.json` |
| Physical inventory conversion state | `Platform/Putnam_OS/System/data/inventory_conversion/sessions/*.json` |

### Synchronization Logic

| Sync path | Direction | Notes |
| --- | --- | --- |
| `sync_cloud_location_registry()` | local projection -> Supabase identity, then Supabase identity -> local projection | Two-way for ETB/location identity only |
| Mobile capture queue process | Supabase capture queue -> local capture folders | One-way capture intake |
| CardUploader inventory adapter | CardUploader CSV -> CardVector snapshot | One-way snapshot read |
| Registry repair from completed sessions | local conversion sessions -> local ETB projection | Only status `Location Complete` |

## Root Cause of Registry Inconsistency

The inconsistency has multiple layers:

1. Supabase is not currently the single source of truth for inventory.
   The local migrations define capture and location identity tables only. They do not define managed inventory, cards, card ownership, or generic storage hierarchy tables.

2. CardVector.app does not update inventory.
   It captures images, records sessions/images, provisions locations, and submits work to a queue. It does not create or update card inventory records.

3. CardVector OS does not read the ETB registry screen from Supabase.
   The Registry UI reads the local JSON projection through `etb_location_rows()`.

4. Location sync is not the same thing as inventory sync.
   `sync_cloud_location_registry()` publishes and merges location identity, not actual card inventory, completed capture state, or CardUploader records.

5. Mobile-staged conversion sessions do not mark locations complete.
   There are seven local mobile conversion sessions with status `Mobile Capture Staged`. The repair function skips every session whose status is not `Location Complete`, so these captures do not update the registry counts/status.

6. The live Supabase table check failed for expected tables.
   Even though local migrations define the tables, the configured live project returned 404 for all expected REST table endpoints. If confirmed in Supabase, current mobile capture and desktop queue operations that depend on those tables cannot work against this project until migrations/API exposure are corrected.

7. A desktop sync UI result-key mismatch can hide success/failure details.
   The queue returns `etbs_received` and `locations_received`, while the UI displays different key names.

## Recommended Target Architecture

The requested target architecture is sound, but it is larger than a bug fix and requires a formal architecture decision:

```text
Supabase
  -> users
  -> canonical cards
  -> canonical inventory items
  -> canonical storage locations
  -> ETBs as location nodes
  -> bins, boxes, binders, shelves, cabinets as location nodes
  -> captures
  -> photos
  -> inventory status
  -> collection metadata
  -> sync state

CardVector.app
  -> authenticated reads/writes through Supabase policies/RPCs
  -> offline cache only

CardVector OS
  -> authenticated reads/writes through Supabase repositories
  -> local cache only
  -> no independent registry truth

CardUploader
  -> either integrated writer/reader of Supabase inventory
  -> or external system mirrored through a controlled sync contract
```

The key decision is whether CardUploader remains the inventory authority and Supabase becomes a durable mirror, or Supabase becomes the actual inventory authority and CardUploader becomes an integration client. The current accepted architecture says CardUploader is the inventory authority.

## Proposed Final Location Model

Recommended future model:

| Field | Purpose |
| --- | --- |
| `location_id` | UUID or stable canonical identifier |
| `parent_location_id` | nullable self-reference for hierarchy |
| `location_type` | Room, Closet, Shelf, Drawer, Cabinet, ETB, Box, Bin, Binder, Slot |
| `display_code` | human code, such as `ETB-002-G` |
| `canonical_path` | computed or stored hierarchy path |
| `status` | Active, Full, Archived, Needs Review |
| `capacity` | optional item/card capacity |
| `metadata` | flexible JSON for type-specific details |
| `created_by`, `updated_by` | audit |
| timestamps | audit/sync |

All storage objects should reference `locations.location_id`, including ETB child slots.

Required relationships:

- Inventory item -> Location
- Capture session -> Location
- Photo -> Capture session
- Photo -> Inventory item, when recognized/assigned
- ETB -> Location node
- Location -> parent Location
- Inventory item -> optional ETB/location projection for compatibility only

## Recommended Migration Plan

### Step 0: Verify Live Supabase State

1. Confirm the Supabase project `iqdpfgpkagjxzedfxrvn` in the dashboard.
2. Confirm whether the five expected tables exist in schema `public`.
3. Confirm whether REST exposure/schema cache is healthy.
4. Confirm whether the local service role key belongs to the same project.
5. Apply or re-apply missing migrations if tables are absent.

Do not proceed to data-source refactor until this is resolved.

### Step 1: Fix Current Inconsistency Without Changing Authority

Small, low-risk changes after report review:

1. Make the Inventory / ETB Registry refresh path optionally perform a read-through location identity sync before loading local rows.
2. Fix the Settings sync result display to use actual queue result keys.
3. Add a desktop indicator for `Mobile Capture Staged` sessions by ETB/location so staged captures are visible without marking inventory complete.
4. Keep completion semantics unchanged: only `Location Complete` should update stored counts unless explicitly approved.

### Step 2: Add Observability

1. Add a sync health panel showing last local-to-cloud sync, last cloud-to-local sync, Supabase table availability, queue pending counts, and staged conversion counts.
2. Add a diagnostic report that reconciles:
   - cloud locations
   - local ETB registry
   - mobile staged sessions
   - completed conversion sessions
   - CardUploader inventory snapshot

### Step 3: Decide Inventory Authority

Create a new ADR:

- Option A: CardUploader remains inventory authority, Supabase is canonical shared mirror/cache.
- Option B: Supabase becomes inventory authority, CardUploader becomes an integration client.

This decision must explicitly supersede or amend ADR-021.

### Step 4: Design Supabase Inventory Schema

If Supabase becomes the single source of truth:

1. Add canonical `locations` hierarchy.
2. Add canonical `cards` or card identity references.
3. Add `inventory_items`.
4. Add `inventory_item_photos`.
5. Add `capture_inventory_links`.
6. Add inventory status/history/audit tables.
7. Add sync metadata and conflict handling.
8. Add RLS and RPCs for safe writes.
9. Add indexes and uniqueness constraints.

### Step 5: Migrate Writers

1. Mobile continues writing capture/photo data.
2. Desktop queue links staged captures to canonical location rows.
3. CardUploader recognition/import writes or syncs inventory through the chosen contract.
4. CardVector OS writes registry/status changes only through Supabase repositories.

### Step 6: Demote Local Stores to Cache

1. Keep local JSON/CSV only as cache, offline queue, or generated export.
2. Add cache invalidation and last-sync metadata.
3. Remove independent registry writes only after all callers are migrated.

## Files Likely Requiring Modification Later

Do not modify these until the report is reviewed and a plan is approved.

| File | Likely future change |
| --- | --- |
| `Docs/Architecture/CV-ADR-021-carduploader-inventory-ownership.md` | Supersede/amend if Supabase becomes inventory authority |
| `Docs/Architecture/CardVector_Subsystem_Ownership_Matrix.md` | Update inventory/location ownership |
| `Docs/Reference/MOBILE_LOCATION_SYNC.md` | Replace projection contract with Supabase SOT contract |
| `supabase/migrations/*.sql` | Add canonical inventory/location hierarchy schema |
| `Docs/app.js` | Link capture sessions/photos to canonical location/inventory model |
| `Platform/Putnam_OS/System/tools/mobile_capture_queue.py` | Read/write through canonical Supabase repositories and improve staged session visibility |
| `Platform/Putnam_OS/System/app/inventory_locations.py` | Demote local registry to cache/projection |
| `Platform/Putnam_OS/System/app/putnam_os.py` | Registry refresh should use canonical repository/application service |
| `Platform/cardvector/application/inventory.py` | Route inventory/location workflows through approved source of truth |
| `Platform/cardvector/integrations/carduploader/inventory.py` | Add live/sync contract if CardUploader remains involved |
| `Platform/Putnam_OS/Putnam_Seller_Tools/location_registry.py` | Align old batch/User-SKU location registry with canonical model or archive after migration |
| `Tools/architecture/check_architecture.py` | Add guardrails against new duplicate registries |

## Risk Assessment

| Risk | Severity | Notes |
| --- | --- | --- |
| Live Supabase schema does not match repository migrations | High | Expected tables returned 404; verify before relying on cloud sync |
| Supabase SOT conflicts with accepted CardUploader ownership ADR | High | Requires explicit architecture decision |
| Local registry contains operational history not present in Supabase | High | Direct replacement could lose counts/status/CardUploader refs |
| Mobile-staged sessions may be duplicated locally | Medium | Two duplicate-looking mobile staged session pairs were observed by mobile session ID |
| Marking mobile staged captures as complete too early | High | Would misstate inventory if CardUploader recognition/conversion not done |
| Two ETB code formats exist | Medium | `ETB-###-A` vs `ETB-##-Letter` |
| Service-role desktop sync writes to Supabase | Medium | Must be kept out of UI/public assets and carefully scoped |
| Offline behavior depends on local JSON | Medium | Supabase SOT needs cache/offline strategy |

## Verification Commands Run

Read-only commands used:

- `git status --short --branch`
- `rg` searches over architecture docs, `Docs/app.js`, queue, inventory application, CardUploader adapter, migrations, and registry files
- `Get-Content` excerpts from registry JSON and migration files
- PowerShell JSON summary of local inventory conversion sessions
- Read-only Supabase REST/storage checks using configured environment credentials without printing secrets

Result:

- Working tree started clean.
- No code or runtime data was modified.
- Supabase storage bucket exists.
- Expected Supabase REST tables returned 404.

## Conclusion

The immediate root cause is not one missing UI refresh. It is that CardVector currently has separate layers for mobile capture, local ETB operational projection, CardUploader inventory snapshots, and cloud location identity. Mobile captures write to Supabase and local staged-session files after queue processing, but the desktop registry screen reads local projection state and only considers sessions complete after a local `Location Complete` workflow state.

The first practical fix should be to verify/apply the Supabase migrations and then make the desktop registry visibly reconcile cloud identity and staged mobile sessions. The larger desired end state, Supabase as the single source of truth for all inventory and locations, should be handled as a formal architecture decision and migration because it supersedes the current CardUploader inventory ownership decision.
