# Phase 7 Rollback

Revert the focused Phase 7 commits in reverse order. Do not reset or rewrite
history.

Phase 7 adds no database migration and creates no production runtime data.
Rollback requires no data conversion.

After revert:

1. compile Marketplace Intelligence, `main.py`, and `putnam_os.py`;
2. run Phase 3 pricing equivalence tests;
3. run Application, Capture, inventory, and batch regression tests;
4. verify the production launcher target and SHA-256;
5. run the strict architecture checker;
6. confirm the worktree is clean.

The analysis CSV loses only the additive explainability columns after rollback.
The historical columns and six-column bulk-revise export remain unchanged.
