# CV-ADR-024 - Supabase Owns The Shared Capture And Location Registry

## Status

Accepted by task authorization; production cutover remains gated.

## Date

2026-07-25

## Owner

Project owner

## Context

CardVector OS originally maintained the ETB Location Registry as a local JSON
projection before CardVector.app used Supabase. CardVector.app mobile capture
now writes upload-oriented mobile session and image records, but the desktop
registry still reads
`Platform/Putnam_OS/System/data/inventory/etb_location_registry.json`.

The local projection is updated only from physical-inventory conversion
sessions marked `Location Complete`. Mobile-origin sessions remain
`Mobile Capture Staged`, so they do not appear in the desktop ETB Location
Registry.

The configured Supabase project already has the
`mobile-capture-originals` storage bucket. Read-only endpoint checks found the
expected registry tables unavailable in the deployed project, which indicates
that the registry schema either was never deployed or exists under other names.

## Decision

Supabase is the canonical source of truth for CardVector shared capture batches,
ETBs/storage containers, storage locations, capture images, and their
relationships.

Managed card inventory remains owned by CardUploader under CV-ADR-021. This ADR
does not create a second CardVector inventory system. It only establishes the
shared capture/location registry and lightweight relationships needed to connect
captures, locations, and external inventory references.

ETBs are represented as canonical location records with `location_type = 'etb'`.
ETB slots are child location records with `location_type = 'slot'`. This avoids
separate authoritative ETB and location registries while preserving current
`ETB-###-A` through `ETB-###-J` behavior.

The legacy JSON registry is demoted to migration input, comparison source,
fallback cache, export, and historical audit artifact after validation. It must
not silently overwrite newer Supabase records.

## Evidence

- Desktop registry read path:
  `Platform/Putnam_OS/System/app/inventory_locations.py`
- Desktop registry UI:
  `Platform/Putnam_OS/System/app/putnam_os.py`
- Local registry projection:
  `Platform/Putnam_OS/System/data/inventory/etb_location_registry.json`
- Mobile capture app:
  `Docs/app.js`
- Mobile queue:
  `Platform/Putnam_OS/System/tools/mobile_capture_queue.py`
- Supabase migrations:
  `supabase/migrations/20260713153000_mobile_capture.sql`,
  `supabase/migrations/20260716130000_mobile_location_registry.sql`
- Current audit:
  `Docs/Architecture/Inventory_Location_Supabase_Audit/Inventory_Location_Supabase_Audit.md`

## Alternatives Considered

- Keep local JSON authoritative and sync mobile sessions into it.
  Rejected because it keeps two application paths dependent on a desktop-local
  file.
- Create separate authoritative ETB and location tables.
  Rejected because ETBs are storage containers in the same hierarchy and separate
  registries would duplicate identity and status.
- Move full inventory ownership into CardVector/Supabase.
  Rejected because CV-ADR-021 establishes CardUploader as managed-inventory
  owner.

## Consequences

- CardVector.app writes canonical capture session/image metadata in addition to
  current compatibility tables during the rollout.
- CardVector OS reads the canonical registry first and falls back to the JSON
  cache with an explicit sync warning.
- Legacy JSON is preserved and backed up before migration.
- Production schema deployment and data import require project-owner approval
  after reviewing the schema, mapping, dry-run report, backup path, rollback
  procedure, and exact commands.

## Dependency Impact

- `Platform/cardvector/integrations/supabase` owns trusted desktop Supabase
  registry access.
- Browser code continues to use Supabase anon access protected by RLS.
- UI code must not scatter direct Supabase access; desktop reads go through the
  shared service/projection.

## Migration Impact

The rollout follows:

1. Schema and tooling.
2. Dry-run legacy migration and backup.
3. Dual-read comparison.
4. Supabase read cutover.
5. Supabase write cutover.
6. Legacy authority retirement after validation.

## Compatibility Impact

Compatibility adapters remain for:

- `inventory_locations.py` legacy ETB registry functions.
- `mobile_capture_queue.py` CLI/service path.
- CardVector.app compatibility writes to `mobile_capture_sessions` and
  `mobile_capture_images`.

## Testing Requirements

- SQL contract tests for canonical tables, RLS, storage policy, and RPC.
- Migration dry-run tests for ETB and slot mapping.
- Desktop projection tests for canonical rows into legacy UI shape.
- Existing mobile capture, mobile location, and Supabase contract tests.
- No live Supabase import before approval.

## Rollback Plan

Before production apply, back up all legacy registry JSON files. If cutover is
not accepted, leave applications in fallback compatibility mode and continue
using the legacy JSON cache. If a Supabase migration is applied and must be
rolled back before data import, drop only the newly created canonical registry
objects after exporting any newly written rows.

## Approval

Implementation authorized by the project owner in the Supabase registry
migration task. Production migration apply, production data import, and final
cutover remain pending review and explicit approval.

## Superseded By

CV-ADR-026 supersedes this ADR for active roadmap priority. The schema and
migration artifacts remain historical/restartable evidence, but production
capture/location registry apply, import, and cutover are paused unless a future
ADR reauthorizes the workflow.
