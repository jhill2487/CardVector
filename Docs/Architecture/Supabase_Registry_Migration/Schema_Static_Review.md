# Supabase Capture/Location Registry Schema Static Review

**Date:** 2026-07-25
**Migration reviewed:** `supabase/migrations/20260725090000_canonical_capture_location_registry.sql`
**Status:** Ready for owner review; production apply has not been run.

## Scope

This static review checks whether the canonical capture/location registry
migration matches the repository implementation and whether it is safe to review
for production apply. It does not verify a live production database state and it
does not apply any SQL.

## Table And Code Alignment

The SQL migration creates the table names used by the shared Supabase registry
repository and the mobile site:

| Table or function | SQL migration | Repository use | Result |
| --- | --- | --- | --- |
| `cardvector_storage_locations` | Created | `Platform/cardvector/integrations/supabase/registry.py`, `Docs/app.js`, OS registry reader | Match |
| `cardvector_capture_sessions` | Created | `Platform/cardvector/integrations/supabase/registry.py`, `Docs/app.js`, mobile queue update path | Match |
| `cardvector_capture_images` | Created | `Platform/cardvector/integrations/supabase/registry.py`, `Docs/app.js`, mobile queue update path | Match |
| `cardvector_inventory_relationships` | Created | `Platform/cardvector/integrations/supabase/registry.py` | Match |
| `cardvector_create_next_etb_slot(text, text)` | Created | `Docs/app.js` ETB slot creation RPC | Match |
| `mobile-capture-originals` | Bucket ensured | Mobile app upload config and migration tooling | Match |

## Relationship Review

- `cardvector_storage_locations.parent_location_id` references
  `cardvector_storage_locations(id)` with `on delete restrict`, supporting a
  parent-child location hierarchy without cascading accidental deletion.
- `cardvector_capture_sessions.location_id` references
  `cardvector_storage_locations(id)` with `on delete set null`, preserving
  capture session history if a location is later archived or removed.
- `cardvector_capture_images.capture_session_id` references
  `cardvector_capture_sessions(id)` with `on delete cascade`, keeping image
  metadata scoped to the session row.
- `cardvector_inventory_relationships` references capture sessions, images, and
  storage locations but does not duplicate CardUploader-managed inventory.

## Identity And Constraint Review

- Locations: `owner_user_id + legacy_id` and `owner_user_id + display_code`
  unique indexes support deterministic legacy import and ETB/slot display-code
  lookups.
- Capture sessions: `owner_user_id + legacy_session_id` unique index supports
  stable import identity.
- Capture images: `capture_session_id + sequence_number` and
  `owner_user_id + storage_bucket + storage_object_path` unique indexes support
  the reviewed identity rules. Filenames are not used as a uniqueness rule.
- Inventory relationships: unique external-inventory-reference index supports
  association without becoming a second inventory source of truth.

## ETB Representation Review

The migration represents ETBs and ETB slots as rows in the canonical
`cardvector_storage_locations` hierarchy. ETBs use `location_type = 'etb'`; ETB
slots use `location_type = 'etb_slot'` and reference the ETB parent row. This
matches CV-ADR-024 and avoids creating a second authoritative ETB registry.

## RLS Review

- RLS is enabled on the canonical registry tables.
- Authenticated users can manage rows where `owner_user_id = auth.uid()`.
- Location operator rows allow authorized operators to read shared location
  rows.
- Anonymous table access is revoked.
- Service role grants are present for server-side migration and desktop service
  operations. Service-role keys are not embedded in client code.

## Storage Policy Review

- The migration ensures the private `mobile-capture-originals` bucket exists.
- Authenticated upload/read/update policies require object paths to begin with
  the authenticated user id.
- Existing storage objects are not deleted by the migration.

## Updated At Review

The migration creates `cardvector_registry_touch_updated_at()` and attaches it
to the canonical tables with `before update` triggers. This gives a consistent
server-side `updated_at` lifecycle for registry records.

## Inventory Safety Review

The migration does not create or alter CardUploader inventory tables, quantity
tables, SKU tables, order-picking tables, or pricing tables. The only inventory
touchpoint is `cardvector_inventory_relationships`, which stores references to
external inventory identifiers and capture/location context.

## Production Safety Notes

- The migration is designed to be safe for an empty canonical schema.
- The migration uses `create table if not exists`, `create index if not exists`,
  and policy/function replacement where appropriate.
- Production apply still requires explicit owner approval after reviewing the
  approved duplicate-skip plan and dry-run reports.
- The Supabase CLI link was not found in the local `supabase/` folder during
  this review, so the production command must explicitly target or verify the
  approved project before apply.

## Review Result

Static review passed with one operational gate: verify the Supabase CLI or
production command target is the approved project reference
`iqdpfgpkagjxzedfxrvn` immediately before any production schema apply.
