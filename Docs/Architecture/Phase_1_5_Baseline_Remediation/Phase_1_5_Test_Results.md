# Phase 1.5 Test Results

**Run date:** 2026-07-18

## Summary

- Feature checkpoint Python compilation: pass for all 14 changed/new modules.
- Focused Price Vector tests: 21 passed.
- Clean-main `main.py` and `putnam_os.py` compilation: pass.
- Architecture guardrail tests: 12 passed.
- Architecture checker warning and strict modes: pass, 48 baseline findings,
  zero new findings.
- Safe mobile, capture, OBS, storefront, desktop workflow, orders, policy,
  Marketplace Intelligence, and pricing checks: pass.
- Three documented legacy failures reproduced.
- No live marketplace, capture upload, inventory mutation, or database write
  was performed.

## Feature Branch Validation

Branch: `codex/checkpoint-price-vector-ebay-phase-1-5`

| Validation | Result |
| --- | --- |
| `py_compile` for 14 changed/new Python files | Pass |
| `test_pricing_engine_consolidation` | Pass, 10 tests |
| `test_price_vector_fmv_separation` | Pass, 11 tests |
| Marketplace Intelligence smoke test | Pass |
| Putnam pricing compatibility smoke test | Pass |
| eBay policy configuration smoke test | Pass |
| Desktop workflow UI tests | Pass, 5 tests |
| Feature secret-pattern scan | Pass; no matches |
| Staged `git diff --check` | Pass |

## Clean Main Validation

Python executable:
`C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\python.exe`

| Command or scope | Result | Duration | Notes |
| --- | --- | ---: | --- |
| `-m py_compile ...\main.py ...\putnam_os.py` | Pass | 1.6 s | Ignored bytecode only |
| Architecture guardrail unit tests | Pass, 12 tests | 2.5 s | Test runtime 1.27 s |
| Architecture checker warning mode | Pass | 2.3 s | 48 baseline, 0 new |
| Architecture checker strict mode | Pass | 2.3 s | 48 baseline, 0 new |
| Architecture manifest JSON load | Pass | 1.0 s | Schema `1.0` |
| Architecture README local-link check | Pass | 0.7 s | 34 checked, 0 missing |
| Bundled Node `--check Docs\app.js` | Pass | 2.4 s | PATH alias unavailable |
| Mobile capture queue | Pass, 25 tests | 2.2 s | Temporary/mock data |
| Supabase capture contract | Pass, 19 tests | 1.6 s | Static contract |
| Public storefront contract | Pass, 7 tests | 2.3 s | Static/export fixture |
| Capture Studio v2 | Pass | 1.6 s | Temporary directory |
| Auto Capture v2.1 | Pass | 2.1 s | Temporary directory |
| Mobile thumbnail pairs | Pass, 3 tests | 2.1 s | Temporary directory |
| OBS manager | Pass | 1.4 s | No live OBS required |
| Desktop workflow UI | Pass, 5 tests | 1.5 s | Source/model checks |
| eBay policy config | Pass | 1.6 s | No eBay operation |
| Orders v1 | Pass | 1.4 s | Temporary directory |
| Workflow context | Pass, 3 tests | 1.4 s | Temporary directory |
| Marketplace Intelligence smoke | Pass | 1.4 s | Fixture-backed |
| Putnam pricing compatibility | Pass | 0.7 s | Package-module invocation |
| Three archived SQLite quick checks | Pass | 8.6 s | Opened read-only |
| Desktop import in supported app context | Pass | 1.3 s | Side effects restored |
| Configuration JSON load | Pass | 1.2 s | Values not displayed |
| Launcher target inspection | Pass | 1.1 s | Still `putnam_os.py` |
| Secret-pattern scans | Pass | <1 s each | No secret values printed |
| `git diff --check` | Pass | <1 s | Line-ending warning only |

Representative exact commands:

```powershell
& $PY -m py_compile Platform\Putnam_OS\System\app\main.py Platform\Putnam_OS\System\app\putnam_os.py
& $PY -m unittest discover -s Tools\architecture -p 'test_*.py' -v
& $PY Tools\architecture\check_architecture.py
& $PY Tools\architecture\check_architecture.py --strict
& $PY -m unittest Platform.Putnam_OS.System.tools.test_mobile_capture_queue -v
& $PY -m unittest Tools.test_mobile_capture_supabase_contract -v
& $PY -m unittest Tools.test_mobile_location_contract -v
& $PY -m unittest Tools.test_public_storefront_contract -v
& $PY -m Platform.Putnam_OS.System.MarketIntelligence.Pricing.test_pricing_engine
& 'C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' --check Docs\app.js
git diff --check
```

Here `$PY` denotes the full Python executable path recorded above. Script-style
desktop tests were invoked directly from their documented application context.

The direct-file pricing invocation failed to resolve package `Platform`.
Running the documented package-module form passed; this is an invocation
constraint, not a product regression.

The Phase 1 architecture snapshot was regenerated against the clean `main`
source. This removed the feature-only `main.py` syntax finding and revealed
the existing `main.py` `sys.path` mutation that the syntax error had prevented
the checker from parsing. The finding count remains 48 and all findings remain
classified as pre-existing; no architecture rule was relaxed.

## Reproduced Pre-Existing Failures

1. `Tools.test_mobile_location_contract`: 13 passed, 1 failed. The stale
   assertion expects a three-argument `captureRoute`; current production code
   includes the already-approved capture-layout argument.
2. `test_listing_optimizer_v1_2.py`: failed its outdated `changes == 7`
   expectation. Current summary reports one cart sweetener and the updated
   pricing behavior documented in earlier audits.
3. `test_inventory_audit_mode_v1_0.py`: OneDrive denied removal of the prior
   `audit_images` test folder. Partially removed tracked fixtures were restored.
4. `Tools/validate_production_startup.py`: its root predicate still requires
   the absent `Docs/AGENTS.md` path.

These failures predate Phase 1.5 and were not modified.

## Files Affected By Validation

Tests created ignored temporary/output/cache files. One import and one legacy
inventory test touched six tracked runtime/fixture files; all six were restored
from `HEAD`, and a post-restore diff confirmed no remaining change.
