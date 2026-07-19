# Phase 6 CardUploader Boundary

The workflow boundary is:

`Capture complete -> batch milestone -> operator CardUploader upload and batch assignment -> operator confirmation -> CSV milestone`

CardVector may record that the operator started or completed a CardUploader
handoff. It may not query or infer:

- cards in the batch,
- card quantities,
- SKUs,
- card locations,
- per-card marketplace state,
- listing or order state.

CSV import implies that the batch upload and CSV export milestones completed;
it does not validate individual CardUploader records. CardUploader remains the
source of truth for every card-level fact.
