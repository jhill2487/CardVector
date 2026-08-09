from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass, field
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Iterable, Mapping

from Platform.cardvector.marketplace_intelligence.models import ExistingListingEvaluation

from .inventory import InventoryItem


MONEY = Decimal("0.01")
DEFAULT_MIN_ABSOLUTE_DELTA = Decimal("0.01")
DEFAULT_MIN_PERCENT_DELTA = Decimal("0.00")
DEFAULT_MAX_PERCENT_MOVE = Decimal("25.00")

PLAN_STATUS_DRY_RUN = "dry_run"
PLAN_STATUS_APPROVED = "approved"
PLAN_STATUS_BLOCKED = "blocked"

APPLY_READY_STATUSES = {PLAN_STATUS_APPROVED}


class CardUploaderPriceUpdateError(RuntimeError):
    """Raised when a CardUploader price-update plan is unsafe to apply."""


@dataclass(frozen=True)
class CardUploaderPriceUpdatePolicy:
    """Safety policy for CardUploader-managed eBay price changes."""

    min_absolute_delta: Decimal = DEFAULT_MIN_ABSOLUTE_DELTA
    min_percent_delta: Decimal = DEFAULT_MIN_PERCENT_DELTA
    max_percent_move: Decimal = DEFAULT_MAX_PERCENT_MOVE
    minimum_price: Decimal = Decimal("0.99")
    require_positive_quantity: bool = True
    allow_decreases: bool = True
    allow_increases: bool = True


@dataclass(frozen=True)
class CardUploaderPriceUpdatePlan:
    """One approved-or-pending price-only CardUploader update."""

    inventory_id: str
    row_number: int
    title: str
    current_price: Decimal
    recommended_price: Decimal
    price_delta: Decimal
    percent_delta: Decimal
    quantity: int
    status: str
    reason_codes: tuple[str, ...] = ()
    review_decision: str = ""
    review_priority: str = ""
    search_query: str = ""
    listing_reference: str = ""
    user_sku: str = ""
    catalog_sku: str = ""
    tcgplayer_sku: str = ""
    tcgplayer_product_id: str = ""
    set_name: str = ""
    card_number: str = ""
    condition: str = ""
    variant: str = ""
    finish: str = ""
    source_file: str = ""
    notes: tuple[str, ...] = ()
    raw_evaluation: Mapping[str, Any] = field(default_factory=dict)

    @property
    def is_apply_ready(self) -> bool:
        return self.status in APPLY_READY_STATUSES

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for key in ("current_price", "recommended_price", "price_delta", "percent_delta"):
            payload[key] = money_text(payload[key])
        payload["reason_codes"] = list(self.reason_codes)
        payload["notes"] = list(self.notes)
        payload["apply_ready"] = self.is_apply_ready
        return payload


def parse_money(value: Any) -> Decimal:
    raw = str(value or "").replace("$", "").replace(",", "").strip()
    if not raw:
        return Decimal("0.00")
    try:
        return Decimal(raw).quantize(MONEY, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        return Decimal("0.00")


def money_text(value: Decimal) -> str:
    return str(value.quantize(MONEY, rounding=ROUND_HALF_UP))


def percent_delta(current: Decimal, recommended: Decimal) -> Decimal:
    if current <= 0:
        return Decimal("0.00")
    return ((recommended - current) / current * Decimal("100")).quantize(MONEY, rounding=ROUND_HALF_UP)


def ebay_sold_search_query(item: InventoryItem) -> str:
    """Build a deterministic sold-comps query from CardUploader identity fields."""

    parts = [
        item.title,
        item.set_name,
        item.card_number,
        item.condition,
        item.variant,
        item.finish,
    ]
    seen: set[str] = set()
    tokens: list[str] = []
    for part in parts:
        cleaned = " ".join(str(part or "").split())
        key = cleaned.lower()
        existing = " ".join(tokens).lower()
        if cleaned and key not in seen and key not in existing:
            tokens.append(cleaned)
            seen.add(key)
    return " ".join(tokens)


def carduploader_price_identity(item: InventoryItem) -> str:
    """Prefer CardUploader's stable card identity over operator location labels."""

    return (
        item.source_id
        or item.catalog_sku
        or item.tcgplayer_sku
        or item.tcgplayer_product_id
        or item.inventory_id
    )


def _block(status: str, notes: list[str]) -> str:
    return PLAN_STATUS_BLOCKED if notes else status


def build_price_update_plan(
    item: InventoryItem,
    evaluation: ExistingListingEvaluation,
    *,
    policy: CardUploaderPriceUpdatePolicy | None = None,
    approved: bool = False,
) -> CardUploaderPriceUpdatePlan:
    """Create a price-only update plan; this never mutates CardUploader."""

    active_policy = policy or CardUploaderPriceUpdatePolicy()
    current = parse_money(item.price)
    recommended = parse_money(evaluation.recommended_price)
    delta = (recommended - current).quantize(MONEY, rounding=ROUND_HALF_UP)
    pct = percent_delta(current, recommended)
    quantity = item.quantity_value
    notes: list[str] = []
    status = PLAN_STATUS_APPROVED if approved else PLAN_STATUS_DRY_RUN

    if recommended < active_policy.minimum_price:
        notes.append("recommended_below_minimum_price")
    if active_policy.require_positive_quantity and quantity <= 0:
        notes.append("non_positive_quantity")
    if delta < 0 and not active_policy.allow_decreases:
        notes.append("decrease_not_allowed")
    if delta > 0 and not active_policy.allow_increases:
        notes.append("increase_not_allowed")
    if abs(delta) < active_policy.min_absolute_delta:
        notes.append("below_min_absolute_delta")
    if abs(pct) < active_policy.min_percent_delta:
        notes.append("below_min_percent_delta")
    if current > 0 and abs(pct) > active_policy.max_percent_move:
        notes.append("exceeds_max_percent_move")
    if str(evaluation.match_confidence or "").lower() not in {"high", "strong"}:
        notes.append("match_confidence_requires_review")
    if str(evaluation.review_decision or "").lower() in {"manual_review", "do_not_list"}:
        notes.append("marketplace_intelligence_requires_review")

    return CardUploaderPriceUpdatePlan(
        inventory_id=carduploader_price_identity(item),
        row_number=item.row_number,
        title=item.title,
        current_price=current,
        recommended_price=recommended,
        price_delta=delta,
        percent_delta=pct,
        quantity=quantity,
        status=_block(status, notes),
        reason_codes=tuple(evaluation.reason_codes),
        review_decision=evaluation.review_decision,
        review_priority=evaluation.review_priority,
        search_query=ebay_sold_search_query(item),
        listing_reference=evaluation.listing_reference,
        user_sku=item.user_sku,
        catalog_sku=item.catalog_sku,
        tcgplayer_sku=item.tcgplayer_sku,
        tcgplayer_product_id=item.tcgplayer_product_id,
        set_name=item.set_name,
        card_number=item.card_number,
        condition=item.condition,
        variant=item.variant,
        finish=item.finish,
        source_file=item.source_file,
        notes=tuple(notes),
        raw_evaluation=evaluation.to_dict(),
    )


def require_apply_ready(plans: Iterable[CardUploaderPriceUpdatePlan]) -> tuple[CardUploaderPriceUpdatePlan, ...]:
    rows = tuple(plans)
    blocked = [plan for plan in rows if not plan.is_apply_ready]
    if blocked:
        raise CardUploaderPriceUpdateError(
            f"Price update apply blocked: {len(blocked)} unapproved or unsafe row(s)."
        )
    return rows


def write_price_update_plan_csv(path: str | Path, plans: Iterable[CardUploaderPriceUpdatePlan]) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    rows = [plan.to_dict() for plan in plans]
    fields = [
        "status",
        "inventory_id",
        "row_number",
        "title",
        "current_price",
        "recommended_price",
        "price_delta",
        "percent_delta",
        "quantity",
        "review_decision",
        "review_priority",
        "reason_codes",
        "notes",
        "search_query",
        "listing_reference",
        "user_sku",
        "catalog_sku",
        "tcgplayer_sku",
        "tcgplayer_product_id",
        "set_name",
        "card_number",
        "condition",
        "variant",
        "finish",
        "source_file",
        "apply_ready",
    ]
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return target


def write_price_update_plan_json(path: str | Path, plans: Iterable[CardUploaderPriceUpdatePlan]) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = [plan.to_dict() for plan in plans]
    target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return target


__all__ = [
    "APPLY_READY_STATUSES",
    "CardUploaderPriceUpdateError",
    "CardUploaderPriceUpdatePlan",
    "CardUploaderPriceUpdatePolicy",
    "PLAN_STATUS_APPROVED",
    "PLAN_STATUS_BLOCKED",
    "PLAN_STATUS_DRY_RUN",
    "build_price_update_plan",
    "carduploader_price_identity",
    "ebay_sold_search_query",
    "money_text",
    "parse_money",
    "percent_delta",
    "require_apply_ready",
    "write_price_update_plan_csv",
    "write_price_update_plan_json",
]
