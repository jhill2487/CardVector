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


def _business_profile_type():
    try:
        from Platform.cardvector.marketplace_intelligence.business_profile import (
            BusinessProfile,
        )
    except ModuleNotFoundError as exc:
        if exc.name != "Platform":
            raise
        return None
    return BusinessProfile


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
    legacy_pricing = load_json(directory / "pricing_profile.json")
    business_data = load_json(directory / "business_profile.json")
    BusinessProfile = _business_profile_type()
    if BusinessProfile is not None:
        business_profile = BusinessProfile.from_mapping(
            business_data,
            legacy_pricing,
        )
        business_data = business_profile.to_dict()
        legacy_pricing = business_profile.price_vector_profile()
    return AppConfig(
        pricing_profile=legacy_pricing,
        business_profile=business_data,
        market_provider=load_json(directory / "market_provider.json"),
    )


def save_pricing_profile(
    pricing_profile: dict[str, Any],
    config_dir: Path | None = None,
) -> Path:
    """Persist pricing settings into the canonical Business Profile."""

    directory = config_dir or CONFIG_DIR
    business_path = directory / "business_profile.json"
    business_data = load_json(business_path)
    BusinessProfile = _business_profile_type()
    if BusinessProfile is None:
        return save_json(directory / "pricing_profile.json", pricing_profile)
    normalized = BusinessProfile.from_mapping(
        business_data,
        load_json(directory / "pricing_profile.json"),
    ).to_dict()
    normalized.setdefault("pricing_policy", {})["price_vector"] = dict(
        pricing_profile
    )
    normalized["pricing_policy"]["minimum_price"] = str(
        pricing_profile.get(
            "minimum_price",
            normalized["pricing_policy"].get("minimum_price", "0.01"),
        )
    )
    normalized["pricing_policy"]["rounding_rule"] = str(
        pricing_profile.get(
            "rounding_rule",
            normalized["pricing_policy"].get("rounding_rule", "nearest_cent"),
        )
    )
    return save_json(business_path, normalized)


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
