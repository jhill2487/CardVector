"""Single orchestration layer for Putnam Platform decisions."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import pricing
from .models import Recommendation


VERSION = "3.4.0"


DEFAULT_BUSINESS_PROFILE = {
    "version": VERSION,
    "goals": {
        "cash_flow": 0.4,
        "profit": 0.4,
        "growth": 0.2,
    },
    "minimum_profit": "0.50",
    "risk_tolerance": "medium",
    "default_marketplace": "eBay",
}


@dataclass(slots=True)
class DecisionResult:
    """Decision Engine result bundle used by current and future modules."""

    processed: list[dict[str, Any]] = field(default_factory=list)
    invalid: list[dict[str, Any]] = field(default_factory=list)
    ladder: dict[str, str] = field(default_factory=dict)
    recommendations: list[Recommendation] = field(default_factory=list)
    business_profile: dict[str, Any] = field(default_factory=dict)


def resolve_root() -> Path:
    env = os.environ.get("USERENVIRONMENT")
    if env and Path(env).exists():
        return Path(env)
    fallback = Path.home() / "OneDrive" / "PutnamCollectibles"
    if fallback.exists():
        return fallback
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".putnam_root").exists():
            return parent
    raise SystemExit("Could not locate PutnamCollectibles root. Set USERENVIRONMENT first.")


class DecisionEngine:
    """Coordinates Putnam decision modules without binding them to the UI."""

    def __init__(self, root: Path | None = None, business_profile_path: Path | None = None):
        self.root = root or resolve_root()
        self.package_dir = Path(__file__).resolve().parent
        self.business_profile_path = business_profile_path or (self.package_dir / "business_profile.json")
        self.business_profile = self.load_business_profile()

    def load_business_profile(self) -> dict[str, Any]:
        if self.business_profile_path.exists():
            return json.loads(self.business_profile_path.read_text(encoding="utf-8-sig"))
        return dict(DEFAULT_BUSINESS_PROFILE)

    def evaluate_pricing(self, records, pricing_config_path: Path | None = None) -> DecisionResult:
        processed, invalid, ladder, recommendations = pricing.evaluate_records(records, pricing_config_path)
        return DecisionResult(
            processed=processed,
            invalid=invalid,
            ladder=ladder,
            recommendations=recommendations,
            business_profile=self.business_profile,
        )


def evaluate_pricing(records, pricing_config_path: Path | None = None, root: Path | None = None) -> DecisionResult:
    return DecisionEngine(root=root).evaluate_pricing(records, pricing_config_path)
