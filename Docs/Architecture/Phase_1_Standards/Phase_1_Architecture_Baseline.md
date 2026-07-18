# Phase 1 Architecture Baseline

- **Generated:** 2026-07-18T01:39:59.058526-04:00
- **Mode:** warning-establish-baseline
- **Total findings:** 48
- **Critical:** 0
- **Error:** 19
- **Warning:** 29
- **Info:** 0
- **Pre-existing:** 48
- **New:** 0

Existing findings are recorded, not fixed, by Phase 1. A baseline item
does not become approved architecture merely because it is recorded.

## Findings

| Severity | Rule | Path | Pre-existing | Blocks migration | Future phase | False-positive status | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ERROR | entry_points.multiple_gui | `<repository>` | Yes | No | Phase 3, 8-10 | not reviewed | Multiple likely Python GUI entry points detected (12): Platform/Marketplace_Intelligence/marketplace_intelligence/ui.py, Platform/Putnam_OS/Putnam_Seller_Tools/listing_optimizer/backups/putnam_os_related_exporter_original_20260627_093120.py, Platform/Putnam_OS/System/app/main.py, Platform/Putnam_OS/System/app/putnam_os.py, Platform/Putnam_OS/System/app/putnam_os_capture_v1_backup_20260629_212812.py, Platform/Putnam_OS/System/app/putnam_os_comp_engine_v1_1_backup_20260629.py, Platform/Putnam_OS/System/app/putnam_os_comp_ui_v1_2_0_backup_20260629.py, Platform/Putnam_OS/System/app/putnam_os_import_v1_backup_20260629_222132.py, Platform/Putnam_OS/System/app/putnam_os_inventory_location_foundation_backup_20260629_231122.py, Platform/Putnam_OS/System/app/putnam_os_listing_workflow_backup_20260629_214810.py, Platform/Putnam_OS/System/app/putnam_os_orders_v1_backup_20260629_220044.py, Platform/Putnam_Platform/capture/Putnam_Capture.py |
| ERROR | imports.sys_path_mutation | `Platform/Putnam_OS/Putnam_Seller_Tools/location_registry.py` | Yes | No | Phase 2-4 | not reviewed | Production source mutates sys.path. |
| ERROR | imports.sys_path_mutation | `Platform/Putnam_OS/Putnam_Seller_Tools/seller_audit/putnam_seller_audit_v1_0.py` | Yes | No | Phase 2-4 | not reviewed | Production source mutates sys.path. |
| ERROR | imports.sys_path_mutation | `Platform/Putnam_OS/Putnam_Seller_Tools/seller_audit/putnam_sku_repair_planner_v1_1.py` | Yes | No | Phase 2-4 | not reviewed | Production source mutates sys.path. |
| ERROR | imports.sys_path_mutation | `Platform/Putnam_OS/System/app/bulk_price_engine.py` | Yes | No | Phase 2-4 | not reviewed | Production source mutates sys.path. |
| ERROR | imports.sys_path_mutation | `Platform/Putnam_OS/System/app/capture_studio.py` | Yes | No | Phase 2-4 | not reviewed | Production source mutates sys.path. |
| ERROR | imports.sys_path_mutation | `Platform/Putnam_OS/System/app/orders_fulfillment.py` | Yes | No | Phase 2-4 | not reviewed | Production source mutates sys.path. |
| ERROR | imports.sys_path_mutation | `Platform/Putnam_OS/System/app/putnam_os.py` | Yes | No | Phase 2-4 | not reviewed | Production source mutates sys.path. |
| ERROR | python.syntax_unreadable | `Platform/Putnam_OS/Putnam_Seller_Tools/listing_optimizer/backups/putnam_os_related_exporter_original_20260627_093120.py` | Yes | Yes | active feature checkpoint | not reviewed | Python source cannot be parsed for architecture inspection. |
| ERROR | python.syntax_unreadable | `Platform/Putnam_OS/System/app/main.py` | Yes | Yes | active feature checkpoint | not reviewed | Python source cannot be parsed for architecture inspection. |
| ERROR | python.syntax_unreadable | `Platform/Putnam_OS/System/app/putnam_os_capture_v1_backup_20260629_212812.py` | Yes | Yes | active feature checkpoint | not reviewed | Python source cannot be parsed for architecture inspection. |
| ERROR | python.syntax_unreadable | `Platform/Putnam_OS/System/app/putnam_os_comp_engine_v1_1_backup_20260629.py` | Yes | Yes | active feature checkpoint | not reviewed | Python source cannot be parsed for architecture inspection. |
| ERROR | python.syntax_unreadable | `Platform/Putnam_OS/System/app/putnam_os_comp_ui_v1_2_0_backup_20260629.py` | Yes | Yes | active feature checkpoint | not reviewed | Python source cannot be parsed for architecture inspection. |
| ERROR | python.syntax_unreadable | `Platform/Putnam_OS/System/app/putnam_os_import_v1_backup_20260629_222132.py` | Yes | Yes | active feature checkpoint | not reviewed | Python source cannot be parsed for architecture inspection. |
| ERROR | python.syntax_unreadable | `Platform/Putnam_OS/System/app/putnam_os_inventory_location_foundation_backup_20260629_231122.py` | Yes | Yes | active feature checkpoint | not reviewed | Python source cannot be parsed for architecture inspection. |
| ERROR | python.syntax_unreadable | `Platform/Putnam_OS/System/app/putnam_os_listing_workflow_backup_20260629_214810.py` | Yes | Yes | active feature checkpoint | not reviewed | Python source cannot be parsed for architecture inspection. |
| ERROR | python.syntax_unreadable | `Platform/Putnam_OS/System/app/putnam_os_orders_v1_backup_20260629_220044.py` | Yes | Yes | active feature checkpoint | not reviewed | Python source cannot be parsed for architecture inspection. |
| ERROR | tracked.runtime_database | `Archive/Projects/Putnam_Pokemon_Lookup_Overlay_v0.9.3/backend/runtime/market_prices.sqlite` | Yes | No | Phase 10-11 | contextual archive exception candidate | Local runtime database is tracked outside an approved fixture path. |
| ERROR | tracked.runtime_database | `Archive/Projects/Putnam_Pokemon_Lookup_Overlay_v0.9.3/database/putnam_pokemon_cloud_ready.sqlite` | Yes | No | Phase 10-11 | contextual archive exception candidate | Local runtime database is tracked outside an approved fixture path. |
| WARNING | entry_points.multiple_launcher_targets | `<repository>` | Yes | No | Phase 3 and Phase 10 | not reviewed | Multiple launcher targets detected: /Platform/Putnam_OS/System/app/putnam_os.py <- Platform/Putnam_OS/Run CardVector OS Production.vbs, Platform/Putnam_OS/Run Putnam OS Production.vbs, Platform/Putnam_OS/Run Putnam OS.bat; /Platform/Putnam_Platform/capture/Putnam_Capture.py <- Platform/Putnam_Platform/tools/Run_Putnam_Capture.bat; /Putnam_Platform/capture/obs_capture_autocrop.py <- Platform/Putnam_Platform/tools/Run_OBS_AutoCrop.bat; /Users/JaredHill/OneDrive/PutnamCollectibles/Putnam_Platform/engines/Bulk_Price_Engine/app/bulk_price_engine.py <- Business/Inventory/Pricing_Revisions/Run Bulk Price Engine.bat; /Users/JaredHill/OneDrive/PutnamCollectibles/Putnam_Platform/engines/Market_Intelligence/app/market_validation.py <- Business/Inventory/Pricing_Revisions/Run Market Validation Prototype.bat; python run_marketplace_intelligence.py <- Platform/Marketplace_Intelligence/Run Marketplace Intelligence.bat |
| WARNING | files.forbidden_production_name | `Platform/Putnam_OS/Putnam_Seller_Tools/listing_optimizer/backups/putnam_listing_optimizer_v1_1_original_20260627_093234.py` | Yes | No | Phase 10 | not reviewed | Production filename matches a forbidden backup/version pattern. |
| WARNING | files.forbidden_production_name | `Platform/Putnam_OS/Putnam_Seller_Tools/listing_optimizer/backups/v1_2_pre_patch_20260628_094458/putnam_listing_optimizer_v1_1.py` | Yes | No | Phase 10 | not reviewed | Production filename matches a forbidden backup/version pattern. |
| WARNING | files.forbidden_production_name | `Platform/Putnam_OS/Putnam_Seller_Tools/listing_optimizer/putnam_listing_optimizer_v1_1.py` | Yes | No | Phase 10 | not reviewed | Production filename matches a forbidden backup/version pattern. |
| WARNING | files.forbidden_production_name | `Platform/Putnam_OS/Putnam_Seller_Tools/listing_optimizer/putnam_listing_optimizer_v1_2.py` | Yes | No | Phase 10 | not reviewed | Production filename matches a forbidden backup/version pattern. |
| WARNING | files.forbidden_production_name | `Platform/Putnam_OS/Putnam_Seller_Tools/seller_audit/putnam_seller_audit_v1_0.py` | Yes | No | Phase 10 | not reviewed | Production filename matches a forbidden backup/version pattern. |
| WARNING | files.forbidden_production_name | `Platform/Putnam_OS/Putnam_Seller_Tools/seller_audit/putnam_sku_repair_planner_v1_1.py` | Yes | No | Phase 10 | not reviewed | Production filename matches a forbidden backup/version pattern. |
| WARNING | files.forbidden_production_name | `Platform/Putnam_OS/Putnam_Seller_Tools/seller_audit/SKU_REPAIR_PLANNER_V1_1_1_CHANGE_SUMMARY.txt` | Yes | No | Phase 10 | not reviewed | Production filename matches a forbidden backup/version pattern. |
| WARNING | files.forbidden_production_name | `Platform/Putnam_OS/System/app/bulk_price_engine.py.before_ebay_patch_20260717_132121.bak` | Yes | No | Phase 10 | not reviewed | Production filename matches a forbidden backup/version pattern. |
| WARNING | files.forbidden_production_name | `Platform/Putnam_OS/System/app/main.py.before_ebay_patch_20260717_132121.bak` | Yes | No | Phase 10 | not reviewed | Production filename matches a forbidden backup/version pattern. |
| WARNING | files.forbidden_production_name | `Platform/Putnam_OS/System/app/putnam_os.py.before_active_listing_fix_20260717_135604.bak` | Yes | No | Phase 10 | not reviewed | Production filename matches a forbidden backup/version pattern. |
| WARNING | files.forbidden_production_name | `Platform/Putnam_OS/System/app/putnam_os_capture_v1_backup_20260629_212812.py` | Yes | No | Phase 10 | not reviewed | Production filename matches a forbidden backup/version pattern. |
| WARNING | files.forbidden_production_name | `Platform/Putnam_OS/System/app/putnam_os_comp_engine_v1_1_backup_20260629.py` | Yes | No | Phase 10 | not reviewed | Production filename matches a forbidden backup/version pattern. |
| WARNING | files.forbidden_production_name | `Platform/Putnam_OS/System/app/putnam_os_comp_ui_v1_2_0_backup_20260629.py` | Yes | No | Phase 10 | not reviewed | Production filename matches a forbidden backup/version pattern. |
| WARNING | files.forbidden_production_name | `Platform/Putnam_OS/System/app/putnam_os_import_v1_backup_20260629_222132.py` | Yes | No | Phase 10 | not reviewed | Production filename matches a forbidden backup/version pattern. |
| WARNING | files.forbidden_production_name | `Platform/Putnam_OS/System/app/putnam_os_inventory_location_foundation_backup_20260629_231122.py` | Yes | No | Phase 10 | not reviewed | Production filename matches a forbidden backup/version pattern. |
| WARNING | files.forbidden_production_name | `Platform/Putnam_OS/System/app/putnam_os_listing_workflow_backup_20260629_214810.py` | Yes | No | Phase 10 | not reviewed | Production filename matches a forbidden backup/version pattern. |
| WARNING | files.forbidden_production_name | `Platform/Putnam_OS/System/app/putnam_os_orders_v1_backup_20260629_220044.py` | Yes | No | Phase 10 | not reviewed | Production filename matches a forbidden backup/version pattern. |
| WARNING | tracked.temporary | `Archive/Historical/Putnam_OS_System_Archive/System_Archive/Patch_3_3_0_Platform_Session_Manager_20260627_004944/putnam_os.py.bak` | Yes | No | Phase 10-11 | contextual archive exception candidate | Temporary or backup artifact is tracked by Git. |
| WARNING | tracked.temporary | `Archive/Historical/Putnam_OS_System_Archive/System_Archive/Patch_3_3_0_Platform_Session_Manager_20260627_004944/Run Putnam OS.bat.bak` | Yes | No | Phase 10-11 | contextual archive exception candidate | Temporary or backup artifact is tracked by Git. |
| WARNING | tracked.temporary | `Archive/Historical/Putnam_OS_System_Archive/System_Archive/Patch_3_3_0_Platform_Session_Manager_20260627_004944/VERSION.bak` | Yes | No | Phase 10-11 | contextual archive exception candidate | Temporary or backup artifact is tracked by Git. |
| WARNING | tracked.temporary | `Archive/Historical/Putnam_OS_System_Archive/System_Archive/Patch_3_3_5_Location_Management_20260628_140109/putnam_os.py.bak` | Yes | No | Phase 10-11 | contextual archive exception candidate | Temporary or backup artifact is tracked by Git. |
| WARNING | tracked.temporary | `Archive/Historical/Putnam_OS_System_Archive/System_Archive/Patch_3_3_5_Location_Management_20260628_140109/putnam_seller_audit_v1_0.py.bak` | Yes | No | Phase 10-11 | contextual archive exception candidate | Temporary or backup artifact is tracked by Git. |
| WARNING | tracked.temporary | `Archive/Historical/Putnam_OS_System_Archive/System_Archive/Patch_3_3_5_Location_Management_20260628_140109/putnam_sku_repair_planner_v1_1.py.bak` | Yes | No | Phase 10-11 | contextual archive exception candidate | Temporary or backup artifact is tracked by Git. |
| WARNING | tracked.temporary | `Archive/Historical/Putnam_OS_System_Archive/System_Archive/Patch_3_3_6_Inventory_Audit_Mode_20260628_234112/CHANGELOG.md.bak` | Yes | No | Phase 10-11 | contextual archive exception candidate | Temporary or backup artifact is tracked by Git. |
| WARNING | tracked.temporary | `Archive/Historical/Putnam_OS_System_Archive/System_Archive/Patch_3_3_6_Inventory_Audit_Mode_20260628_234112/PROJECT_STATUS.md.bak` | Yes | No | Phase 10-11 | contextual archive exception candidate | Temporary or backup artifact is tracked by Git. |
| WARNING | tracked.temporary | `Archive/Historical/Putnam_OS_System_Archive/System_Archive/Patch_3_3_6_Inventory_Audit_Mode_20260628_234112/putnam_os.py.bak` | Yes | No | Phase 10-11 | contextual archive exception candidate | Temporary or backup artifact is tracked by Git. |
| WARNING | tracked.temporary | `Archive/Historical/Putnam_OS_System_Archive/System_Archive/patch_prep_20260626_223837/putnam_os.py.bak` | Yes | No | Phase 10-11 | contextual archive exception candidate | Temporary or backup artifact is tracked by Git. |
| WARNING | tracked.temporary | `Archive/Historical/Putnam_OS_System_Archive/System_Archive/patch_prep_20260626_223837/Run Putnam OS.bat.bak` | Yes | No | Phase 10-11 | contextual archive exception candidate | Temporary or backup artifact is tracked by Git. |

## Checker Errors

None.
