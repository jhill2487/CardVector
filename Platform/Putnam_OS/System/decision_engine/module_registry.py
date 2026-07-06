from __future__ import annotations

from importlib import import_module
from typing import Any


MODULE_NAMES = [
    "pricing",
    "inventory",
    "marketplace",
    "promotion",
    "velocity",
    "market_signals",
    "content",
]


def load_modules() -> list[Any]:
    modules = []
    for name in MODULE_NAMES:
        modules.append(import_module(f"decision_engine.modules.{name}"))
    return modules
