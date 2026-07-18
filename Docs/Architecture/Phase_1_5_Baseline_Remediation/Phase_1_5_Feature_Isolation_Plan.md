# Phase 1.5 Feature Isolation Plan

## Selected Strategy

Create a dedicated branch:

`codex/checkpoint-price-vector-ebay-phase-1-5`

The branch will start at Phase 1 commit `e71f06f` and preserve the coherent
Price Vector/eBay source, tests, migration, documentation, configuration, and
the minimum `main.py` syntax repair in one checkpoint commit.

This is preferred over a stash because it is durable and transparent. It is
preferred over committing the feature to `main` because Phase 2 must begin from
a clean architecture baseline that does not depend on unfinished feature work.
No new worktree is needed because the current worktree can safely change branch
while preserving the dirty files.

## Included In Feature Checkpoint

- 12 tracked Price Vector/eBay/configuration changes
- 4 Price Vector planning/audit documents
- pricing repository
- versioned pricing-decision migration
- 2 focused pricing tests
- minimum escaped-newline repair in `main.py`

## Excluded

- three `.bak` files
- one one-off patch script
- three business-evidence images
- Phase 1.5 reports
- `.gitignore` changes

Excluded artifacts are already protected by Phase 0 hashes/ZIP or their
business-evidence hashes. They will remain local and be covered by certain
ignore rules on `main`.

## Validation Gate

Before the feature commit:

1. `main.py` and all changed Python files compile.
2. Focused consolidation and FMV tests pass.
3. Existing Marketplace Intelligence and pricing smoke tests pass where safe.
4. `git diff --check` passes.
5. Secret-pattern scan passes.
6. Architecture checker reports no newly introduced violation after updating
   the baseline only if the repaired parse reveals existing findings.

If the feature cannot meet this gate, preserve it on the branch with a new
patch/ZIP and do not describe it as validated.

## Return To Migration Baseline

After the feature checkpoint, switch back to `main`. The tracked feature diff
must disappear because it is owned by the feature branch. Apply and commit only
certain ignore rules and Phase 1.5 documentation on `main`, then run the complete
baseline validation.

No branch or artifact will be deleted or pushed in Phase 1.5.

## Execution Result

The plan was executed as documented.

- Branch created:
  `codex/checkpoint-price-vector-ebay-phase-1-5`
- Commit created:
  `3dbadd593860a2847a8824106be9c1e41e74a76c`
- Commit subject:
  `checkpoint(price-vector): preserve active eBay workflow implementation`
- Included: 20 feature/configuration/source/test/documentation files
- Excluded: Phase 1.5 reports and all seven local-only artifacts
- Push: not performed

The working tree was then returned to `main`. No source diff from the feature
checkpoint remains on the migration baseline.
