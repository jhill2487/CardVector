# Phase 5 Rollback Instructions

Phase 5 has no database migration or production data change.

1. Verify the working tree and identify the Phase 5 commits.
2. Revert the documentation commit, application/integration commit, and tests
   in reverse order with normal `git revert`.
3. Run Phase 4 validation and verify the production launcher hash.
4. Do not restore or rewrite runtime inventory files; Phase 5 did not change
   them.

Legacy public functions and source files remain present, so rollback does not
require data conversion. The existing Phase 0 recovery material remains valid.
