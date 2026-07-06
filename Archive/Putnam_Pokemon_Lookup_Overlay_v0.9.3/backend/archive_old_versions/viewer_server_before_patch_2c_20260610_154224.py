from __future__ import annotations

import json
import mimetypes
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote_plus, urlparse

from card_catalog import catalog_status, get_card_by_id, resolve_thumbnail_for_card, search_cards, visual_index_lookup
from price_cache import latest_prices_for_card


ROOT = Path(__file__).resolve().parent
PORT = 8790


def tcgplayer_search_url(card: dict[str, Any]) -> str:
    if card.get("tcgplayer_url"):
        return card["tcgplayer_url"]

    query = " ".join(
        part
        for part in [
            card.get("card_name"),
            card.get("set_name"),
            card.get("printed_number") or card.get("card_number"),
        ]
        if part
    )
    return f"https://www.tcgplayer.com/search/pokemon/product?productLineName=pokemon&q={quote_plus(query)}"


def send_json(handler: SimpleHTTPRequestHandler, payload: dict[str, Any], status: int = 200) -> None:
    body = json.dumps(payload, indent=2).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class ViewerHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        if parsed.path == "/api/health":
            send_json(self, {"ok": True, "service": "pokemon-watcher-viewer", "port": PORT})
            return

        if parsed.path == "/api/catalog":
            send_json(self, {"ok": True, "catalog": catalog_status()})
            return

        if parsed.path == "/api/search":
            query = params.get("q", [""])[0].strip()
            set_query = params.get("set", [""])[0].strip() or None
            number_query = params.get("number", [""])[0].strip() or None

            results = search_cards(
                name=query or None,
                number=number_query,
                set_slug_or_name=set_query,
                limit=20,
            )
            for card in results:
                card["thumbnail_url"] = f"/api/thumb-card?id={card['putnam_card_id']}"
                card["tcgplayer_search_url"] = tcgplayer_search_url(card)
                card["prices"] = latest_prices_for_card(card["putnam_card_id"])
            send_json(self, {"ok": True, "results": results})
            return

        if parsed.path == "/api/thumb-card":
            card_id = params.get("id", [""])[0].strip()
            card = get_card_by_id(card_id) if card_id else None
            image_info = resolve_thumbnail_for_card(card) if card else None
            image_path = Path(image_info["resolved_image_path"]) if image_info else None

            if not image_path or not image_path.exists():
                self.send_error(404, "Thumbnail not found")
                return

            body = image_path.read_bytes()
            content_type = mimetypes.guess_type(str(image_path))[0] or "image/jpeg"
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "public, max-age=3600")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path == "/api/thumb":
            set_folder = params.get("set", [""])[0].strip()
            card_number = params.get("number", [""])[0].strip()
            image_info = visual_index_lookup(set_folder, card_number) if set_folder and card_number else None
            image_path = Path(image_info["resolved_image_path"]) if image_info else None

            if not image_path or not image_path.exists():
                self.send_error(404, "Thumbnail not found")
                return

            body = image_path.read_bytes()
            content_type = mimetypes.guess_type(str(image_path))[0] or "image/jpeg"
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "public, max-age=3600")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        super().do_GET()

    def log_message(self, format: str, *args: Any) -> None:
        return


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", PORT), ViewerHandler)
    print(f"Pokemon watcher viewer at http://127.0.0.1:{PORT}/viewer.html")
    server.serve_forever()


if __name__ == "__main__":
    main()
