# CardVector Platform Standards

These standards govern the architecture of the CardVector Platform. They are
intended to remain stable over time and apply across all platform applications,
including CardVector OS, CardVector Capture Studio, CardVector Pricing Engine,
Pokemon Lookup Overlay, Seller Tools, Legacy Scanner Research, and
future modules.

# Platform Mission

The CardVector Platform exists to support Putnam Collectibles.

Its purpose is not to create software for its own sake.

Its purpose is to reduce operational friction while preserving business
velocity.

Architecture should always support:

- cash flow
- listing velocity
- operational reliability
- maintainability

Never allow engineering complexity to become an operational bottleneck.

# Relationship to the Putnam Principles

These standards implement the Putnam Principles.

They define how the platform should be designed and maintained.

They should never conflict with the Principles.

# Architecture Lock

Effective 2026-07-01, the CardVector product ownership model is locked:

- Putnam Collectibles is the production trading card business.
- CardVector is the software platform.
- CardVector Capture Studio owns image acquisition.
- CardVector Pricing Engine owns pricing, market validation, and listing recommendations.
- CardVector OS owns workflow, inventory, analytics, and business operations.
- CardVector Mobile is the future field companion.
- CardVector Cloud is the future synchronization and web services layer.
- CardUploader owns recognition and listing generation as an external integration.

CardVector integrates with CardUploader rather than competing with it.

Every proposed feature must answer:

1. Which CardVector product owns this?
2. Can it be implemented without duplicating another module's responsibility?
3. Does it strengthen the platform or blur responsibilities?

If a proposed feature duplicates another module's responsibility, redesign it
before implementation.

# Platform Standard 1 - Automate Repetitive Work

If a task:

- is performed repeatedly,
- follows predictable steps,
- and does not require meaningful human judgment,

it should become a CardVector Platform tool.

Human effort should be reserved for decisions, not repetition.

# Platform Standard 2 - Build Once, Benefit Forever

Automation is prioritized when a one-time engineering effort saves time across
many future work sessions.

Favor solutions that continue returning value long after they are built.

# Platform Standard 3 - Environment-Aware Paths

All CardVector Platform applications must resolve repository paths through the
central Platform Path Manager.

Never hard-code:

- usernames
- drive letters
- machine-specific paths
- OneDrive locations

Applications should remain portable across development and production
environments.

# Platform Standard 4 - Clear Platform Responsibilities

CardVector OS is the workflow and business operations application.

It manages:

- inventory
- workflow
- shipping
- analytics
- daily operations

The CardVector Platform provides the supporting infrastructure:

- launchers
- shared libraries
- utilities
- backup tools
- automation scripts
- common services
- path management

Operations orchestration belongs in CardVector OS.

Shared infrastructure belongs in the Platform.

# Platform Standard 9 - Reusable Subsystems

Every major subsystem should be reusable outside CardVector OS whenever
practical.

Single responsibility is the default:

- CardVector Capture Studio captures images.
- CardVector Pricing Engine prices cards and prepares pricing decisions.
- CardVector OS orchestrates the workflow.
- CardUploader performs card recognition and listing generation.

Do not merge responsibilities simply because two modules are currently used in
the same production workflow.

# Platform Standard 5 - Work Sessions Are First-Class Records

Every production work session should be treated as valuable operational data.

Whenever practical, record:

- start time
- end time
- cards processed
- listings created
- footage location
- export batches
- pricing jobs
- notes
- bottlenecks
- ideas for improvement

Operational history is a business asset.

# Platform Standard 6 - One Source of Truth

Every shared service should have one authoritative implementation.

Examples include:

- Path Manager
- Pricing Engine
- Inventory Location Registry
- SKU Generator

Avoid duplicate implementations across applications.

# Platform Standard 10 - Normalized Listing Pipeline

CSV-driven listing workflows should use the locked normalized listing pipeline:

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

Source-specific import differences belong in detection, mapping, and adapter
profiles. Do not create a separate pricing engine for each CSV source.

The CardVector Pricing Engine should operate on normalized listings. CardVector
OS may orchestrate the workflow and user review, but it should not duplicate
pricing or source-adapter responsibilities.

# Platform Standard 7 - Backwards Compatibility

Repository improvements should minimize disruption to active business
operations.

Whenever practical:

- migrate rather than replace,
- preserve compatibility,
- document breaking changes,
- provide migration guidance.

The business should continue operating while the platform evolves.

# Platform Standard 8 - Business Before Architecture

Architecture exists to support the business.

Technical elegance should never take priority over:

- cash flow
- listing velocity
- inventory turnover
- operational reliability

When trade-offs exist, prefer the solution that keeps Putnam Collectibles
operating efficiently.
