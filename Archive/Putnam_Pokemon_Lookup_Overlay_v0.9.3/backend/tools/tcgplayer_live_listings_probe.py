from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def find_project_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in [here.parent.parent.parent, here.parent.parent, Path.cwd(), Path.cwd().parent]:
        if (candidate / "price_cache").exists():
            return candidate
    raise SystemExit("ERROR: Could not find Pokemon_Live_Price_Lookup project root.")


PROJECT_ROOT = find_project_root()
OUT_DIR = PROJECT_ROOT / "price_cache" / "web_fetch_diagnostics"


def post_json(url: str, payload: dict) -> tuple[int, dict]:
    body = json.dumps(payload).encode("utf-8")
    req = Request(
        url,
        data=body,
        method="POST",
        headers={
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Origin": "https://www.tcgplayer.com",
            "Referer": "https://www.tcgplayer.com/",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/149.0.0.0 Safari/537.36"
            ),
        },
    )
    with urlopen(req, timeout=30) as resp:
        text = resp.read().decode("utf-8", errors="replace")
        return resp.status, json.loads(text)


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only TCGplayer live listings probe.")
    parser.add_argument("--product-id", default="42402")
    parser.add_argument("--size", type=int, default=10)
    args = parser.parse_args()

    url = f"https://mp-search-api.tcgplayer.com/v1/product/{args.product_id}/listings?mpfev=5245"

    payload = {
        "filters": {
            "term": {
                "sellerStatus": "Live",
                "channelId": 0
            },
            "range": {
                "quantity": {
                    "gte": 1
                }
            },
            "exclude": {
                "channelExclusion": 0
            }
        },
        "context": {
            "shippingCountry": "US",
            "cart": {}
        },
        "aggregations": ["listingType", "condition", "printing"],
        "size": args.size
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = OUT_DIR / f"tcgplayer_live_listings_{args.product_id}_{stamp}.json"

    print("POST:", url)
    print("Payload size:", args.size)

    try:
        status, data = post_json(url, payload)
    except HTTPError as exc:
        print("HTTP ERROR:", exc.code, exc.reason)
        try:
            print(exc.read().decode("utf-8", errors="replace")[:2000])
        except Exception:
            pass
        return 1
    except URLError as exc:
        print("URL ERROR:", exc.reason)
        return 1

    out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    print("HTTP status:", status)
    print("Saved:", out_path)

    result_blocks = data.get("results") or []
    if not result_blocks:
        print("No result blocks returned.")
        return 0

    block = result_blocks[0]
    listings = block.get("results") or []
    print("totalResults:", block.get("totalResults"))
    print("returned listings:", len(listings))
    print("aggregation keys:", list((block.get("aggregations") or {}).keys()))

    if listings:
        print("")
        print("First listing sample:")
        print(json.dumps(listings[0], indent=2)[:3000])
    else:
        print("")
        print("No listing rows returned. Endpoint may require a different payload, auth cookie, or sort/display settings.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
