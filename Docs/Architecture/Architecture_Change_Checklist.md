# Architecture Change Checklist

## Scope

Any change to ownership, layers, entry points, launcher targets, package roots,
top-level folders, source/runtime boundaries, public subsystem contracts, or
permanent integration direction.

## Checklist

- [ ] Evidence and problem are documented.
- [ ] Existing implementation and caller inventory is complete.
- [ ] ADR is proposed using `ADR_Template.md`.
- [ ] Alternatives and operational consequences are recorded.
- [ ] Project owner explicitly accepts the ADR.
- [ ] Manifest, ownership matrix, roadmap, and registers are updated.
- [ ] Migration is split into reversible packages.
- [ ] Before-state evidence and protected baseline exist.
- [ ] Automated characterization, integration, and guardrail tests are defined.
- [ ] Manual production workflow validation is defined.
- [ ] Data, compatibility, deployment, and rollback impacts are explicit.
- [ ] Each package has separate approval before execution.
- [ ] Final verification proves launchers and workflows remain valid.

Architecture work may not proceed on assumption. Missing evidence is an open
question, not permission to guess.
