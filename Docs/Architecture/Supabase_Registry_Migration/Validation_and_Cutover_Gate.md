# Validation And Cutover Gate

## Validation Commands

```powershell
& 'C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m py_compile Tools\migrate_legacy_registry_to_supabase.py Platform\cardvector\integrations\supabase\registry.py Platform\Putnam_OS\System\app\inventory_locations.py Platform\Putnam_OS\System\tools\mobile_capture_queue.py Platform\Putnam_OS\System\app\putnam_os.py
```

Result: passed.

```powershell
& 'C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m unittest Tests.supabase_registry.test_canonical_registry_migration Tools.test_mobile_location_contract Platform.Putnam_OS.System.tools.test_mobile_capture_queue Tools.test_mobile_capture_supabase_contract
```

Result: passed, 75 tests.

```powershell
& 'C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' --check Docs\app.js
```

Result: passed.

```powershell
& 'C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' Tools\architecture\check_architecture.py
& 'C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' Tools\architecture\check_architecture.py --strict
```

Result: 48 documented baseline findings, 0 new findings in both modes.

```powershell
git diff --check
```

Result: passed. Git reported only line-ending normalization warnings.

```powershell
rg -n "(service_role|SUPABASE_SERVICE_ROLE_KEY|CARDVECTOR_SUPABASE_SERVICE_ROLE_KEY|eyJ[A-Za-z0-9_-]{20,}|password\s*=|apikey\s*=|Authorization:\s*Bearer)" Docs\app.js Platform\cardvector\integrations\supabase Platform\Putnam_OS\System\app\inventory_locations.py Platform\Putnam_OS\System\tools\mobile_capture_queue.py Tools\migrate_legacy_registry_to_supabase.py supabase\migrations\20260725090000_canonical_capture_location_registry.sql Docs\Architecture\Supabase_Registry_Migration Docs\Architecture\CV-ADR-024-supabase-capture-location-registry.md
```

Result: no secret values found. Matches were environment-variable names, SQL
role grants, UI password field names, and token-redaction code.

## Production Gate

Production migration is not approved and was not run.

Blocked items before production apply:

- 82 dry-run conflicts in legacy capture/session/image evidence require review.
- The Supabase migration must be reviewed before `supabase db push`.
- The legacy import command must be reviewed before `--apply`.
- Dual-read discrepancy comparison cannot be completed until the canonical
  tables exist in the deployed project.

## Dual-Read Status

CardVector OS now has a dual-read-capable path:

1. Try canonical Supabase registry rows.
2. Project canonical rows into the legacy ETB UI shape.
3. Fall back to legacy JSON cache when Supabase is unavailable or empty.
4. Display the active source and sync warning in the registry summary.

Current discrepancy report status: pending production schema deployment and
data import approval. No live comparison was performed because the expected
canonical tables are not deployed yet.

## Manual Validation Not Claimed

No live mobile capture, live iPhone Safari flow, live CardVector OS operator UI
review, production Supabase migration, or production import was performed during
this implementation pass.
