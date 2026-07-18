# Small Change Checklist

## Scope

A local behavior-preserving fix or narrow feature within one canonical module,
with no ownership, layer, public-contract, data-schema, entry-point, or runtime
boundary change.

## Checklist

- [ ] Canonical owner and existing implementation confirmed.
- [ ] Unrelated working-tree changes identified and excluded.
- [ ] Focused tests added or updated.
- [ ] Relevant smoke test run.
- [ ] `git diff --check` passes.
- [ ] Manual validation completed when operator behavior changes.
- [ ] Rollback is a single focused revert.
- [ ] Documentation updated if operator-visible behavior changes.

Escalate to a subsystem change if multiple packages, public interfaces,
persistence, background jobs, or external integrations are affected. Escalate
to an architecture change if ownership, dependency direction, entry points, or
repository structure changes.
