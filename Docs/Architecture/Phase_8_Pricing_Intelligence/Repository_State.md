# Phase 8 Repository State

## Starting Baseline

- Branch: `main`
- Starting HEAD: `ab2b1df874bf55477e18aca015c89ca24ee82237`
- Working tree: clean
- Production launcher:
  `Platform/Putnam_OS/Run CardVector OS Production.vbs`
- Architecture guardrail baseline: 48 documented findings, zero new findings

Phase 7 Marketplace Intelligence, Phase 6 batch workflow, CardUploader
inventory ownership, and Capture ownership were present before Phase 8.

## Scope

Phase 8 changes only business-aware pricing configuration, contracts,
calculation, reporting, persistence, tests, and architecture documentation.
There are no live marketplace writes, inventory mutations, Capture changes, or
launcher changes.

The only Putnam OS production edit is the pricing-orchestration adapter in
`putnam_os.py`: it constructs the existing canonical Listing contract and
delegates through `cardvector.application` to Marketplace Intelligence. It
contains no fee, shipping, packaging, acquisition, or profit formulas.
