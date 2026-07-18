# Phase 3 Test Results

**Run date:** 2026-07-18

The bundled Codex Python and Node runtimes were used because the workstation
Microsoft Store Python aliases are not reliable in this environment.

## Passing Validation

| Scope | Result |
| --- | --- |
| Explicit Python compilation for 18 affected files | Pass |
| Canonical/FMV/Price Vector/consolidation suites | Pass, 53 tests |
| Application layer | Pass, 6 tests |
| Workflow context | Pass, 3 tests |
| Desktop workflow contracts | Pass, 5 tests |
| Mobile capture queue | Pass, 25 tests |
| Supabase and storefront contracts | Pass, 26 tests |
| Mobile thumbnail pairs | Pass, 3 tests |
| Capture Studio smoke | Pass |
| Auto Capture smoke | Pass |
| OBS manager smoke | Pass |
| Orders smoke | Pass |
| eBay policy smoke | Pass |
| Marketplace Intelligence standalone smoke | Pass |
| Putnam pricing compatibility smoke | Pass |
| Architecture checker tests | Pass, 12 tests |
| Architecture README links | Pass, 38 checked, 0 missing |
| Manifest parse/ownership | Pass, schema 1.0, architecture 1.1 |
| Node syntax `Docs/app.js` | Pass |
| Supported import/composition probe | Pass |
| Secret-pattern scan | Pass, 31 files, 0 flagged |
| Launcher target/hash | Pass |
| Architecture checker warning and strict | Pass, 48 baseline, 0 new |
| `git diff --check` | Pass |

## Non-Blocking Pre-Existing Results

1. `test_listing_optimizer_v1_2.py` still fails its historical
   `changes == 7` assertion. This is the documented stale expectation from
   Phase 1.5 and the Integration Gate. Phase 3 did not change the optimizer.
2. Package-style import of `putnam_os.py` without its app directory fails on
   its pre-existing bare `workflow_context` import. The supported test/runtime
   bootstrap passed. Packaging cleanup is outside Phase 3.
3. Running `test_workflow_context` as a dotted package initially failed for the
   same sibling-import convention. Running the documented direct script passed
   all three tests.
4. The stale mobile-location assertion and OneDrive inventory-audit cleanup
   issue documented by the Integration Gate were not rerun because they are
   unrelated and the latter can mutate tracked fixtures.

## Safety

No live marketplace request, listing revision, offer, upload, email, production
database write, capture, or inventory mutation occurred. Persistence tests used
temporary SQLite databases only.
