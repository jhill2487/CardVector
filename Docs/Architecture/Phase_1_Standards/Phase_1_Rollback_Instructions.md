# Phase 1 Rollback Instructions

## Scope

Phase 1 contains documentation, repository metadata, and read-only checker
tooling. It contains no production code or runtime-data change.

## Preferred Rollback

1. Confirm no later change depends on the Phase 1 standards.
2. Review the focused Phase 1 commit.
3. Revert that commit with `git revert <phase-1-commit>`.
4. Run `git status --short`.
5. Re-run the Phase 0 WIP reverse-patch check.
6. Confirm the production launcher, `putnam_os.py`, and `main.py` retain their
   preserved hashes and status.

Do not use `git reset --hard`, `git clean`, forced checkout, or history rewrite.

## Partial Rollback

Do not remove only the machine manifest while leaving the checker or contribution
rules active. The index, manifest, rules, templates, baseline, tool, and tests
form one standards package and should be reverted together.

## Phase 0 Recovery

Phase 0 recovery remains independent:

- Branch: `codex/checkpoint-price-vector-ebay-wip-20260717`
- Tracked patch:
  `Work_Sessions/Phase_0_Baseline_20260717_235752/price_vector_ebay_tracked_wip.patch`
- Untracked archive:
  `Work_Sessions/Phase_0_Baseline_20260717_235752/price_vector_ebay_untracked_wip.zip`

Use the detailed instructions in
`../Phase_0_Baseline/Phase_0_Rollback_Instructions.md`.
