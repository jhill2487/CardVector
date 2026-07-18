# Subsystem Change Checklist

## Scope

A change within one canonical subsystem that affects multiple modules, a public
subsystem interface, persistence, background work, or an integration adapter,
without changing permanent ownership or layer direction.

## Checklist

- [ ] Ownership matrix and relevant architecture standards reviewed.
- [ ] Current callers, tests, persistence, and compatibility surfaces inventoried.
- [ ] Change plan and acceptance criteria documented.
- [ ] Subsystem owner/project owner review obtained.
- [ ] Unit, integration, regression, and failure-path tests pass.
- [ ] Production workflow smoke test completed safely.
- [ ] Data migration and rollback tested when applicable.
- [ ] Compatibility/deprecation registers updated when applicable.
- [ ] Operator and architecture documentation updated.
- [ ] Guardrail warning and strict checks reviewed.
- [ ] Focused commits preserve rollback boundaries.

Escalate to an architecture change for a new package root, entry point, canonical
owner, cross-layer dependency, top-level folder, or long-lived compatibility
surface.
