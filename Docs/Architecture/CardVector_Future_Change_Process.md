# CardVector Future Change Process

**Status:** Proposed permanent process

## Standard Change Flow

1. Architecture review.
2. Ownership confirmation.
3. Existing implementation search.
4. Written change plan.
5. Tests/fixtures first or characterization.
6. Focused implementation.
7. Automated and manual validation.
8. Documentation update.
9. Architecture guardrail check.
10. Owner approval and merge.

## Step 1 - Architecture Review

Read:

- Architecture Manifest,
- ownership matrix,
- relevant subsystem reference,
- decision log,
- current roadmap/status/changelog.

Determine change class and whether approval is needed before implementation.

## Step 2 - Ownership Confirmation

State:

- canonical package,
- public API affected,
- data owner,
- integration owner,
- presentation impact,
- compatibility impact.

If two packages appear to own it, stop for architecture decision.

## Step 3 - Existing Implementation Search

Search:

- symbols and business terms,
- file names,
- UI callbacks,
- tests/fixtures,
- launchers,
- config keys,
- schemas/migrations,
- Archive for context only.

Record reusable components and duplicate risk.

## Step 4 - Change Plan

Include:

- objective and non-goals,
- exact files,
- interfaces,
- data/schema changes,
- compatibility behavior,
- tests,
- manual validation,
- rollback,
- documentation.

## Step 5 - Tests

For bug fixes:

- reproduce failure first.

For extraction:

- characterize current behavior first.

For new behavior:

- define acceptance fixtures/contract before implementation where practical.

## Step 6 - Implementation

- extend canonical owner,
- keep diff focused,
- preserve unrelated work,
- avoid cleanup,
- add adapters only when registered,
- do not change external schemas accidentally.

## Step 7 - Validation

Follow `CardVector_Validation_and_Rollback_Standards.md`.

Report tests actually run and manual steps not performed.

## Step 8 - Documentation

Update:

- changelog,
- subsystem reference,
- config/schema docs,
- architecture documents when ownership/dependencies change,
- compatibility registry when adapters change.

## Step 9 - Guardrails

Run:

- architecture checks,
- secret scan,
- package/import checks,
- focused/full tests as required,
- `git diff --check`.

## Step 10 - Approval And Merge

- review diff scope,
- review validation evidence,
- confirm rollback,
- obtain owner approval,
- merge/push according to Git policy,
- verify clean repository and deployment where applicable.

## Change Classes

### Small change

Definition:

- one canonical module,
- no public contract/schema/path/ownership change,
- low blast radius.

Examples:

- UI text correction,
- isolated bug fix,
- report formatting preserving schema.

Approval:

- normal change approval.

Validation:

- focused test and affected smoke test.

### Subsystem change

Definition:

- multiple modules within one owner,
- public API or persisted behavior may change,
- no ownership/layer change.

Examples:

- Capture pairing enhancement,
- Inventory conversion behavior,
- new Price Vector rule.

Approval:

- subsystem plan before implementation.

Validation:

- full subsystem suite, compatibility, manual workflow.

### Architecture change

Definition:

- ownership, dependency direction, package boundaries, entry point, runtime root, or shared service changes.

Approval:

- explicit owner approval before implementation and before proceeding to next phase.

Requirements:

- decision-log entry,
- migration/rollback plan,
- architecture tests,
- broad validation.

### New integration

Definition:

- new external API/service/protocol or new credentials.

Approval:

- explicit owner approval and security/data review.

Requirements:

- port/adapter design,
- secret/config plan,
- failure/retry/rate-limit behavior,
- fixtures/fakes,
- no vendor logic in domain.

### New entry point

Definition:

- any new production desktop, CLI, service, daemon, or web startup surface.

Approval:

- explicit architecture decision.

Default:

- rejected if application services can be reached through an existing approved surface.

### New top-level package

Definition:

- new package directly under `cardvector` or root/Platform.

Approval:

- explicit architecture decision and manifest update.

Default:

- extend an existing subsystem.

## Emergency Fix Process

Production-impacting emergency fixes may shorten planning, but must:

- preserve a clean checkpoint,
- target the canonical/current production path,
- include reproduction and focused test,
- avoid architecture cleanup,
- document debt within one business day,
- receive follow-up review.

Emergency status does not permit secrets, data deletion, or unreviewed schema migration.

## Definition Of Done

- correct owner changed,
- no duplicate implementation,
- tests and manual validation complete,
- errors/logging/config follow standards,
- docs current,
- guardrails pass,
- rollback available,
- repository scope clean,
- owner approval recorded.
