# Phase 5 Data Equivalence

Characterization and contract fixtures require exact equivalence for:

- provider ID and source provenance,
- title and card identity fields,
- User SKU/location source reference,
- Catalog and TCGplayer identifiers,
- quantity, price, and status,
- source-row hash,
- reconciliation status/confidence/quantity mismatch,
- ETB capacity, stored count, and completion status,
- pick-slip order and location text,
- serialized canonical values.

The focused suite passed all 12 tests. It includes a read-only parse of the
tracked 308-row CardUploader export and confirms that its blank `User SKU`
values remain blank rather than becoming invented CardVector locations.
Unsupported available/reserved/sold,
allocation, reservation, pick-state, and live-sync behavior has no prior
CardVector implementation and therefore was not fabricated.
