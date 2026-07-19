# Phase 6 Behavior Equivalence

| Fixture/action | Previous behavior | Canonical addition | Difference |
| --- | --- | --- | --- |
| Capture session discovered | Ready / Ready for CardUploader / Open CardUploader | capture status can be complete | Legacy output unchanged |
| CardUploader opened | Ready / Awaiting CSV Import / Import CardUploader CSV | upload in progress | Legacy output unchanged |
| CSV imported | Needs Attention / Pricing Review / Review Pricing | upload and CSV complete | Legacy output unchanged |
| Pricing output exists | Ready / Ready for eBay Upload / Open Export Folder | price review complete | Legacy output unchanged |
| Pricing failure | Existing log, status, and dialog | price review failed with sanitized message | Existing behavior unchanged |
| Retry failed review | Existing workflow may rerun | failed -> in progress | Additive status only |

The legacy characterization test asserts exact state, stage, and action tuples.
The canonical model tests assert exact status, confirmation, timestamp,
reference, serialization, and error behavior. No dashboard-visible difference
was introduced.
