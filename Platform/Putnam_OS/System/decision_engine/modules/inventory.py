from __future__ import annotations

import csv
from pathlib import Path


MODULE_NAME = "inventory"


def evaluate(context, profile):
    snapshot = Path(context["inventory_snapshot"])
    if not snapshot.exists():
        return {
            "module_name": MODULE_NAME,
            "status": "available",
            "score": 0,
            "confidence": 0.4,
            "notes": [f"Inventory snapshot not found: {snapshot}"],
        }
    with snapshot.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    qty_total = 0
    listed = 0
    tcgs = {}
    for row in rows:
        try:
            qty = int(float(str(row.get("Qty", "0") or "0").replace(",", "")))
        except Exception:
            qty = 0
        qty_total += qty
        if str(row.get("Status", "")).strip().lower() in {"listed", "active", "for sale", "live"}:
            listed += 1
        tcg = row.get("TCG") or "(blank)"
        tcgs[tcg] = tcgs.get(tcg, 0) + qty
    notes = [
        f"Snapshot: {snapshot}",
        f"Rows: {len(rows)}",
        f"Listed rows: {listed}",
        f"Quantity total: {qty_total}",
        "TCG quantity counts: " + ", ".join(f"{k}={v}" for k, v in sorted(tcgs.items())),
    ]
    return {
        "module_name": MODULE_NAME,
        "status": "active",
        "score": min(1.0, qty_total / 1000) if qty_total else 0,
        "confidence": 0.9,
        "notes": notes,
    }
