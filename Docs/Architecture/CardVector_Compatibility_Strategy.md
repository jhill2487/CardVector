# CardVector Compatibility Strategy

**Status:** Proposed
**Purpose:** Preserve working interfaces while eliminating duplicate implementations

## Compatibility Principles

1. Compatibility forwards; it does not calculate.
2. The canonical implementation is called on every path.
3. Adapters preserve documented inputs, outputs, side effects, and errors.
4. Every adapter is temporary and registered.
5. Canonical packages never import compatibility.
6. New features are added only to the canonical owner.
7. A compatibility path is removed only after all callers migrate and tests pass.

## Compatibility Registry

Every adapter must record:

| Field | Requirement |
|---|---|
| Adapter ID | Stable `CV-COMP-###` |
| Legacy path/interface | Exact path and symbols |
| Canonical target | Exact public API |
| Owner | Canonical subsystem owner |
| Reason | Named caller or behavior preserved |
| Behavior contract | Arguments, result, side effects, errors |
| Tests | Delegation plus parity |
| Introduced phase | Migration phase |
| Removal condition | Measurable |
| Target removal phase | Roadmap phase |
| Status | Planned, Active, Deprecated, Removed |

## Adapter Types

### Forwarding imports

An old module imports and re-exports canonical symbols.

Use when:

- callers import classes/functions by module path.

Rules:

- no wildcard re-export,
- explicit `__all__`,
- no side effects,
- no circular import.

### Wrapper functions

An old function maps arguments/results to a canonical service.

Use when:

- legacy shape differs.

Rules:

- mapping only,
- no fallback formula,
- preserve exception contract or translate explicitly,
- delegation test required.

### Launcher redirects

An old launcher starts the one official package entry.

Use when:

- shortcuts or runbooks still reference old files.

Rules:

- one process,
- no alternate configuration,
- warning only in logs,
- target removal date documented.

### Import aliases

Use only when packaging migration would otherwise break a known import. Prefer real forwarding modules over `sys.modules` mutation.

### Runtime warnings

Warnings:

- use `DeprecationWarning` for developer imports,
- use structured logs for launcher/operator transitions,
- never interrupt the daily workflow with repeated popups.

## Initial Planned Adapters

| ID | Legacy interface | Canonical target | Owner | Target phase |
|---|---|---|---|---|
| CV-COMP-001 | `Platform.putnam_paths` | `cardvector.infrastructure.filesystem.paths` | Infrastructure | Phase 11 |
| CV-COMP-002 | Putnam OS pricing modules under `System/MarketIntelligence/Pricing` | `cardvector.marketplace_intelligence` | Marketplace Intelligence | Phase 11 |
| CV-COMP-003 | `System/app/bulk_price_engine.py` | MI pricing + Listings export workflow | MI/Listings | Phase 11 |
| CV-COMP-004 | pricing/export functions in `putnam_os.py` | MI/Listings/Shipping services | Owning subsystem | Phase 11 |
| CV-COMP-005 | `System/app/main.py` public functions and entry | Processing workflow and official entry | Application | Phase 11 or later |
| CV-COMP-006 | `capture_studio.py` and OBS manager imports | Capture API and OBS integration | Capture | Phase 11 |
| CV-COMP-007 | `inventory_locations.py` imports | Inventory API | Inventory | Phase 11 |
| CV-COMP-008 | `orders_fulfillment.py` imports | Orders API | Orders | Phase 11 |
| CV-COMP-009 | `mobile_capture_queue.py` CLI | Capture queue command API | Capture | Phase 11 |
| CV-COMP-010 | Listing Optimizer wrappers | MI/Listings services | MI/Listings | Phase 11 |
| CV-COMP-011 | Putnam OS launcher aliases | official production launcher | Bootstrap | Phase 11 |

IDs become active only when implementation begins and the exact contract is documented.

## Shape Adaptation

Where old callers use dictionaries and canonical services use typed models:

- adapter performs one explicit conversion,
- canonical model remains unchanged,
- unknown fields are preserved only when required by the external CSV contract,
- money uses `Decimal` internally,
- output order/headers remain exact when eBay compatibility requires it.

## Data Compatibility

Runtime state migrations follow:

1. read old and new formats,
2. write old format until shadow validation,
3. optionally dual-write only with transaction/consistency tests,
4. switch canonical write format,
5. retain read migration for defined releases,
6. archive migration code only after all state is converted and backed up.

Do not silently rewrite inventory, capture, acquisition, or audit data at startup.

## Compatibility Test Standard

Each adapter requires:

- delegation spy/mock proving the canonical API is called,
- fixture parity against current output,
- error translation test,
- no duplicate-formula/source assertion where practical,
- import test from old path,
- documented removal condition.

## Removal Process

1. Run repository and workstation caller search.
2. Confirm telemetry/logs show no use during deprecation if available.
3. Migrate all source and tests.
4. Validate both workstations.
5. Update docs.
6. Obtain owner approval.
7. Remove in one commit.
8. Retain rollback tag.

Compatibility is not complete when an adapter works. It is complete when the adapter is safely removed.
