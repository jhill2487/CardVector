# Phase 5 Test Results

## Focused Results

| Scope | Result |
| --- | --- |
| Pre-change inventory characterization | Pass, 4 tests |
| Canonical CardUploader inventory API | Pass, 8 tests |
| Tracked 308-row CardUploader export, read-only | Pass |
| Combined inventory contract/equivalence | Pass, 12 tests |
| Compilation of affected/protected Python files | Pass |
| Application layer | Pass, 6 tests |
| Workflow context and desktop contracts | Pass, 3 + 5 tests |
| FMV separation and pricing consolidation | Pass, 21 tests |
| Canonical Marketplace Intelligence | Pass, 32 tests |
| Marketplace Intelligence and pricing compatibility smokes | Pass |
| Mobile queue, Supabase, and storefront contracts | Pass, 51 tests |
| Thumbnail pairs | Pass, 3 tests |
| Canonical Capture | Pass, 12 tests |
| Capture Studio, Auto Capture, and OBS smokes | Pass |
| Orders pick-slip smoke | Pass |
| eBay policy smoke | Pass |
| Architecture guardrail tests | Pass, 12 tests |
| Architecture checker warning/strict | Pass, 48 baseline and 0 new |
| Architecture README local links | Pass, 40 checked and 0 missing |
| Manifest JSON and Phase 5 ownership fields | Pass |
| Node syntax for `Docs/app.js` | Pass |
| Changed/new-file secret scan | Pass, 34 files and 0 flagged |
| Production launcher target/hash | Pass |
| Protected Phase 3/4 code and schemas | Unchanged |
| `git diff --check` | Pass |

## Documented Pre-existing Result

`Tools.test_mobile_location_contract` reproduced its documented stale
assertion: 13 tests passed and 1 failed. The assertion expects the historical
three-argument `captureRoute`; the approved mobile workflow includes the fourth
capture-layout argument. Phase 5 did not modify `Docs/app.js` or that test.

`test_inventory_audit_mode_v1_0.py` was not rerun because its documented
OneDrive cleanup failure can mutate tracked test artifacts. Phase 5 inventory,
reconciliation, projection, and pick-slip behavior is covered with temporary
directories and the read-only tracked CardUploader export.

No live CardUploader, Supabase, inventory, order, marketplace, camera, or OBS
mutation was performed. No production database or schema was changed.
