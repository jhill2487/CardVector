# Phase 6 Architecture Decision

The accepted decision is recorded in
`../CV-ADR-022-batch-workflow-ownership.md`.

CardVector owns batch-level workflow status for physical inventory conversion
and price review only. CardUploader retains all card-level inventory and
batch-to-card truth. Capture and Marketplace Intelligence retain their Phase 4
and Phase 3 responsibilities.

The canonical implementation is:

- domain/service: `Platform/cardvector/batch_workflow`
- orchestration: `Platform/cardvector/application/batch_workflow.py`
- temporary dashboard adapter: `Platform/Putnam_OS/System/app/workflow_context.py`
- temporary composition: `Platform/Putnam_OS/System/app/putnam_os.py`

No item-level inventory package, table, or synchronization path was created.
