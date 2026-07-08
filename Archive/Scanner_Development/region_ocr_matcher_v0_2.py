"""
Putnam Region OCR Matcher v0.2

Fix from v0.1:
- Trainer JSON region points are ORIGINAL PHOTO coordinates.
- This script extracts each region directly from the original photo using its own 4-point polygon.
- It does NOT treat name/number/setcode points as card-crop coordinates.
- Outputs region crops first, then runs OCR/matching.

Usage:
python region_ocr_matcher_v0_2.py --labels border_training_labels --images input_photos --sqlite database\putnam_pokemon_cloud_ready.sqlite --output region_ocr_results_v0_2
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from difflib import SequenceMatcher

import cv2
import numpy as np

try:
    import pytesseract
    default_tesseract = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.path.exists(default_tesseract):
        pytesseract.pytesseract.tesseract_cmd = default_tesseract
except Exception:
    pytesseract = None

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}

SET_CODE_MAP = {
    "CRI": "Chaos Rising",
    "PRE": "Prismatic Evolutions",
    "PAL": "Paldea Evolved",
    "SVI": "Scarlet & Violet",
    "BLK": "Black Bolt",
    "WHT": "White Flare",
    "OBF": "Obsidian Flames",
    "PAF": "Paldean Fates",
    "TWM": "Twilight Masquerade",
    "SCR": "Stellar Crown",
    "SSP": "Surging Sparks",
    "MEG": "Mega Evolution",
}

@dataclass
class CardRow:
    set_name: str
    card_name: str
    card_number: str
    rarity: str


def normalize_text(s: str) -> str:
    s = str(s or "").lower()
    s = s.replace("é", "e").replace("’", "'").replace("‘", "'")
    s = re.sub(r"[^a-z0-9/' ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def normalize_number(s: str) -> str:
    s = str(s or "").upper().strip()
    m = re.search(r"(\d{1,3})\s*/\s*(\d{1,3})", s)
    if m:
        return f"{int(m.group(1))}/{int(m.group(2))}"
    m = re.search(r"\b0*(\d{1,3})\b", s)
    if m:
        return str(int(m.group(1)))
    return re.sub(r"\s+", "", s)


def number_left(s: str) -> str:
    n = normalize_number(s)
    return n.split("/")[0] if n else ""


def extract_number(text: str) -> str:
    text = text or ""
    m = re.search(r"\b0*(\d{1,3})\s*/\s*0*(\d{1,3})\b", text)
    if m:
        return f"{int(m.group(1))}/{int(m.group(2))}"
    m = re.search(r"\b0*(\d{1,3})\b", text)
    if m:
        return str(int(m.group(1)))
    return ""


def extract_set_code(text: str) -> str:
    raw = re.sub(r"[^A-Za-z0-9 ]+", " ", text or "").upper()
    # Prefer known set codes seen in OCR. Handles BLK EN, CRI EN, PRE EN.
    for code in sorted(SET_CODE_MAP, key=len, reverse=True):
        if re.search(rf"\b{re.escape(code)}\b", raw):
            return code
    # Fallback: first 3-letter uppercase token.
    for token in raw.split():
        if len(token) == 3 and token.isalpha():
            return token
    return ""


def clean_name(text: str) -> str:
    lines = []
    for line in (text or "").splitlines():
        line = line.strip()
        if not line:
            continue
        # remove obvious OCR labels/config noise
        if line.startswith("[") and line.endswith("]"):
            continue
        line = re.sub(r"[^A-Za-z0-9éÉ' .\-]", " ", line)
        line = re.sub(r"\s+", " ", line).strip()
        if len(line) >= 2:
            lines.append(line)
    if not lines:
        return ""
    # choose longest short line, usually name crop only contains the name
    lines = sorted(lines, key=lambda x: (len(x), -len(x.split())), reverse=True)
    return lines[0]


def order_points(pts: np.ndarray) -> np.ndarray:
    pts = np.array(pts, dtype="float32")
    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1).reshape(-1)
    rect = np.zeros((4, 2), dtype="float32")
    rect[0] = pts[np.argmin(s)]      # top-left
    rect[2] = pts[np.argmax(s)]      # bottom-right
    rect[1] = pts[np.argmin(diff)]   # top-right
    rect[3] = pts[np.argmax(diff)]   # bottom-left
    return rect


def warp_region(image: np.ndarray, points: List[Dict[str, float]], min_w: int = 40, min_h: int = 20) -> np.ndarray:
    pts = np.array([[p["x"], p["y"]] for p in points], dtype="float32")
    rect = order_points(pts)
    tl, tr, br, bl = rect
    width_a = np.linalg.norm(br - bl)
    width_b = np.linalg.norm(tr - tl)
    height_a = np.linalg.norm(tr - br)
    height_b = np.linalg.norm(tl - bl)
    max_w = max(int(round(max(width_a, width_b))), min_w)
    max_h = max(int(round(max(height_a, height_b))), min_h)
    dst = np.array([[0,0], [max_w-1,0], [max_w-1,max_h-1], [0,max_h-1]], dtype="float32")
    M = cv2.getPerspectiveTransform(rect, dst)
    return cv2.warpPerspective(image, M, (max_w, max_h))


def prep_for_ocr(crop: np.ndarray, region: str) -> List[Tuple[str, np.ndarray]]:
    out = [("raw", crop)]
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if crop.ndim == 3 else crop
    scale = 4 if region in {"number", "setcode"} else 3
    big = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    out.append((f"gray_{scale}x", big))
    # threshold variants, including inverse for white text on dark backgrounds
    blur = cv2.GaussianBlur(big, (3,3), 0)
    _, otsu = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    _, otsu_inv = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    out.append(("otsu", otsu))
    out.append(("otsu_inv", otsu_inv))
    return out


def ocr_crop(crop: np.ndarray, region: str, debug_dir: Optional[Path], stem: str) -> Tuple[str, str]:
    if pytesseract is None:
        return "", "pytesseract_unavailable"
    configs = {
        "name": ["--psm 7", "--psm 6"],
        "number": ["--psm 7 -c tessedit_char_whitelist=0123456789/", "--psm 8 -c tessedit_char_whitelist=0123456789/"],
        "setcode": ["--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ", "--psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 "],
    }.get(region, ["--psm 7"])
    attempts = []
    for prep_name, img in prep_for_ocr(crop, region):
        for cfg in configs:
            try:
                text = pytesseract.image_to_string(img, config=cfg).strip()
            except Exception as e:
                text = ""
            score = len(re.sub(r"\s+", "", text))
            # region-specific boosts
            if region == "number" and re.search(r"\d", text): score += 20
            if region == "setcode" and extract_set_code(text): score += 20
            if region == "name" and re.search(r"[A-Za-z]{3,}", text): score += 20
            attempts.append((score, prep_name, cfg, text))
    attempts.sort(reverse=True, key=lambda x: x[0])
    best = attempts[0] if attempts else (0, "none", "", "")
    if debug_dir:
        debug_dir.mkdir(parents=True, exist_ok=True)
        with open(debug_dir / f"{stem}_{region}_ocr.txt", "w", encoding="utf-8") as f:
            for score, prep, cfg, txt in attempts:
                f.write(f"=== {prep} | {cfg} | score={score} ===\n{txt}\n\n")
    return best[3], f"{best[1]} {best[2]}"


def load_cards(sqlite_path: Path) -> List[CardRow]:
    con = sqlite3.connect(sqlite_path)
    cur = con.cursor()
    tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    preferred = ["pokemon_cards", "cards", "Pokemon_Lookup_Database"]
    table = next((t for t in preferred if t in tables), tables[0])
    cols = [r[1] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()]
    lower = {c.lower(): c for c in cols}
    def pick(*names):
        for n in names:
            if n.lower() in lower: return lower[n.lower()]
        return None
    name_col = pick("card_name", "Card Name", "name")
    set_col = pick("set_name", "Set Name", "set")
    num_col = pick("card_number", "Card Number", "number")
    rarity_col = pick("rarity", "Rarity")
    if not (name_col and set_col and num_col):
        raise ValueError(f"Could not identify needed columns in {table}: {cols}")
    q = f"SELECT {set_col}, {name_col}, {num_col}" + (f", {rarity_col}" if rarity_col else ", ''") + f" FROM {table}"
    rows = [CardRow(*(str(x or "") for x in r)) for r in cur.execute(q).fetchall()]
    con.close()
    return rows


def match_card(cards: List[CardRow], name: str, number: str, set_code: str) -> Tuple[str, str, str, float, str]:
    set_name_hint = SET_CODE_MAP.get(set_code, "")
    num_left = number_left(number)
    name_norm = normalize_text(name)
    candidates = cards
    reasons = []
    if set_name_hint:
        subset = [c for c in candidates if normalize_text(c.set_name) == normalize_text(set_name_hint)]
        if subset:
            candidates = subset
            reasons.append(f"set code {set_code}->{set_name_hint}")
    if num_left:
        subset = [c for c in candidates if number_left(c.card_number) == num_left]
        if subset:
            candidates = subset
            reasons.append(f"number left {num_left}")
    best = None
    best_score = -1.0
    for c in candidates:
        cn = normalize_text(c.card_name)
        sim = SequenceMatcher(None, name_norm, cn).ratio() if name_norm and cn else 0
        token_hits = 0
        toks = [t for t in cn.split() if len(t) >= 3]
        if toks and name_norm:
            token_hits = sum(1 for t in toks if t in name_norm)
            sim = max(sim, token_hits / len(toks))
        score = sim
        if num_left and number_left(c.card_number) == num_left: score += 1.0
        if set_name_hint and normalize_text(c.set_name) == normalize_text(set_name_hint): score += 1.0
        if score > best_score:
            best = c
            best_score = score
    if not best:
        return "", "", "", 0.0, "no candidates"
    confidence = 0.0
    if set_name_hint and normalize_text(best.set_name) == normalize_text(set_name_hint): confidence += 0.35
    if num_left and number_left(best.card_number) == num_left: confidence += 0.35
    name_sim = SequenceMatcher(None, name_norm, normalize_text(best.card_name)).ratio() if name_norm else 0
    if name_sim >= 0.85 or normalize_text(best.card_name) in name_norm or name_norm in normalize_text(best.card_name):
        confidence += 0.30
        reasons.append(f"name match {name_sim:.2f}")
    elif name_sim >= 0.60:
        confidence += 0.15
        reasons.append(f"partial name {name_sim:.2f}")
    # Do not over-trust number+set only.
    if confidence == 0.70:
        reasons.append("candidate only: number+set without strong name")
    return best.card_name, best.set_name, best.card_number, min(confidence, .99), "; ".join(reasons)


def find_image(images_dir: Path, filename: str) -> Optional[Path]:
    direct = images_dir / filename
    if direct.exists(): return direct
    stem = Path(filename).stem.lower()
    for p in images_dir.rglob("*"):
        if p.suffix.lower() in IMAGE_EXTS and p.stem.lower() == stem:
            return p
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", required=True)
    ap.add_argument("--images", required=True)
    ap.add_argument("--sqlite", required=True)
    ap.add_argument("--output", default="region_ocr_results_v0_2")
    args = ap.parse_args()
    labels_dir = Path(args.labels)
    images_dir = Path(args.images)
    out_dir = Path(args.output)
    crop_dir = out_dir / "region_crops"
    debug_dir = out_dir / "ocr_debug"
    out_dir.mkdir(parents=True, exist_ok=True)
    crop_dir.mkdir(parents=True, exist_ok=True)

    cards = load_cards(Path(args.sqlite))
    print(f"Loaded {len(cards)} cards from SQLite")
    rows = []
    label_files = sorted(labels_dir.glob("*.json"))
    print(f"Region OCR Matcher v0.2: {len(label_files)} label file(s)")
    for label_path in label_files:
        data = json.loads(label_path.read_text(encoding="utf-8"))
        fname = data.get("filename") or (label_path.stem + ".JPG")
        img_path = find_image(images_dir, fname)
        if not img_path:
            print(f"{label_path.name}: image not found for {fname}")
            continue
        image = cv2.imread(str(img_path))
        if image is None:
            print(f"{label_path.name}: could not read {img_path}")
            continue
        stem = Path(fname).stem
        print(f"Processing {fname}...")
        values = {}
        methods = {}
        for region in ["name", "number", "setcode"]:
            pts = data.get("regions", {}).get(region)
            if not pts:
                print(f"  missing region: {region}")
                values[region] = ""
                continue
            crop = warp_region(image, pts)
            crop_path = crop_dir / f"{stem}_{region}_crop.jpg"
            cv2.imwrite(str(crop_path), crop)
            text, method = ocr_crop(crop, region, debug_dir, stem)
            if region == "name": value = clean_name(text)
            elif region == "number": value = extract_number(text)
            else: value = extract_set_code(text)
            values[region] = value
            methods[region] = method
            print(f"  {region}: {value!r}  raw={text!r}")
        card_name, set_name, card_number, conf, reason = match_card(cards, values.get("name",""), values.get("number",""), values.get("setcode",""))
        if card_name:
            print(f"  Match: {card_name} | {set_name} | {card_number} | {conf:.2f}")
            print(f"  Reason: {reason}")
        else:
            print("  Match: needs manual review")
        rows.append({
            "file": fname,
            "ocr_name": values.get("name", ""),
            "ocr_number": values.get("number", ""),
            "ocr_setcode": values.get("setcode", ""),
            "match_name": card_name,
            "match_set": set_name,
            "match_number": card_number,
            "confidence": f"{conf:.2f}",
            "reason": reason,
            "name_method": methods.get("name", ""),
            "number_method": methods.get("number", ""),
            "setcode_method": methods.get("setcode", ""),
        })
    csv_path = out_dir / "region_ocr_results.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["file","ocr_name","ocr_number","ocr_setcode","match_name","match_set","match_number","confidence","reason","name_method","number_method","setcode_method"])
        writer.writeheader(); writer.writerows(rows)
    print(f"Done. Results: {csv_path}")
    print(f"Crops: {crop_dir}")
    print(f"OCR debug: {debug_dir}")

if __name__ == "__main__":
    main()
