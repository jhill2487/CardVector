# Phase 2 Compatibility Map

## Active Adapter

**ID:** `CV-COMP-012`

| Field | Value |
| --- | --- |
| Legacy surface | Workflow methods and context calls in `putnam_os.py` |
| Canonical target | `Platform.cardvector.application.WorkflowApplication` |
| Existing implementation | `Platform/Putnam_OS/System/app/workflow_context.py` |
| Wiring owner | Temporary `build_application_runtime` in `putnam_os.py` |
| Behavior | Thin delegate injection; no fallback implementation |
| Warning behavior | None |
| Tests | Application delegation/parity tests plus existing workflow UI tests |
| Removal condition | Permanent bootstrap injects services and presentation invokes the application API directly |
| Target removal phase | Presentation/bootstrap migration, separately authorized |

## Preserved Interfaces

- `PutnamOS()` remains valid.
- `PutnamOS(application_runtime=...)` adds optional injection without breaking
  existing callers.
- `workflow_job_snapshot`, `workflow_job_by_id`, and existing UI callbacks keep
  their signatures.
- `workflow_context.py` public functions keep their paths and signatures.
- Production launcher still invokes `putnam_os.py`.

## Import Boundary

Legacy code imports the canonical application API:

```text
putnam_os.py -> Platform.cardvector.application
```

The canonical application package never imports the legacy application,
compatibility code, Tkinter, or a subsystem implementation. Existing behavior
is supplied as injected callables.

## Removal Safety

Do not remove the adapter until:

1. a permanent bootstrap is separately approved;
2. all `PutnamOS` construction paths inject the runtime;
3. presentation callbacks use the canonical application API;
4. workflow parity and production launcher tests pass;
5. the compatibility register is updated with owner approval.
