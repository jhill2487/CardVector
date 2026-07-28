# Dry-Run Migration Report

## Command

```powershell
& 'C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m Tools.migrate_legacy_registry_to_supabase --output-dir Work_Sessions\supabase_registry_migration_dry_run_20260725
```

## Result

- Mode: dry-run
- Backup path:
  `Work_Sessions/supabase_registry_migration_dry_run_20260725/backups`
- JSON report:
  `Work_Sessions/supabase_registry_migration_dry_run_20260725/legacy_registry_migration_report.json`
- Human summary:
  `Work_Sessions/supabase_registry_migration_dry_run_20260725/legacy_registry_migration_summary.md`

## Counts

| Metric | Count |
| --- | ---: |
| Locations discovered | 77 |
| Capture sessions discovered | 21 |
| Capture images discovered | 591 |
| Locations prepared | 77 |
| Capture sessions prepared | 19 |
| Capture images prepared | 511 |
| Invalid records | 0 |
| Identical duplicates | 0 |
| Conflicting records | 82 |
| Unresolved relationships | 0 |

The 82 conflicts are exactly the excluded records:

- 2 capture sessions excluded because multiple legacy conversion-session JSON
  files map to the same canonical capture session.
- 80 capture images excluded because duplicate staged capture folders map to
  the same canonical storage object paths.

The balanced totals are:

| Entity | Formula | Balanced |
| --- | --- | --- |
| Locations | `77 discovered = 77 prepared + 0 conflicts + 0 duplicates + 0 invalid` | yes |
| Capture sessions | `21 discovered = 19 prepared + 2 conflicts + 0 duplicates + 0 invalid` | yes |
| Capture images | `591 discovered = 511 prepared + 80 conflicts + 0 duplicates + 0 invalid` | yes |

## Conflict Categories

| Category | Count | Recommended resolution |
| --- | ---: | --- |
| Duplicate capture session | 2 | Merge provenance after review |
| Duplicate storage object path | 80 | Merge provenance after review |

## Generated Review Artifacts

- `Work_Sessions/supabase_registry_migration_dry_run_20260725/legacy_registry_conflict_report.md`
- `Work_Sessions/supabase_registry_migration_dry_run_20260725/legacy_registry_conflict_report.csv`
- `Work_Sessions/supabase_registry_migration_dry_run_20260725/legacy_registry_conflict_report.json`
- `Work_Sessions/supabase_registry_migration_dry_run_20260725/excluded_capture_sessions.csv`
- `Work_Sessions/supabase_registry_migration_dry_run_20260725/excluded_capture_images.csv`
- `Work_Sessions/supabase_registry_migration_dry_run_20260725/proposed_resolution_plan.json`
- `Work_Sessions/supabase_registry_migration_dry_run_20260725/balanced_dry_run_summary.json`

## Backup Evidence

| Source | SHA-256 | Bytes |
| --- | --- | ---: |
| `Platform/Putnam_OS/System/data/inventory/etb_location_registry.json` | `f2077d61d0634ac96313de4f1750fb95734b50be67288b522655c29213448a44` | 752935 |
| `Data/Config/etb_location_registry.json` | `991b70728181f881ec93faf17efd6824cb03365a0c84cc391b030f26d59c41e1` | 7372 |
| `Platform/Putnam_OS/System/config/location_registry.json` | `388ec487fea4666984ff4894dab19c3cec4b1f0736551bea41bebca0b7f83c42` | 4145 |

## Apply Status

Production apply is blocked.

Reason: the dry run found 82 conflicting legacy capture/session/image records.
The proposed resolution plan leaves every conflict unapproved. The migration
tool writes conflict details, refuses unresolved blocking conflicts, and exits
before Supabase writes when `--apply` is requested without reviewed approvals.

No production Supabase migration or production import was executed.
