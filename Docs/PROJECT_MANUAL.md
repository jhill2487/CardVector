
# PROJECT_MANUAL.md

**Project:** CardVector  
**Version:** 1.0  
**Status:** Canonical

---

# 1. Purpose

CardVector is the operating system for Putnam Collectibles.

Its purpose is to provide a stable, efficient platform for managing acquisition, inventory, fulfillment, reporting, and future business operations.

The platform is designed around real production workflows rather than theoretical software practices.

---

# 2. Core Philosophy

The following principles govern every architectural decision.

## Business First
Business value takes precedence over technical novelty.

## Production First
Production workflows provide the highest level of validation.

## Simplicity First
When multiple solutions satisfy the business need, prefer the simpler one.

## Stability
Operators should build long-term confidence and muscle memory.

## Repository First
The repository is the authoritative memory of CardVector.

## Continuous Improvement
Improve through small, validated changes rather than large rewrites.

---

# 3. Inventory Architecture

## Inventory Model

CardVector answers one operational question:

**Where is the card?**

The authoritative physical reference is:

**ETB + Location**

Cards are identified by:

- Name
- Set
- Collector Number
- Variant
- Condition

CardVector does not assign operational inventory IDs to individual cards.

Permanent identities belong to physical objects:

- ETBs
- ETB Locations
- Shelves
- Totes
- Order Bins
- Acquisition Lots

## Physical Storage

Hierarchy:

Shelf (optional)
→ ETB
→ Location
→ Card

Operational standard:

- 10 Locations (A–J) per ETB
- 40 cards per Location
- 400 cards per ETB

These are operating standards, not architectural limits.

Container identities remain permanent.
Only occupancy changes.

## Inventory Conversion

Inventory Conversion establishes the authoritative physical location of existing inventory.

Standard workflow:

1. Select ETB
2. Select Location
3. Capture inventory
4. Complete Location
5. Continue

The ETB Registry records occupancy, capacity, active location and completion status.

---

# 4. Operational Workflows

## Acquisition

An acquisition is a purchasing event rather than a storage location.

Acquisition supports:

- Cost tracking
- ROI
- Profitability
- Inventory aging
- Business reporting

Cards become operational inventory only after assignment to an ETB and Location.

## Fulfillment

CardVector's responsibility is physical inventory.

CardVector manages:

- Physical location
- ETB occupancy
- Location occupancy
- Pick accuracy

Marketplace platforms remain responsible for:

- Listings
- Orders
- Payments
- Shipping
- Tracking

When a location reaches zero cards it becomes available for reuse.

## Marketplace Integration

Marketplace data is imported and reconciled conservatively.

CardVector remains the authority for physical inventory.

---

# 5. Platform Architecture

## Shared Operational Data

Business data is shared independently from source code.

Current synchronization platform:

- OneDrive

Examples:

- Inventory database
- ETB registry
- Product images
- Acquisition records
- Marketplace imports

## Runtime vs Source Data

Git stores:

- Source code
- Documentation
- Templates

Operational business data is synchronized separately.

Temporary runtime data remains workstation specific.

## Data Ownership

Every category of data has a single authoritative owner.

## Data Integrity

Accuracy is preferred over speed.

Conflicts should be presented for operator review.

## Data Migration

Business data should survive platform evolution through safe migration paths.

---

# 6. User Experience

CardVector is professional business software.

Design goals:

- Minimal clicks
- Stable layouts
- Predictable workflows
- Clear terminology
- Fast operation

Routine screens should maximize workspace rather than instructional text.

CardVector is a tool, not a tutorial.

## User Interface Stability

A stable interface is considered a feature.

Layouts should change only when they provide measurable operational benefit.

## Mobile & QR

QR codes identify physical objects.

Mobile extends CardVector OS into the physical workspace.

---

# 7. Engineering Standards

Development sequence:

1. Define the objective.
2. Review existing architecture.
3. Implement the smallest practical change.
4. Validate using production workflows.
5. Commit.
6. Push when appropriate.

## Testing

Production validation is the highest level of confidence.

Testing should identify:

- Bugs
- Workflow friction
- Unnecessary clicks
- Operator confusion
- Performance issues

## Versioning

CardVector follows a production-first release philosophy.

The production system is the primary working system.

## Change Management

Changes should:

- Improve business operations
- Reduce operator effort
- Preserve workflows
- Respect frozen architectural decisions

---

# 8. Infrastructure

Deployment goals:

- Git for source code
- OneDrive for shared operational data
- Portable configuration
- Modular hardware
- Vendor independence
- Business continuity

Core business operations should continue even if external services are temporarily unavailable.

## Public Website Deployment

CardVector public website source is maintained only in the private authoritative repository under `Docs/`.

The public `jhill2487/CardVector-site` repository is deployment output for GitHub Pages and serves `cardvector.app`. It must contain only the approved static artifact generated from `CardVector/Docs`.

Manual website source edits belong in `CardVector/Docs`, not in `CardVector-site`.

---

# 9. Automation & Reporting

Automation exists to reduce repetitive work while preserving operator control.

Low-confidence situations require operator review.

Reporting is read-only and exists to improve business decisions without complicating production workflows.

---

# 10. Platform Evolution

CardVector is intended to mature into a stable operating system.

Once the platform reaches production maturity, architectural evolution should largely stop.

Future work should primarily consist of:

- Bug fixes
- Workflow improvements
- Marketplace updates
- Hardware support
- Operator-requested quality-of-life improvements

---

# 11. Long-Term Vision

CardVector should become trusted infrastructure for Putnam Collectibles.

Success is measured by:

- Accurate inventory
- Efficient fulfillment
- Stable workflows
- Reduced operator effort
- Business continuity
- Long-term maintainability

The goal is a platform that operators trust every day without needing to think about the software itself.
