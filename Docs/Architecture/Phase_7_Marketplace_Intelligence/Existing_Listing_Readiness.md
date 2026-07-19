# Existing Listing Review Readiness

## Read-Only Input

`ExistingListingRequest` accepts:

- marketplace
- listing title
- current price
- quantity
- SKU
- condition
- optional listing ID, set, collector number, variant, and finish

## Read-Only Output

`ExistingListingEvaluation` returns:

- matched card
- identity confidence
- recommended price
- price delta
- review priority
- review decision
- reason codes
- complete `PricingExplanation`

The call is available through `PricingPipeline`,
`PricingService.evaluate_existing_listing`, and
`PricingApplication.evaluate_existing_listing`.

It uses the same matcher, provider, FMV, Price Vector, decision, and explanation
stages as CSV analysis. It has no update, revise, publish, offer, reservation,
inventory-write, or browser-automation operation. Phase 8 may consume this
contract only after explicit approval.
