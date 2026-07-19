# Phase 6 Rollback Instructions

## Code Rollback

Revert the focused Phase 6 commits in reverse order. Do not reset or rewrite
history. The production launcher remains pointed at `putnam_os.py`.

## Runtime Rollback

Phase 6 does not migrate or delete legacy data. If additive batch records have
been created after operator use, preserve:

`Platform/Putnam_OS/System/data/inventory_conversion/batch_workflows/`

before reverting. The old `cardvector_workflow.json`, Capture sessions,
conversion sessions, CardUploader data, and pricing outputs remain valid.

## Verification

After rollback:

1. compile `putnam_os.py`,
2. run legacy workflow-context, Capture, pricing, and inventory tests,
3. verify the production launcher hash/target,
4. run architecture strict mode,
5. confirm no runtime files were deleted.

No database rollback is required because Phase 6 adds no schema or migration.
