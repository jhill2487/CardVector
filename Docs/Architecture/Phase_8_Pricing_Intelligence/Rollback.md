# Phase 8 Rollback

1. Stop CardVector before rollback.
2. Revert Phase 8 commits in reverse order.
3. Confirm `business_profile.json` matches its pre-Phase 8 Git version.
4. Leave additive SQLite columns in place; older code ignores them.
5. Run Phase 7 Marketplace Intelligence, application, and guardrail suites.
6. Verify the production launcher hash and target.

Rollback must not delete pricing records, inventory, Capture files, or runtime
databases. Git history is the source recovery mechanism.
