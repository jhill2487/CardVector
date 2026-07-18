# CardVector Development Standards

**Status:** Proposed permanent standard
**Applies to:** Human developers, Codex sessions, AI agents, scripts, and contractors

## Mandatory Start Sequence

Before production changes:

1. Read `CardVector_Architecture_Manifest.md`.
2. Read `CardVector_Subsystem_Ownership_Matrix.md`.
3. Read current project status/roadmap/changelog.
4. Run `git status`.
5. Confirm branch and remote state.
6. Search for existing implementations and callers.
7. Identify the canonical owner.
8. Write acceptance and rollback criteria.

Stop if the working tree contains conflicting unrelated work.

## Extend Before Creating

Create a production file only when:

- the architecture manifest names its package/role,
- no existing canonical module owns the exact responsibility,
- extending an existing file would violate single responsibility,
- its public API and dependencies are defined,
- tests will cover it,
- its lifecycle is clear.

An implementation convenience is not sufficient justification.

## Mandatory Pre-File-Creation Checklist

The change record or PR must answer:

1. What responsibility does this file own?
2. Which existing subsystem owns that responsibility?
3. Does an existing module already provide this capability?
4. Why can the existing module not be extended?
5. Is this a new implementation or a compatibility adapter?
6. What imports this file?
7. What tests will cover it?
8. Is its location approved by the architecture manifest?
9. Does this create a second entry point or duplicate implementation?
10. What is its long-term lifecycle?

If any answer is unknown, file creation is blocked pending architecture review.

## Naming

Python:

- packages/modules: lowercase `snake_case`,
- classes: `PascalCase`,
- functions/variables: `snake_case`,
- constants: `UPPER_SNAKE_CASE`,
- private implementation: leading underscore or `internal` package,
- tests: `test_<behavior>.py`.

Forbidden production filename tokens:

- `old`
- `backup`
- `copy`
- `final`
- `new`
- `temp`
- `v2`, `v3`, or other embedded implementation versions

Version belongs in package metadata and Git tags, not filenames.

## Package And Import Rules

- Production imports start with `cardvector`.
- No production `sys.path` mutation.
- No imports from `Archive`, `Tools`, `Tests`, `Business`, `Data`, `Capture`, or `Work_Sessions`.
- No wildcard imports.
- No work at import time.
- No application/domain imports from Presentation.
- No canonical imports from Compatibility.
- Dynamic imports require a decision-log entry.
- Circular imports are architectural defects, not runtime-import opportunities.

## Public API Rules

- Each subsystem exposes an explicit package API.
- UI and other subsystems use only public APIs.
- Public functions use typed inputs/results where practical.
- Dictionary compatibility shapes are adapted at boundaries.
- Backward-incompatible changes require deprecation and migration.
- External file/API contracts are versioned and fixture-tested.

## Business Logic

- Domain logic is pure where practical.
- Money uses `Decimal`, never binary float.
- Time uses timezone-aware timestamps for persisted/cloud events.
- Identifiers are canonical and validated once.
- External evidence includes source and capture time.
- UI text is not a business-rule source.
- Configuration changes business behavior; code should not require business-strategy edits.

## Error Handling

- Domain raises specific domain errors.
- Application maps errors to actionable outcomes.
- Integrations translate vendor/network errors into stable application errors.
- Presentation displays concise safe messages.
- Technical trace belongs in logs.
- Never use broad `except Exception` without logging/translation at a boundary.
- Never silently discard operator data.
- Cancellation is distinct from failure.

## Logging

- Use named structured loggers.
- Include correlation/session/job IDs.
- Log state transitions and external failures.
- Do not log secrets, authorization headers, full sensitive payloads, or user credentials.
- Business audit records are explicit reports with stable schemas.
- Console output explains operator-facing CLI progress.

## Configuration

- No username-specific paths.
- No embedded secrets.
- Defaults are centralized and validated.
- Runtime settings are injected.
- New settings include type, default, owner, source precedence, UI exposure, and migration.
- Config reads/writes are atomic.

## Persistence And Files

- Repositories own persistence.
- UI does not write JSON/CSV/SQL directly.
- Source inputs are never modified.
- Outputs are unique/timestamped by default.
- Schema changes require migrations.
- Runtime data is not committed.
- Tests use temporary directories and sanitized fixtures.

## Versioning

- One application version source.
- Subsystem protocol/schema versions only when independently meaningful.
- Meaningful production changes update changelog/release notes.
- Git tags mark releases/checkpoints.
- No versioned duplicate modules.

## Deprecation

Every deprecation records:

- old interface,
- canonical replacement,
- known callers,
- warning behavior,
- introduced release,
- removal criteria,
- target phase,
- owner,
- tests.

No deprecated interface gains features.

## Archive

- Archive only after caller/reference checks and approval.
- One archive package per commit.
- Include a manifest and rollback instructions.
- Production must not import Archive.
- Do not archive runtime/business data as if it were source.

## Test Requirements

Small change:

- focused unit/contract test,
- compilation/static validation,
- affected smoke test.

Subsystem change:

- unit tests,
- integration/fixture tests,
- compatibility tests,
- full affected workflow smoke test,
- manual validation.

Architecture change:

- all above,
- architecture guardrails,
- both-workstation validation where paths/launchers change,
- explicit approval before merge.

## Documentation

Update:

- subsystem reference for behavior,
- changelog for meaningful production change,
- architecture manifest/matrix/decision log for ownership or dependency change,
- migration/rollback notes for compatibility work.

Cross-link; do not duplicate the same rule in multiple canonical documents.

## Commit Standard

- One responsibility per commit.
- No unrelated formatting or cleanup.
- No generated runtime files.
- Commit message names subsystem and action.
- Every commit must be revertible.
- Cleanup and feature work never share a commit.

## AI Agent Rules

- Inspect before modifying.
- Preserve user changes.
- Never infer that old-looking code is unused.
- Do not create a new app/module when a canonical owner exists.
- Report uncertainty.
- Do not proceed past a migration phase without requested approval.
- State tests run and tests not run.
- Never claim manual validation not actually performed.
