# CardVector Validation And Rollback Standards

**Status:** Proposed permanent migration standard

## Required Evidence For Every Migration Package

### Before state

- branch and commit,
- clean or explicitly inventoried working tree,
- affected files and owners,
- current test results,
- current manual workflow result,
- relevant runtime/schema version,
- screenshots or output hashes where useful,
- known pre-existing failures.

### After state

- exact diff,
- test commands and complete results,
- manual validation performed,
- output/schema comparison,
- guardrail results,
- unresolved differences,
- rollback command/process.

No phase proceeds on "compile passed" alone.

## Core Validation Matrix

| Area | Automated validation | Manual validation |
|---|---|---|
| Application startup | import/package smoke, configuration failure tests | official VBS launch and clean close |
| Desktop shell | view construction/source contract | Home, Capture, Processing, Marketplace, Orders, Settings |
| Dashboard | job query tests | exact actionable jobs and no stale cards |
| Marketplace Intelligence | fixture unit/integration tests | representative analysis report |
| Pricing | FMV/recommendation/final separation and parity | CardUploader CSV through review |
| Capture | session/pair/routing/queue tests | desktop/manual/auto/mobile modes as affected |
| Scanner | no production import currently | confirm CardUploader recognition handoff; native scanner only if future |
| Inventory | registry/conversion/sync/reconciliation tests | ETB/location view, conversion, resume |
| Listings/export | exact CSV schema and row fixtures | eBay-ready output and folder handoff |
| Orders | grouping and pick-list fixtures | import sample order and open pick list |
| Shipping | policy validation tests | confirm displayed policy/settings |
| Database | migration up/down or restore test, repository tests | backup location and production migration check |
| Configuration | precedence, missing/corrupt config tests | settings persist, secrets hidden |
| Paths | start from another cwd, temp workspace tests | home/work PCs |
| Logging | redaction and error capture tests | log created, readable, no secrets |
| Error paths | simulated dependency/file/network failures | actionable UI error, app remains open |
| Compatibility | old import/launcher delegation tests | legacy action routes to canonical behavior |
| Public site | static export, route/link/secret tests | live deployment only when requested |

## Automated Test Minimums

Every migration:

- compile changed Python,
- focused unit tests,
- focused integration/contract tests,
- architecture guardrails,
- `git diff --check`.

Subsystem migration:

- all subsystem tests,
- compatibility tests,
- affected end-to-end smoke test.

Entry/path/config migration:

- clean-clone/editable-install test,
- launch from non-repository working directory,
- home and work workstation checks.

Data/schema migration:

- backup,
- migration against a copy,
- read old format,
- write/read new format,
- rollback/restore test.

## Manual Production Smoke Sequence

Use only test/safe data:

1. Launch through official production launcher.
2. Confirm startup status and no secret exposure.
3. Open each production workspace.
4. Verify pending work and exact folder actions.
5. Start/open a capture session if Capture is affected.
6. Confirm mobile queue remains automatic if Capture/paths are affected.
7. Import a sample CardUploader CSV if Processing is affected.
8. Run pricing and inspect recommendation/output.
9. Generate an eBay-ready CSV and confirm exact headers.
10. Verify inventory registry/conversion if Inventory is affected.
11. Import sample orders and generate pick list if Orders is affected.
12. Trigger one controlled failure.
13. Close cleanly with workers active.

Only affected steps are required for small changes, but architecture/entry-point phases run the full sequence.

## Output Parity

For behavior-preserving migrations compare:

- file names,
- relative output folders,
- CSV headers and order,
- row values,
- JSON keys and types,
- state transitions,
- log/report schemas,
- exceptions and cancellation,
- UI-visible result/status.

Differences require explicit approval. Normalized timestamps and generated IDs may be excluded if documented.

## Rollback Levels

### Code-only

Revert the single migration commit.

### Launcher

Redirect official launcher to the previous validated target. Keep prior target for one shadow release.

### Configuration

Restore backed-up config and prior loader. Never destroy unknown keys.

### Data/schema

- stop writes,
- restore backup or run tested reverse migration,
- verify record counts/checksums,
- restart prior code.

### External integration

Disable new adapter/config and return to previous interface. Do not delete cloud source data.

## Rollback Requirements

Every plan states:

- trigger conditions,
- person authorized,
- exact prior commit/tag,
- files/data affected,
- commands/manual steps,
- expected restored state,
- verification after rollback.

"Use Git" is insufficient for data/schema changes.

## Approval Gate

Before moving to the next phase, provide:

- before/after evidence,
- diff summary,
- all test output,
- manual validation status,
- known limitations,
- rollback procedure,
- explicit owner approval.

An automatic CI pass does not substitute for approval on architecture changes.

## Failure Classification

- **Regression:** new failure caused by the migration. Blocks completion.
- **Pre-existing:** reproduced on baseline. Recorded, not silently fixed in unrelated scope.
- **Environmental:** dependency/workstation/service condition. Requires documented manual check.
- **Expected difference:** approved contract change with migration documentation.
- **Unknown:** blocks progression until explained.

## Completion Standard

A migration package is complete only when:

- behavior/contract acceptance criteria pass,
- no new architecture violations,
- no unrelated files included,
- runtime/business data preserved,
- documentation updated,
- rollback tested or demonstrably executable,
- owner approves.
