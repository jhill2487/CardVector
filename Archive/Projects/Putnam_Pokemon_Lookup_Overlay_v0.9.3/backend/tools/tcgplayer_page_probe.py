from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sqlite3
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlparse, parse_qs
from urllib.request import Request, urlopen


def find_project_root() -> Path:
    here = Path(__file__).resolve()
    candidates = [
        here.parent.parent.parent,
        here.parent.parent,
        Path.cwd(),
        Path.cwd().parent,
    ]
    for candidate in candidates:
        if (candidate / "price_cache" / "tcgtracking_cache.sqlite").exists():
            return candidate
    raise SystemExit(
        "ERROR: Could not find Pokemon_Live_Price_Lookup project root with price_cache\\tcgtracking_cache.sqlite"
    )


PROJECT_ROOT = find_project_root()
CACHE_DB = PROJECT_ROOT / "price_cache" / "tcgtracking_cache.sqlite"
OUT_DIR = PROJECT_ROOT / "price_cache" / "web_fetch_diagnostics"


def tcgplayer_direct_url(url: str) -> str:
    if not url:
        return url

    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    if "u" in qs and qs["u"]:
        return unquote(qs["u"][0])
    return url


def product_url_from_cache(product_id: str) -> str | None:
    with sqlite3.connect(CACHE_DB) as con:
        con.row_factory = sqlite3.Row
        row = con.execute(
            """
            select product_id, name, product_url, tcgplayer_url
            from tcgtracking_products
            where product_id = ?
            """,
            [str(product_id)],
        ).fetchone()

    if not row:
        return None

    return tcgplayer_direct_url(row["tcgplayer_url"] or row["product_url"] or "")


def fetch_url(url: str) -> tuple[int, str, dict[str, str]]:
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )

    with urlopen(request, timeout=25) as response:
        raw = response.read()
        charset = response.headers.get_content_charset() or "utf-8"
        text = raw.decode(charset, errors="replace")
        headers = {k: v for k, v in response.headers.items()}
        return response.status, text, headers


def summarize_html(html: str) -> dict[str, object]:
    title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    title = re.sub(r"\s+", " ", title_match.group(1)).strip() if title_match else ""

    keyword_patterns = [
        "marketPrice",
        "lowPrice",
        "midPrice",
        "Near Mint",
        "Lightly Played",
        "Reverse Holofoil",
        "Holofoil",
        "Normal",
    ]

    return {
        "title": title,
        "html_length": len(html),
        "contains_next_data": "__NEXT_DATA__" in html,
        "contains_marketPrice": "marketPrice" in html,
        "contains_lowPrice": "lowPrice" in html,
        "contains_tcgplayer": "tcgplayer" in html.lower(),
        "price_like_values": sorted(set(re.findall(r"\$[0-9][0-9,]*(?:\.[0-9]{2})?", html)))[:50],
        "keyword_hits": {p: bool(re.search(re.escape(p), html, re.I)) for p in keyword_patterns},
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Diagnostic fetch for one TCGplayer product page. Read-only; does not modify cache."
    )
    parser.add_argument("--product-id", help="TCGplayer product id from tcgtracking_cache.sqlite, e.g. 42402")
    parser.add_argument("--url", help="Direct or affiliate TCGplayer URL")
    args = parser.parse_args()

    if not args.product_id and not args.url:
        print("Usage examples:")
        print("  python .\\tools\\tcgplayer_page_probe.py --product-id 42402")
        print("  python .\\tools\\tcgplayer_page_probe.py --url https://www.tcgplayer.com/product/42402/...")
        return 2

    url = args.url or product_url_from_cache(args.product_id)
    if not url:
        print(f"ERROR: Could not find URL for product_id={args.product_id}")
        return 1

    url = tcgplayer_direct_url(url)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_id = args.product_id or "url"
    html_path = OUT_DIR / f"tcgplayer_probe_{safe_id}_{stamp}.html"
    json_path = OUT_DIR / f"tcgplayer_probe_{safe_id}_{stamp}.json"

    print("Project root:", PROJECT_ROOT)
    print("Cache DB:", CACHE_DB)
    print("Fetching:", url)

    try:
        status, html, headers = fetch_url(url)
    except HTTPError as exc:
        print(f"HTTP ERROR: {exc.code} {exc.reason}")
        try:
            body = exc.read().decode("utf-8", errors="replace")
            html_path.write_text(body, encoding="utf-8")
            print("Saved error response:", html_path)
        except Exception:
            pass
        return 1
    except URLError as exc:
        print(f"URL ERROR: {exc.reason}")
        return 1
    except TimeoutError:
        print("ERROR: Request timed out.")
        return 1

    summary = summarize_html(html)
    summary["status"] = status
    summary["url"] = url
    summary["headers_subset"] = {
        "content-type": headers.get("Content-Type"),
        "cache-control": headers.get("Cache-Control"),
        "server": headers.get("Server"),
    }

    html_path.write_text(html, encoding="utf-8")
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("HTTP status:", status)
    print("HTML saved:", html_path)
    print("Summary saved:", json_path)
    print("")
    print("Summary:")
    print(json.dumps(summary, indent=2)[:3000])

    if not summary.get("price_like_values"):
        print("")
        print("NOTE: No obvious dollar values were found in the initial HTML.")
        print("That may mean pricing is rendered client-side or blocked from simple fetch.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
