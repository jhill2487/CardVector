# Supabase Capture/Location Registry Pre-Production Approval Package

**Date:** 2026-07-25
**Status:** Ready for owner review; production commands have not been run.
**Approved project reference:** `iqdpfgpkagjxzedfxrvn`
**Approved project host:** `iqdpfgpkagjxzedfxrvn.supabase.co`

## 1. Root Cause Summary

CardVector OS still reads a legacy local ETB/location JSON projection for the
Inventory / ETB Location Registry. That projection was created before the shared
Supabase registry existed and only reflects conversion sessions that reached
the legacy `Location Complete` path. CardVector.app mobile captures upload
photos and create staged capture artifacts, but mobile-origin sessions can
remain `Mobile Capture Staged` and do not automatically appear in the legacy OS
registry projection.

The migration dry-run conflicts were not distinct records. All 82 reviewed
conflicts are duplicate legacy staging artifacts:

- 2 duplicate capture-session artifacts with the same legacy session id and
  same deterministic canonical session id.
- 80 duplicate capture-image artifacts with the same storage bucket/object path,
  same canonical image identity, and same canonical cloud object.

No hidden exclusion issue remains.

## 2. Final Canonical Architecture

Supabase is the canonical shared registry for:

- storage locations
- ETBs and ETB slots
- capture sessions
- capture image metadata
- capture/location/inventory reference relationships

CardVector.app writes canonical Supabase records during mobile capture.
CardVector OS reads the same canonical records for the ETB Location Registry and
uses legacy JSON only as migration input, fallback cache, export, or audit
evidence. CardUploader remains the owner of managed inventory records,
quantities, recognition, allocation, and order-picking facts.

## 3. Schema Migration

Schema migration file:

`supabase/migrations/20260725090000_canonical_capture_location_registry.sql`

The static review is recorded in:

`Docs/Architecture/Supabase_Registry_Migration/Schema_Static_Review.md`

## 4. Supabase Project Reference

| Source | Project ref or host | Result |
| --- | --- | --- |
| CardVector.app public config | `iqdpfgpkagjxzedfxrvn.supabase.co` | Matches |
| Process environment `CARDVECTOR_SUPABASE_URL` | `iqdpfgpkagjxzedfxrvn.supabase.co` | Matches |
| User environment `CARDVECTOR_SUPABASE_URL` | Missing | Non-blocking for this dry run; set before production operations if needed |
| Machine environment `CARDVECTOR_SUPABASE_URL` | Missing | Non-blocking for this dry run |
| Supabase CLI linked project | Not found in local `supabase/.temp` | Must be linked or explicitly verified before production apply |
| Storage bucket name | `mobile-capture-originals` | Matches |

No secret values are included in this package.

## 5. Legacy Source Files

Primary legacy registry source:

`Platform/Putnam_OS/System/data/inventory/etb_location_registry.json`

Legacy capture/session sources include:

- `Platform/Putnam_OS/System/data/inventory_conversion/sessions/`
- `Capture/Physical_Inventory_Conversion/`
- mobile capture staged artifacts referenced by the migration reports

## 6. Backup Location

Latest resolved dry-run backup:

`Work_Sessions/supabase_registry_migration_resolved_dry_run_20260725_1/backups`

The migration tool creates a fresh backup under the chosen production report
directory before apply. Production apply must not proceed if backup files are
missing.

## 7. Migration Counts

Latest resolved dry-run:

| Entity | Discovered | Prepared | Approved duplicate skips | Invalid | Unresolved conflicts | Balanced |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Locations | 77 | 77 | 0 | 0 | 0 | Yes |
| Capture sessions | 21 | 19 | 2 | 0 | 0 | Yes |
| Capture images | 591 | 511 | 80 | 0 | 0 | Yes |

Mathematical reconciliation:

- `77 locations = 77 prepared`
- `21 capture sessions = 19 prepared + 2 approved exact-duplicate skips`
- `591 capture images = 511 prepared + 80 approved exact-duplicate skips`

## 8. Approved Duplicate-Skip Counts

Reviewed resolution file:

`Work_Sessions/supabase_registry_migration_dry_run_20260725/approved_resolution_plan_exact_duplicates.json`

Approved actions:

- 82 total `skip_exact_duplicate`
- 0 merges
- 0 updates
- 0 deletes
- 0 overwrite actions

The approved action is to skip the duplicate incoming legacy artifact while
preserving the one canonical record.

## 9. Zero Unresolved Conflicts

Resolved dry-run report:

`Work_Sessions/supabase_registry_migration_resolved_dry_run_20260725_1/legacy_registry_migration_report.json`

Result:

- Blocking conflicts: 0
- Unresolved conflicts in balanced summary: 0

## 10. Zero Invalid Records

Resolved dry-run result:

- Invalid records: 0

## 11. Zero Unresolved Relationships

Resolved dry-run result:

- Unresolved relationships: 0

## 12. RLS Review Result

Static review found RLS enabled on canonical registry tables. Authenticated users
manage rows where `owner_user_id = auth.uid()`, anonymous table access is
revoked, and service-role access is granted only for server-side operations.

Production apply remains gated on verifying the target project before running
the migration.

## 13. Storage Policy Review Result

The migration ensures the private `mobile-capture-originals` bucket exists and
adds authenticated object policies constrained to object paths whose first path
segment is the authenticated user id. Existing storage objects are not deleted.

## 14. Idempotency Test Result

Two resolved dry-runs were executed with the same reviewed resolution file:

- `Work_Sessions/supabase_registry_migration_resolved_dry_run_20260725_1`
- `Work_Sessions/supabase_registry_migration_resolved_dry_run_20260725_2`

Results matched:

- Same prepared counts.
- Same approved duplicate-skip counts.
- Same zero blocking conflicts.
- Same balanced totals.
- Same deterministic canonical id mappings.

## 15. Rollback Procedure

Before production apply:

1. Confirm the production Supabase project reference is `iqdpfgpkagjxzedfxrvn`.
2. Confirm fresh legacy backups were created by the migration tool.
3. Preserve the pre-apply git commit SHA.
4. Preserve the production migration report directory.

If schema apply must be rolled back before import:

1. Stop CardVector registry writes.
2. Restore the previous git state if application files were deployed.
3. Use Supabase dashboard or reviewed SQL rollback to remove only the canonical
   registry objects created by this migration if they are empty.
4. Do not delete existing storage objects or legacy JSON files.

If data import must be rolled back:

1. Stop CardVector registry writes.
2. Use the production migration report to identify inserted canonical rows.
3. Prefer archival/status reversal over deletion unless owner approves row
   deletion.
4. Restore OS reads to the legacy JSON fallback if needed.
5. Preserve all migration reports and backups for audit.

## 16. Exact Production Commands Proposed

These commands are proposed only. They have not been run.

```powershell
cd C:\Users\user\OneDrive\PutnamCollectibles
supabase link --project-ref iqdpfgpkagjxzedfxrvn
supabase migration list
supabase db push
```

After the schema is applied and reviewed:

```powershell
cd C:\Users\user\OneDrive\PutnamCollectibles
$env:CARDVECTOR_SUPABASE_URL = "https://iqdpfgpkagjxzedfxrvn.supabase.co"
$env:CARDVECTOR_SUPABASE_SERVICE_ROLE_KEY = "<set outside source control>"
python -m Tools.migrate_legacy_registry_to_supabase --apply --resolution-file Work_Sessions\supabase_registry_migration_dry_run_20260725\approved_resolution_plan_exact_duplicates.json --report-dir Work_Sessions\supabase_registry_migration_production_apply_YYYYMMDD_HHMMSS --confirm-schema-migration --approved-project-ref iqdpfgpkagjxzedfxrvn
```

## 17. Expected Effects Of Each Command

- `supabase link --project-ref iqdpfgpkagjxzedfxrvn`: links the local Supabase
  CLI workspace to the approved project.
- `supabase migration list`: confirms local and remote migration state before
  applying SQL.
- `supabase db push`: applies versioned SQL migrations, including the canonical
  registry schema.
- Environment variable assignment: supplies the approved project URL and a
  service-role key without storing secrets in source.
- `python -m Tools.migrate_legacy_registry_to_supabase --apply ...`: imports
  prepared legacy rows into the canonical schema, skips the 82 reviewed exact
  duplicates, refuses unresolved conflicts, refuses unbalanced totals, and
  writes production migration reports.

## 18. Post-Migration Validation Checklist

1. Confirm canonical table counts match the prepared import counts.
2. Confirm 77 locations are present.
3. Confirm 19 canonical capture sessions are present.
4. Confirm 511 canonical capture images are present.
5. Confirm no duplicate storage bucket/object path rows exist.
6. Confirm no duplicate `owner_user_id + legacy_session_id` rows exist.
7. Confirm mobile-origin sessions appear in CardVector OS without legacy JSON
   conversion.
8. Confirm CardVector.app can select/create locations against Supabase.
9. Confirm CardVector OS can refresh the canonical registry.
10. Confirm RLS blocks unauthorized reads/writes.
11. Confirm storage policies allow authenticated user-owned image paths only.
12. Preserve all production apply reports.

## 19. Production Command Status

Production commands have not been run.

Specifically, this task did not run:

- `supabase db push`
- production schema apply
- production data import
- production cutover
- production inventory changes
