from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from .business_profile import load_business_profile
from .module_registry import load_modules
from .recommendation import Recommendation


class DecisionEngine:
    """Read-only orchestration layer for future Putnam OS recommendations."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.profile = load_business_profile(self.root)
        self.modules = load_modules()

    def evaluate_modules(self) -> list[dict[str, Any]]:
        context = {
            "root": self.root,
            "profile": self.profile,
            "inventory_snapshot": self.root / "Putnam_OS" / "System" / "data" / "carduploader_inventory_snapshot.csv",
            "completed_jobs": self.root / "Putnam_OS" / "Completed Jobs",
        }
        results = []
        for module in self.modules:
            try:
                result = module.evaluate(context, self.profile)
            except Exception as exc:
                result = {
                    "module_name": getattr(module, "MODULE_NAME", module.__name__.split(".")[-1]),
                    "status": "error",
                    "score": 0,
                    "confidence": 0,
                    "notes": [str(exc)],
                }
            results.append(self._normalize_module_result(result))
        return results

    def health(self) -> dict[str, Any]:
        results = self.evaluate_modules()
        active = [r for r in results if r["status"] in {"active", "available"}]
        placeholders = [r for r in results if r["status"] == "not_implemented"]
        errors = [r for r in results if r["status"] == "error"]
        return {
            "business_goal": self.profile.get("primary_goal", ""),
            "secondary_goal": self.profile.get("secondary_goal", ""),
            "risk_tolerance": self.profile.get("risk_tolerance", ""),
            "modules_loaded": len(results),
            "modules_active": len(active),
            "placeholders": len(placeholders),
            "errors": len(errors),
            "last_engine_check": datetime.now().isoformat(timespec="seconds"),
            "module_results": results,
        }

    def build_recommendation(self, results: list[dict[str, Any]]) -> Recommendation:
        scores = {r["module_name"]: float(r.get("score", 0) or 0) for r in results}
        confidence_values = [float(r.get("confidence", 0) or 0) for r in results if r["status"] != "not_implemented"]
        confidence = sum(confidence_values) / len(confidence_values) if confidence_values else 0
        notes: list[str] = []
        for result in results:
            notes.extend(str(n) for n in result.get("notes", []))
        return Recommendation(
            card_key="portfolio",
            recommendation="Decision Engine framework check complete. No automated action taken.",
            confidence=round(confidence, 3),
            scores=scores,
            notes=notes,
            source_modules=[r["module_name"] for r in results],
        )

    def run_check(self, write_log: bool = True) -> dict[str, Any]:
        health = self.health()
        recommendation = self.build_recommendation(health["module_results"])
        health["recommendation"] = recommendation.to_dict()
        log_path = None
        if write_log:
            log_path = self.write_log(health)
        health["log_path"] = str(log_path) if log_path else ""
        return health

    def write_log(self, health: dict[str, Any]) -> Path:
        logs = self.root / "Putnam_OS" / "System" / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = logs / f"Decision_Engine_Log_{stamp}.txt"
        lines = [
            "Putnam OS Decision Engine Check",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            f"Business goal: {health['business_goal']}",
            f"Secondary goal: {health['secondary_goal']}",
            f"Risk tolerance: {health['risk_tolerance']}",
            f"Modules loaded: {health['modules_loaded']}",
            f"Modules active: {health['modules_active']}",
            f"Placeholders: {health['placeholders']}",
            f"Errors: {health['errors']}",
            "",
            "Module results:",
        ]
        for result in health["module_results"]:
            lines.append(f"- {result['module_name']}: {result['status']} score={result['score']} confidence={result['confidence']}")
            for note in result.get("notes", []):
                lines.append(f"  - {note}")
        rec = health["recommendation"]
        lines.extend([
            "",
            "Recommendation:",
            f"  card_key: {rec['card_key']}",
            f"  recommendation: {rec['recommendation']}",
            f"  confidence: {rec['confidence']}",
        ])
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    @staticmethod
    def _normalize_module_result(result: dict[str, Any]) -> dict[str, Any]:
        return {
            "module_name": str(result.get("module_name", "unknown")),
            "status": str(result.get("status", "unknown")),
            "score": float(result.get("score", 0) or 0),
            "confidence": float(result.get("confidence", 0) or 0),
            "notes": list(result.get("notes", [])),
        }
