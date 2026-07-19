# Phase 7 Repository State

## Starting Baseline

- Branch: `main`
- HEAD: `9462a7fea408077ecedfaad852089648840d7297`
- Upstream: `origin/main`
- Working tree: clean
- Git operation in progress: none
- Production launcher: `Platform/Putnam_OS/Run CardVector OS Production.vbs`
- Production target: `Platform/Putnam_OS/System/app/putnam_os.py`
- Launcher SHA-256:
  `AD5044D8D439CE6B321951E85A335DE86927AAA9453FE05DF0A23C1327006EE7`
- Strict architecture result: 48 documented baseline findings, zero new
  findings

Phase 6 commits through `9462a7f` are present. The canonical Application,
Marketplace Intelligence, Capture, CardUploader inventory integration, and
Batch Workflow packages are present.

## Protected Ownership Boundaries

- CardUploader owns recognition, card-level inventory, batch assignment, and
  marketplace assignment.
- Capture owns image acquisition, queueing, mobile intake, and staging.
- Marketplace Intelligence owns evidence interpretation, FMV, Price Vector,
  confidence, recommendations, and pricing exports.
- CardVector Application and Batch Workflow own orchestration and milestone
  state.

Phase 7 does not authorize a launcher, Capture, CardUploader, inventory, batch,
listing-mutation, or marketplace-synchronization change.

## Pre-Existing Documentation Drift

The root `AGENTS.md` references `Docs/AGENTS.md`,
`Docs/Putnam_Standards/PUTNAM_PRINCIPLES.md`,
`Docs/Putnam_Standards/PUTNAM_PLATFORM_STANDARDS.md`,
`Docs/PROJECT_STATUS.md`, and `Docs/ROADMAP.md`. Those paths are absent at the
starting commit. The normative `Docs/Architecture` package, root
`CONTRIBUTING.md`, and root `AGENTS.md` are present. This pre-existing drift is
outside Phase 7 and does not affect Marketplace Intelligence ownership.
