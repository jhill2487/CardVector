#!/usr/bin/env python3
"""Offline, read-only image reconciliation; never changes the live card search.

Inputs: R2 card-image-index.csv and a licensed PokéWallet JSON export.
Optional reviewed set aliases JSON: {"<PokéWallet set name>": ["<R2 folder>"]}.
Writes matched.json, needs_review.json, missing.json, summary.json.
"""
import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

def norm(value):
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()

def number(value):
    raw = str(value or "").split("/")[0].lower().strip()
    return re.sub(r"^0+(?=\d)", "", raw)

def read_cards(payload):
    if isinstance(payload, dict):
        payload = payload.get("results", payload.get("cards", payload.get("data", [])))
    if not isinstance(payload, list):
        raise ValueError("PokéWallet export must contain a list of cards or results")
    result = []
    seen = set()
    for entry in payload:
        info = entry.get("card_info", entry) if isinstance(entry, dict) else {}
        if not isinstance(info, dict) or info.get("product_type") == "sealed":
            continue
        name = info.get("clean_name") or info.get("name")
        set_name = info.get("set_name")
        card_num = info.get("card_number") or info.get("number")
        if not all([name, set_name, card_num]):
            continue
        key = (str(info.get("set_id") or ""), norm(set_name), number(card_num), norm(name))
        if key in seen:
            continue
        seen.add(key)
        result.append(dict(name=str(name), set=str(set_name), number=str(card_num),
                           set_id=str(info.get("set_id") or ""), provider_id=str(entry.get("id") or "")))
    return result

def parse_image(row):
    path = (row.get("RelativePath") or "").replace("\\", "/")
    parts = path.split("/")
    if len(parts) < 2 or ".." in parts or not re.search(r"\.(?:jpg|jpeg|png|webp)$", path, re.I):
        return None
    folder, filename = parts[-2], parts[-1]
    stem = re.sub(r"\.[^.]+$", "", filename)
    name, num = "", ""
    old = re.fullmatch(r"en_US-.+?-([A-Za-z]*\d+)-(.+)", stem, re.I)
    modern = re.fullmatch(r"[a-z0-9-]+_en_([a-z0-9]+)_(?:std|rev|holo)", stem, re.I)
    if old:
        num, name = old.group(1), old.group(2).replace("_", " ").replace("-", " ")
    elif modern:
        num = modern.group(1)
    else:
        marker = "-" + folder + "-"
        idx = stem.rfind(marker)
        if idx > 0:
            rem = stem[idx + len(marker):]
            suffix = re.fullmatch(r"(?:[a-z0-9]+-)?([a-z]*\d+)", rem, re.I)
            if suffix:
                num = suffix.group(1)
                name = stem[:idx].replace("-", " ").replace("_", " ")
    return dict(path=path, folder=folder, filename=filename, name=name, number=num)

def reconcile(cards, images, aliases):
    by_set_number = defaultdict(list)
    for image in images:
        if image and image["number"]:
            by_set_number[(norm(image["folder"]), number(image["number"]))].append(image)
    matched, review, missing = [], [], []
    for card in cards:
        # Only reviewed aliases or an EXACT normalized set name are permitted.
        set_names = [card["set"], *aliases.get(card["set"], [])]
        folders = {norm(v) for v in set_names}
        candidates = []
        for folder in folders:
            candidates.extend(by_set_number.get((folder, number(card["number"])), []))
        # A named filename must agree with the PokéWallet identity. Otherwise
        # it is a potential misclassification, not usable artwork.
        matching = [im for im in candidates if not im["name"] or norm(im["name"]) == norm(card["name"])]
        conflicts = [im for im in candidates if im not in matching]
        record = {"card": card, "candidates": [im["path"] for im in candidates]}
        if len(matching) == 1 and not conflicts:
            matched.append({**record, "image_path": matching[0]["path"]})
        elif candidates:
            review.append({**record, "reason": "ambiguous images or name conflict"})
        else:
            missing.append({**record, "reason": "no image in mapped set and number"})
    return matched, review, missing

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pokewallet", type=Path, required=True)
    parser.add_argument("--kaggle-index", type=Path, required=True)
    parser.add_argument("--set-aliases", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cards = read_cards(json.loads(args.pokewallet.read_text(encoding="utf-8-sig")))
    with args.kaggle_index.open(encoding="utf-8-sig", newline="") as file:
        images = [parse_image(row) for row in csv.DictReader(file)]
    aliases = json.loads(args.set_aliases.read_text()) if args.set_aliases else {}
    if not isinstance(aliases, dict) or any(not isinstance(v, list) for v in aliases.values()):
        raise ValueError("Set aliases must map verified set names to lists of R2 folders")
    matched, review, missing = reconcile(cards, images, aliases)
    args.output.mkdir(parents=True, exist_ok=True)
    for name, rows in [("matched", matched), ("needs_review", review), ("missing", missing)]:
        (args.output / (name + ".json")).write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    summary = {"pokewallet_records": len(cards), "r2_images": sum(bool(i) for i in images),
               "matched": len(matched), "needs_review": len(review), "missing": len(missing)}
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary))
if __name__ == "__main__":
    main()
