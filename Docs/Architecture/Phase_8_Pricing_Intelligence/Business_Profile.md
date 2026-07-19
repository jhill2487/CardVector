# Canonical Business Profile

## Source

```text
Platform/Marketplace_Intelligence/config/business_profile.json
```

`BusinessProfile` in
`Platform/cardvector/marketplace_intelligence/business_profile.py` normalizes
the JSON into immutable Decimal-based pricing contracts.

## Sections

- General: business name, currency, tax placeholder, seller preferences
- Acquisition: `$0.05` default and card/batch/supplier/default precedence
- Packaging: named component costs and calculated profile total
- Shipping: eBay Standard Envelope 1, 2, and 3 ounce profiles
- Marketplace: eBay, TCGplayer, and inactive future placeholders
- Pricing policy: minimum price, minimum profit, margin, other costs,
  rounding, default marketplace, and existing Price Vector policy

## Packaging Calculation

The Standard Envelope profile totals its configured components:

```text
team bag              $0.03
envelope              $0.03
shipping label        $0.02
shipping shield       $0.07
configured zero-cost components
----------------------------
total                  $0.15
```

Penny sleeve, top loader, semi-rigid, tape, and other supplies are explicit
keys even where the current cost is unverified or represented by the shipping
shield line. Updating their cost requires changing only the Business Profile.

## Marketplace Profiles

eBay and TCGplayer are active. Whatnot and direct website are inactive
placeholders. Each active profile defines fee tiers, processing, fixed order
fees, rounding, packaging, and shipping assumptions.

The eBay profile uses the conservative trading-card fee default because the
exact Store subscription tier has not been verified in repository evidence.
That value is configurable and should be reconciled against actual eBay
statements.

For eBay Standard Envelope, an explicit `Shipping Profile` value or
`Shipping Weight Oz` value on a listing selects the matching enabled profile.
Without either value, the marketplace's configured one-ounce default applies.
The engine reads the profile cost and never embeds postage constants.

## Backward Compatibility

The old flat `pricing_profile.json` is loaded only when a nested canonical
profile is absent. Existing flat-profile test and script callers keep their
prior recommendation values. The desktop Pricing Settings action now saves the
nested `pricing_policy.price_vector` object in the canonical profile.
