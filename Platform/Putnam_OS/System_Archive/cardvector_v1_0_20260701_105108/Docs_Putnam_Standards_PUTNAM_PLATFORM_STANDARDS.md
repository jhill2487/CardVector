# Putnam Platform Standards

These standards govern the architecture of the Putnam Platform. They are
intended to remain stable over time and apply across all platform applications,
including Putnam OS, Putnam Scanner, Pokemon Lookup Overlay, Seller Tools, and
future modules.

# Platform Mission

The Putnam Platform exists to support Putnam Collectibles.

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

# Platform Standard 1 - Automate Repetitive Work

If a task:

- is performed repeatedly,
- follows predictable steps,
- and does not require meaningful human judgment,

it should become a Putnam Platform tool.

Human effort should be reserved for decisions, not repetition.

# Platform Standard 2 - Build Once, Benefit Forever

Automation is prioritized when a one-time engineering effort saves time across
many future work sessions.

Favor solutions that continue returning value long after they are built.

# Platform Standard 3 - Environment-Aware Paths

All Putnam Platform applications must resolve repository paths through the
central Platform Path Manager.

Never hard-code:

- usernames
- drive letters
- machine-specific paths
- OneDrive locations

Applications should remain portable across development and production
environments.

# Platform Standard 4 - Clear Platform Responsibilities

Putnam OS is the business operating system.

It manages:

- inventory
- listings
- pricing
- shipping
- analytics
- daily operations

The Putnam Platform provides the supporting infrastructure:

- launchers
- shared libraries
- utilities
- backup tools
- automation scripts
- common services
- path management

Business logic belongs in Putnam OS.

Shared infrastructure belongs in the Platform.

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
