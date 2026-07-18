# Phase 0 Rollback Instructions

## Safety Rules

Do not use `git reset --hard`, `git clean`, forced checkout, history rewrite,
or deletion. Do not apply the WIP patch over a dirty tree.

## Recovery Components

Phase 0 uses four independent components:

1. The documentation commit on `main`.
2. Local branch `codex/checkpoint-price-vector-ebay-wip-20260717`, which
   anchors the exact patch base.
3. A binary Git patch containing all tracked Price Vector/eBay/config changes.
4. A ZIP containing the untracked Price Vector files and patch-process
   artifacts.

The three business-evidence JPGs remain at their original paths and are
verified by hashes in `Phase_0_Working_Tree_Inventory.md`. They are not copied
into the code archive.

## Restore the Architecture Documents

Locate the documentation commit:

```powershell
git log --oneline --all --grep "CardVector architecture audit"
```

If it must be restored onto another branch:

```powershell
git cherry-pick <documentation-commit>
```

Only run this from a clean worktree after reviewing the commit.

## Restore the WIP Tracked Changes

1. Verify a clean recovery worktree.
2. Check out or create a branch from
   `codex/checkpoint-price-vector-ebay-wip-20260717`.
3. Verify the patch hash against the value recorded in
   `Phase_0_Readiness_Assessment.md`.
4. Run:

```powershell
git apply --check "<absolute-path-to-patch>"
git apply --binary "<absolute-path-to-patch>"
```

5. Run `git status --short` and compare it with the JSON inventory.

## Restore Untracked Feature Files

1. Verify the ZIP hash recorded in `Phase_0_Readiness_Assessment.md`.
2. Extract into an empty temporary directory first.
3. Compare the archive manifest with
   `Phase_0_Working_Tree_Inventory.json`.
4. Copy only the listed files back to their original repository-relative
   paths after confirming those paths do not already contain newer work.

Do not overwrite newer files without explicit owner review.

## Business Evidence

The three claim images were deliberately excluded from the WIP code archive.
They remain in OneDrive at their original locations. Verify their SHA-256
hashes against the inventory before any move or backup operation.

## If the Patch Does Not Apply

Stop. Do not force it. Confirm:

- Current base commit matches the checkpoint branch.
- Line endings have not been rewritten.
- The worktree is clean.
- The patch file hash is correct.

Use a temporary worktree for recovery testing if necessary. Never troubleshoot
by resetting or cleaning the primary worktree.

## Roll Back the Documentation Commit

The documentation commit does not alter behavior. If the owner later decides
to remove it, use a normal revert commit:

```powershell
git revert <documentation-commit>
```

Do not rewrite history.
