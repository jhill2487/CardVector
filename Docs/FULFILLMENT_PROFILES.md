# Fulfillment Profiles

## Purpose

Fulfillment profiles define packaging-cost assumptions for future Putnam OS
Profit per Envelope reporting.

This is a configuration foundation only. The profiles are not connected to live
pricing, export, shipping, or profit calculations yet.

## Config Location

```text
Data/Config/fulfillment_profiles.json
```

## Current Profiles

### Standard Envelope

- Shipping Shield: 0.07
- Thermal Labels 2x: 0.02
- Team Bag: 0.03
- Envelope: 0.03
- Total Packaging Cost: 0.15

### Ground Advantage

- Shipping Shield: 0.07
- Thermal Labels 2x: 0.02
- Team Bag: 0.03
- Bubble Mailer: 0.18
- Total Packaging Cost: 0.30

## Future Use

These profiles are intended for future Profit Dashboard and Profit per Envelope
reporting. They will allow Putnam OS to estimate packaging cost by fulfillment
method without hard-coding packaging assumptions into analytics code.

## Future Formula

```text
Revenue
+ Shipping Collected
- eBay Fees
- USPS Postage
- Packaging Cost
- Card Cost Basis
= Net Profit
```

## Current Status

Status: Backlog foundation.

No live business logic uses these profiles yet.
