# Phase 0 Readiness Assessment

Updated: 2026-07-17

## Checkpoint Status

The repository is partially ready for architecture migration:

- Architecture audit, design, and Phase 0 evidence are cleanly separable.
- Active Price Vector/eBay work is identified and can be preserved without
  altering it.
- Git integrity is healthy.
- The official launcher target is known and `putnam_os.py` compiles/imports.

The repository is **not ready to begin Phase 1** yet.

## Blocking Findings

1. `Platform/Putnam_OS/System/app/main.py` has an unterminated f-string at line
   650. The active feature WIP cannot be called validated.
2. The working tree remains intentionally dirty while the WIP stays in place.
3. The registered `fix/ebay-active-listings-pricing` worktree is stale and
   requires owner review before any worktree maintenance.
4. Root `AGENTS.md` points to missing governance paths, causing the production
   startup validator to reject the repository root.
5. Shared versus workstation-local ownership of
   `putnam_os_config.json` remains unresolved.
6. Three potentially sensitive business-evidence images are untracked inside
   the repository and need a documented business-data policy.

## Validation Status

Passes:

- Marketplace Intelligence fixture workflow
- FMV/recommendation/final-price separation and persistence
- Putnam pricing compatibility script
- Mobile queue and Supabase contract
- Public storefront contract
- Capture Studio, auto capture, thumbnails, OBS manager
- Desktop workflow source checks, eBay policy, orders, workflow context
- `putnam_os.py` compilation and desktop imports
- Node syntax and `git diff --check`
- Configuration JSON parsing

Known failures:

- `main.py` syntax: active uncommitted feature WIP
- Pricing consolidation test: blocked by the same syntax error
- Mobile location contract: stale exact-source assertion previously identified
- Startup validator: stale/missing governance-path predicate

Skipped for safety:

- Listing Optimizer acceptance test
- Inventory Audit artifact test
- Live GUI and marketplace operations

## Phase 1 Decision

Status: **NOT READY**

Recommended next action after Phase 0 approval:

1. Complete a narrowly scoped Price Vector/eBay recovery task that fixes the
   `main.py` syntax error without changing intended behavior.
2. Run the full focused pricing suite and preserve the coherent feature in its
   own commit.
3. Decide whether `putnam_os_config.json` is shared or local.
4. Repair governance-path references in a documentation/tooling-only task.
5. Review the stale worktree registration.
6. Obtain explicit owner approval before Phase 1.

No architecture migration should start while the source WIP is invalid and the
working tree is dirty.

## Recovery Artifact Record

The final checkpoint branch, documentation commit, patch path/hash, ZIP
path/hash, and final status are added after checkpoint creation. The reports
must be compared with the original inventory before Phase 0 is declared
complete.
