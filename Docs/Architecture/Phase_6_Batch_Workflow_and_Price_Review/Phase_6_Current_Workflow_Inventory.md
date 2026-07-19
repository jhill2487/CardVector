# Phase 6 Current Workflow Inventory

| Path | Current responsibility | Inputs/outputs | Persistence/status | Decision |
| --- | --- | --- | --- | --- |
| `Platform/Putnam_OS/System/app/workflow_context.py` | Pending-work discovery and resumability links | Capture sessions, queue rows, artifact paths -> dashboard job dicts | `cardvector_workflow.json`; Ready/CardUploader/CSV/Pricing/eBay stages | Retain as `CV-COMP-017` |
| `Platform/cardvector/application/workflows.py` | Phase 2 dashboard orchestration facade | Delegate calls -> existing job dictionaries | No independent persistence | Retain |
| `Platform/Putnam_OS/System/app/putnam_os.py` | UI callbacks for capture staging, CardUploader, CSV import, and pricing | Operator actions and result callbacks | Updates legacy context and runtime UI | Delegate milestones |
| `Platform/Putnam_OS/System/data/inventory_conversion/` | Physical conversion session runtime | ETB/location Capture metadata | Runtime JSON; legacy conversion statuses | Retain unchanged |
| `Platform/cardvector/capture` | Canonical image acquisition and staging | Capture sessions/images -> staged Capture result | Existing Capture contracts | Retain owner |
| `Platform/cardvector/integrations/carduploader` | Recognition and inventory boundaries | Handoff URL and read-only inventory snapshots | No CardVector card mutation | Retain owner boundary |
| `Platform/cardvector/marketplace_intelligence` | FMV and pricing decisions | Pricing inputs -> pricing results/exports | Existing pricing repository/output | Retain owner |
| `Platform/Putnam_OS/System/app/main.py` | Secondary compatibility pricing UI | CSV -> pricing review output | Independent compatibility surface | Retain; no batch caller found |

## Status Values Observed

The legacy dashboard exposes `Ready for CardUploader`, `Awaiting CSV Import`,
`Pricing Review`, and `Ready for eBay Upload`. Physical conversion uses
`Waiting for Capture`, `Ready for Capture`, `Mobile Capture Staged`, and
`Location Complete`. Phase 6 preserves those public strings and maps new
canonical status independently.

## Duplicate Assessment

No pre-existing canonical batch model was found. The legacy context is a
dashboard/job dictionary, not card-level inventory. The new package does not
copy Capture, pricing, CardUploader, inventory, or UI algorithms.

Legacy conversion `cards_captured` and dashboard `image_count`/`row_count`
remain compatibility-only Capture/UI summaries. They are intentionally absent
from the canonical batch workflow schema.
