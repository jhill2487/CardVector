# Price Vector Implementation Gap Map

Audit baseline: `main` at
`0fe2475d4b72c9a3251cbed0d2bd4890b0ceec85`

Status vocabulary:

- **Existing**: requirement is represented and usable now.
- **Partially existing**: useful code/data exists but the approved contract is
  incomplete or not canonical.
- **Missing**: no implementation was found.
- **Blocked by external access**: implementation requires a provider,
  credential, license, or live data access that is not currently available.

## Business Profile

| Approved requirement | Status | Current evidence | Gap |
| --- | --- | --- | --- |
| Business name: Putnam Collectibles | Partially existing | Project documentation and Putnam OS branding use the name. `Platform/Marketplace_Intelligence/config/business_profile.json` says `Community Seller`. | Make the canonical pricing profile explicit. |
| Inventory ownership: 100% owned by Putnam Collectibles in v1 | Missing | No ownership field in pricing or inventory models. | Add a fixed v1 ownership policy field. |
| Active marketplaces: eBay and TCGplayer | Partially existing | eBay is the Putnam OS default; normalized listings retain TCGplayer IDs. | No explicit active-marketplace list or TCGplayer seller settings. |
| Inactive placeholders: Whatnot and direct website | Missing | Public site links exist, but no Price Vector marketplace activation profile exists. | Add inactive profile entries only; no integrations. |
| Pricing strategy: Competitive Turnover | Missing | Existing strategies are market match, undercut, hold band, fast sell, and profit. | Define Competitive Turnover in configuration and deterministic rules. |
| Acquisition cost is optional | Existing | Acquisition selection and purchase price are optional in Putnam OS. | Price Vector does not yet consume the value. |
| Acquisition method is supported | Partially existing | Acquisition JSON has general `source` and `platform`. | Add an explicit normalized method field. |
| Acquisition-cost confidence is supported | Missing | No confidence field found. | Add optional confidence enum/value to the input and output record. |

## Pricing Methodology

| Approved requirement | Status | Current evidence | Gap |
| --- | --- | --- | --- |
| Market Intelligence produces normalized market evidence | Partially existing | `MarketSnapshot`, `MarketPrice.metadata`, provider adapters, and cached comp rows exist. | No single normalized evidence schema with accepted/rejected reason, condition, date, source, and weight. |
| Market Intelligence produces Fair Market Value | Partially existing | Putnam OS `calculate_market_value()` creates a weighted value. | FMV is not a first-class object and the calculation is duplicated. |
| Price Vector consumes FMV rather than querying sources directly | Partially existing | The integrated Putnam OS calculator consumes a market report; standalone `PricingEngine` receives provider output. | Canonical engine needs an explicit FMV-only service method and a provider-call prohibition test. |
| Raw primary evidence: TCGplayer recent sales | Blocked by external access | No TCGplayer recent-sales provider exists. | Requires supported data/API access; excluded from Phase 1. |
| Raw primary evidence: condition-matched eBay sold listings | Partially existing | Cached CardUploader/eBay sold comps are filtered for identity and excluded terms. | Explicit condition equality is not enforced, and the source is cached rather than a supported live integration. |
| TCGplayer Market Price may be supporting evidence | Partially existing | TCGtracking local values can be reference-only. | This is not a verified TCGplayer Market Price field/source. Phase 1 can represent supporting evidence fixtures. |
| Active listings may be used for competition analysis | Partially existing | eBay active listings are normalized inputs; `MarketSnapshot.ebay_active` exists. | No competition-analysis provider or normalized competition metric exists. |
| PriceCharting must not be used for raw-card FMV | Existing | No PriceCharting provider, config, import, or reference was found. | Add a regression test when the FMV evidence contract is introduced. |
| Graded primary evidence: eBay sold listings | Partially existing | eBay sold-cache support exists, but graded terms are deliberately excluded from raw-card comps. | A graded evidence path is not implemented and is outside Phase 1. |
| Graded primary evidence: Card Ladder | Blocked by external access | No integration or stored data exists. | Requires external access; excluded from Phase 1. |
| Graded primary evidence: Alt | Blocked by external access | No integration or stored data exists. | Requires external access; excluded from Phase 1. |
| FMV and recommended listing price are separate | Partially existing | Integrated `PricingDecision` has `market_value` and `recommended_price`; standalone result has market and pricing objects. | No canonical `FairMarketValue` type or explicit original/final recommendation fields. |
| Every recommendation records evidence | Partially existing | Reports record provider, source, accepted/rejected counts, and some metadata. | No durable evidence list is attached to every recommendation. |
| Every recommendation records confidence | Existing | `MarketPrice`, `PricingDecision`, and reports retain confidence. | Confidence vocabulary is inconsistent: strings, integers, and letter grades. |
| Every recommendation records reasoning | Existing | Market, pricing, and decision reason fields are written to reports. | Standardize without removing existing explanatory detail. |

## Approval Rules

| Approved requirement | Status | Current evidence | Gap |
| --- | --- | --- | --- |
| Under $5 auto-approve unless confidence is very low | Missing | Current rules use global confidence or price/change thresholds. | Implement the approved price-tier matrix. |
| $5 through $20 auto-approve only when confidence is high | Missing | No combined price/confidence rule exists. | Implement exact inclusive boundaries. |
| Over $20 always requires manual review | Partially existing | Pricing JSON contains a `$20` high-review value, but active engines do not consistently enforce it; standalone default is `$100`. | Enforce centrally in Price Vector. |
| Over $20 triggers internal quality review | Missing | No internal quality-review flag exists. | Add a separate boolean/status. |
| Internal quality does not change marketplace condition | Existing | No current quality-review path mutates condition. | Add a regression test when quality review is introduced. |
| Grade Vector and grading ROI are not part of v1 | Existing | No Grade Vector or grading ROI implementation was found in pricing. | Preserve this exclusion. |

## Overrides

| Approved requirement | Status | Current evidence | Gap |
| --- | --- | --- | --- |
| Preserve original recommendation | Missing | Current report records recommended/final values in places, but there is no override contract. | Add immutable `original_recommended_price`. |
| Preserve final listing price | Partially existing | Export/review reports contain final export price. | Tie it to the same recommendation/override record. |
| Store optional override reason | Missing | No pricing override reason field. | Add nullable reason. |
| Store user and timestamp | Missing | No pricing override operator/timestamp fields. | Add both fields to the report record. |
| Do not automatically retrain from overrides | Existing | No learning/retraining path exists. | Add a regression test and explicit documentation. |

## Persistence And Workflow

| Supporting capability | Status | Current evidence | Gap |
| --- | --- | --- | --- |
| Pricing recommendation database | Missing | Pricing persists to JSON/CSV/TXT only. Supabase tables are capture/location only. | No database migration is needed for fixture-backed Phase 1; durable DB design remains future work. |
| Approval queue UI | Partially existing | Changed/review reports and Putnam OS report viewers exist. | No row-level Price Vector approve/override UI. |
| Manual override UI | Missing | No controls or persistence. | Defer UI until the deterministic service contract is tested. |
| Marketplace-specific recommendation | Partially existing | Listing source and eBay export are known; business profile has one default marketplace. | No eBay/TCGplayer recommendation context model. |
| Acquisition provenance in recommendation | Partially existing | Acquisition metadata is written beside Putnam OS jobs. | Not attached per normalized listing/recommendation. |

## Phase 1 Readiness

The repository can begin a fixture-backed Price Vector Phase 1 without live
provider access because it already has:

- A canonical normalized `Listing`.
- A reusable, configuration-driven `PricingEngine`.
- A separate `DecisionEngine`.
- Report serialization.
- Stored sample listings and market data.

Phase 1 is not blocked by TCGplayer, eBay, Card Ladder, or Alt access if FMV and
evidence are supplied by fixtures. Live market-source work must remain in Market
Intelligence and outside Price Vector Phase 1.
