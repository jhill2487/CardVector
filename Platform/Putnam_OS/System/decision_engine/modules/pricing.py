from __future__ import annotations

from pathlib import Path


MODULE_NAME = "pricing"


def evaluate(context, profile):
    completed = Path(context["completed_jobs"])
    notes = []
    score = 0.0
    confidence = 0.5
    status = "available"
    if completed.exists():
        reports = sorted(
            list(completed.glob("Pricing_Analysis_*/summary.txt")) + list(completed.glob("Price_Revision_*/price_revision_report_*.txt")),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if reports:
            latest = reports[0]
            notes.append(f"Latest pricing summary found: {latest}")
            score = 1.0
            confidence = 0.8
            status = "active"
        else:
            notes.append("No prior pricing summary found. Pricing logic was not run by this check.")
    else:
        notes.append("Completed Jobs folder not found.")
    return {
        "module_name": MODULE_NAME,
        "status": status,
        "score": score,
        "confidence": confidence,
        "notes": notes,
    }
