from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Recommendation:
    card_key: str
    recommendation: str
    confidence: float
    scores: dict[str, float] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    source_modules: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
