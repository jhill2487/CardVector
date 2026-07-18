# Phase 0 Baseline Test Results

Run date: 2026-07-17

## Summary

- 12 of 13 individually compiled changed/new Python modules passed.
- `main.py` failed compilation at line 650.
- Node syntax validation passed.
- 15 test commands passed.
- 2 test commands failed because of the active `main.py` syntax issue or a
  previously documented stale mobile route assertion.
- 1 startup validator failed because its repository-root predicate references
  governance files that no longer exist at those paths.
- 2 unsafe artifact-writing tests were intentionally not run.
- No test invoked a live marketplace, uploaded a capture, changed inventory,
  or wrote a production database.

## Environment Resolution Attempt

Initial commands using `py` and `node` did not execute:

- `py.exe`: `The file cannot be accessed by the system`
- `node`: command not found in the current PATH

These are environment invocation failures, not application test results.
All executable validations were rerun with the bundled Python and Node paths
recorded in `Phase_0_Baseline_Test_Plan.md`.

## Syntax and Static Validation

| Validation | Result | Duration | Files affected |
| --- | --- | ---: | --- |
| Individual `py_compile` of 13 active modules | 12 pass, 1 fail | 2.25 s total | Ignored `__pycache__` only |
| `main.py` compile | **Fail** | 0.26 s | None beyond ignored bytecode |
| `node --check Docs/app.js` | Pass | 3.93 s | None |
| `git diff --check` | Pass | <1 s | None |
| JSON load of `putnam_os_config.json` | Pass | <1 s | None |
| Desktop import check for paths, capture, inventory, orders, and `putnam_os` | Pass | 0.52 s | Ignored bytecode only |

`main.py` failure:

```text
Platform/Putnam_OS/System/app/main.py:650
SyntaxError: unterminated f-string literal
```

This file is part of the uncommitted eBay active-listing WIP. Phase 0 did not
repair it.

## Pricing and Marketplace Tests

| Command/test | Result | Duration | Notes |
| --- | --- | ---: | --- |
| `test_marketplace_intelligence_v1.py` | Pass | 1.25 s | Local fixtures and temporary reports |
| `test_pricing_engine_consolidation` | **Fail** | 1.10 s | Import blocked by `main.py` syntax error |
| `test_price_vector_fmv_separation` | Pass, 11 tests | 0.91 s | Includes temporary SQLite persistence |
| Putnam pricing adapter script with repository `PYTHONPATH` | Pass | 0.25 s | Direct compatibility smoke test |

The first attempt to run the Putnam pricing file through `unittest` found zero
tests because it is a script-style smoke test. Running the file directly with
the repository on `PYTHONPATH` passed.

## Mobile, Capture, and Contract Tests

| Command/test | Result | Duration | Notes |
| --- | --- | ---: | --- |
| Mobile capture queue | Pass, 25 tests | 2.65 s | Mocks and temporary directories |
| Supabase mobile capture contract | Pass, 19 tests | 0.51 s | Static SQL/JS contract |
| Mobile location contract | **Fail**, 1 of 14 | 0.86 s | Stale exact-source assertion |
| Public storefront contract | Pass, 7 tests | 0.89 s | Static public-site contract |
| Capture Studio v2 | Pass | 0.74 s | Temporary folder |
| Auto Capture v2.1 | Pass | 2.06 s | Temporary folder |
| Mobile capture thumbnail pairs | Pass, 5 tests | 0.98 s | Temporary folder |
| OBS connection manager | Pass | 0.14 s | No live OBS requirement |

Mobile location failure:

```text
Expected exact source text:
captureRoute(state.etbId, state.location, state.captureType)
```

The current implementation includes a capture-layout argument. This matches
the previously identified stale mobile route assertion and is unrelated to
Phase 0.

## Desktop Workflow Tests

| Command/test | Result | Duration | Notes |
| --- | --- | ---: | --- |
| Desktop workflow UI | Pass | 0.39 s | Source assertions |
| eBay policy config | Pass | 0.64 s | In-memory rows, no live eBay |
| Orders v1 | Pass | 0.22 s | Temporary directory |
| Workflow context | Pass, 3 tests | 0.32 s | Temporary directory |

## Startup and Repository Validation

Static inspection confirmed both production VBS launchers target:

```text
Platform\Putnam_OS\System\app\putnam_os.py
```

`putnam_os.py` compiles and imports successfully.

`Tools/validate_production_startup.py` failed before validation because its
root finder requires both `AGENTS.md` and `Docs/AGENTS.md`; `Docs/AGENTS.md`
does not exist. The validator also writes ignored startup logs by design. This
is a pre-existing path/governance mismatch, not a production launcher failure.

No `.db`, `.sqlite`, or `.sqlite3` file was found under `Data/` or `Platform/`
during the read-only database inventory. Runtime databases may live in ignored
or external locations and were not opened.

## Files Affected by Tests

- Ignored Python bytecode/cache files.
- Ignored startup validation log directory may have been touched before the
  root predicate failed; no tracked log or source file changed.
- Temporary files under the Windows temporary directory.

Post-test `git status` showed the same original tracked modifications and
untracked files plus the newly created Phase 0 documents. No original change
was lost.
