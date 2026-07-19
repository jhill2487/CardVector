# Phase 6 Price Review Integration

The preserved chain is:

`CardUploader CSV -> CardVector import -> Marketplace Intelligence review -> existing output`

Phase 6 records only:

- CSV received/export complete,
- review started,
- review complete or failed,
- timestamps,
- optional source/output artifact references,
- notes and sanitized error text.

Marketplace Intelligence continues to own FMV, recommendation, final price,
confidence, persistence, and serialization. Item-level prices remain in the
existing CSV/pricing outputs and never enter `BatchWorkflow`.

No formula, threshold, field, output format, or error category was changed.
