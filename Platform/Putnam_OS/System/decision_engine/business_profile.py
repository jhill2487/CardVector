from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_BUSINESS_PROFILE = {
    "primary_goal": "cash_flow",
    "secondary_goal": "profit",
    "risk_tolerance": "low",
    "minimum_profit": 0.25,
    "default_marketplace": "ebay",
}


def business_profile_path(root: Path) -> Path:
    return root / "Putnam_OS" / "System" / "config" / "business_profile.json"


def load_business_profile(root: Path) -> dict[str, Any]:
    path = business_profile_path(root)
    if not path.exists():
        return dict(DEFAULT_BUSINESS_PROFILE)
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    profile = dict(DEFAULT_BUSINESS_PROFILE)
    profile.update({k: v for k, v in data.items() if v is not None})
    return profile
