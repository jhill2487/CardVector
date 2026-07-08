from __future__ import annotations

import base64
import json
import struct
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from card_catalog import catalog_status, search_cards, write_catalog_status
from price_cache import latest_prices_for_card


ROOT = Path(__file__).resolve().parent
RUNTIME = ROOT / "runtime"
PRICE_CACHE_PATH = ROOT / "price_cache.sample.json"
STATUS_PATH = RUNTIME / "status.json"
MAX_AUDIO_CHUNKS = 120


@dataclass
class WatcherState:
    started_at: float
    last_frame_at: float | None = None
    last_audio_at: float | None = None
    frame_count: int = 0
    audio_chunk_count: int = 0
    latest_card_id: str | None = None
    latest_card_name: str | None = None
    confidence: float = 0.0
    prices: dict[str, Any] | None = None
    catalog: dict[str, Any] | None = None
    candidates: list[dict[str, Any]] | None = None
    note: str = "Waiting for Chrome tab capture."


STATE = WatcherState(started_at=time.time())


def ensure_runtime() -> None:
    RUNTIME.mkdir(parents=True, exist_ok=True)


def read_message() -> dict[str, Any] | None:
    raw_length = sys.stdin.buffer.read(4)
    if not raw_length:
        return None
    message_length = struct.unpack("<I", raw_length)[0]
    payload = sys.stdin.buffer.read(message_length)
    if not payload:
        return None
    return json.loads(payload.decode("utf-8"))


def send_message(message: dict[str, Any]) -> None:
    encoded = json.dumps(message, separators=(",", ":")).encode("utf-8")
    sys.stdout.buffer.write(struct.pack("<I", len(encoded)))
    sys.stdout.buffer.write(encoded)
    sys.stdout.buffer.flush()


def decode_data_url(data_url: str) -> bytes:
    _, encoded = data_url.split(",", 1)
    return base64.b64decode(encoded)


def load_price_cache() -> dict[str, Any]:
    if not PRICE_CACHE_PATH.exists():
        return {}
    return json.loads(PRICE_CACHE_PATH.read_text(encoding="utf-8"))


def write_status() -> None:
    ensure_runtime()
    payload = {
        "ok": True,
        "updated_at": time.time(),
        **asdict(STATE),
        "catalog_status_file": "catalog_status.json",
        "latest_frame": "latest_frame.jpg" if (RUNTIME / "latest_frame.jpg").exists() else None,
    }
    STATUS_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def prune_audio_chunks() -> None:
    audio_files = sorted(RUNTIME.glob("audio_*.webm"), key=lambda path: path.stat().st_mtime)
    stale_files = audio_files[:-MAX_AUDIO_CHUNKS]
    for path in stale_files:
        path.unlink(missing_ok=True)


def identify_from_latest_signals() -> None:
    STATE.catalog = catalog_status()
    price_cache = load_price_cache()
    STATE.candidates = search_cards(name="Charizard ex", number="199", set_slug_or_name="151", limit=5)

    if not STATE.candidates:
        STATE.note = "Capture received. Pokemon catalog is referenced, but no demo candidate was found."
        return

    card = STATE.candidates[0]
    STATE.latest_card_id = card.get("putnam_card_id")
    STATE.latest_card_name = card.get("card_name")
    STATE.confidence = 0.25
    if STATE.latest_card_id:
        STATE.prices = latest_prices_for_card(STATE.latest_card_id)
    STATE.note = "Pokemon catalog loaded from SQLite/Kaggle. Recognition engine not connected yet."


def handle_message(message: dict[str, Any]) -> dict[str, Any]:
    ensure_runtime()
    message_type = message.get("type")

    if message_type == "frame":
        frame = decode_data_url(message["dataUrl"])
        (RUNTIME / "latest_frame.jpg").write_bytes(frame)
        STATE.last_frame_at = time.time()
        STATE.frame_count += 1
        identify_from_latest_signals()
        write_status()
        return {"ok": True, **asdict(STATE)}

    if message_type == "audio":
        audio = decode_data_url(message["dataUrl"])
        audio_path = RUNTIME / f"audio_{int(time.time() * 1000)}.webm"
        audio_path.write_bytes(audio)
        prune_audio_chunks()
        STATE.last_audio_at = time.time()
        STATE.audio_chunk_count += 1
        identify_from_latest_signals()
        write_status()
        return {"ok": True, **asdict(STATE)}

    return {"ok": False, "error": f"Unknown message type: {message_type}"}


def main() -> None:
    ensure_runtime()
    STATE.catalog = write_catalog_status()
    write_status()
    send_message({"ok": True, "note": "Pokemon watcher companion connected."})

    while True:
        message = read_message()
        if message is None:
            break
        try:
            send_message(handle_message(message))
        except Exception as exc:
            send_message({"ok": False, "error": str(exc)})


if __name__ == "__main__":
    main()
