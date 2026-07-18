# Phase 1 Test Results

**Date:** 2026-07-18

## Results

| Validation | Result | Notes |
| --- | --- | --- |
| Machine manifest JSON parse | Pass | Schema `1.0`; required owner map present |
| Guardrail Python compilation | Pass | Tool and test module |
| Guardrail unit tests | Pass | 12 tests |
| Warning-mode repository scan | Pass | Exit 0; 48 baseline; 0 new; 0 checker errors |
| Strict-mode repository scan | Pass | Exit 0; 48 baseline; 0 new; 0 checker errors |
| Architecture README local links | Pass | No missing local targets |
| Phase 0 WIP reverse patch check | Pass | Preserved tracked WIP still matches recovery patch |
| Production launcher status | Pass | No launcher change |
| Move/delete status | Pass | No moved or deleted production file |
| `git diff --check` | Pass | No whitespace errors; existing line-ending warnings only |

## Commands

Documented portable commands:

```powershell
py Tools\architecture\check_architecture.py
py Tools\architecture\check_architecture.py --strict
py -m unittest discover -s Tools\architecture -p "test_*.py"
```

This workstation's Microsoft Store `py.exe`/`python.exe` aliases intermittently
reported that the executable was already inaccessible while a long-running
Python process was present. Validation was therefore run with the installed
interpreter directly:

```powershell
& "$env:LOCALAPPDATA\Python\pythoncore-3.14-64\python.exe" -m py_compile `
  Tools\architecture\check_architecture.py `
  Tools\architecture\test_check_architecture.py

& "$env:LOCALAPPDATA\Python\pythoncore-3.14-64\python.exe" -m unittest `
  discover -s Tools\architecture -p "test_*.py" -v

& "$env:LOCALAPPDATA\Python\pythoncore-3.14-64\python.exe" `
  Tools\architecture\check_architecture.py

& "$env:LOCALAPPDATA\Python\pythoncore-3.14-64\python.exe" `
  Tools\architecture\check_architecture.py --strict
```

The 12 tests cover forbidden names, archive imports, Tkinter layer violations,
`sys.path` mutation, hard-coded paths, tracked runtime artifacts, warning and
strict exit behavior, saved baselines, manifest loading/errors, and missing
documents.

## Known Pre-Existing Failures

- `Platform/Putnam_OS/System/app/main.py` remains unparseable because active
  Price Vector/eBay WIP contains an unterminated f-string at line 650.
- Eight historical backup Python files are also unparseable.
- These failures predate Phase 1 and are recorded in the baseline.

No live marketplace, upload, inventory mutation, database write, or production
workflow action was run.
