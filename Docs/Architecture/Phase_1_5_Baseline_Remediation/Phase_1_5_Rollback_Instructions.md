# Phase 1.5 Rollback Instructions

## Feature Checkpoint

The complete Price Vector/eBay checkpoint is:

```text
branch: codex/checkpoint-price-vector-ebay-phase-1-5
commit: 3dbadd593860a2847a8824106be9c1e41e74a76c
```

To inspect or resume it without changing `main`, create a new worktree or
switch only from a clean working tree. Do not delete the branch until the
feature is merged, superseded, or separately archived.

Phase 0 recovery remains available at:

```text
Work_Sessions/Phase_0_Baseline_20260717_235752/
```

Its patch, ZIP, manifest, and SHA-256 evidence provide an independent recovery
path for the original dirty state.

## Main-Branch Commits

The runtime-ignore commit is `9bfe9cc`. Reverting that commit restores the
prior ignore behavior without deleting ignored files.

The Phase 1 baseline snapshot correction and Phase 1.5 report commit may be
reverted as one documentation-only unit after this package is committed.

Use ordinary `git revert` on a clean branch. Do not use `git reset --hard`,
`git clean`, forced checkout, or history rewriting.

## Local-Only Artifacts

The seven ignored local artifacts remain in their original locations. Reverting
`.gitignore` does not remove them. If recovery is needed, compare against the
Phase 0 manifest before copying from the ZIP.

## Validation Rollback

Tracked files touched by legacy validation were restored from `HEAD`. If that
condition is questioned, verify:

```text
git diff -- Platform/Putnam_OS/System/config/location_registry.json
git diff -- Platform/Putnam_OS/System/data
git diff -- Platform/Putnam_OS/System/app/test_artifacts
```

All commands must return no tracked diff before Phase 2 begins.
