# Phase 6 Canonical API

Public import root: `Platform.cardvector.batch_workflow`.

## Contracts

- `BatchWorkflow`
- `BatchWorkflowQuery`
- `BatchWorkflowResult`
- `WorkflowStepStatus`
- `OverallBatchStatus`
- typed batch, transition, and persistence exceptions

## Service Operations

- `create_batch`, `ensure_batch`, `get_batch`, `list_batches`
- `mark_capture_started`, `mark_capture_complete`
- `mark_carduploader_upload_started`, `mark_carduploader_upload_complete`
- `set_marketplace_selection`, `mark_marketplace_selection_needs_review`
- `mark_csv_exported`
- `start_price_review`, `complete_price_review`, `fail_price_review`
- `add_batch_note`

`BatchWorkflowApplication` exposes the current application use cases and emits
optional application events. No operation reads CardUploader card contents or
performs pricing.
