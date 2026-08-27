"""Build the public CardVector direct-store inventory feed.

The feed is a static browse snapshot, not the inventory source of truth.
CardUploader remains the managed-inventory owner; checkout availability is
validated separately before any future payment or marketplace release step.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


DEFAULT_CHECKOUT_MODE = "hybrid_static_browse_live_availability_pending"
DEFAULT_CURRENCY = "USD"


def parse_decimal(value: str) -> Decimal | None:
    try:
      amount = Decimal(str(value or "").replace("$", "").replace(",", "").strip())
    except (InvalidOperation, ValueError):
      return None
    return amount if amount > 0 else None


def parse_quantity(value: str) -> int:
    try:
        return max(0, int(Decimal(str(value or "0").strip() or "0")))
    except (InvalidOperation, ValueError):
        return 0


def normalize_game(value: str) -> str:
    raw = " ".join(str(value or "").replace("_", " ").split()).strip().lower()
    if not raw:
        return "Trading Card"
    if "pokemon" in raw or "pokémon" in raw:
        return "Pokemon Japanese" if "japanese" in raw else "Pokemon"
    if raw in {"mtg", "magic", "magic the gathering"} or "magic" in raw:
        return "Magic: The Gathering"
    if "yugioh" in raw or "yu gi oh" in raw or "yu-gi-oh" in raw:
        return "Yu-Gi-Oh!"
    return raw.title()


def stable_public_item_id(row: dict[str, str], price: Decimal) -> str:
    for field in ("Catalog SKU", "TCGplayer SKU", "TCGplayer Product ID"):
        value = str(row.get(field, "")).strip()
        if value:
            identity = f"{field}:{value}:{price}"
            return f"cv-{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:16]}"
    identity = "|".join(
        str(row.get(field, "")).strip()
        for field in ("Title", "TCG", "Set", "Card Number", "Condition", "Variant")
    )
    identity = f"{identity}|{price}"
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12]
    return f"cv-{digest}"


def first_image_url(row: dict[str, str], include_images: bool) -> str:
    if not include_images:
        return ""
    urls = [url.strip() for url in str(row.get("Image URLs", "")).split("|") if url.strip()]
    return urls[0] if urls else ""


def build_item(row: dict[str, str], include_images: bool) -> dict[str, Any] | None:
    title = str(row.get("Title", "")).strip()
    quantity = parse_quantity(row.get("Qty", ""))
    price = parse_decimal(row.get("Price", ""))
    status = str(row.get("Status", "")).strip().lower()
    if not title or quantity <= 0 or price is None:
        return None
    if status in {"sold", "removed", "deleted", "draft", "inactive"}:
        return None

    item = {
        "id": stable_public_item_id(row, price),
        "title": title,
        "game": normalize_game(row.get("TCG", "")),
        "condition": str(row.get("Condition", "") or "Near Mint").strip(),
        "variant": str(row.get("Variant", "") or row.get("Finish", "")).strip(),
        "set_name": str(row.get("Set", "")).strip(),
        "card_number": str(row.get("Card Number", "")).strip(),
        "rarity": str(row.get("Rarity", "")).strip(),
        "price": float(price),
        "quantity_available": quantity,
        "image_url": first_image_url(row, include_images),
        "source": "CardUploader inventory snapshot",
        "status": status or "available",
    }
    return {key: value for key, value in item.items() if value not in ("", None)}


def build_feed(input_path: Path, include_images: bool = False, limit: int | None = None) -> dict[str, Any]:
    with input_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    items_by_id: dict[str, dict[str, Any]] = {}
    skipped_zero_quantity = 0
    skipped_invalid = 0
    skipped_status = 0

    for row in rows:
        status = str(row.get("Status", "")).strip().lower()
        quantity = parse_quantity(row.get("Qty", ""))
        price = parse_decimal(row.get("Price", ""))
        item = build_item(row, include_images=include_images)
        if item is None:
            if quantity <= 0:
                skipped_zero_quantity += 1
            elif status in {"sold", "removed", "deleted", "draft", "inactive"}:
                skipped_status += 1
            else:
                skipped_invalid += 1
            continue
        existing = items_by_id.get(item["id"])
        if existing:
            existing["quantity_available"] += item["quantity_available"]
        else:
            items_by_id[item["id"]] = item

    items = list(items_by_id.values())
    items.sort(key=lambda item: (item.get("game", ""), item.get("title", ""), item.get("condition", "")))
    if limit is not None:
        items = items[: max(0, limit)]

    games: dict[str, int] = {}
    for item in items:
        games[item["game"]] = games.get(item["game"], 0) + 1

    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return {
        "schema_version": "1.1",
        "generated_at": now,
        "source": "carduploader_inventory_csv",
        "source_file": input_path.name,
        "checkout_mode": DEFAULT_CHECKOUT_MODE,
        "currency": DEFAULT_CURRENCY,
        "availability": {
            "mode": "static_browse_feed",
            "supabase_enabled": False,
            "live_checkout_required": True,
            "notes": "Public browsing uses this static feed. Future checkout must perform a live availability check before payment capture.",
        },
        "summary": {
            "source_rows": len(rows),
            "published_items": len(items),
            "published_quantity": sum(item["quantity_available"] for item in items),
            "games": games,
            "skipped_zero_quantity": skipped_zero_quantity,
            "skipped_status": skipped_status,
            "skipped_invalid": skipped_invalid,
            "images_included": include_images,
        },
        "items": items,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="CardUploader inventory CSV export")
    parser.add_argument("--output", required=True, type=Path, help="Direct inventory JSON output")
    parser.add_argument("--include-image-urls", action="store_true", help="Include first external image URL per item")
    parser.add_argument("--limit", type=int, default=None, help="Optional maximum published item count")
    args = parser.parse_args()

    feed = build_feed(args.input, include_images=args.include_image_urls, limit=args.limit)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(feed, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        f"Published {feed['summary']['published_items']} items "
        f"from {feed['summary']['source_rows']} source rows to {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
