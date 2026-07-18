# Phase 5 Order-Picking Boundary

CardUploader owns inventory-side allocation, reservation, and pick state.
Orders remain responsible for order lifecycle.

The repository's current `orders_fulfillment.py` only:

- reads an order CSV,
- groups lines in source order,
- copies SKU/location text into static TXT/HTML pick slips,
- writes a summary CSV.

It does not reserve, allocate, decrement, confirm, cancel, or synchronize
inventory. Phase 5 preserves that behavior and does not misrepresent it as
CardUploader pick-state integration.
