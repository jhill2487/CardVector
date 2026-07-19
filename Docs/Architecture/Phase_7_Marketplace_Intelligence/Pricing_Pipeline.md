# Canonical Pricing Pipeline

The canonical coordinator is
`Platform/cardvector/marketplace_intelligence/pipeline.py:PricingPipeline`.
It composes existing proven components; it does not duplicate their formulas.

| Stage | Owner | Current implementation | Output |
| --- | --- | --- | --- |
| Card input | CSV adapters or existing-listing request | historical `csv_import.py` or `ExistingListingRequest` | `Listing` |
| Identity validation | Marketplace Intelligence | `ListingMatcher.identify` | `ListingIdentity` |
| Variant resolution | Marketplace Intelligence | listing identity plus explicit variant/finish uncertainty | identity details and reason codes |
| Comparable discovery | Marketplace adapter | configured provider | provider candidates |
| Comparable filtering | Marketplace Intelligence evidence | canonical comparable diagnostics | accepted/rejected evidence |
| Market normalization | Marketplace adapter | `MarketPrice` and metadata | normalized source result |
| Outlier stage | Marketplace Intelligence | no removal in current production behavior | `outliers_removed=0` |
| Confidence | Marketplace adapter | current count/spread/identity formula | provider confidence |
| FMV | Marketplace Intelligence | explicit FMV adapter | `FairMarketValue` |
| Price Vector | Marketplace Intelligence | proven `PricingEngine` | `PriceRecommendation` |
| Review recommendation | Marketplace Intelligence | existing decision plus advisory explanation policy | `Decision` and `PricingExplanation` |
| Export | Marketplace Intelligence | existing reports and bulk export | backward-compatible CSV |

The historical `MarketplaceIntelligenceEngine` delegates its normal repository
execution path to `PricingPipeline`. Its direct-package fallback remains
temporarily available under `CV-COMP-014` until packaging makes canonical
imports available from every standalone invocation.

The pipeline performs no marketplace writes. It accepts injected matcher,
provider, Price Vector, decision, and clock dependencies, which makes fixture
and repeatability tests deterministic.
