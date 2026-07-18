# Price Vector Integration Gate Test Results

**Run date:** 2026-07-18
**Implementation under test:** `main` at `aaf9a0f49b779a02f720fd99610183a5026b5ef9`

The installed interpreter was invoked directly at
`C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\python.exe` to avoid the
known Microsoft Store alias contention.

## Blocking Validation

| Command or scope | Result | Duration |
| --- | --- | ---: |
| `-m py_compile` for 18 affected/application Python files | Pass | 0.928 s |
| FMV separation and pricing consolidation unit tests | Pass, 21 tests | 1.163 s |
| `unittest discover -s Tests\application` | Pass, 6 tests | 0.405 s |
| `test_workflow_context.py` | Pass, 3 tests | 0.391 s |
| `test_desktop_workflow_ui.py` | Pass, 5 tests | 0.292 s |
| Mobile capture queue unit tests | Pass, 25 tests | 0.730 s |
| Supabase capture contract tests | Pass, 19 tests | 0.286 s |
| Public storefront contract tests | Pass, 7 tests | 0.693 s |
| Mobile thumbnail-pair tests | Pass, 3 tests | 0.724 s |
| Capture Studio v2 smoke | Pass | 0.439 s |
| Auto Capture v2.1 smoke | Pass | 0.721 s |
| OBS connection manager smoke | Pass | 0.216 s |
| Orders v1 smoke | Pass | 0.296 s |
| eBay policy configuration smoke | Pass | 0.733 s |
| Marketplace Intelligence smoke | Pass | 0.441 s |
| Putnam pricing compatibility smoke | Pass | 0.325 s |
| Architecture guardrail unit tests | Pass, 12 tests | 1.514 s |
| Architecture checker warning mode | Pass; 48 baseline, 0 new | 1.741 s |
| Architecture checker strict mode | Pass; 48 baseline, 0 new | 1.676 s |
| `node --check Docs\app.js` | Pass | 0.174 s |
| Architecture README local links | Pass; 36 checked, 0 missing | 0.158 s |
| Architecture manifest JSON parse | Pass; schema 1.0 | 0.327 s |
| Production launcher target/hash | Pass | 0.324 s |
| Integration secret-pattern scan | Pass; 20 files, 0 matches | 0.285 s |
| `git diff --check` | Pass | 0.081 s |

Representative commands:

```powershell
& $PY -m py_compile <18 affected and application files>
& $PY -m unittest `
  Platform.Marketplace_Intelligence.tests.test_price_vector_fmv_separation `
  Platform.Marketplace_Intelligence.tests.test_pricing_engine_consolidation -v
& $PY -m unittest discover -s Tests\application -p "test_*.py" -v
& $PY -m unittest Platform.Putnam_OS.System.tools.test_mobile_capture_queue -v
& $PY -m unittest Tools.test_mobile_capture_supabase_contract -v
& $PY -m unittest Tools.test_public_storefront_contract -v
& $PY -m unittest discover -s Tools\architecture -p "test_*.py" -v
& $PY Tools\architecture\check_architecture.py
& $PY Tools\architecture\check_architecture.py --strict
& $PY -m Platform.Putnam_OS.System.MarketIntelligence.Pricing.test_pricing_engine
& $NODE --check Docs\app.js
git diff --check cardvector-pre-price-vector-integration..HEAD
```

## Output And Contract Coverage

The 21 focused pricing tests verify distinct FMV, recommendation, and final
price fields; default final price; explicit FMV input; persistence round trip;
legacy field compatibility; report/export fields; representative pricing
parity; active TCGplayer listing exclusion from FMV; and exclusion of
recognition and Grade Vector.

The application and desktop contract tests verify that Phase 2 workflow
delegation remains active. Queue, Capture, OBS, Orders, Supabase, and storefront
tests verify that adjacent validated workflows were not regressed.

## Documented Pre-Existing Failures

These failures match the Phase 1.5 baseline and do not block this gate:

1. `Tools.test_mobile_location_contract`: 13 passed, 1 failed in 0.435 s.
   The stale assertion expects a three-argument `captureRoute`; production uses
   the approved capture-layout argument.
2. `test_listing_optimizer_v1_2.py`: failed in 0.549 s because its historical
   `changes == 7` assertion does not match the previously approved pricing
   behavior.
3. `Tools/validate_production_startup.py`: failed in 0.154 s because its root
   predicate requires the absent historical `Docs/AGENTS.md`.
4. `test_inventory_audit_mode_v1_0.py` was not rerun. Phase 1.5 documents its
   OneDrive cleanup permission failure, and running it can alter tracked test
   fixtures.

The Listing Optimizer test created tracked runtime-state changes and one
timestamped output directory before reaching its known assertion. All three
tracked files were restored to merged `HEAD`, and the exact generated directory
was removed. A subsequent status check was clean before report creation.

No live eBay, TCGplayer, Supabase upload, OBS capture, inventory mutation, or
production database operation was performed.
