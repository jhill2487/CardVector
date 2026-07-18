# Phase 2 Validation Report

**Date:** 2026-07-18
**Baseline:** `c53138e7f9a79a81b3d8ac766f5494089c72c902`
**Scope:** Application-layer orchestration extraction only

## Baseline

- Branch: `main`
- Working tree: clean
- Ahead/behind: 5 ahead, 0 behind
- `putnam_os.py` compilation: pass
- workflow-context tests: 3 pass
- desktop workflow UI tests: 5 pass
- strict architecture checker: 48 baseline findings, 0 new

## Implementation Validation

| Validation | Result |
| --- | --- |
| Application layer, `putnam_os.py`, workflow context, and test compilation | Pass, 0.774 s |
| Application unit/parity tests | Pass, 6 tests |
| Existing workflow-context tests | Pass, 3 tests |
| Existing desktop workflow UI tests | Pass, 5 tests |
| Architecture guardrail unit tests | Pass, 12 tests |
| Architecture checker warning mode | Pass, 48 baseline findings, 0 new |
| Architecture checker strict mode | Pass, 48 baseline findings, 0 new |
| Import and execution-context initialization | Pass |
| Dependency graph validation | Pass; application AST boundary test found no forbidden imports |
| Manifest JSON validation | Pass; Phase 2 and application root are declared |
| Architecture Markdown local links | Pass, 36 links checked |
| Changed-file secret-pattern scan | Pass, 18 files checked, 0 matches |
| Production launcher verification | Pass; target file hash unchanged |
| Protected workflow implementation | Pass; `workflow_context.py` hash unchanged |
| Marketplace Intelligence protected diff | Pass; no changes |
| Capture protected diff | Pass; no changes |
| Inventory protected diff | Pass; no changes |
| Pricing compatibility smoke test | Pass |
| Marketplace Intelligence smoke test | Pass |
| Mobile capture queue | Pass, 25 tests |
| Capture Studio v2 | Pass |
| Auto Capture v2.1 | Pass |
| Mobile thumbnail pairs | Pass, 3 tests |
| OBS connection manager | Pass |
| Orders v1 | Pass |
| eBay policy configuration | Pass |
| `git diff --check` | Pass |

The production launcher SHA-256 remains:

```text
AD5044D8D439CE6B321951E85A335DE86927AAA9453FE05DF0A23C1327006EE7
```

The unchanged legacy workflow implementation SHA-256 remains:

```text
C3AD746B2C4D36477532F0ECDF6D2AF01FE4330D65D46ED770EDE0BE06FD651C
```

## Manual Validation

No GUI was launched and no live operation was performed. Static/source
contracts confirm that UI widget construction, navigation, action labels,
background workers, and launcher target are unchanged. Operator visual approval
is not claimed.

## Known Baseline Failures

Phase 1.5 records four pre-existing legacy failures. None is changed or repaired
by Phase 2. They were not rerun because their failure causes are outside this
phase and one inventory test can touch tracked fixtures.
