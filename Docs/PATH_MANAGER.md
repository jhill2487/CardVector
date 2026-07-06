# Platform Path Manager v1.0

`Platform/putnam_paths.py` is the central source of truth for repository paths
after the root folder reorganization.

The repository now separates code, business files, generated data, docs, tools,
archives, and work-session notes into top-level folders:

- `Platform/`
- `Business/`
- `Data/`
- `Docs/`
- `Tools/`
- `Archive/`
- `Work_Sessions/`

New code should import paths from `Platform.putnam_paths` instead of assuming
old root-level folders still exist.

Example:

```python
from Platform.putnam_paths import data_path, platform_path

imports_dir = data_path("Imports")
putnam_os_dir = platform_path("Putnam_OS")
```

The path manager returns `pathlib.Path` objects and can locate the repository
root by checking `.putnam_root`, the root `AGENTS.md` stub, `Docs/AGENTS.md`,
and the known folder layout.

Rule: new code should not assume `Imports`, `Exports`, `logs`, `Media`, or
`processed` exist at the repository root. Use `Data/Imports`, `Data/Exports`,
`Data/Logs`, `Data/Media`, and `Data/Processed` through
`Platform/putnam_paths.py`.
