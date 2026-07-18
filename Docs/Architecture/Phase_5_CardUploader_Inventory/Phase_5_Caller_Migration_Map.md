# Phase 5 Caller Migration Map

| Caller | Previous target | Phase 5 target | Compatibility |
| --- | --- | --- | --- |
| Putnam OS CardUploader import normalization | Local constants/functions | `InventoryApplication` -> `CardUploaderInventoryService` | Public helper names retained |
| Putnam OS ETB UI callbacks | Direct `inventory_locations` imports | `InventoryApplication` projection delegates | Exact function shapes retained |
| Reconciliation CardUploader reader | Local CSV mapping | `CardUploaderInventoryService` | `CardUploaderInventorySource` retained |
| Application runtime | Pricing/Capture/Workflow services | Adds registered `inventory` service | Existing services unchanged |

Retained callers:

- mobile queue uses the ETB compatibility projection,
- inventory audit persists workflow evidence,
- Marketplace Intelligence reads CardUploader prices,
- Orders generates static pick slips,
- `main.py` has no inventory workflow to migrate.
