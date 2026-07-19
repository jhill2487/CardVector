# Phase 6 Batch Workflow Model

`BatchWorkflow` contains only:

- `batch_id`
- `location_label`
- five step statuses and their completion/confirmation timestamps
- `ebay_selected`, `tcgplayer_selected`, and `other_marketplaces`
- optional CSV and price-review artifact references
- batch notes
- created/updated timestamps
- batch-workflow error status and message
- derived overall status

The five steps are Capture, CardUploader upload, marketplace selection,
CardUploader CSV export, and price review.

## Forbidden Data

The model and serializer do not accept or emit card name, set, card number,
quantity, SKU/custom label, per-card location, condition, image list,
marketplace listing ID, or order state. Unknown JSON fields are discarded when
loading into the canonical model.

Legacy Capture/conversion records still contain `cards_captured`, `image_count`,
or dashboard `row_count` fields needed by their existing UI contracts. Phase 6
does not copy those fields into `BatchWorkflow` and does not rewrite or delete
the legacy records.

`location_label` identifies the operator's batch/ETB label; it is not a per-card
location record and does not establish CardUploader location truth.
