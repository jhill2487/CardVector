# CardVector Agent Instructions

Before changing this repository, read `Docs/Architecture/README.md`, the
Architecture Manifest, accepted ADRs, and the subsystem ownership matrix.

## Mandatory Rules

- Search before creating files.
- Extend the canonical subsystem owner; never create a parallel implementation.
- Never add an alternate launcher or entry point without accepted architecture
  approval.
- Never place business logic in UI modules.
- Never import Tkinter or UI concerns into domain logic.
- Never import production code from `Archive/` or runtime-data folders.
- Never mutate `sys.path` without explicit architecture approval.
- Never create production filenames containing `old`, `backup`, `copy`, `final`,
  `new`, `temp`, or version suffixes.
- Preserve backward compatibility only through registered, tested adapters.
- Add focused tests for production changes.
- Update architecture documents when ownership or dependency rules change.
- Stop and explain uncertainty when architecture evidence is incomplete.
- Distinguish observed facts from assumptions and recommendations.
- Preserve unrelated working-tree changes.

## Before Editing Code

Confirm:

1. The responsibility and canonical owner are identified.
2. Existing implementations and callers were searched.
3. The change is classified as small, subsystem, or architecture.
4. A new file is necessary under the pre-file-creation checklist.
5. Tests, manual validation, and rollback are defined.
6. The target path is allowed by the machine-readable manifest.
7. The change does not create a second implementation or entry point.

Use `CONTRIBUTING.md` and the checklists in `Docs/Architecture/` for the full
process.
