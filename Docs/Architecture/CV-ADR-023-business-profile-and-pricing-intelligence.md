# CV-ADR-023 - Canonical Business Profile And Business-Aware Pricing

## Status

Accepted

## Date

2026-07-19

## Owner

Putnam Collectibles

## Context

Marketplace Intelligence already owns FMV and Price Vector. The repository also
contains two business-profile JSON files, a flat Marketplace Intelligence
pricing profile, a packaging-cost foundation, eBay policy names, and a
historical Business Intelligence script with hard-coded shipping costs. None
was a complete business-pricing authority.

## Decision

`Platform/Marketplace_Intelligence/config/business_profile.json` is the single
canonical Business Profile for pricing. Typed contracts and business-rule
calculation live under:

```text
Platform/cardvector/marketplace_intelligence/
```

Marketplace Intelligence determines FMV. The canonical Business Rules Engine
then applies acquisition, packaging, shipping, marketplace fees, minimum-price,
and profit policy before a recommendation is finalized.

## Evidence

- `Platform/Marketplace_Intelligence/config/business_profile.json`
- `Platform/Marketplace_Intelligence/config/pricing_profile.json`
- `Platform/Putnam_OS/System/config/business_profile.json`
- `Data/Config/fulfillment_profiles.json`
- `Platform/Marketplace_Intelligence/business_intelligence/business_intelligence_v0_1.py`
- `Docs/PriceVector/current_code_audit.md`
- eBay Standard Envelope announcement effective 2026-07-12
- eBay and TCGplayer published fee pages recorded in profile metadata

## Alternatives Considered

- Create a separate Business Intelligence package and configuration.
- Make the Putnam OS profile canonical.
- Continue hard-coded fee and shipping constants.
- Keep `pricing_profile.json` as an independently writable source.

## Consequences

- Existing Marketplace Intelligence profile data is extended, not duplicated.
- `pricing_profile.json` remains a read-only compatibility fallback.
- The existing pricing settings UI writes the canonical Business Profile.
- Existing flat-profile callers retain their old outputs through a tested
  compatibility mode.
- New and existing inventory use the same pipeline and business-rule stage.
- Shipping values in this profile are pricing estimates. Fulfillment execution
  remains outside Marketplace Intelligence.

## Dependency Impact

The application layer may call Marketplace Intelligence. Marketplace
Intelligence does not depend on CardUploader inventory persistence, Tkinter,
live marketplace mutation, or shipping fulfillment.

## Migration Impact

Phase 8 adds typed profile and business-rule contracts, additive report fields,
and additive SQLite pricing-decision columns. It does not alter launcher,
inventory, capture, recognition, batch, listing publication, or live
marketplace behavior.

## Compatibility Impact

`CV-COMP-018` retains the flat pricing profile as fallback input.
`CV-COMP-019` records older Putnam OS and fulfillment profile files as
noncanonical references until their callers are retired or migrated.

## Testing Requirements

- Profile parsing and canonical-save tests
- Fee, shipping, packaging, acquisition, minimum-price, and profit tests
- Existing/new inventory pipeline equivalence
- Report and persistence round-trip tests
- Existing Price Vector and Phase 7 regression tests

## Rollback Plan

Revert the Phase 8 commits. Existing migration columns are additive and may
remain unused. Restore the prior Business Profile from Git. Do not delete
pricing records or production data during rollback.

## Approval

Approved by the project owner through the Phase 8 authorization.

## Supersedes

The assumption that the flat Marketplace Intelligence pricing profile or
Putnam OS business profile could independently define pricing economics.

## Superseded By

None.
