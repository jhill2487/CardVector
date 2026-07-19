# Phase 6 Marketplace Selection Boundary

`ebay_selected`, `tcgplayer_selected`, `other_marketplaces`, and
`marketplace_selection_status` are operator workflow confirmations only.

They mean the operator confirmed the intended batch-level handoff. They do not:

- mirror CardUploader marketplace assignments,
- assert that every card is listed,
- identify which cards use a marketplace,
- contain marketplace listing IDs,
- replace CardUploader validation.

An explicit confirmation with no marketplace selected is valid and records
both booleans as false. The current desktop UI has no dedicated marketplace
confirmation action, so Phase 6 exposes the tested application API without
inventing a new screen or workflow.
