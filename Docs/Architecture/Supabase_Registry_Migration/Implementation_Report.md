# Supabase Registry Migration Implementation Report

## Current Status

Paused by CV-ADR-026 on 2026-09-01. This report remains historical evidence and
restart material. Do not use it as approval to run production schema migration,
legacy import, or cutover commands.

## Implementation Summary

This implementation creates the canonical Supabase-backed registry foundation
for shared CardVector capture batches, ETBs/storage locations, capture images,
and lightweight inventory relationships.

CardVector.app now attempts canonical Supabase writes while preserving the
existing compatibility write path. CardVector OS now reads canonical Supabase
registry rows first and falls back to the legacy JSON cache with a visible sync
warning. The desktop mobile queue performs best-effort canonical status updates
after staging or failure without blocking the existing local staging behavior.

## Files Created

- `supabase/migrations/20260725090000_canonical_capture_location_registry.sql`
- `Platform/cardvector/integrations/supabase/__init__.py`
- `Platform/cardvector/integrations/supabase/registry.py`
- `Tools/migrate_legacy_registry_to_supabase.py`
- `Tests/supabase_registry/test_canonical_registry_migration.py`
- `Docs/Architecture/CV-ADR-024-supabase-capture-location-registry.md`
- `Docs/Architecture/Supabase_Registry_Migration/Current_State_Findings.md`
- `Docs/Architecture/Supabase_Registry_Migration/Canonical_Model_and_Field_Mapping.md`
- `Docs/Architecture/Supabase_Registry_Migration/Dry_Run_Migration_Report.md`
- `Docs/Architecture/Supabase_Registry_Migration/Migration_Runbook_and_Rollback.md`
- `Docs/Architecture/Supabase_Registry_Migration/Implementation_Report.md`

## Files Modified

- `Docs/app.js`
- `Platform/Putnam_OS/System/app/inventory_locations.py`
- `Platform/Putnam_OS/System/app/putnam_os.py`
- `Platform/Putnam_OS/System/tools/mobile_capture_queue.py`
- `Tools/test_mobile_location_contract.py`
- `Docs/Architecture/README.md`
- `Docs/Architecture/CardVector_Architecture_Manifest.md`
- `Docs/Architecture/CardVector_Subsystem_Ownership_Matrix.md`
- `Docs/Architecture/CardVector_Architecture_Decision_Log.md`
- `Docs/Architecture/cardvector_architecture_manifest.json`
- `Docs/Architecture/Compatibility_Adapter_Register.md`
- `Docs/Architecture/Deprecation_Register.md`

## Production Status

Not applied to production.

Historically, the Supabase migration and legacy import were ready for review,
but the dry-run
report found 82 conflicts in legacy capture/session/image evidence. The
conflicts now have Markdown, CSV, JSON, excluded-record, balanced-count, and
proposed-resolution artifacts in
`Work_Sessions/supabase_registry_migration_dry_run_20260725`. Production apply
is blocked until those conflicts are reviewed or resolved through an explicit
resolution file.

## Validation

See `Dry_Run_Migration_Report.md` for migration counts and backup evidence.
See the final task response for the exact validation commands and command
results.
