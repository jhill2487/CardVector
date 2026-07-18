# Phase 4 Test Results

**Run date:** 2026-07-18

The bundled Codex Python and Node runtimes were used because workstation
Microsoft Store Python aliases are not reliable.

## Focused Results

| Scope | Result |
| --- | --- |
| Pre-change Capture Studio smoke | Pass |
| Pre-change Auto Capture smoke | Pass |
| Pre-change OBS manager smoke | Pass |
| Pre-change mobile queue | Pass, 25 tests |
| Pre-change thumbnail pairs | Pass, 3 tests |
| Pre-change Supabase/mobile contract | Pass, 19 tests |
| Legacy Capture characterization | Pass, 5 tests |
| Canonical Capture and handoff contract | Pass, 7 tests |
| Phase 2 Application layer | Pass, 6 tests |
| Runtime composition | Pass |
| Explicit compilation of affected and protected Python entry files | Pass |
| Capture, queue, pairing, and canonical bundle | Pass, 40 tests |
| Capture Studio smoke | Pass |
| Auto Capture smoke | Pass |
| OBS manager smoke | Pass |
| Marketplace Intelligence/pricing equivalence | Pass, 53 tests |
| Application layer | Pass, 6 tests |
| Workflow context | Pass, 3 tests |
| Desktop workflow contracts | Pass, 5 tests |
| Supabase and public storefront contracts | Pass, 26 tests |
| Orders smoke | Pass |
| eBay policy smoke | Pass |
| Marketplace Intelligence standalone smoke | Pass |
| Putnam pricing compatibility smoke | Pass |
| Architecture checker unit tests | Pass, 12 tests |
| Architecture checker warning/strict | Pass, 48 baseline and 0 new |
| Architecture Markdown links | Pass, 39 checked and 0 missing |
| Manifest parse and ownership fields | Pass |
| Node syntax for `Docs/app.js` | Pass |
| Changed/new-file secret scan | Pass, 32 files and 0 flagged |
| Production launcher target/hash | Pass |
| `git diff --check` | Pass |

## Documented Pre-existing Result

`Tools.test_mobile_location_contract` reproduced its documented stale
assertion: 13 tests passed and 1 failed. The assertion expects
`captureRoute(state.etbId, state.location, state.captureType)`, while the
approved production workflow includes the fourth capture-layout argument.
Phase 4 did not modify `Docs/app.js` or this test.

Pillow emitted its existing `Image.getdata()` future-deprecation warning during
frame-signature coverage. The same call and output are intentionally preserved
for exact behavior; no test failed.

## Safety

No live camera, OBS instance, mobile device, CardUploader recognition,
marketplace action, production database write, inventory mutation, or real
Capture-folder operation occurred.
