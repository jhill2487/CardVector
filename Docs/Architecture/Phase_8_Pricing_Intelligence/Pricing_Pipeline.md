# Unified Pricing Pipeline

## Stages

```text
Card or listing
  -> identity validation
  -> variant resolution
  -> comparable discovery/filtering
  -> normalized market evidence
  -> Fair Market Value
  -> existing Price Vector market recommendation
  -> Business Rules Engine
  -> final recommendation and profitability
  -> review/export/persistence
```

Marketplace Intelligence owns both pricing stages while preserving their
separation:

1. Market Intelligence determines evidence and FMV.
2. Business Intelligence decides what Putnam Collectibles should charge.

## Existing Inventory

`ExistingListingRequest` becomes a normalized Listing, then follows the same
`PricingPipeline.analyze_listing()` path. Its result includes current price,
FMV, final recommendation, delta, confidence, reason codes, and profitability.

## New Inventory

CardUploader CSV import creates the same Listing contract. Card-level
acquisition cost is used when supplied; otherwise the `$0.05` Business Profile
default applies. The Putnam OS eBay export adapter supplies that Listing and
the canonical Business Profile to the Application pricing service, so it
receives the same business-rules calculation without owning pricing logic.
CardUploader remains inventory owner.

## Compatibility

Flat legacy profiles still enter the same Business Rules Engine, but the engine
recognizes their registered compatibility mode and preserves prior outputs.
Canonical production configuration always enables business rules.
