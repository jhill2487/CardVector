"""Shared data models for Putnam Platform decision modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class Recommendation:
    """A normalized recommendation emitted by one Decision Engine module."""

    module: str
    item_id: str
    status: str
    action: str
    confidence: float = 0.0
    reason: str = ""
    current_value: str = ""
    recommended_value: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
