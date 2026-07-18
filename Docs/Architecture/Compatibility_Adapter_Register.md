# CardVector Compatibility Adapter Register

Entries are planned until implementation creates and tests the adapter. Adapters
must forward to the canonical owner and must not contain independent business
logic.

| Adapter | Legacy interface | Canonical target | Reason | Tests | Warning behavior | Owner | Creation phase | Removal condition | Target removal phase |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CV-COMP-001 | `Platform.putnam_paths` | Future `cardvector.infrastructure.paths` | Preserve path callers during path-service migration | Caller and path parity tests required | None until migration | Infrastructure | Planned Phase 2-4 | All imports use canonical path service | Phase 10-11 |
| CV-COMP-002 | `Platform/Putnam_OS/System/MarketIntelligence/Pricing` | `Platform/Marketplace_Intelligence` | Preserve Putnam OS pricing interfaces | Pricing fixture parity tests | Deprecation warning only after caller plan | Marketplace Intelligence | In progress/planned | All callers use canonical engine | Phase 5 |
| CV-COMP-003 | `Platform/Putnam_OS/System/app/bulk_price_engine.py` | `Platform/Marketplace_Intelligence` | Preserve bulk pricing entry surface | Bulk pricing smoke and parity tests | None in Phase 1 | Marketplace Intelligence | Planned | Callers migrated | Phase 5 |
| CV-COMP-004 | Pricing/export functions in `putnam_os.py` | Marketplace Intelligence and Listings services | Incremental monolith extraction | Characterization and UI callback tests | None until extraction | Application | Planned | UI invokes application services only | Phase 8-9 |
| CV-COMP-005 | `Platform/Putnam_OS/System/app/main.py` | Future official bootstrap and desktop shell | Retain callers while second application is retired | Caller inventory and parity suite | Runtime warning only after owner approval | Compatibility | Planned | Register removal criteria in deprecation record | Phase 10-11 |
| CV-COMP-006 | Capture/OBS interfaces used by desktop UI | Future `cardvector.capture` | Preserve validated capture workflow | Capture smoke tests | None | Capture | Planned | All callers use capture service | Phase 6 |
| CV-COMP-007 | `inventory_locations.py` public interfaces | Future `cardvector.inventory` | Preserve inventory registry callers | Registry and persistence tests | None | Inventory | Planned | All callers use canonical inventory service | Phase 7 |
| CV-COMP-008 | Orders fulfillment UI/service interfaces | Future `cardvector.orders` | Preserve order workflow | Orders fixture tests | None | Orders | Planned | All callers migrated | Phase 7-9 |
| CV-COMP-009 | `mobile_capture_queue.py` CLI | Future capture application service | Preserve operational command | Queue contract and routing tests | None | Capture | Planned | Launcher and automation use canonical CLI | Phase 6 |
| CV-COMP-010 | Listing Optimizer interfaces | Marketplace Intelligence and Listings | Preserve listing workflow during owner split | Existing optimizer tests plus adapters | None | Marketplace Intelligence/Listings | Planned | Pricing and record ownership separated | Phase 5 |
| CV-COMP-011 | Existing launcher aliases | Official production launcher | Avoid operator disruption | Launcher target smoke tests | Clear deprecation message after approval | Bootstrap | Planned | Operator migration complete | Phase 10 |
