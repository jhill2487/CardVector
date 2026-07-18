# Phase 5 CardUploader Inventory API

Public imports are exposed from
`Platform.cardvector.integrations.carduploader`.

## Contracts

- `InventoryItem`: source identity, SKU references, card identity, quantity,
  price, status, location reference, provenance, and raw source row.
- `InventoryQuery`: text, status, TCG, and location filters.
- `InventoryResult`: provider, source file, items, columns, errors, timestamp.
- `InventoryCapabilities`: explicit supported/unsupported provider operations.
- `CardUploaderInventoryError` and
  `CardUploaderInventoryCapabilityUnavailable`.

## Service

`CardUploaderInventoryService` supports:

- `load_inventory(path)`
- `search_inventory(path, query)`
- `get_inventory_item(path, inventory_id)`
- exact export-column validation and normalization

It does not support authoritative writes, reservations, allocations, pick
confirmation, or live synchronization. `require_capability` fails explicitly
for those operations.
