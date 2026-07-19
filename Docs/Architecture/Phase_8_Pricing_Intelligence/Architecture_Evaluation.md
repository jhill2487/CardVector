# Phase 8 Architecture Evaluation

## Conclusion

A suitable canonical Business Profile already existed at:

```text
Platform/Marketplace_Intelligence/config/business_profile.json
```

Phase 8 extends it. No new configuration root or pricing engine is introduced.
The canonical owner remains
`Platform/cardvector/marketplace_intelligence`.

## Existing Implementations

| Path | Observed responsibility | Phase 8 disposition |
| --- | --- | --- |
| `Platform/Marketplace_Intelligence/config/business_profile.json` | Small seller identity and recommendation-label profile | Extended as canonical Business Profile |
| `Platform/Marketplace_Intelligence/config/pricing_profile.json` | Flat Price Vector settings written by the Marketplace Intelligence UI | Read-only legacy fallback through `CV-COMP-018` |
| `Platform/Putnam_OS/System/config/business_profile.json` | Legacy cash-flow, risk, minimum-profit, and default-marketplace values | Retained; not a pricing authority |
| `Platform/Putnam_OS/System/decision_engine/business_profile.py` | Loader for the legacy Putnam OS profile | Retained; no Phase 8 calculation ownership |
| `Data/Config/fulfillment_profiles.json` | Packaging-cost foundation for Standard Envelope and Ground Advantage | Historical source; canonical values now live in Business Profile |
| `Platform/Marketplace_Intelligence/business_intelligence/business_intelligence_v0_1.py` | Prototype analytics script with hard-coded packaging and postage | Not reused as an engine; evidence only |
| `Platform/Putnam_OS/System/config/ebay_business_policies.json` | eBay policy names and IDs | Remains listing/export configuration, not fee configuration |
| `Platform/Marketplace_Intelligence/config/pricing_profile.json` | Existing Price Vector limits, strategy, rounding, and review thresholds | Nested under canonical Business Profile without changing formulas |

## Overlap

The two business profiles overlap on marketplace and profit intent but have
incompatible schemas. The flat pricing profile overlaps the canonical profile's
pricing-policy responsibility. The fulfillment profile and prototype script
contain conflicting packaging estimates.

## Canonical Ownership Decision

- Business Profile: Marketplace Intelligence
- FMV: Marketplace Intelligence
- Price Vector market recommendation: Marketplace Intelligence
- Business Rules Engine and profitability estimate: Marketplace Intelligence
- Workflow coordination: CardVector Application
- Inventory truth: CardUploader
- Shipping fulfillment: future Shipping owner
- Listing publication: future Listings owner

Shipping profiles in Business Profile estimate pricing cost only. They do not
buy postage, choose fulfillment for an order, or mutate shipping policies.

## Evidence-Based Defaults

- Acquisition cost: `$0.05` per card, approved Phase 8 default
- Standard Envelope packaging: `$0.15`, from the repository foundation
- eBay Standard Envelope effective 2026-07-12:
  `$0.78`, `$1.07`, `$1.36`
- eBay trading-card fee default: conservative `13.25%` plus the documented
  per-order fee; the actual account tier remains configurable
- TCGplayer Level 1-4 default: `10.75%` commission plus `2.5% + $0.30`

Fee and postage defaults carry source URLs and dates in the profile and require
periodic operator review.

## Reuse

The existing `PricingEngine` retains Price Vector formulas. `PricingPipeline`
adds a mandatory business-rules stage after FMV and the existing market
recommendation. This is delegation and extension, not a second pricing engine.
