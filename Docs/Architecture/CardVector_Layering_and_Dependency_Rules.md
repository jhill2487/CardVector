# CardVector Layering And Dependency Rules

**Status:** Proposed
**Primary evidence:** `Dependency_Map.md` and `Architecture_Audit.md`

## Dependency Direction

```text
Presentation
    |
    v
Application
    |
    v
Domain

Infrastructure ----implements----> Application/Domain ports
Integrations ------implements----> Application/Domain ports

Bootstrap composes all concrete implementations.
Compatibility forwards inward to canonical public APIs.
```

The domain never points outward. Application code names required capabilities as ports. Bootstrap selects concrete adapters.

## Layer 1 - Presentation

### Responsibilities

- Desktop shell and navigation.
- Tkinter views, dialogs, widgets, status, progress, and view models.
- Operator event translation.
- Rendering application results and sanitized errors.
- Dispatching UI updates to the Tkinter thread.

### Allowed dependencies

- Application commands, queries, and result models.
- Shared presentation-safe types.
- UI toolkit and image-rendering libraries.

### Forbidden dependencies

- Direct file, JSON, SQLite, Supabase, OBS, eBay, or CardUploader access.
- Pricing formulas.
- Inventory mutation rules.
- CSV schema inference.
- Infrastructure concrete classes except during temporary migration wiring.
- Compatibility modules.

### Current examples

- `Platform/Putnam_OS/System/app/putnam_os.py` contains the presentation layer, but also many forbidden responsibilities.
- `Platform/Marketplace_Intelligence/marketplace_intelligence/ui.py` is another presentation surface.

### Migration implication

Keep current widgets and callbacks. Replace callback internals with application service calls one workflow at a time.

## Layer 2 - Application

### Responsibilities

- Use cases and workflows.
- Commands and queries.
- Transactions and cross-subsystem sequencing.
- Job context and resumability.
- Authorization decisions at the application boundary.
- Background-job coordination.
- Ports required from persistence and external systems.

### Allowed dependencies

- Domain models and services.
- Public APIs of canonical subsystems.
- Shared domain primitives.

### Forbidden dependencies

- Tkinter or message boxes.
- Concrete filesystem paths.
- Database drivers.
- HTTP clients.
- Browser launch implementation.
- OBS or Supabase SDKs.

### Current examples

- `workflow_context.py` is a strong seed for workflow orchestration.
- UI methods such as `run_workflow_action`, `finish_carduploader_import`, and `set_current_pricing_job` currently mix application and presentation behavior.

### Migration implication

Extract command/query services first. Return result objects that the current UI can render without behavior changes.

## Layer 3 - Domain

### Responsibilities

- Business concepts, invariants, value objects, policies, and pure calculations.
- Capture pair completeness.
- External inventory identifiers and CardUploader contract values.
- FMV/recommendation/final-price distinctions.
- Listing and order semantics.
- Domain errors.

### Allowed dependencies

- Python standard library.
- `cardvector.shared.domain`.
- Approved pure libraries without I/O side effects.

### Forbidden dependencies

- Tkinter.
- Files, environment variables, database drivers, HTTP, subprocess, webbrowser.
- Infrastructure and integrations.
- Compatibility modules.
- Repository-relative paths.

### Current examples

- Marketplace Intelligence models/pricing logic are closest to domain behavior.
- `inventory_locations.py` combines legacy capture/location projection rules
  with JSON persistence; it is not the managed-inventory owner.
- `optimized_export_price`, policy checks, and inventory capacity logic currently sit near UI code.

### Migration implication

Separate pure decisions from persistence without changing formulas. Characterization tests precede extraction.

## Layer 4 - Infrastructure

### Responsibilities

- Local configuration sources.
- Repository/workspace/user-data path resolution.
- Structured logging.
- JSON/CSV/SQLite repositories.
- Atomic file writes.
- Serialization.
- Local background scheduling and thread executors.
- Cache and temporary-file implementation.

### Allowed dependencies

- Application ports.
- Domain models.
- Shared primitives.
- Technology libraries.

### Forbidden dependencies

- Tkinter views.
- Marketplace business decisions.
- Calling compatibility wrappers.
- Defining external protocol semantics.

### Current examples

- `Platform/putnam_paths.py`.
- local JSON state in `System/data`.
- direct file/log helpers spread across `putnam_os.py`.
- current untracked Marketplace Intelligence pricing repository.

### Migration implication

Introduce interfaces first, then move concrete implementation. Do not change runtime locations and code structure in the same package.

## Layer 5 - Integration

### Responsibilities

- External protocol and vendor adapters.
- Request/response translation.
- Authentication handoff without exposing secrets.
- Retries, timeouts, rate-limit handling, and external error mapping.
- External source provenance.

### Allowed dependencies

- Application ports and domain models.
- Infrastructure HTTP/storage primitives where useful.
- Vendor libraries.

### Forbidden dependencies

- Tkinter.
- Business strategy.
- Direct use by domain code.
- Embedded service-role keys or credentials.

### Current examples

- Supabase behavior in `mobile_capture_queue.py`.
- OBS behavior in `obs_connection_manager.py`.
- CardUploader provider/cache and browser handoff code.
- eBay CSV and Seller Hub handoff behavior.

### Migration implication

Separate protocol mechanics from application decisions. Preserve current atomic queue and routing contracts.

## Layer 6 - Compatibility

### Responsibilities

- Forward old imports to canonical APIs.
- Adapt legacy arguments/results.
- Redirect launchers.
- Emit controlled deprecation warnings where operator-safe.
- Preserve output contracts during migration.

### Allowed dependencies

- Canonical application/subsystem public APIs.

### Forbidden dependencies

- Canonical packages importing compatibility.
- New business logic.
- Independent persistence.
- Feature expansion.

### Current examples

- Putnam OS pricing forwarding modules.
- Listing Optimizer v1.2 wrapper.
- eventual `main.py` forwarding surface.

### Migration implication

Every adapter is registered in the compatibility inventory with a removal phase and test.

## Bootstrap Exception

`cardvector.bootstrap` is the composition root. It may import:

- presentation,
- application,
- domain,
- infrastructure,
- integrations.

It may only:

- load validated settings,
- initialize logging,
- resolve paths,
- construct repositories/adapters/services,
- start the chosen presentation.

It may not calculate prices, parse business CSVs, mutate inventory, or contain UI widgets.

## Cross-Subsystem Rules

1. Subsystems communicate through public application APIs or shared domain identifiers.
2. A subsystem may not import another subsystem's infrastructure.
3. Cross-subsystem workflows belong in `cardvector.application`, not either subsystem.
4. Shared models are permitted only when two or more owners truly share the same concept.
5. "Utility" is not an ownership category. A helper remains with the subsystem unless technology-independent and reused.
6. Reporting semantics remain with the subsystem; generic rendering may be shared.
7. Integration adapters implement owner-defined ports.

## Import Rules

Allowed:

```python
from cardvector.application import InventoryApplication
from cardvector.marketplace_intelligence.api import PricingService
from cardvector.shared.domain.money import Money
```

Forbidden:

```python
from Platform.Putnam_OS.System.app.putnam_os import money
from cardvector.presentation.desktop.views import InventoryView
from Archive.Scanner_Development import recognizer
sys.path.insert(0, ...)
```

Relative imports are allowed within one package boundary. Cross-package imports use absolute `cardvector.*` paths.

## Dynamic Imports

Dynamic imports are permitted only for:

- an approved plugin boundary,
- an optional dependency isolated behind a documented adapter,
- packaging/runtime discovery that cannot use normal imports.

Each use requires:

- decision-log entry,
- import contract,
- explicit failure behavior,
- test for dependency present and absent,
- named owner.

The current dynamic label-generator load should be replaced by normal dependency injection during its migration phase.

## Cycle Prevention

Layer cycles are prohibited. Subsystem cycles are resolved by:

- moving orchestration to the application layer,
- defining a port in the consuming application package,
- extracting a genuinely shared value object,
- publishing an event/result rather than importing the caller.

No cycle may be "fixed" by runtime import placement or `sys.path` mutation.

## Test Boundary

Domain tests require no GUI, network, filesystem, or installed external app.

Application tests use fake ports.

Infrastructure/integration tests use temporary paths, fixtures, or controlled services.

Presentation tests may use headless construction or source-contract checks, but business correctness is tested below the UI.
