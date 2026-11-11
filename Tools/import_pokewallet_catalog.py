#!/usr/bin/env python3
"""Incrementally import authorized PokéWallet set cards without touching live search.

Uses documented /sets and /sets/:set_id?page=N&limit=200 endpoints.
A checkpoint is written after each successful page; rerun to resume.
The API key is read only from the POKEWALLET_API_KEY environment variable.
"""
import argparse
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://api.pokewallet.io"
PAGE_SIZE = 200

def save_atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    temp.replace(path)

def request_json(path, secret, timeout=25):
    request = urllib.request.Request(BASE + path, headers={
        "X-API-Key": secret, "Accept": "application/json",
        "User-Agent": "CardVector-Admin-Catalog-Reconciliation/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as res:
            payload = json.load(res)
    except urllib.error.HTTPError as error:
        if error.code == 429:
            raise RuntimeError("PokéWallet rate limit reached. Resume after quota resets.") from None
        raise RuntimeError("PokéWallet HTTP " + str(error.code) + "; checkpoint preserved.") from None
    if not isinstance(payload, dict) or payload.get("success") is False:
        raise RuntimeError("Unexpected PokéWallet API response; checkpoint preserved.")
    return payload

def initial_state():
    return {"version": 1, "sets": [], "next_set": 0, "next_page": 1, "cards": [],
            "request_count_total": 0, "finished": False}

def normalize_card(row, set_row):
    if not isinstance(row, dict):
        return None
    info = row.get("card_info") or {}
    if not isinstance(info, dict) or info.get("product_type") == "sealed":
        return None
    name = info.get("clean_name") or info.get("name")
    number = info.get("card_number")
    if not name or not number:
        return None
    return {"id": str(row.get("id") or ""), "card_info": {
        "name": str(name), "set_name": str(set_row["name"]),
        "set_id": str(set_row["set_id"]), "card_number": str(number),
        "variants": info.get("variants") if isinstance(info.get("variants"), list) else []
    }}

def run_batch(state, api, save, budget=50, interval=40, sleep=time.sleep):
    """Run at most budget API requests, including set discovery. Always checkpoint."""
    calls = 0
    last_call = None
    def get(path):
        nonlocal calls, last_call
        if last_call is not None:
            delay = interval - (time.monotonic() - last_call)
            if delay > 0:
                sleep(delay)
        response = api(path)
        last_call = time.monotonic()
        calls += 1
        state["request_count_total"] += 1
        return response

    if not state["sets"] and calls < budget:
        payload = get("/sets")
        sets = payload.get("data")
        if not isinstance(sets, list) or not sets:
            raise RuntimeError("PokéWallet set directory unavailable; checkpoint preserved.")
        state["sets"] = sorted([
            {"set_id": str(s["set_id"]), "name": str(s["name"]),
             "card_count": int(s.get("card_count") or 0), "sealed_count": int(s.get("sealed_count") or 0)}
            for s in sets if isinstance(s, dict) and s.get("set_id") is not None and s.get("name")
        ], key=lambda item: (item["name"].casefold(), item["set_id"]))
        save(state)
    while calls < budget and state["next_set"] < len(state["sets"]):
        current = state["sets"][state["next_set"]]
        page = state["next_page"]
        set_id = urllib.parse.quote(current["set_id"], safe="")
        payload = get("/sets/" + set_id + "?page=" + str(page) + "&limit=" + str(PAGE_SIZE))
        items = payload.get("cards")
        metadata = payload.get("set")
        if not isinstance(items, list) or not isinstance(metadata, dict):
            raise RuntimeError("Unexpected set page schema; checkpoint preserved.")
        if str(metadata.get("set_id")) != current["set_id"]:
            raise RuntimeError("Set ID mismatch; refusing cross-set card mapping.")
        total = int(metadata.get("total_cards") or 0)
        if total and (page-1)*PAGE_SIZE < total and not items:
            raise RuntimeError("Unexpected empty page within a nonempty set.")
        state["cards"].extend(card for item in items if (card := normalize_card(item, current)))
        more = page * PAGE_SIZE < total if total else len(items) == PAGE_SIZE
        if more:
            state["next_page"] = page + 1
        else:
            state["next_set"] += 1
            state["next_page"] = 1
        save(state)
    state["finished"] = bool(state["sets"] and state["next_set"] >= len(state["sets"]))
    save(state)
    return {"requests_this_run": calls, "sets_complete": state["next_set"],
            "sets_total": len(state["sets"]), "card_records": len(state["cards"]),
            "finished": state["finished"]}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--catalog-output", type=Path, required=True)
    parser.add_argument("--max-requests", type=int, default=50)
    parser.add_argument("--interval-seconds", type=float, default=40)
    args = parser.parse_args()
    if not 1 <= args.max_requests <= 80 or args.interval_seconds < 36:
        parser.error("Use 1–80 calls/run with at least 36 seconds between requests on the free tier.")
    secret = os.environ.get("POKEWALLET_API_KEY", "").strip()
    if not secret:
        parser.error("POKEWALLET_API_KEY must be configured as a secret environment variable.")
    state = json.loads(args.state.read_text(encoding="utf-8")) if args.state.exists() else initial_state()
    try:
        summary = run_batch(state, lambda p: request_json(p, secret),
                            lambda s: save_atomic(args.state, s),
                            budget=args.max_requests, interval=args.interval_seconds)
    finally:
        save_atomic(args.state, state)
        # Export only minimal identification metadata, never price history or API secrets.
        save_atomic(args.catalog_output, {"cards": state["cards"]})
    print(json.dumps(summary))

if __name__ == "__main__":
    main()
