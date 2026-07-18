# Phase 1.5 main.py Syntax Repair

## Exact Defect

Compilation fails at:

```text
Platform/Putnam_OS/System/app/main.py:650
raise FileNotFoundError(f"CSV not found:
SyntaxError: unterminated f-string literal
```

Inspection shows the same defect pattern in the result and message strings
through line 692. Escaped `\n` sequences intended by the one-off patch script
were materialized as physical newlines inside ordinary quoted strings.

## Evidence For Intended Text

`patch_cardvector_ebay_existing_listings.py`, lines 41 and 56-69, contains the
exact intended generated block using escaped newline sequences:

```python
raise FileNotFoundError(f"CSV not found:\n{src}")
```

and adjacent result/message strings using `\n` and `\n\n`. The summary keys are
also confirmed by `bulk_price_engine.run_revision()`.

## Approved Minimum Repair

Replace only the malformed physical newlines inside the affected string
literals with the intended `\n` escape sequences from the preserved patch
script. Do not change control flow, function names, summary keys, calls,
interfaces, formatting outside the affected literals, or application behavior.

## Validation Required

- compile `main.py`;
- inspect the resulting diff;
- run the consolidation test that imports `main.py`;
- verify the visible text structure remains identical to the intended patch;
- record the feature checkpoint commit containing the repair.

## Applied Correction

The repair was applied only to the feature-branch version of `main.py`, because
the malformed strings were part of the preserved Price Vector/eBay work. The
clean `main` version already compiles and was not edited.

The corrected literals are:

```python
raise FileNotFoundError(f"CSV not found:\n{src}")
```

and the adjacent result/message strings now use the patch script's intended
`\n` and `\n\n` escapes. No function name, branch, call, summary key, public
interface, or surrounding formatting was changed as part of the syntax repair.

## Evidence And Validation

- Feature checkpoint:
  `3dbadd593860a2847a8824106be9c1e41e74a76c`
- Repaired feature-file SHA-256:
  `EB22E7770CAFAD945A50942231636BC2A676417FF16B49E16DD8D4E57398341D`
- Feature `main.py` compilation: pass
- Pricing consolidation tests importing `main.py`: 10 passed
- Clean-main `main.py` compilation: pass
- Clean-main `main.py` working-tree diff: none

The feature checkpoint contains broader pre-existing feature edits to
`main.py`; the syntax correction itself is limited to the malformed literals
described above.
