# CardVector Platform Vision

Architecture Lock Effective: 2026-07-01

This document is the stable platform vision for CardVector. Roadmaps, screens,
and implementation details may change; the product family and ownership model
below are locked unless deliberately revised as a governance decision.

## Mission

Build the best operating platform for trading card businesses.

CardVector exists to make trading card operations faster, clearer, and more
repeatable without hiding the judgment that makes a good operator valuable.

## Core Products

```text
CardVector Platform
|
+-- CardVector Capture Studio
+-- CardVector Pricing Engine
+-- CardVector OS
+-- CardVector Mobile (future)
+-- CardVector Cloud (future)
```

## Architecture Lock

### Business

Putnam Collectibles is the production trading card business.

### Software Platform

CardVector is the software platform.

### Product Family

- CardVector Capture Studio: image acquisition.
- CardVector Pricing Engine: pricing, market validation, and listing recommendations.
- CardVector OS: workflow, inventory, analytics, and business operations.
- CardVector Mobile: future field companion.
- CardVector Cloud: future synchronization and web services.

### External Integration

CardUploader performs recognition and listing generation.

CardVector integrates with CardUploader rather than competing with it.

## Business Relationship

Putnam Collectibles is the production business that validates and drives
CardVector development.

Putnam Collectibles remains the operating business, seller identity, and source
of real-world workflow feedback. CardVector is the software platform created
from that production experience.

## Product Responsibilities

### CardVector Capture Studio

Captures images. It does not recognize cards or generate listings.

Responsibilities include OBS Studio integration, automatic capture, manual
capture, front/back pairing, session management, thumbnail review, future
mobile integration, future binder capture, and future export destinations.

### CardVector Pricing Engine

Handles pricing, market validation, and listing recommendations. It should
remain reusable outside CardVector OS.

It consumes normalized listings, not source-specific CSV formats.

### CardVector OS

Owns workflow, inventory, analytics, and business operations. It orchestrates
capture, import, pricing review, eBay CSV handoff, inventory, orders, shipping,
analytics, acquisitions, and business intelligence.

### CardUploader

CardUploader performs card recognition and listing generation. CardVector
integrates with best-of-breed external tools instead of rebuilding working
systems without a business reason.

## Guiding Principles

- Workflow first.
- Modular architecture.
- Reusable components outside CardVector OS.
- Single responsibility for every major subsystem.
- External best-of-breed integrations are acceptable and encouraged.
- Production feedback from Putnam Collectibles drives priorities.
- Business continuity matters more than architectural purity.

## Normalized Listing Pipeline

All listing CSV sources should flow through the same adapter pipeline:

```text
CSV Input
|
v
Source Detection
|
v
Column Mapping / Adapter Profile
|
v
Normalized Listing
|
v
Existing Pricing Engine
|
v
Reports / Recommendations
|
v
Source-appropriate export
```

Source-specific logic belongs in source detection, column mapping, and adapter
profiles. Pricing logic belongs in the existing CardVector Pricing Engine.
Exports should be appropriate to the originating source or destination without
forking the pricing engine.

## Locked Feature Design Questions

From 2026-07-01 forward, every proposed feature should answer:

1. Which CardVector product owns this?
2. Can it be implemented without duplicating another module's responsibility?
3. Does it strengthen the platform or blur responsibilities?

If the answer to question 2 is "it duplicates another module," redesign the
feature before implementing it.

## Governance

This vision is intended to remain stable. Roadmaps can change quickly; the
platform identity and product responsibilities should change rarely and
deliberately.
