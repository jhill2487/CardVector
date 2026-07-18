# Phase 5 Inventory Implementation Inventory

| Path | Current responsibility | Classification | Phase 5 disposition |
| --- | --- | --- | --- |
| `Platform/cardvector/integrations/carduploader/inventory.py` | CardUploader snapshot contract and parser | Canonical integration | New canonical provider API |
| `Platform/cardvector/application/inventory.py` | Inventory query/projection orchestration | Canonical application | New facade |
| `Platform/Putnam_OS/System/app/putnam_os.py` | Import, audit, conversion, UI, ETB callbacks | Production legacy UI/logic | Snapshot and ETB entry points delegate |
| `Platform/Putnam_OS/System/app/inventory_reconciliation.py` | CardUploader/eBay snapshot matching and reports | Production reporting/compatibility | CardUploader source delegates |
| `Platform/Putnam_OS/System/app/inventory_locations.py` | ETB A-J projection, QR, labels, JSON/Supabase merge | Production compatibility projection | Retained under `CV-COMP-007` |
| `Platform/Putnam_OS/Putnam_Seller_Tools/location_registry.py` | Older ETB-##-Letter batch convention | Legacy production helper | Retained; format conflict documented |
| `Platform/Putnam_OS/System/tools/mobile_capture_queue.py` | Capture queue and Supabase location sync | Production Capture compatibility | Retained unchanged |
| `supabase/migrations/20260716130000_mobile_location_registry.sql` | Private ETB/location identity for mobile Capture | Cloud compatibility projection | Retained unchanged |
| `Platform/Putnam_OS/System/app/orders_fulfillment.py` | Static pick-slip rendering from order CSV | Orders production helper | Retained unchanged |
| `Platform/Putnam_OS/System/decision_engine/modules/inventory.py` | Read-only snapshot metrics | Legacy analytics | Retained |
| `Platform/Marketplace_Intelligence/.../providers.py` | CardUploader price evidence | Canonical pricing implementation | Retained unchanged |
| `Platform/Marketplace_Intelligence/marketplace_intelligence/csv_import.py` | Imports marketplace/pricing rows that may include quantity fields | Canonical pricing input | Retained unchanged |
| `Platform/Marketplace_Intelligence/business_intelligence/business_intelligence_v0_1.py` | Historical business metrics over inventory-like exports | Legacy analytics | Retained unchanged |
| `Platform/Putnam_OS/Putnam_Seller_Tools/seller_audit/putnam_seller_audit_v1_0.py` | Audits listing/SKU/location evidence | Seller Tools production helper | Retained unchanged |
| `Platform/Putnam_OS/Putnam_Seller_Tools/seller_audit/putnam_sku_repair_planner_v1_1.py` | Plans SKU repairs without owning managed inventory | Seller Tools production helper | Retained unchanged |
| `Platform/Putnam_OS/Putnam_Seller_Tools/listing_optimizer/**` | Reads listing and inventory evidence for listing optimization | Listings/legacy support | Retained unchanged |
| `Platform/Putnam_OS/System/app/main.py` | Pricing desktop entry point; no active managed-inventory workflow found | Legacy production UI | No Phase 5 caller migration |
| `Tools/test_mobile_location_contract.py` / `Tools/validate_mobile_location_workflow.js` | Mobile capture-location contract validation | Tests/tools | Retained unchanged |
| `Data/Imports/CardUploader_Inventory/*.csv` | Imported CardUploader export | Tracked operational evidence | Read-only during Phase 5 |
| `Data/Exports/carduploader_inventory_snapshot.csv` | Latest local projection | Ignored runtime snapshot | Not modified |
| `Data/Exports/Reconciliation/**` / `Data/Exports/Pick_Lists/**` | Generated reconciliation and static pick-slip evidence | Generated output | Not modified |
| `Platform/Putnam_OS/System/data/inventory/**` | Local ETB projection | Ignored runtime state | Not modified |
| `Platform/Putnam_OS/System/data/inventory_audit/**` | Audit resume/history | Runtime state | Not modified |
| `Platform/Putnam_OS/System/data/inventory_conversion/**` | Conversion-session workflow metadata | Runtime state | Not modified |
| `Platform/Putnam_OS/System/app/test_artifacts/inventory_audit_v1_0/**` | Tracked inventory-audit fixtures and expected outputs | Test artifact | Not modified |

Archived and timestamped backup copies were inventoried but are not production
owners and remain untouched.
