# Phase 3 Caller Migration Map

| Caller | Old target | New target | Contract result |
| --- | --- | --- | --- |
| `putnam_os.py` pricing helpers | historical `pricing_engine` module | `PricingApplication` -> `PricingService` -> canonical `pricing` | Exact |
| `putnam_os.py` export decisions | historical `build_pricing_decision` | injected application pricing service | Exact |
| `putnam_os.py` comparable helpers | local formulas | canonical `evidence` wrappers | Exact |
| `putnam_os.py` `market_analyze` | local loop/calculation | canonical `analyze_sales_rows` with existing fetch/parser callbacks | Exact |
| Phase 2 runtime | workflow service only | adds registered `pricing` application service | Existing workflow service unchanged |
| `bulk_price_engine.py` | historical pricing path | canonical `pricing` facade | Exact |
| `main.py` | historical pricing path | canonical `pricing` facade | Exact |
| Putnam pricing adapter | historical pricing path | canonical `pricing` facade | Exact |
| Putnam pricing model adapter | historical model path | canonical `models` facade | Identity-equal |
| historical MI engine | local pricing import | canonical pricing when repository package is available | Exact |
| historical direct launcher | local pricing import | documented fallback when `Platform` package is unavailable | Exact |

## Contracts Preserved

- input arguments and defaults
- dataclass output types
- errors
- logging and console lines
- persistence fields
- CSV/report fields and filenames
- eBay policy behavior
- progress callbacks

No caller was removed. No production launcher target changed.
