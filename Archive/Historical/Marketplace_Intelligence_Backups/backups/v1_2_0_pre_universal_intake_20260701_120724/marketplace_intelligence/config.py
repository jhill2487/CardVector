from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = PACKAGE_ROOT / "config"
REPORTS_DIR = PACKAGE_ROOT / "reports"
RECENT_FILES = CONFIG_DIR / "recent_files.json"


@dataclass
class AppConfig:
    pricing_profile: dict[str, Any]
    business_profile: dict[str, Any]
    market_provider: dict[str, Any]


def load_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8-sig"))
    return dict(default or {})


def save_json(path: Path, data: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def load_app_config(config_dir: Path | None = None) -> AppConfig:
    directory = config_dir or CONFIG_DIR
    return AppConfig(
        pricing_profile=load_json(directory / "pricing_profile.json"),
        business_profile=load_json(directory / "business_profile.json"),
        market_provider=load_json(directory / "market_provider.json"),
    )


def decimal_setting(data: dict[str, Any], key: str, default: str) -> Decimal:
    return Decimal(str(data.get(key, default)))


def load_recent_files() -> list[str]:
    data = load_json(RECENT_FILES, {"recent_files": []})
    return [str(path) for path in data.get("recent_files", [])]


def remember_recent_file(path: Path, limit: int = 8) -> None:
    files = [str(Path(path))]
    for existing in load_recent_files():
        if existing not in files:
            files.append(existing)
    save_json(RECENT_FILES, {"recent_files": files[:limit]})
