from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from price_cache import insert_price_snapshot, upsert_price_link


TCGDEX_CARD_URL = "https://api.tcgdex.net/v2/en/cards/{tcgdex_card_id}"
VARIANT_PRIORITY = ("holo", "normal", "reverse", "firstEditionHolo", "firstEditionNormal")


def normalize_tcgdex_card_id(tcgdex_card_id: str) -> str:
    known = {
        "sv3pt5": "sv03.5",
        "sv3.5": "sv03.5",
    }
    if "-" not in tcgdex_card_id:
        return tcgdex_card_id
    set_id, local_id = tcgdex_card_id.rsplit("-", 1)
    return f"{known.get(set_id, set_id)}-{local_id}"


def fetch_json(url: str) -> dict[str, Any]:
    request = Request(url, headers={"User-Agent": "PutnamPokemonWatcher/0.1"})
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def select_tcgplayer_market(pricing: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
    tcgplayer = pricing.get("tcgplayer") or {}
    if not isinstance(tcgplayer, dict):
        return None

    for variant in VARIANT_PRIORITY:
        values = tcgplayer.get(variant)
        if isinstance(values, dict) and values.get("marketPrice") is not None:
            return variant, values

    for variant, values in tcgplayer.items():
        if isinstance(values, dict) and values.get("marketPrice") is not None:
            return variant, values

    return None


def refresh_one(putnam_card_id: str, tcgdex_card_id: str) -> bool:
    tcgdex_card_id = normalize_tcgdex_card_id(tcgdex_card_id)
    url = TCGDEX_CARD_URL.format(tcgdex_card_id=tcgdex_card_id)
    payload = fetch_json(url)
    selected = select_tcgplayer_market(payload.get("pricing") or {})
    if not selected:
        return False

    variant, values = selected
    upsert_price_link(
        putnam_card_id=putnam_card_id,
        provider="tcgdex",
        provider_product_id=tcgdex_card_id,
        provider_url=url,
        match_confidence=1.0,
    )
    insert_price_snapshot(
        putnam_card_id=putnam_card_id,
        provider="tcgdex",
        condition="MARKET",
        market_price=float(values["marketPrice"]),
        low_price=float(values["lowPrice"]) if values.get("lowPrice") is not None else None,
        high_price=float(values["highPrice"]) if values.get("highPrice") is not None else None,
        sample_size=None,
    )
    print(f"{putnam_card_id}: tcgdex {tcgdex_card_id} {variant} market={values['marketPrice']}")
    return True


def refresh_from_csv(csv_path: Path) -> int:
    refreshed = 0
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            putnam_card_id = (row.get("putnam_card_id") or "").strip()
            tcgdex_card_id = (row.get("tcgdex_card_id") or "").strip()
            if not putnam_card_id or not tcgdex_card_id:
                continue

            try:
                if refresh_one(putnam_card_id, tcgdex_card_id):
                    refreshed += 1
            except (HTTPError, URLError, TimeoutError, ValueError, KeyError) as exc:
                print(f"{putnam_card_id}: failed {tcgdex_card_id}: {exc}")
    return refreshed


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: tcgdex_prices.py path\\to\\tcgdex_links.csv")
        raise SystemExit(1)

    count = refresh_from_csv(Path(sys.argv[1]))
    print(f"refreshed {count} TCGdex fallback market prices")


if __name__ == "__main__":
    main()
