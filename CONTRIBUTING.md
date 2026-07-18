# Contributing To CardVector

CardVector is production software for Putnam Collectibles. Preserve daily
business workflows and extend the canonical owner of a responsibility instead
of creating a parallel implementation.

## Before A Change

1. Read `Docs/Architecture/README.md`.
2. Read the Architecture Manifest and accepted ADRs.
3. Check `CardVector_Subsystem_Ownership_Matrix.md`.
4. Run `git status` and identify unrelated work.
5. Search the repository for existing implementations and callers.
6. Classify the work with the small, subsystem, or architecture checklist.
7. Define acceptance tests and rollback before editing production code.

Stop and request architecture approval when ownership, layer direction,
entry-point behavior, package placement, or a public subsystem contract is
unclear.

## Mandatory Pre-File-Creation Checklist

For a significant new production module, answer:

1. What responsibility does this file own?
2. Which existing subsystem owns that responsibility?
3. Does an existing module already provide this capability?
4. Why can the existing module not be extended?
5. Is this a new implementation or a compatibility adapter?
6. What imports this file?
7. What tests will cover it?
8. Is its location approved by the architecture manifest?
9. Does this create a second entry point or duplicate implementation?
10. What is its long-term lifecycle?

Use `Docs/Architecture/New_File_Request_Template.md` for significant production
modules. It is not required for routine documentation or isolated test fixtures.

## Repository Rules

- One canonical implementation owns each responsibility.
- Extend the owner before creating a new module.
- Do not add entry points or launcher targets without an accepted ADR.
- Do not put business rules in Tkinter widgets or UI callbacks.
- Domain code must not import Tkinter, dialogs, filesystem adapters, databases,
  or vendor clients.
- Do not import production code from `Archive/` or runtime-data folders.
- Do not mutate `sys.path` without explicit architecture approval.
- Do not use `old`, `backup`, `copy`, `final`, `new`, `temp`, or version suffixes
  in production filenames.
- Git history is the backup mechanism.
- Do not track captures, logs, caches, temporary files, user configuration,
  secrets, or operational databases as source.
- Keep commits small and single-purpose. Never mix feature work with cleanup or
  an architecture migration package.

## Tests And Documentation

Every production change requires focused automated tests proportional to its
risk, relevant smoke tests, `git diff --check`, and a documented rollback.
Compilation alone is not validation. Update architecture documentation whenever
ownership, dependencies, entry points, compatibility, deprecation, or runtime
boundaries change.

## Deprecation And Compatibility

A deprecation must be entered in
`Docs/Architecture/Deprecation_Register.md` with known callers, support period,
removal criteria, owner, and target phase. Compatibility adapters must be thin
forwarders, must contain no second business implementation, must be tested, and
must be entered in `Compatibility_Adapter_Register.md`.

## Pull Requests And Commits

- Describe scope, owner, tests, manual validation, rollback, and documentation.
- Identify unrelated working-tree changes and exclude them.
- Link accepted ADRs for architecture changes.
- State whether a compatibility adapter or deprecation was added.
- Preserve a reversible commit sequence.

## Architecture Commands

```powershell
py Tools\architecture\check_architecture.py
py Tools\architecture\check_architecture.py --strict
py -m unittest discover -s Tools\architecture -p "test_*.py"
```

Warning mode reports current debt. Strict mode rejects unbaselined violations.
The tool is read-only.
