# Phase 2 Rollback

## Trigger Conditions

Rollback Phase 2 if:

- workflow job dictionaries or ordering differ;
- workflow context files differ;
- Home or Processing behavior changes;
- startup/import behavior regresses;
- a new architecture violation appears;
- any protected subsystem or launcher changes.

## Code Rollback

Phase 2 is one source-and-documentation migration commit. Revert that commit
with ordinary `git revert` from a clean working tree.

The revert removes:

- `Platform/cardvector/application`;
- its namespace file;
- application tests;
- Phase 2 documentation;
- `putnam_os.py` facade wiring;
- Phase 2 manifest/decision/register updates.

It restores the direct `workflow_context.py` imports and the former
`putnam_os.py` cache bookkeeping. No runtime data or schema rollback is needed.

## Verification After Rollback

1. Compile `putnam_os.py` and `workflow_context.py`.
2. Run `test_workflow_context.py`.
3. Run `test_desktop_workflow_ui.py`.
4. Run architecture checker strict mode.
5. Verify the production VBS SHA-256 remains
   `AD5044D8D439CE6B321951E85A335DE86927AAA9453FE05DF0A23C1327006EE7`.
6. Confirm the working tree contains no unaccounted changes.

Do not use `git reset --hard`, `git clean`, forced checkout, or runtime-data
deletion.
