# Phase 3 Output Equivalence

## Result

**PASS: no pricing, FMV, confidence, persistence, serialization, status, or
error-category difference was detected.**

| Fixture | Previous output | Canonical output | Difference |
| --- | --- | --- | --- |
| No market report | unavailable FMV; original final price | same | none |
| One comparable | unavailable FMV | same | none |
| Weighted report | FMV/recommended/final `5.10` | same | none |
| Missing last-three | FMV `4.86` | same | none |
| Confidence 59 | manual review; final `3.99` | same | none |
| Confidence 80 | auto applied; final `5.10` | same | none |
| Active TCGplayer evidence | excluded from FMV | same | none |
| PriceCharting raw value | excluded from raw FMV | same | none |
| eBay sold summary | accepted FMV | same | none |
| Low-price boundaries | exact seven-case mapping | same | none |
| Bulk partial failure | unchanged/changed/invalid categories | same | none |
| Provider comparable cases | accepted/graded/name/number results | same | none |
| Putnam market analysis | report/rejection/analytics records | same | none |
| Persistence round trip | all distinct pricing fields | same | none |
| Report serialization | exact fields and values | same | none |

## Evidence

- 53 focused characterization, canonical API, FMV, and consolidation tests
- standalone Marketplace Intelligence fixture smoke test
- Putnam pricing compatibility smoke test
- desktop workflow contract tests

The canonical model and persistence APIs use identity-equal aliases to the
proven dataclasses and repository. No conversion layer can alter values.
