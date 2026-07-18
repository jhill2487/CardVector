# CardVector Architecture Guardrails

**Status:** Proposed
**Purpose:** Prevent duplication and layer drift through automated checks

## Enforcement Model

Guardrails have three rollout states:

1. **Observe:** report existing debt without blocking.
2. **Protect baseline:** block new violations while allowlisting existing debt.
3. **Enforce:** remove allowlist entries as migration phases resolve them.

No guardrail should force unrelated cleanup into a feature commit.

## Guardrail Matrix

| Guardrail | Detects | Severity | Commit blocking | Suggested tool | False-positive considerations |
|---|---|---|---|---|---|
| Official entry-point check | More than one production-labeled launcher or package entry | Critical | Yes after Phase 3 | Custom Python AST/file check | Test/tool `__main__` guards are allowed |
| Launcher target check | Multiple production launchers targeting different apps | Critical | Yes after Phase 3 | Custom script parsing BAT/VBS/pyproject | Compatibility redirects may exist if they target the same entry |
| Duplicate application class check | Multiple production `PutnamOS`/desktop roots | High | Protect baseline, then block | AST class scan | Tests and archived code excluded |
| Forbidden filename check | `old`, `backup`, `copy`, `final`, `new`, version suffixes in production source | High | Yes for new files | Custom path regex / pre-commit | Legitimate domain words require explicit allowlist |
| Duplicate filename warning | Same module basename in multiple production packages | Medium | Warning; block only for canonical names | Custom inventory script | `models.py`, `api.py`, `errors.py` are expected per package |
| Unapproved top-level folder check | New root/Platform package absent from manifest | High | Yes | Manifest allowlist script | Generated ignored folders excluded |
| Archive import check | Production imports from `Archive` | Critical | Yes immediately | Ruff rule/custom AST/rg | Documentation strings excluded |
| Runtime-folder import check | Imports from Business/Data/Capture/MobileCapture/Work_Sessions | Critical | Yes immediately | Custom AST | File paths as runtime inputs are not imports |
| Layer dependency check | Domain -> UI/infrastructure/integration, subsystem -> another subsystem infrastructure | Critical | Yes after package migration | `import-linter` or `grimp` contracts | Compatibility phase needs explicit contract exclusions |
| Tkinter below Presentation | `tkinter`, dialogs, widgets in domain/application/subsystems | Critical | Protect baseline then block | AST import check | Presentation package only |
| UI import below Presentation | imports from `cardvector.presentation` outside bootstrap/tests | Critical | Yes | Import-linter | Bootstrap may construct presentation |
| Compatibility reverse dependency | Canonical package importing `cardvector.compatibility` | Critical | Yes | Import-linter | None |
| Production -> Tools/Tests | Runtime source importing maintenance/test code | High | Yes | AST import check | Test-only optional code must use test fixtures |
| `sys.path` mutation check | `sys.path.insert/append`, PYTHONPATH manipulation | High | Block new; enforce after Phase 2 | AST/ruff custom check | Bootstrap must use packaging, not mutation |
| Dynamic import check | `importlib`, `__import__`, module loading by path | High | Warning then approval block | AST check + decision-log allowlist | Approved plugin/optional dependency requires ID |
| Circular dependency check | Package strongly connected components | Critical | Yes after package graph exists | `grimp`, `pydeps`, import-linter | Type-check-only imports handled carefully |
| Hard-coded absolute path check | Drive letters, usernames, fixed OneDrive roots in production source | High | Yes for new; baseline cleanup staged | Semgrep/custom regex | Tests may use temporary/fixture paths; docs can cite evidence |
| Secret scan | Keys, tokens, Authorization values, private URLs | Critical | Yes immediately | Gitleaks/TruffleHog plus public-export scanner | Browser-safe anon key allowlisted explicitly |
| Runtime file tracking check | Logs, caches, DBs, captures, exports, `.bak` in Git | Critical for secrets/data; High otherwise | Yes after data baseline | `git ls-files` pattern check | Sanitized fixtures only under allowlisted test paths |
| Source backup check | Timestamped duplicate source and `.bak` in production | High | Yes for new | Path regex | Active migration backups prohibited; use Git |
| Orphan module check | Production module with no imports, entry registration, or documented public API | Medium | Warning/review | Vulture plus package inventory | Reflection, dynamic plugins, CLI registration |
| Dead code check | Unreferenced functions/classes | Medium | Warning | Vulture/Ruff F401/F841 | UI callbacks and framework registration need allowlist |
| Public API check | Cross-package import from internal modules | High | Yes after APIs defined | Import-linter/custom AST | Tests may inspect internals only in subsystem unit scope |
| New module test check | New production `.py` without corresponding test/waiver | High | Yes | Git diff + manifest script | Pure `__init__`/typing modules may use documented waiver |
| Ownership documentation check | New package/file absent from ownership manifest | High | Yes | Architecture manifest registry | Compatibility files use compatibility registry |
| Migration adapter registry check | Compatibility wrapper without ID/removal condition/test | High | Yes | Header/registry validation | Initial migrations may register before code exists |
| Database migration check | Schema changed without numbered migration | Critical | Yes | Git diff path/schema check | Fixture-only schema changes excluded |
| Public artifact secret/path check | Private paths/secrets in exported website | Critical | Yes | Existing export scanner plus regex | Public URLs/config explicitly allowlisted |
| Encoding/format check | Mojibake, trailing whitespace, invalid UTF-8 | Medium | Yes for changed lines | Ruff/pre-commit/custom text scan | Intentional non-ASCII brand/text is allowed UTF-8 |

## Recommended Toolchain

### Immediate, low-dependency

- `ruff` for imports, unused code, and basic Python quality.
- `python -m compileall` / `py_compile`.
- `git diff --check`.
- custom `Tools/check_architecture.py` for repository-specific path and manifest rules.
- existing public export/secret scan.

### After packaging

- `import-linter` for layer and package contracts.
- `grimp` for import graph and cycle analysis.
- `pytest` or existing `unittest` discovery under one command.
- `vulture` in warning mode for dead-code candidates.
- Gitleaks in CI and local pre-push.

No tool becomes canonical business logic. Architecture checks only inspect structure/contracts.

## CI Stages

### Pull request fast checks

- changed-file architecture checks,
- forbidden paths/names,
- secret scan,
- compilation,
- focused tests,
- `git diff --check`.

### Full main-branch checks

- full import graph,
- all test suites,
- runtime tracking scan,
- public export and secret scan,
- package build/install smoke test,
- official entry import/startup smoke test.

### Release checks

- clean-clone install,
- production launcher,
- both-workstation smoke validation,
- migration state validation,
- public site export/deploy validation when relevant.

## Baseline Allowlist Standard

Known current violations may be allowlisted only with:

- exact path,
- violated rule,
- audit evidence,
- owner,
- target migration phase,
- expiration/review date.

An allowlist entry cannot use a wildcard broad enough to permit new violations.

Initial likely entries:

- current `putnam_os.py` Tkinter/business mixing,
- `main.py` duplicate GUI,
- current `sys.path` mutation,
- existing backup modules,
- stale hard-coded launchers,
- tracked runtime files pending classification,
- current dynamic label generator.

## Blocking Policy

Immediately block:

- secrets,
- imports from Archive/runtime folders,
- new production backup/version filenames,
- new hard-coded usernames,
- new unapproved production entry points,
- new unapproved top-level packages,
- canonical imports from Compatibility.

Protect baseline:

- layer violations,
- Tkinter below Presentation,
- `sys.path` mutation,
- dynamic imports,
- duplicate GUIs,
- tracked runtime debt.

## Guardrail Acceptance Criteria

- checks run locally and in CI,
- output names the rule, file, owner, and remediation,
- known debt is narrowly allowlisted,
- a new duplicate entry point fails,
- a new Archive import fails,
- a new runtime file in Git fails,
- a new module without ownership/test fails,
- public artifact scan remains clean,
- false-positive waiver requires an architecture decision or documented exception.
