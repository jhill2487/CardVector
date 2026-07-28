# Supabase Registry Migration File List And Git Plan

**Date:** 2026-07-25
**Recommended branch:** `codex/supabase-capture-location-registry`
**Status:** No branch switch, staging, commit, reset, clean, stash, or checkout was
performed during this gate.

## Migration-Related Files

These files are part of the Supabase capture/location registry migration and
should be staged together after owner review:

- `Docs/Architecture/CardVector_Architecture_Decision_Log.md`
- `Docs/Architecture/CardVector_Architecture_Manifest.md`
- `Docs/Architecture/CardVector_Subsystem_Ownership_Matrix.md`
- `Docs/Architecture/Compatibility_Adapter_Register.md`
- `Docs/Architecture/Deprecation_Register.md`
- `Docs/Architecture/README.md`
- `Docs/Architecture/cardvector_architecture_manifest.json`
- `Docs/Architecture/CV-ADR-024-supabase-capture-location-registry.md`
- `Docs/Architecture/Supabase_Registry_Migration/`
- `Docs/app.js`
- `Platform/cardvector/integrations/supabase/`
- `Platform/Putnam_OS/System/app/inventory_locations.py`
- `Platform/Putnam_OS/System/app/putnam_os.py`
- `Platform/Putnam_OS/System/tools/mobile_capture_queue.py`
- `Tests/supabase_registry/`
- `Tools/migrate_legacy_registry_to_supabase.py`
- `Tools/test_mobile_location_contract.py`
- `supabase/migrations/20260725090000_canonical_capture_location_registry.sql`

## Existing Audit Documentation

The following folder appears related to the investigation that led to this
migration. Review before staging so it is intentionally included or excluded:

- `Docs/Architecture/Inventory_Location_Supabase_Audit/`

## Unrelated Working-Tree Changes To Preserve

Do not stage or commit these as part of the Supabase registry migration unless
the owner explicitly directs it:

- Deleted: `Business/eBay_Store_Items/Generated image 1.png`
- Untracked: `Business/eBay_Store_Items/Putnam Collectibles Logo.png`

## Safe Branch Plan

If the working tree still contains only the known migration changes plus the
two unrelated image changes above, creating a branch is safe because Git will
carry the working-tree state to the new branch:

```powershell
git switch -c codex/supabase-capture-location-registry
```

Expected effect:

- Creates and switches to `codex/supabase-capture-location-registry`.
- Preserves all current uncommitted files.
- Does not stage, commit, delete, reset, or clean anything.

If the branch already exists, use:

```powershell
git switch codex/supabase-capture-location-registry
```

Only do this if `git status --short` has been reviewed immediately beforehand.

## Safe Staging Plan

Stage only the migration-related paths:

```powershell
git add Docs/Architecture/CardVector_Architecture_Decision_Log.md Docs/Architecture/CardVector_Architecture_Manifest.md Docs/Architecture/CardVector_Subsystem_Ownership_Matrix.md Docs/Architecture/Compatibility_Adapter_Register.md Docs/Architecture/Deprecation_Register.md Docs/Architecture/README.md Docs/Architecture/cardvector_architecture_manifest.json Docs/Architecture/CV-ADR-024-supabase-capture-location-registry.md Docs/Architecture/Supabase_Registry_Migration Docs/app.js Platform/cardvector/integrations/supabase Platform/Putnam_OS/System/app/inventory_locations.py Platform/Putnam_OS/System/app/putnam_os.py Platform/Putnam_OS/System/tools/mobile_capture_queue.py Tests/supabase_registry Tools/migrate_legacy_registry_to_supabase.py Tools/test_mobile_location_contract.py supabase/migrations/20260725090000_canonical_capture_location_registry.sql
```

Do not stage `Business/eBay_Store_Items/Generated image 1.png` or
`Business/eBay_Store_Items/Putnam Collectibles Logo.png`.

## Suggested Commit Plan

Use one focused commit after approval:

```powershell
git commit -m "feat(supabase): add canonical capture location registry migration"
```

If the audit folder is intentionally included, keep it in the same commit only
if the owner wants the implementation and its investigation evidence preserved
together. Otherwise commit the audit folder separately as documentation.
