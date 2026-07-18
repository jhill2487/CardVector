# CardVector Target Repository Structure

**Status:** Proposed
**Evidence:** `Repository_Inventory.md`, `Dependency_Map.md`, and `Module_Ownership.md`

## Design Choice

The permanent source architecture uses one installable Python package at `Platform/cardvector`. This is more durable than continuing to add importable peers directly under `Platform`, because it:

- gives production imports one namespace,
- supports `python -m cardvector`,
- eliminates working-directory-dependent imports,
- allows subsystem ownership without a repository-wide rewrite,
- supports desktop, CLI, web-service, and automation entry points over the same application services,
- allows current paths to survive temporarily as compatibility wrappers.

The repository continues to separate source, business data, runtime data, documentation, tools, and archives.

## Proposed Tree

```text
PutnamCollectibles/
|-- pyproject.toml
|-- AGENTS.md
|-- PLATFORM_VISION.md
|-- .env.example
|-- .gitignore
|-- .github/
|   `-- workflows/
|
|-- Platform/
|   |-- cardvector/
|   |   |-- __init__.py
|   |   |-- __main__.py
|   |   |-- bootstrap.py
|   |   |
|   |   |-- presentation/
|   |   |   `-- desktop/
|   |   |       |-- application.py
|   |   |       |-- shell.py
|   |   |       |-- navigation.py
|   |   |       |-- dialogs.py
|   |   |       |-- view_models/
|   |   |       `-- views/
|   |   |
|   |   |-- application/
|   |   |   |-- commands/
|   |   |   |-- queries/
|   |   |   |-- ports/
|   |   |   |-- workflows/
|   |   |   `-- background_jobs.py
|   |   |
|   |   |-- shared/
|   |   |   |-- domain/
|   |   |   |-- errors.py
|   |   |   |-- money.py
|   |   |   `-- validation.py
|   |   |
|   |   |-- capture/
|   |   |   |-- domain/
|   |   |   |-- application/
|   |   |   `-- ports/
|   |   |-- marketplace_intelligence/
|   |   |   |-- domain/
|   |   |   |-- application/
|   |   |   `-- ports/
|   |   |-- listings/
|   |   |   |-- domain/
|   |   |   |-- application/
|   |   |   `-- ports/
|   |   |-- orders/
|   |   |   |-- domain/
|   |   |   |-- application/
|   |   |   `-- ports/
|   |   |-- shipping/
|   |   |   |-- domain/
|   |   |   |-- application/
|   |   |   `-- ports/
|   |   |-- reporting/
|   |   |-- analytics/
|   |   |-- content/
|   |   |-- scanner/
|   |   |
|   |   |-- infrastructure/
|   |   |   |-- configuration/
|   |   |   |-- filesystem/
|   |   |   |-- logging/
|   |   |   |-- persistence/
|   |   |   |-- jobs/
|   |   |   `-- serialization/
|   |   |
|   |   |-- integrations/
|   |   |   |-- carduploader/
|   |   |   |-- ebay/
|   |   |   |-- tcgplayer/
|   |   |   |-- supabase/
|   |   |   `-- obs/
|   |   |
|   |   `-- compatibility/
|   |       |-- putnam_os/
|   |       |-- marketplace_intelligence/
|   |       |-- seller_tools/
|   |       `-- launchers/
|   |
|   `-- Putnam_OS/
|       `-- Run CardVector OS Production.vbs
|
|-- Business/
|-- Data/
|   |-- Imports/
|   |-- Exports/
|   |-- Reports/
|   `-- Samples/
|-- Capture/
|-- MobileCapture/
|-- Docs/
|   |-- Architecture/
|   |-- Reference/
|   |-- Reports/
|   `-- PriceVector/
|-- Tools/
|-- Tests/
|   |-- architecture/
|   |-- contracts/
|   |-- integration/
|   `-- smoke/
|-- supabase/
|   `-- migrations/
|-- Work_Sessions/
`-- Archive/
```

The tree is a target, not a move instruction. Existing production files stay in place until their migration phase.

## Root-Level Ownership

| Folder/file | Purpose | Belongs | Must not contain | Allowed dependencies |
|---|---|---|---|---|
| `pyproject.toml` | Packaging, entry point, test/lint configuration | Build metadata and dependency groups | Business rules or secrets | N/A |
| `Platform/` | All production Python source | The `cardvector` package and temporary legacy wrappers | Captures, exports, logs, operator data | May use versioned config/schema |
| `Business/` | Human-owned business operations | Source reports, seller records, branding, operator documents | Importable Python packages | No production imports |
| `Data/` | Workspace inputs/outputs and sanitized samples | Imports, exports, reports, approved fixtures | Secrets or production source | Accessed through filesystem ports |
| `Capture/` | Capture output workspace | Dated session folders and manifests | Source code | Accessed through Capture repositories |
| `MobileCapture/` | Desktop mobile-queue staging state | Processing/failed/converted runtime data | Source code | Accessed through Capture infrastructure |
| `Docs/` | Current architecture, governance, references, public source | Markdown and public static source | Runtime data or private secrets | No production runtime dependency |
| `Tools/` | Developer/operator maintenance commands | Export, migration, validation, diagnostics | Canonical business rules | May import public platform APIs |
| `Tests/` | Cross-package validation | Architecture, contract, integration, smoke tests | Production runtime state | May import public/test APIs |
| `supabase/` | Cloud schema history | Idempotent migrations and setup docs | Service-role secrets | Deployed independently |
| `Work_Sessions/` | Disposable development artifacts | Validation exports and scratch evidence | Canonical source | Ignored by Git |
| `Archive/` | Historical reference | Superseded projects and manifests | Imported production code | No dependencies from production |

## Source Package Folders

### `cardvector.presentation.desktop`

Purpose:

- Tkinter shell, navigation, views, dialogs, view models, and widget styling.

Belongs:

- `PutnamOS` presentation replacement,
- Home/Capture/Processing/Marketplace/Orders/Settings views,
- UI-specific background callback dispatch.

Must not belong:

- price calculations,
- location mutation,
- CSV schema parsing,
- direct JSON/database writes,
- external API calls.

May depend on:

- `cardvector.application` public commands/queries and presentation-safe models.

Must not be depended on by:

- domain, subsystem, infrastructure, or integration packages.

### `cardvector.application`

Purpose:

- cross-subsystem workflow orchestration.

Belongs:

- pending-work aggregation,
- job context,
- Capture -> CardUploader -> Processing -> eBay handoffs,
- application commands/queries,
- background-job coordination interfaces.

Must not belong:

- Tkinter widgets,
- marketplace formulas,
- direct file/database/network implementations.

May depend on:

- subsystem application APIs,
- domain models,
- ports/interfaces.

### `cardvector.shared`

Purpose:

- small, stable, technology-independent primitives shared by multiple subsystems.

Belongs:

- money value object,
- timestamps/identifiers,
- result/error types,
- validation primitives.

Must not belong:

- miscellaneous helpers used by only one subsystem,
- config file loading,
- Tkinter,
- business rules that have a subsystem owner.

May depend on:

- Python standard library only, except approved foundational libraries.

### `cardvector.capture`

Purpose:

- image acquisition session semantics and capture workflow.

Belongs:

- capture session/pair models,
- front-only/front-back rules,
- capture commands,
- queue claim/download contracts,
- dated-routing policy,
- thumbnail/pair metadata contracts.

Must not belong:

- recognition,
- pricing,
- inventory valuation,
- Tkinter.

May depend on:

- shared domain,
- Capture ports.

Concrete OBS/Supabase/filesystem implementations live in integrations/infrastructure.

### CardUploader inventory integration

Purpose:

- expose CardUploader-owned inventory to CardVector application workflows.

Belongs:

- CardUploader request/response contracts,
- read-only exported-snapshot normalization,
- future supported CardUploader API adapters,
- provider capability reporting and external error translation.

Must not belong:

- inventory business truth, independent quantities, location rules,
- reservations, allocations, picking state, or inventory persistence,
- CardVector-managed inventory databases,
- eBay listing-price logic or capture UI.

CardVector inventory views and commands live in `cardvector.application`.
Temporary ETB/location projections remain registered compatibility adapters;
they do not justify a `cardvector.inventory` package.

### `cardvector.marketplace_intelligence`

Purpose:

- market evidence, FMV, Price Vector, and marketplace pricing decisions.

Belongs:

- normalized evidence,
- provider ports,
- FMV and confidence,
- recommendation/final-price models,
- pricing profiles,
- changed-listing analysis,
- pricing decision persistence contracts.

Must not belong:

- Tkinter,
- CardUploader recognition,
- raw UI callbacks,
- inventory occupancy.

### `cardvector.listings`

Purpose:

- listing records, listing validation, business-policy application, and marketplace-ready export orchestration.

Belongs:

- normalized listing models,
- eBay column-preservation rules,
- listing validation,
- export summaries/log contracts,
- listing job state.

Must not belong:

- FMV calculation,
- eBay network upload,
- UI file dialogs.

### `cardvector.orders`

Purpose:

- order import, grouping, pick-list models, and fulfillment preparation.

Belongs:

- order and line-item normalization,
- pick-list generation,
- fulfillment report contracts.

Must not belong:

- shipping-label purchase,
- CardUploader internals,
- Tkinter.

### `cardvector.shipping`

Purpose:

- shipping policy semantics and fulfillment configuration.

Belongs:

- buyer-paid/free-shipping policy models,
- service/cost assumptions,
- eBay policy validation contracts.

Must not belong:

- order parsing,
- pricing evidence,
- browser automation.

### `cardvector.reporting`

Purpose:

- cross-workflow report coordination and shared renderers.

Belongs:

- generic CSV/HTML/PDF/text rendering interfaces,
- report catalog and output metadata.

Must not belong:

- subsystem metric definitions or decisions. Those stay with the subsystem.

### `cardvector.analytics`

Purpose:

- metric definitions and analysis over durable operational events.

Belongs:

- listing velocity, turnover, order, acquisition, and workflow metrics.

Must not belong:

- operational state mutation,
- pricing decisions,
- UI-only dashboard values.

### `cardvector.content`

Purpose:

- approved content workflow if the current Putnam Content feature remains active.

Must not become:

- a catch-all for files or website source.

Status:

- target ownership exists, but implementation requires an open-question decision.

### `cardvector.scanner`

Purpose:

- only a future approved native scanner/recognition subsystem.

Current status:

- no production implementation,
- CardUploader owns recognition,
- archived scanner research is not imported.

Creation requires an architecture decision. The target name is reserved to prevent another parallel scanner package.

### `cardvector.infrastructure`

Purpose:

- technology-specific internal adapters.

Belongs:

- configuration sources,
- path/workspace resolution,
- logging setup,
- SQLite/JSON/filesystem repositories,
- job scheduling,
- serialization.

Must not belong:

- business decisions,
- Tkinter,
- external marketplace protocol logic.

May depend on:

- application ports and domain models.

### `cardvector.integrations`

Purpose:

- external system protocol adapters.

Belongs:

- CardUploader browser/CSV/cache adapters,
- eBay CSV/API/handoff adapters,
- TCGplayer provider adapters,
- Supabase REST/RPC/Storage clients,
- OBS WebSocket client.

Must not belong:

- business strategies,
- UI,
- secrets embedded in source.

### `cardvector.compatibility`

Purpose:

- temporary forwarding behavior for known legacy interfaces.

Belongs:

- wrappers, aliases, shape adapters, launcher redirects, deprecation warnings.

Must not belong:

- independent formulas,
- new features,
- permanent public APIs,
- unbounded "legacy utilities."

Canonical packages must never import it.

## Packaging And Deployment

The root `pyproject.toml` should eventually define:

- source package directory `Platform`,
- console script only if an approved CLI is required,
- `python -m cardvector` support,
- test/development dependency groups,
- architecture-check commands,
- version from one canonical source.

Desktop packaging may initially remain Python plus VBS. A future installer may call the same package entry point.

Public website deployment remains an independent static export:

`Docs source -> Tools/export_cardvector_site.py -> CardVector-site`

Desktop code must not be bundled into public artifacts.
