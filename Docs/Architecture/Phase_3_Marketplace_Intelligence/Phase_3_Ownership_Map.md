# Phase 3 Ownership Map

| Responsibility | Canonical public owner | Proven implementation retained | Phase 3 status |
| --- | --- | --- | --- |
| Pricing contracts | `Platform/cardvector/marketplace_intelligence/models.py` | historical `models.py` | Aliased; no duplicate dataclasses |
| FMV | `Platform/cardvector/marketplace_intelligence/pricing.py` | historical `pricing_engine.py` | Canonical facade active |
| Price Vector | `Platform/cardvector/marketplace_intelligence/pricing.py` | historical `pricing_engine.py` | Canonical facade active |
| Pricing service | `Platform/cardvector/marketplace_intelligence/service.py` | proven functions | Active delegating service |
| Putnam comparable interpretation | `Platform/cardvector/marketplace_intelligence/evidence.py` | formerly in `putnam_os.py` | Extracted as pure logic |
| Stored provider normalization | `Platform/cardvector/marketplace_intelligence/adapters` | historical `providers.py` | Aliased for compatibility |
| Pricing persistence | `Platform/cardvector/marketplace_intelligence/persistence.py` | historical repository/migration | Aliased; behavior unchanged |
| Pricing orchestration | `Platform/cardvector/application/pricing.py` | none | Injected application facade |
| CSV/report rendering | historical Marketplace Intelligence reports and Putnam workflows | current modules | Retained; no schema change |
| Live CardUploader sales fetch | current Putnam OS integration boundary | `fetch_carduploader_sales()` | Retained outside core pricing |
| eBay listing files and policy columns | Listings/Putnam workflow modules | current modules | Not migrated |
| Legacy desktop entry | `main.py` compatibility | current file | Retained |

## Explicit Non-Owners

- `putnam_os.py` no longer owns comparable matching, evidence confidence, or
  pricing calculation.
- `main.py` and `bulk_price_engine.py` are callers, not pricing owners.
- Tkinter UI, live browser actions, capture, inventory, orders, shipping, and
  listing publication remain outside Marketplace Intelligence.

## Deferred

The historical package paths remain the physical proven implementation until a
separately approved relocation phase. Their continued presence is a registered
compatibility condition, not permission for new callers to use them.
