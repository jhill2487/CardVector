# Fulfillment Profiles

## Purpose

Fulfillment profiles define packaging-cost assumptions for future Putnam OS
Profit per Envelope reporting.

This file is the historical source for the initial packaging assumptions.
Phase 8 copied the approved values into the canonical Marketplace Intelligence
Business Profile. `Data/Config/fulfillment_profiles.json` is now a read-only
compatibility reference and is not a second live configuration source.

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

Status: Historical reference.

Live business-aware pricing reads:

```text
Platform/Marketplace_Intelligence/config/business_profile.json
```
