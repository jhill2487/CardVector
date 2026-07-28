# Migration Runbook And Rollback

## Production Approval Gate

Before applying the production Supabase migration or importing production data,
review and approve:

1. Proposed schema:
   `supabase/migrations/20260725090000_canonical_capture_location_registry.sql`
2. Legacy-to-Supabase field mapping:
   `Docs/Architecture/Supabase_Registry_Migration/Canonical_Model_and_Field_Mapping.md`
3. Dry-run report:
   `Docs/Architecture/Supabase_Registry_Migration/Dry_Run_Migration_Report.md`
4. Backup location:
   `Work_Sessions/supabase_registry_migration_dry_run_20260725/backups`
5. Rollback procedure in this document.
6. Exact commands below.

## Exact Commands For Later Approval

Do not run these until approved.

```powershell
supabase db push
& 'C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m Tools.migrate_legacy_registry_to_supabase --apply --confirm-backup --output-dir Work_Sessions\supabase_registry_migration_apply_YYYYMMDD_HHMMSS
```

The apply command will refuse to run while invalid or conflicting records remain
in the dry-run report.

## Safe Rollout

1. Deploy schema only.
2. Run dry-run migration and review conflicts.
3. Resolve or explicitly accept conflict rules.
4. Run apply mode after backup confirmation.
5. Compare legacy JSON projection with canonical Supabase rows.
6. Enable Supabase read source in CardVector OS.
7. Keep legacy JSON as read-only fallback/export during verification.
8. Enable canonical writes in both CardVector.app and CardVector OS.
9. Retire legacy authority only after the verification period.

## Rollback Before Data Import

If the schema is deployed but no data is imported:

1. Disable canonical registry reads by unsetting desktop Supabase service-role
   environment variables or leaving tables unavailable.
2. CardVector OS falls back to the legacy JSON cache.
3. Revert the migration commit if needed.
4. Drop the newly created canonical schema objects only after confirming no new
   rows were written.

## Rollback After Data Import

If rows are imported and cutover is not accepted:

1. Export canonical Supabase rows from all new registry tables.
2. Preserve the dry-run/apply reports and legacy JSON backups.
3. Disable canonical registry reads.
4. Keep legacy JSON as the operator-facing source.
5. Do not delete Supabase rows until export and owner approval are complete.

## Data-Loss Controls

- The migration tool backs up legacy JSON files before dry-run or apply.
- Apply mode requires `--confirm-backup`.
- Apply mode is blocked when invalid or conflicting records exist.
- Upserts use deterministic IDs, making reruns idempotent.
- The local JSON registry is not deleted or overwritten.
