# Phase 5 Storage Adapter Map

| Storage | Data | Access | Phase 5 action |
| --- | --- | --- | --- |
| CardUploader CSV export | Inventory identity, SKUs, card fields, Qty, status, price | Read-only parser | Canonical integration |
| `Data/Exports/carduploader_inventory_snapshot.csv` | Local latest-export projection | File read/write by legacy import | Preserved; not inventory authority |
| ETB registry JSON | A-J capacity and conversion state | Legacy read/write | Compatibility projection |
| Supabase `cardvector_etbs` / `cardvector_locations` | Mobile Capture location identities | Authenticated reads, restricted RPC/service sync | Preserved; not managed inventory |
| Inventory audit JSON/CSV | Review session and evidence | Legacy read/write | Preserved runtime workflow |
| Reconciliation CSV/JSON | CardUploader/eBay comparison report | Generated output | Preserved |
| SQLite | No active managed-inventory schema found | None | No migration |

No schema, database path, transaction behavior, or production data changed.
