# Phase 1.5 Runtime Artifact Classification

## Current Working-Tree Artifacts

| Artifact | Decision | Reason |
| --- | --- | --- |
| Three `*.bak` files beside active app source | Preserve outside Git; ignore `*.bak` | Exact copies are already in the verified Phase 0 ZIP; backup names are forbidden production artifacts |
| `patch_cardvector_ebay_existing_listings.py` | Preserve outside Git; ignore exact root path | One-off patch process artifact, not a permanent tool; verified in Phase 0 ZIP |
| `Business/eBay_Store_Items/PIP Insurance Claims/` | Preserve outside Git; ignore folder | Potentially sensitive claim evidence, not source code; Phase 0 hashes protect current files |
| `Work_Sessions/` patch/ZIP/manifest | Preserve outside Git; existing ignore rule | Required recovery evidence |

## Categories With No Current Untracked Status

Logs, caches, generated reports, captures, processed imports, Marketplace
Intelligence reports, and known runtime directories are already covered by
existing ignore rules. No new local database appears in the dirty-tree status.

## Proposed Certain Ignore Rules

```gitignore
*.bak
/patch_cardvector_ebay_existing_listings.py
/Business/eBay_Store_Items/PIP Insurance Claims/
```

These certain rules were committed on `main` as `9bfe9cc`. `git check-ignore`
confirmed that the seven local-only artifacts are covered.

Broad `*.patch`, `*.bundle`, `*.zip`, `*.sqlite`, `*.sqlite3`, and `*.db` rules
were intentionally not added. The repository contains tracked archived
databases and may later approve fixtures or static datasets; broad patterns
require a dedicated retention decision and explicit exceptions.

## Validation Side Effects

The legacy inventory test partially removed three tracked report fixtures
before failing on OneDrive permissions. Importing `putnam_os` also updated
three tracked operator/session files. All six files were verified as clean
immediately before those commands and restored from `HEAD` afterward:

- `Platform/Putnam_OS/System/app/test_artifacts/inventory_audit_v1_0/reports/*`
- `Platform/Putnam_OS/System/config/location_registry.json`
- `Platform/Putnam_OS/System/data/acquisitions/records/ACQ-20260703_010121.json`
- `Platform/Putnam_OS/System/data/current_session.json`

No production data change remains. Future baseline validation must not import
`putnam_os` directly or run the inventory audit test in the OneDrive worktree.

No file will be deleted or moved.
