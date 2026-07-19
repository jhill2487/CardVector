# Business Rules Engine

## Responsibility

`BusinessRulesEngine` applies Putnam Collectibles economics to a Price Vector
recommendation. It never calculates FMV and never reads raw market evidence.

## Inputs

- Listing and marketplace context
- Explicit Fair Market Value
- Existing Price Vector recommendation
- Canonical Business Profile
- Optional card-level acquisition cost

## Calculation

```text
Estimated net profit =
  final listing price
  - marketplace fees
  - seller-paid shipping
  - packaging
  - acquisition cost
  - other configured costs
```

Minimum Viable Price is the lowest cent-rounded price satisfying:

```text
net profit >= configured minimum profit
and
net profit / listing price >= configured minimum margin
and
listing price >= configured minimum listing price
```

The calculation accounts for marketplace percentage fees, fixed-order fees,
fee thresholds, fee caps, shipping thresholds, and rounding.

## Output

Each business-aware recommendation exposes:

- Estimated fees
- Estimated shipping
- Estimated packaging
- Acquisition cost
- Other costs
- Estimated net profit
- Profit margin
- Minimum viable price
- Shipping profile
- Free-shipping decision
- Business-rule adjustments
- Business recommendation state

States are:

- Increase Price
- Decrease Price
- No Change
- Manual Review
- Do Not List

Existing Price Vector review decisions remain authoritative. Business rules do
not silently auto-approve a recommendation that previously required review.

## Safety

- Missing FMV stays Manual Review.
- Missing FMV cannot bypass the configured business floor.
- Inactive or unknown marketplaces stay Manual Review.
- Final price cannot fall below Minimum Viable Price.
- All math uses `Decimal`.
- No HTTP, UI, inventory write, or marketplace write occurs.
