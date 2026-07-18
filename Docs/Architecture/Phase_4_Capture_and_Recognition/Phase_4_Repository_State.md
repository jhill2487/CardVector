# Phase 4 Repository State

**Recorded:** 2026-07-18T16:47:50-04:00
**Repository root:** `C:\Users\user\OneDrive\PutnamCollectibles`

## Verified Baseline

| Item | Observed value |
| --- | --- |
| Branch | `main` |
| HEAD | `4f6329944177e456a59cb10e3c390ed8e5bd17c7` |
| Upstream relation | `main` is 11 commits ahead of `origin/main` and 0 behind |
| Working tree | Clean |
| Git operation | None in progress |
| Production launcher | `Platform/Putnam_OS/Run CardVector OS Production.vbs` |
| Launcher target | `Platform/Putnam_OS/System/app/putnam_os.py` |
| Launcher SHA-256 | `AD5044D8D439CE6B321951E85A335DE86927AAA9453FE05DF0A23C1327006EE7` |
| Phase 2 application package | Present under `Platform/cardvector/application` |
| Phase 3 marketplace package | Present under `Platform/cardvector/marketplace_intelligence` |
| Architecture checker | 48 documented baseline findings; 0 new violations |
| Recovery reference | `cardvector-pre-price-vector-integration` |

The latest Phase 3 commits are:

- `f4c61a1 refactor(marketplace): establish canonical pricing services`
- `7be56f5 test(marketplace): add Phase 3 equivalence coverage`
- `4f63299 docs(architecture): document Phase 3 marketplace consolidation`

## Governing Ownership Evidence

- `CardVector_Architecture_Manifest.md` assigns Capture to
  `cardvector.capture`.
- The manifest states that CardUploader owns current production recognition.
- `CardVector_Subsystem_Ownership_Matrix.md` reserves a native
  `cardvector.scanner` package for a separately approved decision.
- Production source does not import `Archive/Scanner_Development`.
- Phase 4 therefore may consolidate Capture and establish a CardUploader
  handoff contract, but it may not activate or copy archived OCR code.

## Pre-change Safety Validation

All commands used temporary directories, mocks, or source-only checks.

| Scope | Result |
| --- | --- |
| Capture Studio | Pass |
| Auto Capture | Pass |
| OBS manager | Pass |
| Mobile capture queue | 25 passed |
| Mobile thumbnail pairs | 3 passed |
| Supabase/mobile capture contract | 19 passed |

No live camera, OBS instance, mobile device, marketplace, user capture folder,
or production database was accessed.
