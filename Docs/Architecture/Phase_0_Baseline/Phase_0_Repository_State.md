# Phase 0 Repository State

Captured: 2026-07-17T23:57:52-04:00

## Scope

This report records the repository state before any CardVector architecture
migration. It is evidence only. No production source, launcher, configuration,
runtime data, or business data was changed while collecting it.

## Git Identity

| Field | Observed value |
| --- | --- |
| Repository | `C:\Users\user\OneDrive\PutnamCollectibles` |
| Computer | `DESKTOP-GVH6A87` |
| Branch | `main` |
| HEAD | `13fff8e4ec0945a10d37fb01b971b1db5a5c94e7` |
| HEAD subject | `feat(site): add Google Analytics tag` |
| Upstream | `origin/main` |
| Ahead / behind | `0 / 0` |
| Remote | `https://github.com/jhill2487/CardVector.git` |
| Staged changes | None |
| Stashes | None |

## Safety State

- No merge, rebase, cherry-pick, revert, or bisect operation was in progress.
- No unresolved index entries were present.
- No Git operation lock was present.
- `git fsck --full --no-reflogs` exited `0`.
- The integrity check reported no corrupt, missing, invalid, fatal, or error
  objects. It reported 557 dangling objects; these are unreachable history
  residue and were not modified.
- `git diff --check` exited `0`. Git emitted line-ending warnings for eight
  pricing files but no whitespace errors.

## Branches, Tags, and Worktrees

Local branches:

| Branch | Commit | Upstream | State |
| --- | --- | --- | --- |
| `main` | `13fff8e` | `origin/main` | Current worktree |
| `fix/ebay-active-listings-pricing` | `13fff8e` | `origin/fix/ebay-active-listings-pricing` | Registered to a stale secondary worktree |

Existing tag:

- `phase0-foundation` -> `4bcbba72d2d928598628ac579d103f463c0f9856`
  (`Phase 0: Repository architecture reorganization`, 2026-07-08)

Worktrees:

- `C:/Users/user/OneDrive/PutnamCollectibles`, branch `main`, healthy.
- `C:/Users/JaredHill/OneDrive/CardVector-ebay-fix`, branch
  `fix/ebay-active-listings-pricing`, reported as prunable because its gitdir
  file points to a non-existent location.

The stale worktree was not pruned, repaired, or otherwise changed. It requires
owner review before Phase 1.

## Ignored Runtime and Development Areas

The following relevant paths were observed as ignored:

- `Capture/`
- `Data/Completed_Jobs/`
- `Data/Exports/`
- `Data/Imports/Processed/sample_acceptance_03.csv` through
  `sample_acceptance_06.csv`
- `Data/Logs/`
- `Data/Media/`
- `Data/Processed/`
- `MobileCapture/`
- `Platform/Putnam_OS/System/cache/`
- `Platform/Putnam_OS/System/logs/`
- `Work_Sessions/`

These paths were not treated as source code and were not staged.

## Governance Path Finding

The root `AGENTS.md` refers agents to paths that are not present at their stated
locations:

- `Docs/AGENTS.md`
- `Docs/Putnam_Standards/PUTNAM_PRINCIPLES.md`
- `Docs/Putnam_Standards/PUTNAM_PLATFORM_STANDARDS.md`
- `Docs/PROJECT_STATUS.md`
- `Docs/ROADMAP.md`

Related historical standards are present under `Docs/Reference/`, while current
project documents use names such as `PROJECT_MANUAL.md` and
`PROJECT_ROADMAP.md`. This mismatch also causes
`Tools/validate_production_startup.py` to reject the repository root. It was
documented, not repaired.

## Commands Used

The following read-only commands established this state:

```text
git status --porcelain=v2 --branch
git status --short --ignored
git diff --cached --name-status
git diff --name-status
git diff --stat
git diff --numstat
git diff --check
git ls-files -u
git ls-files --others --exclude-standard
git stash list
git branch -vv
git tag --list
git show -s phase0-foundation
git remote -v
git config --get branch.main.remote
git config --get branch.main.merge
git worktree list --porcelain
git fsck --full --no-reflogs
```

The complete dirty-file inventory is in
`Phase_0_Working_Tree_Inventory.md` and
`Phase_0_Working_Tree_Inventory.json`.
