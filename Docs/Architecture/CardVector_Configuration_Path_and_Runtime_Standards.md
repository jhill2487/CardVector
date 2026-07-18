# CardVector Configuration, Path, And Runtime Standards

**Status:** Proposed
**Evidence:** Current path/config duplication and tracked runtime findings

## Directory Concepts

CardVector uses four distinct roots:

### 1. Package root

The installed `cardvector` Python package. Resolved by Python packaging, never by crawling parent folders in domain code.

### 2. Repository root

Needed only for development tools, migrations, documentation, and source validation.

Resolution:

- Git/tool context,
- package metadata in editable development installs,
- explicit development argument.

Production business services should not require it.

### 3. Workspace root

Putnam Collectibles business workspace containing:

- `Business`,
- `Data`,
- `Capture`,
- `MobileCapture`.

Configured by:

`CARDVECTOR_WORKSPACE_ROOT`

For the current deployment it may remain the repository root during migration. The architecture treats it as a separate concept so source can later be installed elsewhere without moving business data.

### 4. User runtime root

Workstation-local application state.

Recommended Windows defaults:

- user configuration: `%APPDATA%\CardVector`
- local state/cache/log/temp: `%LOCALAPPDATA%\CardVector`

Cross-workstation business data belongs in the workspace, not local state.

## Permanent Path Service

`cardvector.infrastructure.filesystem.paths`

returns an immutable `PathSettings` model containing:

- package root,
- optional repository root,
- workspace root,
- business root,
- data root,
- capture root,
- mobile queue root,
- import/export/report roots,
- user config root,
- state/cache/log/temp roots.

Paths are constructed once at bootstrap and injected. Subsystems do not read `%USERPROFILE%`, `USERENVIRONMENT`, or `.putnam_root` independently.

## Compatibility Resolution

During migration only:

1. explicit `CARDVECTOR_WORKSPACE_ROOT`,
2. current configured workspace path,
3. `.putnam_root` compatibility marker,
4. `USERENVIRONMENT` compatibility value,
5. documented current OneDrive default.

No hard-coded username. No recursive filesystem search. Compatibility use is logged without exposing private paths in public output.

## Configuration Categories

| Category | Example | Location | Git |
|---|---|---|---|
| Package defaults | default capacity, non-secret feature defaults | source package | Yes |
| Schema | validation models, JSON schema | source package | Yes |
| Business profile | approved pricing/shipping strategy defaults | versioned sanitized config or database migration | Yes when non-secret |
| User preferences | last folder, UI settings | user config root | No |
| Workstation settings | OBS host/scene, local device choices | user config root | No |
| Workspace settings | business workspace behavior | workspace `Data/Config` or approved DB | Usually no |
| Runtime state | current session, queue status, resume data | workspace/local state | No |
| Secrets | service keys, passwords, tokens | environment/secret store | Never |
| Browser-safe config | Supabase URL and anon key | public site source | Yes, explicitly reviewed |
| Test fixtures | sanitized stable input/output | `Tests/fixtures` | Yes |

## Configuration Precedence

Lowest to highest:

1. package defaults,
2. versioned business defaults,
3. workspace configuration,
4. user/workstation configuration,
5. environment variables,
6. explicit approved CLI overrides.

The source of each effective non-secret value can be inspected in diagnostics.

## Secrets Standard

- Secrets never appear in source, JSON committed to Git, logs, screenshots, reports, public exports, or exceptions.
- Service-role keys are environment-only or use an approved OS secret store.
- Browser code receives only explicitly public keys.
- Settings UI shows presence/status, not secret values.
- Secret scans run before public export and commits.
- Logs redact Authorization headers, tokens, passwords, cookies, and query-string credentials.

## Runtime Data Classes

### Production business data

Examples:

- captures,
- imports,
- eBay reports,
- inventory records,
- orders,
- acquisitions.

Requires backup/retention policy. Not source code.

### Generated outputs

Examples:

- eBay export CSV,
- pick lists,
- label PDFs,
- analysis reports.

Timestamped, never overwrite unless an explicit atomic update contract exists.

### Operational state

Examples:

- current conversion/audit session,
- workflow context,
- queue claims,
- last-used folder.

Atomic writes and recovery behavior required. Not tracked.

### Logs

Rotated and retained by policy. Business audit logs with durable meaning are reports, not generic logs.

### Cache

Re-creatable. May be deleted safely after the application closes unless provider terms require retention. Cache corruption must not destroy source data.

### Temporary files

Created under local temp/state with unique names. Atomic writes use temporary siblings and replace. Cleaned on success and recoverable after failure.

## Database Standards

- Schema changes use numbered, immutable migrations.
- Applied migrations remain in Git.
- Production databases are not committed.
- SQLite files live under the configured workspace/state data root.
- Tests use temporary databases.
- Repositories own transactions and serialization.
- UI never executes SQL.
- Cloud service migrations remain under `supabase/migrations`.
- Backup and restore are documented before destructive migration.

## Imports And Exports

Imports:

- original file never modified,
- source path and timestamp recorded,
- format detection owned by the consuming subsystem,
- validation errors include row/column context,
- large work occurs off the UI thread.

Exports:

- portable configured output root,
- timestamp or unique path,
- no overwrite by default,
- source job/session metadata retained separately when marketplace format cannot accept it,
- exact external schemas preserved,
- successful write precedes success log/status.

## Recommended Gitignore Categories

Do not edit `.gitignore` until tracked-state migration is approved. Future rules should cover:

```gitignore
# Python/build
__pycache__/
*.py[cod]
.pytest_cache/
.mypy_cache/
.ruff_cache/
build/
dist/
*.egg-info/

# Local environments and secrets
.venv/
.env
.env.*
!.env.example

# Runtime workspace
Capture/
MobileCapture/
Work_Sessions/
Data/Imports/
Data/Exports/
Data/Reports/
Data/Logs/
Data/Media/
Data/Processed/

# Local databases/state/cache/temp
*.sqlite
*.sqlite3
*.db
*.log
*.tmp
*.bak
Data/Cache/
```

Exceptions require an allowlisted sanitized fixture path.

## Tracked Runtime Migration Standard

For each currently tracked runtime file:

1. classify owner and authority,
2. back it up,
3. create a sanitized default/sample if needed,
4. test a fresh clone with no runtime file,
5. test upgrade with the existing file,
6. update `.gitignore`,
7. remove only from Git index, not operator disk, in a dedicated commit,
8. validate both workstations.

## Acceptance Criteria

- no production source contains a username-specific path,
- no domain/application service discovers its own root,
- startup from any working directory works,
- source and workspace can be configured separately,
- secrets scan clean,
- fresh clone creates runtime state safely,
- current workspace data remains intact,
- generated outputs are not tracked,
- configuration errors identify the key/source without revealing secrets.
