# Phase 5 Inventory Source Of Truth

| Field | Authoritative owner | Current repository read path | Current write/sync evidence |
| --- | --- | --- | --- |
| Inventory identity | CardUploader | Export source ID, User SKU, Catalog SKU, TCGplayer SKU/product ID | Manual export only |
| SKU | CardUploader | CardUploader export columns | No CardVector write API |
| Quantity | CardUploader | `Qty` in export snapshot | No live sync |
| Available/reserved/sold quantity | CardUploader | Not represented in current export contract | Unsupported in CardVector |
| Card location | CardUploader | `User SKU` is retained as an optional source location reference | No supported live API; the tracked 308-row export currently leaves this field blank |
| Recognition result | CardUploader | Capture handoff and returned CSV | Manual handoff/export |
| Image association | CardUploader | Not represented in inventory export | Unsupported in current adapter |
| Allocation/reservation | CardUploader | No repository contract found | Unsupported in CardVector |
| Pick state | CardUploader | No repository contract found | Static CardVector pick slips do not mutate it |
| Fulfillment state | CardUploader/eBay by external workflow | No CardVector inventory contract | Out of Phase 5 |
| Pricing recommendation | Marketplace Intelligence | Canonical Phase 3 API | Separate from inventory truth |
| Listing reference | eBay | Reconciliation `Item number` | Read-only reports |

The CardVector ETB registry and Supabase location tables store capture/location
capacity and workflow state. They are not card-level inventory authority.
Conflicts are not automatically resolved because no supported CardUploader live
inventory/location API exists. The safe fallback is a read-only CardUploader
snapshot plus clearly labeled local projections.
