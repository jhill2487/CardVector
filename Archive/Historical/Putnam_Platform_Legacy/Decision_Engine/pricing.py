"""Pricing module for Putnam Platform Decision Engine.

This module contains the existing ladder pricing behavior from the Bulk Price
Engine. Keep changes here behavior-neutral until pricing output changes are
explicitly requested.
"""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

from .models import Recommendation


DEFAULT_LADDER = {
    "0.99": "0.99",
    "1.49": "0.99",
    "1.59": "1.09",
    "1.69": "1.19",
    "1.79": "1.29",
    "1.99": "1.49",
    "2.49": "1.99",
    "2.99": "2.49",
}


def money(value) -> Decimal:
    if value is None:
        raise InvalidOperation("None")
    s = str(value).strip().replace("$", "").replace(",", "")
    if s == "":
        raise InvalidOperation("blank")
    return Decimal(s).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def money_str(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}"


def load_ladder(config_path: Path | None = None) -> dict[str, str]:
    if config_path and config_path.exists():
        data = json.loads(config_path.read_text(encoding="utf-8-sig"))
        ladder = data.get("price_ladder", data)
    else:
        ladder = DEFAULT_LADDER
    return {money_str(money(k)): money_str(money(v)) for k, v in ladder.items()}


def apply_ladder(records, ladder):
    processed = []
    invalid = []
    for rec in records:
        try:
            old = money(rec["old_price_raw"])
        except Exception as e:
            rec2 = dict(rec)
            rec2.update({"status": "INVALID_PRICE", "old_price": "", "new_price": "", "change": "", "reason": str(e)})
            invalid.append(rec2)
            continue
        key = money_str(old)
        if key in ladder:
            new = money(ladder[key])
            changed = new != old
            status = "CHANGE" if changed else "UNCHANGED"
            reason = f"ladder {key} -> {money_str(new)}" if changed else "ladder leaves price unchanged"
        else:
            new = old
            changed = False
            status = "UNCHANGED"
            reason = "price not in ladder"
        rec2 = dict(rec)
        rec2.update({
            "old_price": money_str(old),
            "new_price": money_str(new),
            "change": money_str(new - old),
            "status": status,
            "reason": reason,
        })
        processed.append(rec2)
    return processed, invalid


def build_recommendations(processed, invalid) -> list[Recommendation]:
    recommendations: list[Recommendation] = []
    for rec in processed:
        recommendations.append(
            Recommendation(
                module="pricing",
                item_id=str(rec.get("item_number") or rec.get("sku") or rec.get("line_no") or ""),
                status=str(rec.get("status", "")),
                action="revise_price" if rec.get("status") == "CHANGE" else "hold_price",
                confidence=1.0,
                reason=str(rec.get("reason", "")),
                current_value=str(rec.get("old_price", "")),
                recommended_value=str(rec.get("new_price", "")),
                metadata={
                    "line_no": rec.get("line_no"),
                    "title": rec.get("title"),
                    "sku": rec.get("sku"),
                    "change": rec.get("change"),
                },
            )
        )

    for rec in invalid:
        recommendations.append(
            Recommendation(
                module="pricing",
                item_id=str(rec.get("item_number") or rec.get("sku") or rec.get("line_no") or ""),
                status="INVALID_PRICE",
                action="review_manually",
                confidence=0.0,
                reason=str(rec.get("reason", "")),
                metadata={
                    "line_no": rec.get("line_no"),
                    "title": rec.get("title"),
                    "sku": rec.get("sku"),
                    "old_price_raw": rec.get("old_price_raw"),
                },
            )
        )

    return recommendations


def evaluate_records(records, config_path: Path | None = None):
    ladder = load_ladder(config_path)
    processed, invalid = apply_ladder(records, ladder)
    recommendations = build_recommendations(processed, invalid)
    return processed, invalid, ladder, recommendations
