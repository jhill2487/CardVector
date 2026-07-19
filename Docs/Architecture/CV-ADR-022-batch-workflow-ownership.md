# CV-ADR-022 - CardVector Owns Batch Workflow Status Only

- **Decision ID:** CV-ADR-022
- **Status:** Accepted
- **Date:** 2026-07-19
- **Owner:** Putnam Collectibles / CardVector
- **Approval:** Approved by the project owner through the Phase 6 authorization

## Context

The production workflow captures photos, hands them to CardUploader, assigns a
user-selected batch/location ID in CardUploader, exports a CSV, and reviews that
CSV in CardVector. `workflow_context.py` already records handoff links, while
physical conversion sessions record Capture progress. Phase 5 established that
CardUploader owns managed inventory.

## Decision

CardVector owns batch-level physical-inventory-conversion and price-review
workflow state only. CardUploader remains the canonical owner of card-level
inventory and batch-to-card associations. CardVector does not know or persist
the individual cards inside a batch.

The canonical package is `Platform/cardvector/batch_workflow`. Application
orchestration is in `Platform/cardvector/application/batch_workflow.py`.

## Evidence

- `Platform/Putnam_OS/System/app/workflow_context.py` records Capture,
  CardUploader, CSV, pricing-job, and export handoff state.
- `Platform/Putnam_OS/System/app/putnam_os.py` contains the corresponding UI
  milestone callbacks.
- Phase 5 proved CardUploader inventory snapshot ownership and found no
  supported CardUploader mutation API.
- The operator-authorized Phase 6 workflow requires only user-confirmed batch
  milestones.

## Alternatives Considered

1. Store batch contents in CardVector: rejected because it duplicates
   CardUploader inventory truth.
2. Store CardVector workflow state in CardUploader: rejected because no
   supported workflow-state API exists.
3. Keep status only in Tkinter memory: rejected because it is not resumable.
4. Extend the legacy dashboard dictionary indefinitely: rejected as a
   permanent contract, but retained temporarily for compatibility.

## Consequences

- The batch record stores statuses, confirmations, timestamps, notes, and
  optional artifact references only.
- It never stores card names, numbers, quantities, SKUs, per-card locations,
  image lists, conditions, listing IDs, or order state.
- Marketplace booleans are operator workflow confirmations, not item-level
  marketplace truth.
- Existing `cardvector_workflow.json` behavior remains a temporary
  compatibility surface under `CV-COMP-017`.
- Runtime records use atomic JSON files under the existing ignored physical
  conversion runtime root.

## Migration And Compatibility Impact

Existing UI callbacks delegate milestone writes through
`BatchWorkflowApplication`. Failures are logged and do not interrupt existing
Capture, CardUploader import, or pricing success paths. No existing persistence
record or output contract is rewritten.

## Testing Requirements

- Status and transition contract tests.
- Atomic repository and failure tests using temporary directories.
- Application delegation and event tests.
- Legacy dashboard-stage equivalence tests.
- A schema allowlist test proving no card-level field can serialize.
- Capture, pricing, inventory, desktop, and architecture regressions.

## Rollback

Revert the Phase 6 commits. Existing workflow context and production callbacks
remain intact because no legacy record is migrated or deleted.
