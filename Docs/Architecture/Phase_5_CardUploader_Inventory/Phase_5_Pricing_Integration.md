# Phase 5 Pricing Integration

Marketplace Intelligence remains the canonical pricing owner.

| Value | Owner | Persistence |
| --- | --- | --- |
| CardUploader current/source price | CardUploader snapshot | CardUploader/export projection |
| FMV | Marketplace Intelligence | Phase 3 pricing record |
| Recommended listing price | Marketplace Intelligence | Phase 3 pricing record |
| Final listing price | Approved listing workflow | Phase 3/listing handoff |
| Inventory quantity/location/status | CardUploader | CardUploader |

CardVector may request inventory snapshot data through `InventoryApplication`
and send price evidence to Marketplace Intelligence. Pricing does not transfer
inventory ownership. Phase 5 changes no formulas, thresholds, persistence
fields, or exports.
