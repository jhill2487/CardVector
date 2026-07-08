from __future__ import annotations

import os
from pathlib import Path


def _looks_like_repo_root(path: Path) -> bool:
    path = path.expanduser().resolve()
    return (
        (path / ".putnam_root").exists()
        or (
            (path / "AGENTS.md").exists()
            and (path / "Docs" / "AGENTS.md").exists()
            and (path / "Platform").is_dir()
            and (path / "Data").is_dir()
        )
    )


def _candidate_roots() -> list[Path]:
    candidates: list[Path] = []
    for env_name in ("PUTNAM_ROOT", "USERENVIRONMENT"):
        value = os.environ.get(env_name)
        if value:
            candidates.append(Path(value))
    candidates.extend([Path.cwd(), Path(__file__).resolve()])
    return candidates


def repo_root() -> Path:
    for start in _candidate_roots():
        try:
            resolved = start.expanduser().resolve()
        except OSError:
            continue
        search = [resolved] if resolved.is_dir() else [resolved.parent]
        search.extend(search[0].parents)
        for candidate in search:
            if _looks_like_repo_root(candidate):
                return candidate
    raise RuntimeError(
        "Could not locate PutnamCollectibles root. Expected .putnam_root, "
        "AGENTS.md plus Docs/AGENTS.md, or the known Platform/Data layout."
    )


ROOT = repo_root()

PLATFORM_DIR = ROOT / "Platform"
BUSINESS_DIR = ROOT / "Business"
DATA_DIR = ROOT / "Data"
DOCS_DIR = ROOT / "Docs"
TOOLS_DIR = ROOT / "Tools"
ARCHIVE_DIR = ROOT / "Archive"
WORK_SESSIONS_DIR = ROOT / "Work_Sessions"

PUTNAM_OS_DIR = PLATFORM_DIR / "Putnam_OS"
PUTNAM_SCANNER_DIR = PLATFORM_DIR / "Putnam_Scanner"
POKEMON_LOOKUP_DIR = PLATFORM_DIR / "Pokemon_Live_Price_Lookup"
TCG_AUTOMATION_DIR = PLATFORM_DIR / "TCG_Automation"
PUTNAM_PLATFORM_DIR = PLATFORM_DIR / "Putnam_Platform"

BUSINESS_EBAY_STORE_ITEMS_DIR = BUSINESS_DIR / "eBay_Store_Items"
BUSINESS_INVENTORY_DIR = BUSINESS_DIR / "Inventory"

DATA_IMPORTS_DIR = DATA_DIR / "Imports"
DATA_EXPORTS_DIR = DATA_DIR / "Exports"
DATA_LOGS_DIR = DATA_DIR / "Logs"
DATA_MEDIA_DIR = DATA_DIR / "Media"
DATA_PROCESSED_DIR = DATA_DIR / "Processed"
DATA_CONFIG_DIR = DATA_DIR / "Config"


def platform_path(*parts: str | os.PathLike[str]) -> Path:
    return PLATFORM_DIR.joinpath(*parts)


def business_path(*parts: str | os.PathLike[str]) -> Path:
    return BUSINESS_DIR.joinpath(*parts)


def data_path(*parts: str | os.PathLike[str]) -> Path:
    return DATA_DIR.joinpath(*parts)


def docs_path(*parts: str | os.PathLike[str]) -> Path:
    return DOCS_DIR.joinpath(*parts)


def tools_path(*parts: str | os.PathLike[str]) -> Path:
    return TOOLS_DIR.joinpath(*parts)


def archive_path(*parts: str | os.PathLike[str]) -> Path:
    return ARCHIVE_DIR.joinpath(*parts)


def work_sessions_path(*parts: str | os.PathLike[str]) -> Path:
    return WORK_SESSIONS_DIR.joinpath(*parts)


def ensure_dir(path: str | os.PathLike[str]) -> Path:
    resolved = Path(path)
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


KEY_PATHS = {
    "ROOT": ROOT,
    "PLATFORM_DIR": PLATFORM_DIR,
    "BUSINESS_DIR": BUSINESS_DIR,
    "DATA_DIR": DATA_DIR,
    "DOCS_DIR": DOCS_DIR,
    "TOOLS_DIR": TOOLS_DIR,
    "ARCHIVE_DIR": ARCHIVE_DIR,
    "WORK_SESSIONS_DIR": WORK_SESSIONS_DIR,
    "PUTNAM_OS_DIR": PUTNAM_OS_DIR,
    "PUTNAM_SCANNER_DIR": PUTNAM_SCANNER_DIR,
    "POKEMON_LOOKUP_DIR": POKEMON_LOOKUP_DIR,
    "TCG_AUTOMATION_DIR": TCG_AUTOMATION_DIR,
    "PUTNAM_PLATFORM_DIR": PUTNAM_PLATFORM_DIR,
    "BUSINESS_EBAY_STORE_ITEMS_DIR": BUSINESS_EBAY_STORE_ITEMS_DIR,
    "BUSINESS_INVENTORY_DIR": BUSINESS_INVENTORY_DIR,
    "DATA_IMPORTS_DIR": DATA_IMPORTS_DIR,
    "DATA_EXPORTS_DIR": DATA_EXPORTS_DIR,
    "DATA_LOGS_DIR": DATA_LOGS_DIR,
    "DATA_MEDIA_DIR": DATA_MEDIA_DIR,
    "DATA_PROCESSED_DIR": DATA_PROCESSED_DIR,
    "DATA_CONFIG_DIR": DATA_CONFIG_DIR,
}


def _main() -> int:
    for name, path in KEY_PATHS.items():
        status = "exists" if path.exists() else "missing"
        print(f"{name}: {path} [{status}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
