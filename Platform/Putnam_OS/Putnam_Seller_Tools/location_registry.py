from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def _bootstrap_repo_import_path() -> Path | None:
    current = Path(__file__).resolve()
    for candidate in [current.parent, *current.parents]:
        if (
            (candidate / ".putnam_root").exists()
            or ((candidate / "AGENTS.md").exists() and (candidate / "Docs" / "AGENTS.md").exists())
        ):
            if str(candidate) not in sys.path:
                sys.path.insert(0, str(candidate))
            return candidate
    return None


_bootstrap_repo_import_path()

try:
    from Platform.putnam_paths import PUTNAM_OS_DIR, ROOT
except Exception:
    PUTNAM_OS_DIR = None
    ROOT = None


REGISTRY_VERSION = 1
LOCATION_RE = re.compile(r"^ETB-(\d{2,3})-([A-Z])$")

GAME_ALIASES = {
    "magic": "magic",
    "mtg": "magic",
    "magic the gathering": "magic",
    "one piece": "one_piece",
    "onepiece": "one_piece",
    "op": "one_piece",
    "pokemon": "pokemon",
    "pokémon": "pokemon",
}

DEFAULT_GAME_NAMES = {
    "magic": "Magic / MTG",
    "one_piece": "One Piece",
    "pokemon": "Pokemon",
}


def project_root() -> Path:
    if ROOT is not None:
        return ROOT
    env = os.environ.get("USERENVIRONMENT")
    if env and Path(env).exists():
        return Path(env)
    user_profile = os.environ.get("USERPROFILE")
    if user_profile:
        candidate = Path(user_profile) / "OneDrive" / "PutnamCollectibles"
        if candidate.exists():
            return candidate
    current = Path.cwd()
    for candidate in [current, *current.parents]:
        if (candidate / "AGENTS.md").exists():
            return candidate
    return current


def registry_path(root: Path | None = None) -> Path:
    root = root or project_root()
    if ROOT is not None and PUTNAM_OS_DIR is not None and Path(root).resolve() == ROOT.resolve():
        return PUTNAM_OS_DIR / "System" / "config" / "location_registry.json"
    if (root / "Platform" / "Putnam_OS").exists():
        return root / "Platform" / "Putnam_OS" / "System" / "config" / "location_registry.json"
    return root / "Putnam_OS" / "System" / "config" / "location_registry.json"


def canonical_game(value: str | None) -> str:
    normalized = str(value or "").strip().lower()
    if not normalized:
        return "unknown"
    return GAME_ALIASES.get(normalized, normalized.replace(" ", "_"))


def display_game(game: str | None) -> str:
    canonical = canonical_game(game)
    return DEFAULT_GAME_NAMES.get(canonical, canonical.replace("_", " ").title())


def validate_location(location: str) -> str:
    value = str(location or "").strip().upper()
    match = LOCATION_RE.match(value)
    if not match:
        raise ValueError("Batch Location must use ETB-###-Letter format, example ETB-001-A.")
    return f"ETB-{int(match.group(1)):03d}-{match.group(2)}"


def _default_registry() -> dict[str, Any]:
    now = datetime.now().isoformat(timespec="seconds")
    return {
        "version": REGISTRY_VERSION,
        "updated_at": now,
        "rule": "User SKU = Batch Location",
        "games": {
            "magic": {
                "display_name": "Magic / MTG",
                "current_location": "ETB-004-A",
                "used_locations": ["ETB-004-A"],
            },
            "one_piece": {
                "display_name": "One Piece",
                "current_location": "ETB-005-A",
                "used_locations": ["ETB-005-A"],
            },
            "pokemon": {
                "display_name": "Pokemon",
                "current_location": "ETB-001-A",
                "used_locations": ["ETB-001-A"],
            },
        },
        "history": [
            {
                "timestamp": now,
                "game": "magic",
                "location": "ETB-004-A",
                "source": "initial_registry_seed",
                "status": "assigned",
                "note": "Category location established during SKU repair planning.",
            },
            {
                "timestamp": now,
                "game": "one_piece",
                "location": "ETB-005-A",
                "source": "initial_registry_seed",
                "status": "assigned",
                "note": "Category location established during SKU repair planning.",
            },
        ],
    }


def load_registry(root: Path | None = None) -> dict[str, Any]:
    path = registry_path(root)
    if not path.exists():
        return _default_registry()
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        data = _default_registry()
    data.setdefault("version", REGISTRY_VERSION)
    data.setdefault("rule", "User SKU = Batch Location")
    data.setdefault("games", {})
    data.setdefault("history", [])
    for entry in data.get("games", {}).values():
        current = str(entry.get("current_location") or "").strip()
        if current:
            try:
                entry["current_location"] = validate_location(current)
            except ValueError:
                pass
        normalized_used = []
        for location in entry.get("used_locations", []) or []:
            try:
                normalized_used.append(validate_location(location))
            except ValueError:
                normalized_used.append(str(location or "").strip().upper())
        entry["used_locations"] = sorted(set(normalized_used), key=location_sort_key)
    return data


def save_registry(registry: dict[str, Any], root: Path | None = None) -> Path:
    path = registry_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    registry["updated_at"] = datetime.now().isoformat(timespec="seconds")
    path.write_text(json.dumps(registry, indent=2), encoding="utf-8")
    return path


def location_sort_key(location: str) -> tuple[int, str]:
    match = LOCATION_RE.match(str(location or "").strip().upper())
    if not match:
        return (999, str(location))
    return (int(match.group(1)), match.group(2))


def next_location_after(location: str) -> str:
    value = validate_location(location)
    match = LOCATION_RE.match(value)
    if not match:
        return value
    box = int(match.group(1))
    letter = match.group(2)
    if letter < "Z":
        return f"ETB-{box:03d}-{chr(ord(letter) + 1)}"
    return f"ETB-{box + 1:03d}-A"


def suggest_next_location(game: str | None, root: Path | None = None) -> str:
    registry = load_registry(root)
    canonical = canonical_game(game)
    entry = registry.get("games", {}).get(canonical, {})
    used = [str(v).strip().upper() for v in entry.get("used_locations", []) if str(v).strip()]
    current = str(entry.get("current_location", "")).strip().upper()
    candidates = [v for v in used + ([current] if current else []) if LOCATION_RE.match(v)]
    if candidates:
        latest = sorted(set(candidates), key=location_sort_key)[-1]
        return next_location_after(latest)
    return "ETB-001-A"


def shared_registry_path(root: Path | None = None) -> Path | None:
    if root is None:
        return None
    root = Path(root)
    if ROOT is not None and root.resolve() == ROOT.resolve():
        return None
    return root / "Platform" / "Putnam_OS" / "System" / "data" / "inventory" / "etb_location_registry.json"


def sync_shared_registry_if_configured() -> None:
    url = os.environ.get("CARDVECTOR_SUPABASE_URL") or os.environ.get("SUPABASE_URL") or ""
    key = (
        os.environ.get("CARDVECTOR_SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or ""
    )
    if not url.strip() or not key.strip():
        return
    try:
        from Platform.Putnam_OS.System.tools.mobile_capture_queue import sync_cloud_location_registry

        sync_cloud_location_registry()
    except Exception:
        pass


def record_location(
    location: str,
    game: str | None,
    source: str,
    root: Path | None = None,
    status: str = "assigned",
    note: str = "",
    total_listings: int | None = None,
) -> Path:
    value = validate_location(location)
    canonical = canonical_game(game)
    registry = load_registry(root)
    games = registry.setdefault("games", {})
    entry = games.setdefault(
        canonical,
        {
            "display_name": display_game(canonical),
            "current_location": "",
            "used_locations": [],
        },
    )
    entry["display_name"] = entry.get("display_name") or display_game(canonical)
    entry["current_location"] = value
    used = {str(v).strip().upper() for v in entry.get("used_locations", []) if str(v).strip()}
    used.add(value)
    entry["used_locations"] = sorted(used, key=location_sort_key)
    event = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "game": canonical,
        "location": value,
        "source": source,
        "status": status,
        "note": note,
    }
    if total_listings is not None:
        event["total_listings"] = int(total_listings)
    registry.setdefault("history", []).append(event)
    path = save_registry(registry, root)
    if total_listings is not None:
        try:
            from Platform.Putnam_OS.System.app.inventory_locations import record_completed_batch_location

            record_completed_batch_location(
                value,
                int(total_listings),
                game=canonical,
                source=source,
                note=note,
                path=shared_registry_path(root),
            )
            if root is None or (ROOT is not None and Path(root).resolve() == ROOT.resolve()):
                sync_shared_registry_if_configured()
        except Exception:
            pass
    return path


def registry_rows(root: Path | None = None) -> list[dict[str, str]]:
    registry = load_registry(root)
    rows: list[dict[str, str]] = []
    for game, entry in sorted(registry.get("games", {}).items()):
        rows.append(
            {
                "game": game,
                "display_name": str(entry.get("display_name") or display_game(game)),
                "current_location": str(entry.get("current_location") or ""),
                "used_locations": ", ".join(entry.get("used_locations", [])),
                "suggested_next_location": suggest_next_location(game, root),
            }
        )
    return rows


def registry_summary_text(root: Path | None = None) -> str:
    rows = registry_rows(root)
    if not rows:
        return "No batch locations registered yet."
    lines = ["User SKU = Batch Location", ""]
    for row in rows:
        lines.append(
            f"{row['display_name']}: current {row['current_location'] or '(blank)'}, "
            f"next suggested {row['suggested_next_location']}"
        )
    return "\n".join(lines)
