# Phase 0 Proposed Commit Plan

## Principles

- Never mix architecture documentation with feature source.
- Never label incomplete code as validated.
- Do not stage configuration, business evidence, runtime data, backups, or
  one-time patch tools with production source.
- Prefer commits and portable recovery artifacts over a stash.
- Do not create the baseline tag while the full working tree remains dirty.

## Group 1: Architecture Documentation

Proposed commit:

```text
docs(architecture): add CardVector architecture audit and migration standards
```

Exact scope:

- `Docs/Architecture/CardVector_*.md`
- `Docs/Architecture/Phase_0_Baseline/*`
- The eight architecture audit reports under `Docs/Reports/`

Excluded:

- `Docs/PriceVector/`
- all `Platform/` source
- configuration
- business data
- backup files
- patch scripts
- runtime and ignored output

Rationale: this group is documentation-only, cleanly separable, and does not
alter production behavior.

## Group 2: Price Vector / eBay Feature Work

Desired future commit:

```text
checkpoint(price-vector): preserve current eBay and Price Vector work before architecture migration
```

Current disposition: **do not create this commit yet**.

Reason:

- `Platform/Putnam_OS/System/app/main.py` does not compile due an unterminated
  f-string at line 650.
- `test_pricing_engine_consolidation` cannot import the module.
- Committing this group to `main` as a completed feature checkpoint would
  misstate its validation status.

Preservation method:

1. Create a local branch pointer named
   `codex/checkpoint-price-vector-ebay-wip-20260717` at the post-documentation
   recovery base.
2. Create a binary Git patch of all tracked WIP changes.
3. Create a ZIP archive of untracked Price Vector files and patch-process
   artifacts.
4. Keep the original files unchanged in the working tree.
5. Verify hashes and artifact readability.

The branch anchors the exact commit against which the patch applies. The patch
and ZIP preserve changes that a branch alone cannot store.

## Group 3: Configuration

File:

- `Platform/Putnam_OS/System/config/putnam_os_config.json`

Action:

- Keep unstaged.
- Include its tracked diff in the WIP patch.
- Require owner review before deciding whether it is shared product
  configuration or workstation-specific configuration.

## Group 4: Business Evidence

Files:

- Three JPGs under
  `Business/eBay_Store_Items/PIP Insurance Claims/Order 27-14693-04250/`

Action:

- Leave in place and unstaged.
- Preserve SHA-256 hashes in the inventory.
- Do not include them in a source commit or WIP code archive.
- Define a business-data policy before adding an ignore rule.

## Group 5: Runtime and Developer Artifacts

Runtime/output directories remain ignored and unstaged.

The three `.bak` files and root patch script will be copied into the WIP ZIP
for recovery but not committed. Their eventual archive/ignore treatment is a
future cleanup decision.

## Tag and Push Decision

- Do not create `cardvector-pre-architecture-migration-baseline` because the
  complete state is not clean and active feature work is not validated.
- Do not move or overwrite the existing `phase0-foundation` tag.
- Do not push commits, branches, tags, patches, or archives in Phase 0 without
  explicit instruction.
