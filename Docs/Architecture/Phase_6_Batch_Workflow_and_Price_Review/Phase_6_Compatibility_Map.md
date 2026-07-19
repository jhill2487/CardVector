# Phase 6 Compatibility Map

## Active Adapter

`CV-COMP-017` preserves:

- `workflow_context.py` job discovery and stage mapping,
- `cardvector_workflow.json` resumability links,
- legacy job dictionaries and action labels,
- existing pending-work and Processing UI behavior.

The canonical package does not import the adapter. `putnam_os.py` temporarily
composes and writes both the legacy UI context and canonical milestone record.

## Removal Condition

Remove the adapter only after:

1. presentation reads canonical batch queries,
2. artifact-link metadata has an approved owner,
3. old context files are migrated or explicitly retained,
4. dashboard and resume equivalence tests pass,
5. the project owner approves the runtime-data change.

No deprecation entry was added because the adapter remains active and supported.
