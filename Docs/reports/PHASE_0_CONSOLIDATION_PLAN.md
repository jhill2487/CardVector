# CardVector Phase 0 Consolidation Plan

Generated: 2026-07-06

Inputs:

- `Docs/Reports/PHASE_0_PROJECT_AUDIT.md`
- `Docs/Reports/PHASE_0_CANONICAL_RESPONSIBILITIES.md`

Scope: planning only. This document does not authorize cleanup and does not
move, rename, delete, refactor, or change application behavior.

## 1. Executive Summary

CardVector has a clear target architecture, but the repository still contains
root-level audit artifacts, legacy launchers, backup source files beside active
source, duplicate/overlapping platform folders, generated runtime outputs, and
older path systems.

The consolidation strategy should be incremental, reversible, and validation
driven. The validated production workflow must remain stable:

```text
Capture -> CardUploader -> Pricing -> eBay CSV -> eBay Upload
```

Cleanup should happen as small packages. Each package should be backed up,
committed independently, validated manually, and rolled back immediately if it
affects daily business operations.

The safest first cleanup is root-level audit artifacts. The riskiest cleanup is
anything near active CardVector OS source, pricing, capture/OBS, inventory
registries, runtime data, or historical business records.

## 2. Cleanup Principles

1. Preserve the validated production workflow.
2. Prefer archiving over deleting.
3. Make every cleanup package small enough to review in one sitting.
4. Make every cleanup package reversible.
5. Confirm canonical ownership before moving or retiring non-canonical files.
6. Never treat runtime business data as disposable source clutter.
7. Never clean up `putnam_os.py`, pricing, capture, inventory, or path logic
   without a targeted validation checklist.
8. Do not remove duplicate-looking files until import/launcher/reference checks
   confirm they are not active.
9. Do not consolidate documentation until the concept owner is explicit.
10. Document every cleanup package in `Docs/CHANGELOG.md` or a dedicated cleanup
    report after execution.

## 3. Pre-Cleanup Requirements

### Backup / Snapshot Required

Before any cleanup package executes:

- Create a full repository snapshot or archive.
- Capture a directory listing of the root and affected package area.
- Preserve all generated data, business reports, capture images, logs, exports,
  databases, and historical CSVs.
- Record the exact cleanup package name, timestamp, and rollback location.

Recommended backup location:

```text
Archive/Consolidation_Backups/<timestamp>_<package_name>/
```

### GitHub Pre-Cleanup Baseline Commit Recommended

Before cleanup begins, create a baseline commit in GitHub or the active version
control system:

```text
pre-cleanup-baseline-cardvector-phase-0
```

If Git is unavailable in the working folder, create a full filesystem backup
and do not proceed with cleanup until version control status is understood.

### Manual Validation Checkpoints

Run these after every cleanup package that touches anything outside reports:

- CardVector OS launches from the production launcher.
- Capture tab opens.
- Existing capture session folder can be opened.
- Manual Capture still works if OBS is available.
- Import CardUploader CSV still opens a file picker.
- Pricing workflow still loads/analyzes a known sample CSV.
- eBay CSV export still preserves required columns.
- Inventory tab opens.
- ETB label generation either works or shows a friendly dependency/error
  message.
- Orders tab opens.
- Marketplace Intelligence launches if its package was affected.

### Do-Not-Touch List

Do not touch these in early cleanup packages:

- `Platform/Putnam_OS/System/app/putnam_os.py`
- `Platform/Putnam_OS/System/app/capture_studio.py`
- `Platform/Putnam_OS/System/app/obs_connection_manager.py`
- `Platform/Putnam_OS/System/app/inventory_locations.py`
- `Platform/Putnam_OS/System/app/orders_fulfillment.py`
- `Platform/Putnam_OS/System/tools/generate_etb_qr_labels.py`
- `Platform/putnam_paths.py`
- `Platform/Marketplace_Intelligence/marketplace_intelligence/`
- `Platform/Putnam_OS/System/data/`
- `Platform/Putnam_OS/System/logs/`
- `Platform/Putnam_OS/System/cache/`
- `Platform/Putnam_OS/Completed Jobs/`
- `Platform/Putnam_OS/Incoming Files/`
- `Capture/`
- `Business/`
- `Data/`
- `Archive/`
- `Platform/Putnam_OS/System_Archive/`
- all databases
- all capture images
- all business CSVs
- all export history logs
- all pricing/export reports used for business review

## 4. Cleanup Package Overview

| Package | Name | Risk | Purpose |
|---:|---|---:|---|
| 01 | Root audit artifacts | LOW | Move one-off root audit scripts/reports into an approved archive/report area. |
| 02 | Root media/runtime artifacts | MEDIUM | Decide where large root media/runtime files belong. |
| 03 | Duplicate launchers | MEDIUM | Confirm one production launcher and classify aliases. |
| 04 | Duplicate documentation | MEDIUM | Reduce concept overlap after governance roles are confirmed. |
| 05 | Backup Python files near active source | HIGH | Move confirmed obsolete backups away from active app source. |
| 06 | Duplicate platform folders | HIGH | Resolve root/canonical folder overlaps only after owner decisions. |
| 07 | Hard-coded path references | HIGH | Replace active hard-coded paths with canonical path manager usage. |
| 08 | Runtime/cache retention policy | MEDIUM | Define retention rules before purging generated outputs. |
| 09 | Documentation consolidation | MEDIUM | Establish one document owner per concept. |
| 10 | Legacy pricing/capture owner confirmation | HIGH | Decide active vs legacy implementations before future refactors. |

## 5. Package Details

### Package 01 - Root Audit Artifacts

Purpose:

Clean root-level one-off audit scripts and generated text reports after user
review so the root folder reflects active business and platform structure.

Files/folders affected:

- `cardvector_workspace_auditor.py`
- `cardvector_production_path_auditor.py`
- `cardvector_production_path_auditor_v2.py`
- `cardvector_production_module_auditor.py`
- `cardvector_production_reference_auditor.py`
- `cardvector_root_cleanup_auditor.py`
- `cardvector_folder_inspector.py`
- `cardvector_batch_folder_inspector.py`
- `cardvector_config_reference_finder.py`
- matching root `CARDVECTOR_*_REPORT.txt`
- `FOLDER_INSPECTION_Putnam_OS.txt`

Risk level: LOW

Dependencies:

- User confirms these are superseded by `Docs/Reports/PHASE_0_*` reports.
- Confirm no launcher, scheduled task, or documentation references these scripts
  as active tools.

Exact recommended actions:

1. Create a backup package under `Archive/Consolidation_Backups/`.
2. Move the root audit scripts and reports into an approved archive location.
3. Prefer an archive subfolder such as
   `Archive/Phase_0_Audit_Artifacts_<timestamp>/`.
4. Add a short cleanup note in the cleanup report.

What NOT to touch:

- `Docs/Reports/PHASE_0_PROJECT_AUDIT.md`
- `Docs/Reports/PHASE_0_CANONICAL_RESPONSIBILITIES.md`
- `Docs/Reports/PHASE_0_CONSOLIDATION_PLAN.md`
- `Tools/validate_production_startup.py`
- any application code.

Validation steps:

- Confirm root no longer shows the archived audit artifacts.
- Confirm `Docs/Reports/` still contains Phase 0 reports.
- Launch CardVector OS.

Rollback strategy:

- Move archived files back to root from the package backup.

Can Codex safely execute later:

Yes, after user approval and a pre-cleanup baseline.

### Package 02 - Root Media / Runtime Artifacts

Purpose:

Classify and relocate root-level media/runtime files that are not source code.

Files/folders affected:

- `ScreenRecording_06-30-2026 14-42-57_1.MP4`
- any future root-level runtime media found during package execution.

Risk level: MEDIUM

Dependencies:

- User confirms whether the screen recording is business evidence, development
  evidence, or disposable.

Exact recommended actions:

1. Do not delete.
2. If retained, move to an approved owner such as `Data/Media/`,
   `Work_Sessions/`, or `Archive/Media/`.
3. Record original path and destination in a cleanup report.

What NOT to touch:

- `Capture/`
- `Data/Media/` contents
- `Work_Sessions/` recordings
- business images or capture sessions.

Validation steps:

- Confirm file exists at its new destination.
- Confirm no application workflow references the old root media path.

Rollback strategy:

- Move the file back to root from the backup/destination.

Can Codex safely execute later:

Yes, only after user chooses the destination owner.

### Package 03 - Duplicate Launchers

Purpose:

Confirm the official CardVector OS launcher and classify older launchers as
aliases or archive candidates.

Files/folders affected:

- `Platform/Putnam_OS/Run CardVector OS Production.vbs`
- `Platform/Putnam_OS/Run Putnam OS Production.vbs`
- `Platform/Putnam_OS/Run Putnam OS.bat`
- Marketplace launcher files only if separately approved:
  `Platform/Marketplace_Intelligence/run_marketplace_intelligence.py`
  and `Run Marketplace Intelligence.bat`.

Risk level: MEDIUM

Dependencies:

- User confirms whether the Putnam-named launchers remain useful aliases.
- Verify shortcuts, desktop pins, or user habits do not rely on older launchers.

Exact recommended actions:

1. Confirm `Run CardVector OS Production.vbs` launches production OS.
2. Decide whether `Run Putnam OS Production.vbs` remains a compatibility alias.
3. Decide whether `Run Putnam OS.bat` is a developer/legacy launcher.
4. Archive only launchers confirmed unused.
5. Update documentation paths only after launcher decision is made.

What NOT to touch:

- `putnam_os.py`
- VBS internals unless a later task explicitly updates launcher behavior.
- Marketplace Intelligence launchers unless package scope is expanded.

Validation steps:

- Launch CardVector OS from the official launcher.
- If aliases remain, launch from each alias and confirm same app opens.
- Confirm startup logs still write.

Rollback strategy:

- Restore launcher files from backup.
- Revert documentation path changes.

Can Codex safely execute later:

Partially. Codex can inventory and archive confirmed-unused launchers, but user
must decide which launchers are still personally used.

### Package 04 - Duplicate Documentation

Purpose:

Clarify which document owns each concept before reducing documentation overlap.

Files/folders affected:

- `Docs/GOVERNANCE.md`
- `Docs/GOVERNANCE_OVERVIEW.md`
- `Docs/PROJECT_MANUAL.md`
- `Docs/PROJECT_INDEX.md`
- `Docs/PUTNAM_MANIFESTO.md`
- `Docs/PATH_MANAGER.md`
- `Docs/*_REPORT.md`
- app-specific README/CHANGELOG files under `Platform/Putnam_OS/` and
  `Platform/Marketplace_Intelligence/`.

Risk level: MEDIUM

Dependencies:

- Governance hierarchy remains authoritative.
- User confirms whether docs should be consolidated, archived, or preserved as
  historical context.

Exact recommended actions:

1. Create a documentation concept map.
2. Assign one owner per concept:
   - governance,
   - platform vision,
   - current status,
   - roadmap,
   - changelog,
   - path manager,
   - app-specific usage,
   - historical reports.
3. Add cross-links instead of copying large repeated sections.
4. Archive only docs confirmed historical.

What NOT to touch:

- `AGENTS.md`
- `Docs/AGENTS.md`
- `Docs/Putnam_Standards/PUTNAM_PRINCIPLES.md`
- `Docs/Putnam_Standards/PUTNAM_PLATFORM_STANDARDS.md`
- `PLATFORM_VISION.md`
- `Docs/PROJECT_STATUS.md`
- `Docs/ROADMAP.md`
- `Docs/CHANGELOG.md`
- `Docs/README.md`

Validation steps:

- New Codex session can still find standards from root `AGENTS.md`.
- Documentation links resolve.
- Governance hierarchy remains intact.

Rollback strategy:

- Restore documentation from backup.
- Revert cross-link changes.

Can Codex safely execute later:

Yes, but only as a documentation-only package with user approval.

### Package 05 - Backup Python Files Near Active Source

Purpose:

Move confirmed obsolete backup Python files away from active app source so
future sessions do not confuse them with production modules.

Files/folders affected:

- `Platform/Putnam_OS/System/app/putnam_os_capture_v1_backup_20260629_212812.py`
- `Platform/Putnam_OS/System/app/putnam_os_comp_engine_v1_1_backup_20260629.py`
- `Platform/Putnam_OS/System/app/putnam_os_comp_ui_v1_2_0_backup_20260629.py`
- `Platform/Putnam_OS/System/app/putnam_os_import_v1_backup_20260629_222132.py`
- `Platform/Putnam_OS/System/app/putnam_os_inventory_location_foundation_backup_20260629_231122.py`
- `Platform/Putnam_OS/System/app/putnam_os_listing_workflow_backup_20260629_214810.py`
- `Platform/Putnam_OS/System/app/putnam_os_orders_v1_backup_20260629_220044.py`

Risk level: HIGH

Dependencies:

- Run reference searches to confirm no imports/launchers use these files.
- Confirm current `putnam_os.py` contains the accepted replacement behavior.
- Confirm backups are already represented in `System_Archive` or create a
  package backup.

Exact recommended actions:

1. Do not delete.
2. Compare each backup filename purpose against current `putnam_os.py`.
3. Create a manifest listing each backup file and why it is obsolete.
4. Move confirmed backups into a timestamped archive folder.
5. Leave an archive manifest, not a replacement module.

What NOT to touch:

- `Platform/Putnam_OS/System/app/putnam_os.py`
- `capture_studio.py`
- `obs_connection_manager.py`
- `inventory_locations.py`
- `orders_fulfillment.py`
- tests, unless a later test cleanup package is approved.

Validation steps:

- Run `py -m compileall Platform`.
- Run `py -m py_compile Platform/Putnam_OS/System/app/putnam_os.py`.
- Launch CardVector OS.
- Smoke test Capture, Import, Pricing, Inventory, and Orders tabs.

Rollback strategy:

- Move archived backup files back into `System/app/`.
- Restore from package backup if needed.

Can Codex safely execute later:

Yes, but only after a baseline commit and explicit approval because risk is
high.

### Package 06 - Duplicate Platform Folders

Purpose:

Resolve root/canonical folder overlaps without breaking legacy references.

Files/folders affected:

- root `Putnam_Platform/`
- `Platform/Putnam_Platform/`
- root `Putnam_Seller_Tools/`
- `Platform/Putnam_OS/Putnam_Seller_Tools/`
- `Collectr/`
- `Shared/`
- `Putnam_Content/`

Risk level: HIGH

Dependencies:

- User decisions about folder ownership.
- Reference scan across scripts, docs, launchers, and generated reports.
- Confirm whether root `Putnam_Seller_Tools/` business intelligence and branding
  are active.
- Confirm `Collectr/` purpose.

Exact recommended actions:

1. Do not move all folders at once.
2. Produce one owner decision per folder.
3. For each folder, classify as:
   - canonical,
   - legacy reference,
   - business operations,
   - generated output,
   - archive candidate,
   - unknown.
4. Move only one confirmed folder per cleanup commit.
5. Update docs only after each confirmed move.

What NOT to touch:

- unknown folders until the user identifies them.
- `Business/`, `Data/`, `Capture/`, or `Archive/`.
- active app imports.

Validation steps:

- Run path reference search before and after each move.
- Launch CardVector OS.
- Launch Marketplace Intelligence if related folders are touched.
- Confirm seller audit/SKU repair still run if seller tools are touched.

Rollback strategy:

- Move the folder back to its original path.
- Restore docs from backup.

Can Codex safely execute later:

Only after manual user decisions. This is not safe as an automatic cleanup.

### Package 07 - Hard-Coded Path References

Purpose:

Replace active hard-coded user paths and obsolete root assumptions with
canonical path resolution.

Files/folders affected:

- `Business/Inventory/Pricing_Revisions/Run Market Validation Prototype.bat`
- `Business/Inventory/Pricing_Revisions/Run Bulk Price Engine.bat`
- active legacy tools that directly require `USERENVIRONMENT`
- documentation examples that point to old root folders.

Risk level: HIGH

Dependencies:

- Decide whether affected `.bat` files are active.
- Confirm whether legacy engines remain active or become reference-only.
- Prefer `Platform/putnam_paths.py` for Python code.

Exact recommended actions:

1. Inventory hard-coded paths.
2. Classify each as active code, launcher, documentation, historical report, or
   generated data.
3. Change only active code/launchers in a later implementation task.
4. Do not rewrite historical logs/reports.

What NOT to touch:

- historical CSVs,
- logs,
- old reports,
- archived checkpoints,
- runtime records that intentionally preserve historical absolute paths.

Validation steps:

- Run launcher/tool smoke tests for each changed path.
- Confirm output still lands in the expected business/data folder.
- Confirm no source CSVs are modified.

Rollback strategy:

- Restore original path files from backup.

Can Codex safely execute later:

Partially. Codex can safely fix active path files after user confirms those
tools are active. Historical data should remain untouched.

### Package 08 - Runtime / Cache Retention Policy

Purpose:

Create a formal policy before removing generated data, reports, caches, or
test outputs.

Files/folders affected:

- `Capture/`
- `Data/Exports/`
- `Data/Imports/`
- `Data/Logs/`
- `Data/Processed/`
- `Platform/Marketplace_Intelligence/reports/`
- `Platform/Marketplace_Intelligence/backups/`
- `Platform/Putnam_OS/Completed Jobs/`
- `Platform/Putnam_OS/Incoming Files/`
- `Platform/Putnam_OS/System/cache/`
- `Platform/Putnam_OS/System/logs/`
- `Platform/Putnam_OS/System/data/`
- `Platform/Putnam_OS/System/app/test_artifacts/`
- `__pycache__/`

Risk level: MEDIUM

Dependencies:

- User retention preferences.
- Identify business-critical vs disposable runtime data.

Exact recommended actions:

1. Create a retention policy document.
2. Categorize runtime data:
   - permanent business record,
   - temporary processing output,
   - cache,
   - test artifact,
   - backup/checkpoint,
   - media evidence.
3. Define retention windows.
4. Only after policy approval, create cleanup tasks.

What NOT to touch:

- capture images,
- acquisition records,
- inventory audit history,
- export history,
- completed eBay CSV jobs,
- business reports used for decisions.

Validation steps:

- Documentation-only policy requires no app smoke test.
- Future cleanup based on policy must validate app workflows.

Rollback strategy:

- Documentation rollback only for the policy stage.
- Future cleanup must archive before deletion.

Can Codex safely execute later:

Yes for creating the policy. Cleanup execution requires separate approval.

### Package 09 - Documentation Consolidation

Purpose:

Enforce one canonical document per concept without losing historical decisions.

Files/folders affected:

- `Docs/`
- `Docs/Putnam_Standards/`
- `Docs/Reports/`
- app-level README/CHANGELOG files.

Risk level: MEDIUM

Dependencies:

- Complete Package 04 concept map first.
- User confirms which docs are current vs historical.

Exact recommended actions:

1. Keep root `AGENTS.md` as the entry stub.
2. Keep governance hierarchy intact.
3. Convert overlapping docs into links and summaries.
4. Move old reports into `Docs/Reports/Archive/` only if approved.
5. Keep app-specific README/CHANGELOG files with their apps.

What NOT to touch:

- top-level governance standards,
- platform vision,
- current project status,
- current roadmap,
- current changelog.

Validation steps:

- Start from root `AGENTS.md` and confirm a new session can locate all core
  governance docs.
- Confirm no broken Markdown links in updated docs.

Rollback strategy:

- Restore docs from package backup.

Can Codex safely execute later:

Yes, after the user approves the concept map.

### Package 10 - Legacy Pricing / Capture Owner Confirmation

Purpose:

Confirm which implementations are production, shadow mode, experimental, legacy
reference, or deferred before future refactoring.

Files/folders affected:

- `Platform/Putnam_OS/System/app/putnam_os.py`
- `Platform/Marketplace_Intelligence/marketplace_intelligence/`
- `Platform/Putnam_OS/System/app/bulk_price_engine.py`
- `Platform/Putnam_Platform/engines/Bulk_Price_Engine/`
- `Platform/Putnam_Platform/Decision_Engine/`
- `Platform/Putnam_Platform/engines/Market_Intelligence/`
- `Platform/Putnam_Platform/capture/Putnam_Capture.py`
- `Platform/Putnam_Platform/capture/obs_capture_autocrop.py`

Risk level: HIGH

Dependencies:

- User confirms CardVector product ownership:
  - Capture Studio captures.
  - CardUploader recognizes.
  - Marketplace Intelligence/Pricing Engine recommends prices.
  - CardVector OS orchestrates.
- Test coverage or manual smoke tests exist for active workflows.

Exact recommended actions:

1. Do not move or edit code.
2. Add lifecycle labels in documentation only:
   - Production,
   - Shadow Mode,
   - Experimental,
   - Legacy Reference,
   - Deferred.
3. Decide whether old pricing/capture tools remain fallback tools.
4. Only after labels are approved, plan refactors or archives as separate
   implementation tasks.

What NOT to touch:

- pricing calculations,
- eBay export logic,
- OBS/capture implementation,
- CardUploader import behavior,
- inventory data.

Validation steps:

- Documentation review only at this stage.
- Future refactor packages must run full smoke tests.

Rollback strategy:

- Revert documentation labels.

Can Codex safely execute later:

Yes for documentation labeling. No for code movement/refactor without a new
approved task.

## 6. Recommended Execution Order

1. Create pre-cleanup baseline commit or full filesystem snapshot.
2. Execute Package 01: Root audit artifacts.
3. Execute Package 02: Root media/runtime artifacts, only after destination
   decision.
4. Execute Package 03: Duplicate launchers.
5. Execute Package 04: Duplicate documentation concept map.
6. Execute Package 08: Runtime/cache retention policy.
7. Execute Package 10: Legacy pricing/capture owner confirmation.
8. Execute Package 05: Backup Python files near active source.
9. Execute Package 07: Hard-coded path references.
10. Execute Package 06: Duplicate platform folders.
11. Execute Package 09: Documentation consolidation.
12. Create consolidated baseline commit after all approved packages pass
    validation.

Rationale:

- Start with low-risk clutter.
- Do not touch source-adjacent backups until canonical owners are confirmed.
- Do not move duplicate platform folders until references and user decisions are
  settled.
- Do not consolidate docs until package outcomes are documented.

## 7. Manual Decisions Required Before Cleanup

1. Is `Run CardVector OS Production.vbs` the only official CardVector OS
   launcher?
2. Should Putnam-named launchers remain compatibility aliases?
3. Is `Platform/Putnam_OS/System/app/main.py` legacy?
4. Is root `Putnam_Platform/` still active?
5. Is root `Putnam_Seller_Tools/` active for business intelligence/branding?
6. What is `Collectr/`, and should it remain at root?
7. Should `Putnam_Content/` stay root-level or move under `Business/Content/`
   later?
8. Should `Shared/` remain root-level, move under `Tools/Templates/`, or stay
   untouched?
9. Are ETB container locations and game/batch locations intentionally separate
   registries?
10. Should Marketplace Intelligence become the only reusable pricing
    recommendation engine?
11. Should legacy capture CLI remain as a fallback tool?
12. How long should capture images, completed jobs, logs, reports, caches, and
    smoke-test outputs be retained?

## 8. Items That Must Remain Deferred

Defer these until after production validation and explicit approval:

- Any edits to `putnam_os.py`.
- Any pricing engine consolidation.
- Any capture/OBS refactor.
- Any inventory registry merge.
- Any database or schema migration.
- Any deletion of business data, logs, capture images, reports, or exports.
- Any move of `Capture/`, `Business/`, `Data/`, or `Archive/`.
- Any cleanup of `System_Archive/`.
- Any automated cleanup script.
- Any replacement module creation.
- Any import path change.
- Any folder move involving unknown folders like `Collectr/`.

## 9. Suggested Commit Strategy

Recommended commit sequence:

```text
pre-cleanup-baseline-cardvector-phase-0
cleanup-package-01-root-audit-artifacts
cleanup-package-02-root-media-runtime-artifacts
cleanup-package-03-launcher-consolidation
cleanup-package-04-documentation-concept-map
cleanup-package-08-runtime-retention-policy
cleanup-package-10-legacy-owner-labels
cleanup-package-05-source-adjacent-backup-archive
cleanup-package-07-path-reference-fixes
cleanup-package-06-duplicate-folder-consolidation
cleanup-package-09-documentation-consolidation
consolidated-baseline-cardvector-phase-0
```

Rules:

- One cleanup package per commit.
- Never mix code cleanup with documentation consolidation.
- Never mix runtime cleanup with application source cleanup.
- Commit only after validation passes.
- If validation fails, rollback before continuing.

## 10. Questions for User Review

1. Approve Package 01 as the first executable cleanup package?
2. Should Package 01 archive root audit artifacts under `Archive/` or
   `Docs/Reports/Archive/`?
3. Where should the root MP4 screen recording live: `Data/Media/`,
   `Work_Sessions/`, or `Archive/Media/`?
4. Should the old Putnam-named launchers remain as aliases for comfort during
   the transition?
5. Should source-adjacent backup Python files be archived only after a diff
   manifest is created?
6. Should root `Putnam_Seller_Tools/` be treated as a separate business
   intelligence area rather than a duplicate?
7. Should `Marketplace_Intelligence` be promoted as the sole future reusable
   pricing engine before cleaning legacy pricing folders?
8. Should legacy capture CLI remain available until automated OBS capture is
   fully trusted in production?
9. What retention window should apply to captures and completed listing jobs?
10. Should cleanup results be tracked in a new dedicated cleanup log, or only in
    `Docs/CHANGELOG.md`?

