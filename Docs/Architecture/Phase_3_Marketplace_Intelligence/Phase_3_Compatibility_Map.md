# Phase 3 Compatibility Map

## Active Adapters

| ID | Legacy surface | Canonical target | Phase 3 behavior |
| --- | --- | --- | --- |
| CV-COMP-002 | Putnam `MarketIntelligence/Pricing` package | canonical Marketplace Intelligence | Forwarding imports/functions |
| CV-COMP-003 | `bulk_price_engine.py` | canonical pricing facade | Existing CSV/files retained; math delegated |
| CV-COMP-004 | pricing helpers in `putnam_os.py` | application pricing facade | Public helper names retained |
| CV-COMP-005 | `main.py` | canonical pricing facade | Entry behavior retained |
| CV-COMP-010 | Listing Optimizer | canonical pricing plus future Listings | Deferred; no unsafe direct-script rewrite |
| CV-COMP-013 | historical Marketplace Intelligence implementation paths | canonical Marketplace Intelligence API | Proven classes/functions aliased |
| CV-COMP-014 | direct Marketplace Intelligence launcher mode | canonical package | Uses historical pricing import only when repository package path is unavailable |

## Direct-Launcher Exception

`MarketplaceIntelligenceEngine` imports the canonical pricing facade when
`Platform` is importable. Its historical direct launcher runs with only
`Platform/Marketplace_Intelligence` on `sys.path`; in that mode it falls back
to the same proven local function objects. This is a packaging compatibility
exception, not a second algorithm.

Removal condition: the standalone launcher must run through an installed or
repository-root canonical package, and its smoke test must continue to pass.

## Public Compatibility Preserved

- Putnam pricing function names
- `main.py` and bulk-engine entry functions
- legacy pricing/model imports
- Marketplace Intelligence UI/CLI imports
- pricing dataclass compatibility properties
- CSV/report schemas

No warnings were added because operator-facing deprecation has not been
approved.
