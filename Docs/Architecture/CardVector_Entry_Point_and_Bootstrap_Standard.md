# CardVector Entry Point And Bootstrap Standard

**Status:** Proposed
**Evidence:** `Entry_Point_Report.md`

## Current State

Official current launcher:

`Platform/Putnam_OS/Run CardVector OS Production.vbs`

Current target:

`Platform/Putnam_OS/System/app/putnam_os.py`

This remains unchanged until the new bootstrap passes shadow validation on both workstations.

## Permanent Entry Point

Official Python invocation:

```text
py -m cardvector
```

Implementation:

```text
Platform/cardvector/__main__.py
```

The module exports one `main(argv=None) -> int` function and calls it under a normal `__main__` guard.

## Permanent Production Launcher

Preferred permanent launcher path:

`Platform/Putnam_OS/Run CardVector OS Production.vbs`

The filename remains operator-facing and stable. Its implementation eventually:

1. locates the project/package environment without a username,
2. invokes `py -m cardvector`,
3. captures bootstrap-level failure output,
4. returns the Python process exit code,
5. does not generate or execute a second application script.

Aliases remain compatibility redirects only during a documented deprecation period.

## Startup Chain

```text
Run CardVector OS Production.vbs
    |
    v
py -m cardvector
    |
    v
cardvector.__main__.main()
    |
    v
cardvector.bootstrap.run_desktop()
    |
    +--> resolve package and workspace paths
    +--> load environment and validated configuration
    +--> initialize structured logging
    +--> run startup validation
    +--> construct repositories and external adapters
    +--> construct canonical subsystem services
    +--> construct workflow/application services
    +--> construct desktop presentation adapter
    |
    v
cardvector.presentation.desktop.application.run()
```

## Bootstrap Responsibilities

Allowed:

- parse startup-only arguments,
- resolve workspace/user-data directories,
- load settings in defined precedence,
- initialize logging,
- validate required directories and optional integrations,
- create repositories, clients, services, and executors,
- install a top-level exception handler,
- launch the requested presentation.

Forbidden:

- pricing calculations,
- CSV parsing,
- inventory mutation,
- eBay policy decisions,
- capture pair logic,
- Tkinter widget construction,
- migration execution without explicit command,
- service-role key logging.

## Configuration Startup Order

1. Package/version defaults.
2. Version-controlled non-secret defaults.
3. user configuration file.
4. workstation configuration.
5. environment-variable overrides.
6. explicit command-line overrides for approved diagnostics.

Each merged setting is validated before services start. The bootstrap records configuration sources, not secret values.

## Path Startup Order

1. Resolve installed package location using Python packaging.
2. Resolve workspace root from explicit `CARDVECTOR_WORKSPACE_ROOT`.
3. Use configured Putnam Collectibles workspace default when valid.
4. During compatibility only, recognize `.putnam_root` and `USERENVIRONMENT`.
5. Never recursively search user folders.

The current `Platform/putnam_paths.py` becomes a compatibility facade over the new path service.

## Logging Startup

Logging starts before optional integrations.

Minimum fields:

- timestamp,
- severity,
- subsystem/logger,
- event,
- workstation,
- application version,
- correlation/job/session ID when available.

Console/startup fallback remains available if the log directory cannot be created. Secrets and full authorization headers are always redacted.

## Dependency Composition

Bootstrap constructs in this order:

1. path and configuration objects,
2. logging and error reporting,
3. persistence repositories,
4. external integrations,
5. subsystem application services,
6. cross-workflow application services,
7. presentation.

No service locates its own repository root or reads global UI variables.

## Startup Failure Reporting

Before UI construction:

- write a sanitized startup log,
- print a concise terminal message,
- optionally show one minimal native message only from the launcher/bootstrap boundary,
- return a nonzero exit code.

After UI construction:

- application exceptions map to actionable UI errors,
- technical detail goes to logs,
- background worker exceptions are captured and reported without terminating Tkinter.

## Test And Non-GUI Entry

Tests call factories directly:

```text
create_services(settings, adapters)
create_application_services(...)
```

They do not launch Tkinter or invoke the production VBS.

Future approved surfaces:

```text
py -m cardvector                 desktop
py -m cardvector.cli ...         CLI, if approved
cardvector.web:create_app()      web/API, if approved
```

These reuse application services and bootstrap factories. They do not import the desktop UI.

## Entry Point Rules

1. No new executable production module without an approved decision-log entry.
2. Subsystem CLIs are developer/operator tools, not alternative CardVector applications.
3. Direct `if __name__ == "__main__"` is permitted for tests/tools and the official package entry only.
4. Production source modules must not execute parsing or work at import time.
5. Launchers must not encode business rules or user-specific paths.
6. Only one launcher may be labeled production.

## Transition Plan

1. Add package metadata and import smoke tests.
2. Add `cardvector.__main__` and bootstrap that still calls the current `putnam_os` application.
3. Validate `py -m cardvector` without changing the VBS.
4. Run both paths in shadow validation.
5. Redirect the official VBS.
6. Retain prior direct command as rollback for one release.
7. Deprecate aliases after workstation/shortcut search.

## Acceptance Criteria

- `py -m cardvector` starts from any working directory.
- no `sys.path` mutation is required by the new path,
- startup logging initializes before services,
- missing optional OBS/Supabase configuration does not crash unrelated workflows,
- fatal configuration errors are concise and logged,
- tests construct application services without Tkinter,
- the official launcher starts the same validated application,
- rollback is a one-line launcher target reversal.
