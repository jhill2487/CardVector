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


## Card Search — Mandatory Catalog-Wide Invariant

**All changes that can affect card search results MUST cascade to every supported card and printing, regardless of Pokémon name, set, era, card number, or search query.** This includes card identity, artwork/image recovery, finish availability, prices, release-date ordering, filters, pagination, selection, and wanted-card/dashboard views.

- Implement fixes in the canonical shared catalog/search/resolver layer. Do not patch a single Pokémon, individual card ID, set, search term, or UI screen to mask a systemic defect.
- A particular card may be a **regression fixture** illustrating a failure, never the only card for which a fix operates. Catalog-sourced reviewed exceptions are permissible only when the *physical printing is independently verified*, the data is explicit and auditable, and the shared resolver consumes the same format for all records. Never invent a variant or substitute another printing's image.
- Apply the same rules to searches by name, set, illustrator and any future search mode; initial results, "show more"/pagination, selected cards, existing wanted requests, and dashboard editing must behave consistently.
- Preserve canonical card identities and saved requests. Treat missing/unverified provider data as missing/unverified, not as evidence that the item does not exist. Keep fallback sources quota-aware and exact-printing-safe.
- **Before declaring completion:** identify every caller of the shared resolver; test a diverse cross-catalog fixture (old/new releases, promos, specialty sets, non-holo/holo/reverse, missing images, multiple pages and search modes); confirm no regressions in identity, finishes, sorting or selection; verify the deployed build in a real browser, not just static checks. If browser verification is unavailable, clearly mark the work unverified rather than claiming the bug fixed.
- Every related PR must state catalog-wide impact, affected search paths, test evidence, and the associated GitHub Actions workflow name/run/status. A failed workflow is not a successful deployment; report manual publication separately.

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
