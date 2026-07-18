# Phase 5 Compatibility Map

- `CV-COMP-007`: `inventory_locations.py` and Supabase ETB/location projection
  remain active until a supported CardUploader location API exists.
- `CV-COMP-016`: legacy `CardUploaderInventorySource` delegates snapshot parsing
  to the canonical CardUploader service.
- Putnam OS public inventory helper names remain wrappers over
  `InventoryApplication`.
- The older Seller Tools `ETB-##-Letter` registry remains untouched and is not
  canonical.

No compatibility interface was deprecated or removed.
