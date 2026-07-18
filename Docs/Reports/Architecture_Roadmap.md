# CardVector Architecture Roadmap

**Audit date:** 2026-07-17
**Objective:** Move toward one entry point and one owner per responsibility without interrupting the production card-selling workflow.

## Migration Rules

1. Business operations take priority over architecture work.
2. Never mix cleanup and feature work in one commit.
3. Every package is incremental and reversible.
4. Preserve public interfaces while internal callers migrate.
5. Add characterization tests before moving business logic.
6. Archive before deletion.
7. Do not move runtime/business data with source code.
8. Validate from both home and work PCs when paths or launchers change.
9. Keep CardUploader recognition and eBay publication outside CardVector ownership.
10. Never place production imports on Archive paths.

## Phase 0 - Stabilize The Baseline

### Purpose

Create a trustworthy starting point before architecture work.

### Actions

- Review and commit or deliberately stash the current Price Vector/FMVs/pricing persistence work.
- Resolve the untracked eBay patch script and `.bak` files without losing valid changes.
- Separate operator business data from source commits.
- Record the exact production launcher and current workflow.
- Run the current automated suite and document known failures.
- Create a baseline tag or checkpoint commit.

### Validation

- Working tree clean.
- Local `main` equals `origin/main`.
- Production launcher starts.
- Capture -> CardUploader -> pricing -> eBay export smoke test passes.
- Inventory registry and orders smoke tests pass.

### Rollback

Return to the baseline commit.

## Phase 1 - Architecture Manifest

### Purpose

Turn the audit recommendations into approved ownership contracts.

### Actions

- Approve `Module_Ownership.md`.
- Decide whether standalone Marketplace Intelligence remains a supported app.
- Decide the disposition criteria for `main.py`.
- Define source/config/runtime/business-data categories.
- Repair root governance links.
- Create a short current architecture manifest in Docs.

### Do Not Do

- No folder moves.
- No import rewrites.
- No legacy deletion.

### Validation

- Operator and developer can identify the owner for every major responsibility.
- Governance startup order points to existing files.

## Phase 2 - Entry Point Consolidation

### Purpose

Create one official production bootstrap without changing application behavior.

### Actions

- Add a minimal `Platform/main.py`.
- Have it initialize paths/config and invoke the existing production application.
- Redirect only `Run CardVector OS Production.vbs`.
- Retain the old launcher temporarily as rollback.
- Add launcher/import smoke tests independent of current working directory.

### Validation

- New launcher starts on both workstations.
- Existing direct launch remains functional during shadow validation.
- Startup logs and clean shutdown work.

### Rollback

Point the production VBS back to `putnam_os.py`.

## Phase 3 - Shared Infrastructure

### Purpose

Remove repeated environmental behavior before moving business subsystems.

### Package 3A: Paths

- Promote `putnam_paths.py` as the only root/path resolver.
- Migrate one subsystem at a time.
- Keep compatibility constants during transition.

### Package 3B: Configuration

- Separate defaults, operator settings, workstation settings, runtime state, and secrets.
- Add schema/validation and atomic writes.

### Package 3C: Logging

- Introduce named subsystem loggers.
- Preserve explicit business audit CSVs as reports.
- Sanitize secrets.

### Package 3D: Common file primitives

- Consolidate only semantics-identical CSV/JSON/filename/money helpers.

### Validation

- Tests run from repository root and another working directory.
- Both workstations resolve the same repository and runtime roots.
- No secrets appear in logs.

## Phase 4 - Marketplace And Price Vector Consolidation

### Purpose

Complete one canonical pricing and market-evidence implementation.

### Actions

- Finish delegation from Putnam OS compatibility interfaces to Marketplace Intelligence.
- Preserve FMV, recommendation, and final price as separate values.
- Move remaining comp/evidence normalization from UI only after fixture parity tests.
- Identify and retire independent Listing Optimizer formulas.
- Decide whether System MarketIntelligence Models/Identity/Inspector are adapters or archive candidates.

### Do Not Do

- No live provider expansion merely for consolidation.
- No recognition work.
- No pricing-strategy redesign.

### Validation

- Representative outputs remain unchanged.
- Putnam OS and standalone MI use the same engine.
- No pricing formulas remain in UI.
- eBay CSV structure remains compatible.

## Phase 5 - Putnam OS Application Boundary

### Purpose

Separate workflow orchestration from Tkinter without redesigning the UI.

### Actions

- Promote `workflow_context.py` into the application layer.
- Move pending-work aggregation, handoff state, and actionable alerts behind services.
- Move file dialogs/status presentation only after services return stable results.
- Keep Tkinter callbacks as thin adapters.
- Determine and retire the second GUI path only after caller migration.

### Validation

- Home/Capture/Processing/Marketplace/Orders/Settings behavior remains intact.
- Background tasks do not block the UI.
- Exact capture/export folder associations survive restart.

## Phase 6 - Subsystem Consolidation

Perform as separate commits and releases.

### 6A Capture

- Canonicalize Capture Studio, OBS manager, mobile queue, thumbnails, and manifests.
- Preserve manual/auto/mobile modes and dated routing.
- Archive legacy standalone capture only after operator confirmation.

### 6B Inventory

- Canonicalize location identity, occupancy, conversion sessions, synchronization, QR payloads, and reconciliation.
- Explicitly adapt or retire legacy Seller Tools location rules.
- Preserve offline registry behavior.

### 6C Orders

- Move normalization/grouping/pick slips behind Orders services.
- Keep UI and manual printing behavior unchanged.

### Validation

- Dedicated subsystem tests.
- End-to-end production smoke test after each package.
- No cross-subsystem import cycles.

## Phase 7 - Runtime And Data Policy

### Purpose

Keep Git as source history without risking business data.

### Actions

- Inventory every tracked runtime/config file.
- Create versioned sample/default files.
- Back up operational state.
- Move runtime authority to Data/Capture/MobileCapture or approved external services.
- Untrack generated state only after startup/recovery tests.
- Define cache and log retention.

### Validation

- Fresh clone starts with defaults.
- Existing workstation preserves inventory/location/session state.
- Home/work PC synchronization does not overwrite operator state.

## Phase 8 - Archive And Repository Cleanup

### Purpose

Remove ambiguity after canonical replacements are proven.

### Cleanup packages

1. Broken hard-coded launchers.
2. Tracked source backup files.
3. Current patch `.bak` artifacts.
4. Legacy second launcher aliases.
5. Legacy capture application.
6. Superseded pricing/optimizer modules.
7. Stale documentation and root references.
8. Empty/unknown folders after user decision.

Each package must include:

- manifest,
- reference search,
- tests,
- launcher validation,
- rollback instructions,
- one commit.

## Phase 9 - Final Verification

### Required checks

- One official production entry point.
- One canonical owner per subsystem.
- No production imports from Archive or Tools.
- No independent pricing formulas outside Marketplace Intelligence.
- No UI-owned inventory/capture/order business rules.
- No hard-coded usernames.
- No tracked generated runtime state without explicit justification.
- New-developer setup works from current Docs.
- Full production workflow validated.

## Suggested Commit Strategy

```text
checkpoint: pre-architecture baseline
docs: establish canonical architecture manifest
architecture: add production bootstrap
shared: consolidate path resolution
shared: separate configuration and runtime state
shared: standardize application logging
pricing: complete marketplace intelligence delegation
app: separate workflow orchestration from tkinter
capture: consolidate capture services
inventory: consolidate location and conversion services
orders: consolidate fulfillment services
data: establish runtime retention policy
archive: retire validated legacy implementations
docs: publish consolidated architecture baseline
```

## Success Criteria

A new developer can answer these questions in under five minutes:

1. What launches CardVector?
2. Where does pricing live?
3. Where does capture live?
4. Where does inventory live?
5. Which data is source-controlled?
6. Which files are runtime/operator state?
7. How does CardUploader fit?
8. How does eBay fit?
9. Which code is historical only?
10. How can a change be rolled back?

The migration is complete only when those answers match both documentation and runtime behavior.
