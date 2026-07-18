# Phase 2 Application Architecture

## Scope

Phase 2 establishes the canonical orchestration owner at:

```text
Platform/cardvector/application/
```

It does not create a new entry point, bootstrap, path service, presentation
package, domain package, infrastructure package, or subsystem implementation.
The production launcher and direct `putnam_os.py` startup remain unchanged.

## Package Structure

```text
Platform/cardvector/
    __init__.py
    application/
        __init__.py
        runtime.py
        workflows.py
```

`runtime.py` owns technology-neutral execution primitives:

- `ApplicationRuntime`
- `ServiceRegistry`
- `CommandDispatcher`
- `ExecutionContext`
- `CancellationToken`
- `ProgressReporter`
- `EventPublisher`

`workflows.py` owns cross-workflow coordination through:

- `WorkflowDelegates`
- `WorkflowApplication`

The package root exports the supported public application API. Callers should
not import private implementation details.

## Dependency Direction

```text
putnam_os.py
    |
    | injects existing workflow_context functions
    v
WorkflowApplication
    |
    | calls injected delegates only
    v
existing workflow_context.py
```

The canonical application package imports only the Python standard library. It
does not import Tkinter, Putnam OS, Marketplace Intelligence, Capture,
Inventory, Listings, Shipping, persistence, filesystem adapters, vendor
clients, or compatibility modules.

## Current Composition

`putnam_os.py` temporarily creates `ApplicationRuntime`, registers a
`WorkflowApplication`, and injects the existing `workflow_context.py`
functions. This is a migration composition seam, not the permanent bootstrap.
The future bootstrap remains unauthorized and unimplemented.

`PutnamOS.__init__` accepts an optional `application_runtime`. Existing no-arg
construction remains supported. This permits tests and future bootstrap code to
inject application services without changing current launcher behavior.

## Runtime Contracts

### Execution

`ExecutionContext` carries:

- execution ID,
- cancellation token,
- progress reporter,
- event publisher,
- caller-provided metadata.

It contains no business state and performs no I/O.

### Commands

`CommandDispatcher` maps a command name to one injected handler. It checks
cancellation before calling the handler. It does not interpret business
payloads.

### Services

`ServiceRegistry` provides explicit service registration and lookup. Duplicate
registration requires explicit replacement.

### Progress And Events

Progress and event publication use in-process subscribers. They do not know
about Tkinter, threads, logs, databases, or external brokers.

## New-File Approval Record

The project owner explicitly authorized `Platform/cardvector/application` in
the Phase 2 prompt.

1. Responsibility: cross-workflow orchestration and execution coordination.
2. Canonical owner: `cardvector.application`.
3. Existing implementation searched: `putnam_os.py` and
   `workflow_context.py`.
4. Existing modules cannot become canonical because they live in the legacy UI
   package and mix presentation/persistence ownership.
5. New implementation type: orchestration facade; existing algorithms remain
   delegates.
6. Importers: current `putnam_os.py`; future bootstrap/presentations.
7. Tests: `Tests/application/test_application_layer.py`.
8. Location: explicitly approved by Phase 2 and the architecture manifest.
9. Entry point/duplication: no entry point; no business implementation.
10. Lifecycle: permanent application API; legacy wiring is temporary.

## Explicit Non-Ownership

The Application layer does not own pricing, Marketplace Intelligence, Capture,
Inventory, OCR/recognition, Listings, Shipping, persistence, UI widgets, paths,
configuration, or vendor protocol code.
