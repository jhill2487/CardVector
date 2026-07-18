# Phase 1 Acceptance Criteria

## Required Standards

- [x] Architecture README exists and identifies authority and document hierarchy.
- [x] Machine-readable architecture manifest exists and parses as JSON.
- [x] `CONTRIBUTING.md` implements the approved development process.
- [x] One repository-level AI instruction file exists: `AGENTS.md`.
- [x] `.github/CODEOWNERS` assigns real ownership.
- [x] ADR template exists.
- [x] Deprecation register exists.
- [x] Compatibility adapter register exists.
- [x] New-file request template exists.
- [x] Small, subsystem, and architecture change checklists exist.

## Guardrails

- [x] Architecture checker is read-only.
- [x] Warning mode reports current violations and exits zero.
- [x] Strict mode rejects unbaselined findings.
- [x] Guardrail unit tests pass.
- [x] Baseline violations are recorded in Markdown and JSON.
- [x] Architecture commands are documented.

## Production Safety

- [x] No production behavior changed.
- [x] No production file was moved, renamed, deleted, or consolidated.
- [x] The production launcher target was not changed.
- [x] `putnam_os.py` was not changed by Phase 1.
- [x] `main.py` was not changed by Phase 1.
- [x] No future production package structure was created.
- [x] Existing Price Vector/eBay work remains preserved outside this change.

## Phase Boundary

Phase 1 acceptance does not imply Phase 2 readiness. Phase 2 requires a clean
and valid feature baseline plus resolution of the blockers recorded in
`Phase_1_Readiness_Assessment.md`.
