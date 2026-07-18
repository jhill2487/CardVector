# Phase 0 Baseline Test Plan

## Safety Boundary

Run only syntax, import, fixture, contract, and temporary-directory tests.
Do not launch the production GUI, call live marketplaces, upload captures,
write inventory, or mutate production databases.

## Test Matrix

| Area | Coverage | Planned validation | Safety |
| --- | --- | --- | --- |
| Production launcher | Manual/static smoke test exists | Inspect launcher target and startup chain; do not launch GUI | Read-only |
| Desktop startup | Partial automated coverage | Compile active modules and import desktop services | Writes ignored bytecode only |
| Dashboard | Partial coverage | `test_desktop_workflow_ui.py` | Source assertions |
| Marketplace Intelligence | Automated test exists | Fixture smoke test | Temporary output only |
| Price Vector | Automated tests exist | Canonical engine, FMV separation, persistence, compatibility adapter | Temporary data only |
| eBay workflow | Partial coverage | Business-policy smoke test and pricing consolidation | No live eBay action |
| Capture | Automated tests exist | Capture Studio, auto-capture, mobile queue, thumbnail pairs, OBS manager | Temporary data/mocks |
| Card recognition | Partial/manual benchmark coverage | Inventory tests only; do not run scanner benchmark in Phase 0 | Potentially expensive / external assets |
| Inventory | Partial automated coverage | Inventory audit test identified but not run | Test writes source-tree artifacts |
| Orders | Automated smoke test exists | `test_orders_v1.py` | Temporary data only |
| Exports | Partial automated coverage | Marketplace fixture reports and eBay policy row generation | Temporary/in-memory |
| Database | Partial coverage | Price Vector repository test with temporary SQLite; inventory runtime DB read-only inventory | Temporary/read-only |
| Configuration | Partial coverage | JSON parse and key inventory | Read-only |
| Logging | Partial coverage | Startup validator only | Writes ignored validation logs |
| Error handling | Partial coverage | Queue sanitization and contract tests | Mocks/fixtures |
| Public mobile/storefront | Automated contract tests exist | Supabase, location, and storefront contracts; Node syntax check | Read-only |

## Explicitly Skipped

- `test_listing_optimizer_v1_2.py`: writes source-tree test artifacts and
  production export-history logs.
- `test_inventory_audit_mode_v1_0.py`: deletes and recreates a source-tree
  test-artifact directory.
- Live production launcher execution: starts the GUI and writes startup state.
- Live eBay, TCGplayer, Supabase upload, inventory mutation, and scanner
  benchmark operations.

## Runtime Resolution

The Windows `py.exe` launcher was unavailable to this sandbox, and `node` was
not on its PATH. Rerun tests with the Codex workspace runtimes:

```text
C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe
C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe
```

This is a test-command adjustment only. Project configuration and launchers
must not be changed in Phase 0.
