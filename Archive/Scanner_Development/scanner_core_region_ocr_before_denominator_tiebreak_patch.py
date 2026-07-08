#!/usr/bin/env python3
"""Scanner Studio core region OCR engine.

This patch intentionally LOCKS geometry to the known-good v0.7 pipeline:
  known_good/template_region_warp_matcher_v0_7.py

It adds OCR on top of the generated name/number/setcode crops, without changing
warp/template projection behavior.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import importlib.util
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Tuple

import cv2
import numpy as np

try:
    from PIL import Image, ImageOps, ImageEnhance, ImageFilter
except Exception:
    Image = None
    ImageOps = None
    ImageEnhance = None
    ImageFilter = None

try:
    import pytesseract
    default_tess = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.path.exists(default_tess):
        pytesseract.pytesseract.tesseract_cmd = default_tess
except Exception:
    pytesseract = None

ROOT = Path(__file__).resolve().parent


def _safe_base_from_upload(path: Path) -> str:
    """Map IMG_7507_113000.JPG back to IMG_7507."""
    stem = path.stem
    parts = stem.split("_")
    if len(parts) >= 2 and parts[0].upper() == "IMG" and parts[1].isdigit():
        return f"{parts[0]}_{parts[1]}"
    return stem


def _clean_name_text(text: str) -> str:
    text = str(text or "").strip()
    text = re.sub(r"[\[\]{}()_~`|\\]", " ", text)
    text = re.sub(r"[^A-Za-z0-9' .\-éÉ]", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" .,-")
    return text


def _clean_number_text(text: str) -> str:
    raw = str(text or "").upper().replace("O", "0")
    raw = re.sub(r"\s+", "", raw)
    m = re.search(r"(\d{1,3})/(\d{1,3})", raw)
    if not m:
        return ""
    left = str(int(m.group(1))) if m.group(1).isdigit() else m.group(1)
    right = str(int(m.group(2))) if m.group(2).isdigit() else m.group(2)
    return f"{left}/{right}"


def _clean_setcode_text(text: str) -> str:
    raw = str(text or "").upper()
    raw = re.sub(r"[^A-Z]", "", raw)
    # Normalize common EN suffix behavior; keep compact code for now.
    return raw


def _ocr_variants_pil(image_path: Path, region: str) -> List[Tuple[str, Image.Image]]:
    if Image is None:
        return []
    img = Image.open(image_path).convert("RGB")
    variants: List[Tuple[str, Image.Image]] = [("raw", img)]
    gray = ImageOps.grayscale(img)
    # Region-specific enlargement; number/setcode are tiny.
    scales = [4, 6, 8] if region in ("number", "setcode") else [3, 5, 7]
    for scale in scales:
        enlarged = gray.resize((gray.width * scale, gray.height * scale), Image.Resampling.LANCZOS)
        variants.append((f"gray_{scale}x", enlarged))
        contrast = ImageEnhance.Contrast(enlarged).enhance(2.5)
        sharp = contrast.filter(ImageFilter.SHARPEN)
        variants.append((f"contrast_sharp_{scale}x", sharp))
        # Otsu/adaptive through cv2 where available.
        arr = np.array(enlarged)
        try:
            _, otsu = cv2.threshold(arr, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            variants.append((f"otsu_{scale}x", Image.fromarray(otsu)))
        except Exception:
            pass
    return variants


def _run_ocr_attempts(image_path: Path, region: str) -> List[Dict[str, str]]:
    attempts: List[Dict[str, str]] = []
    if pytesseract is None or Image is None:
        return attempts

    if region == "name":
        configs = ["--psm 8", "--psm 7", "--psm 6"]
    elif region == "number":
        configs = [
            "--psm 8 -c tessedit_char_whitelist=0123456789/ABCDEFGHIJKLMNOPQRSTUVWXYZ",
            "--psm 7 -c tessedit_char_whitelist=0123456789/ABCDEFGHIJKLMNOPQRSTUVWXYZ",
            "--psm 13 -c tessedit_char_whitelist=0123456789/ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        ]
    else:
        configs = [
            "--psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ",
            "--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ",
            "--psm 13 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        ]

    for variant_name, img in _ocr_variants_pil(image_path, region):
        for cfg in configs:
            try:
                text = pytesseract.image_to_string(img, config=cfg).strip()
            except Exception as exc:
                text = ""
            attempts.append({"variant": variant_name, "config": cfg, "text": text})
    return attempts


def _choose_best_name(attempts: List[Dict[str, str]]) -> str:
    candidates: List[str] = []
    bad_words = {"pokemon", "basic", "stage", "evolves", "attack", "weakness", "retreat"}
    for a in attempts:
        for line in str(a.get("text", "")).splitlines():
            c = _clean_name_text(line)
            if not c or len(c) < 3 or len(c) > 28:
                continue
            if any(w in c.lower().split() for w in bad_words):
                continue
            # Prefer alphabetic, short name-like outputs.
            if sum(ch.isalpha() for ch in c) < 3:
                continue
            candidates.append(c)
    if not candidates:
        return ""
    # Most common cleaned candidate, then shortest reasonable.
    counts: Dict[str, int] = {}
    for c in candidates:
        key = c.strip()
        counts[key] = counts.get(key, 0) + 1
    return sorted(counts, key=lambda k: (-counts[k], len(k)))[0]


def _choose_best_number(attempts: List[Dict[str, str]]) -> str:
    nums: List[str] = []
    for a in attempts:
        n = _clean_number_text(a.get("text", ""))
        if n:
            nums.append(n)
    if not nums:
        return ""
    counts: Dict[str, int] = {}
    for n in nums:
        counts[n] = counts.get(n, 0) + 1
    return sorted(counts, key=lambda k: (-counts[k], len(k)))[0]


def _choose_best_setcode(attempts: List[Dict[str, str]]) -> str:
    codes: List[str] = []
    for a in attempts:
        c = _clean_setcode_text(a.get("text", ""))
        if 2 <= len(c) <= 6:
            codes.append(c)
    if not codes:
        return ""
    counts: Dict[str, int] = {}
    for c in codes:
        counts[c] = counts.get(c, 0) + 1
    return sorted(counts, key=lambda k: (-counts[k], len(k)))[0]


def _load_db(sqlite_path: Path) -> List[Dict[str, str]]:
    if not sqlite_path.exists():
        return []
    con = sqlite3.connect(str(sqlite_path))
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    preferred = ["pokemon_cards", "cards", "Pokemon_Lookup_Database"]
    table = next((t for t in preferred if t in tables), tables[0] if tables else "")
    if not table:
        return []
    rows = cur.execute(f"SELECT * FROM {table}").fetchall()
    out = []
    for r in rows:
        d = dict(r)
        # Flexible field mapping.
        def get(*names):
            for n in names:
                if n in d and d[n] is not None:
                    return str(d[n])
            return ""
        out.append({
            "card_name": get("card_name", "Card Name", "name"),
            "set_name": get("set_name", "Set Name", "set"),
            "card_number": get("card_number", "Card Number", "number"),
            "rarity": get("rarity", "Rarity"),
        })
    con.close()
    return out


def _number_left(number: str) -> str:
    m = re.search(r"(\d{1,3})(?:/\d{1,3})?", str(number or ""))
    if not m:
        return ""
    return str(int(m.group(1)))


def _norm(s: str) -> str:
    s = str(s or "").lower().replace("é", "e")
    s = re.sub(r"[^a-z0-9' ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _match_strict(rows: List[Dict[str, str]], name: str, number: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    name_n = _norm(name)
    num_left = _number_left(number)
    candidates: List[Dict[str, Any]] = []
    if not name_n or not num_left:
        return ({"status": "Needs Review", "card_name": "", "set_name": "", "card_number": "", "confidence": 0, "reason": "Missing clean name or clean number"}, [])

    for r in rows:
        db_name = r.get("card_name", "")
        db_num = _number_left(r.get("card_number", ""))
        sim = SequenceMatcher(None, name_n, _norm(db_name)).ratio() if db_name else 0.0
        number_ok = (db_num == num_left)
        score = (0.75 if number_ok else 0.0) + (0.25 * sim)
        if number_ok or sim >= 0.75:
            item = dict(r)
            item["score"] = round(score, 3)
            item["name_similarity"] = round(sim, 3)
            candidates.append(item)
    candidates.sort(key=lambda x: x.get("score", 0), reverse=True)
    candidates = candidates[:10]

    if candidates:
        top = candidates[0]
        second = candidates[1]["score"] if len(candidates) > 1 else 0
        top_sim = top.get("name_similarity", 0)
        top_num_ok = _number_left(top.get("card_number", "")) == num_left
        # Conservative: name must be quite close and number must agree.
        if top_num_ok and top_sim >= 0.88 and (top["score"] - second >= 0.08 or len(candidates) == 1):
            return ({
                "status": "Auto Match",
                "card_name": top.get("card_name", ""),
                "set_name": top.get("set_name", ""),
                "card_number": top.get("card_number", ""),
                "confidence": min(0.99, top.get("score", 0)),
                "reason": "Strict name+number agreement using known-good geometry crops",
            }, candidates)

    return ({"status": "Needs Review", "card_name": "", "set_name": "", "card_number": "", "confidence": 0, "reason": "No strict name+number database agreement"}, candidates)


def scan_image(image_path, config, output_dir):
    """Studio entrypoint expected by scanner_server.py."""
    image_path = Path(image_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    kg_path = ROOT / "known_good" / "template_region_warp_matcher_v0_7.py"
    template_label = ROOT / "known_good" / "IMG_7505.json"
    base = _safe_base_from_upload(image_path)
    target_label = ROOT / "known_good" / f"{base}.json"
    if not target_label.exists():
        target_label = ROOT / "border_training_labels" / f"{base}.json"

    if not kg_path.exists():
        return {"status": "Needs Review", "message": f"Missing known-good script: {kg_path}"}
    if not template_label.exists():
        return {"status": "Needs Review", "message": f"Missing template label: {template_label}"}
    if not target_label.exists():
        return {"status": "Needs Review", "message": f"Missing target label: {target_label}"}

    spec = importlib.util.spec_from_file_location("kg_v07", kg_path)
    kg = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(kg)

    template = kg.load_json(template_label)
    target = kg.load_json(target_label)
    img = cv2.imread(str(image_path))
    if img is None:
        return {"status": "Needs Review", "message": f"Could not read image: {image_path}"}

    card_pts = kg.pts_array(target["regions"]["card"])
    warped, _ = kg.warp_card(img, card_pts, 734, 1024)
    norm_regions, _ = kg.template_normalized_regions(template)

    warped_dir = output_dir / "warped_cards"
    crops_dir = output_dir / "region_crops"
    ocr_dir = output_dir / "ocr_debug"
    warped_dir.mkdir(exist_ok=True)
    crops_dir.mkdir(exist_ok=True)
    ocr_dir.mkdir(exist_ok=True)

    warped_path = warped_dir / f"{image_path.stem}_warped_card.jpg"
    cv2.imwrite(str(warped_path), warped)

    crop_paths: Dict[str, Path] = {}
    crop_urls: Dict[str, str] = {}
    crop_dims: Dict[str, Dict[str, int]] = {}
    for key in ["name", "number", "setcode"]:
        poly = kg.denormalize_region(norm_regions[key], 734, 1024)
        crop = kg.crop_polygon_from_warped(warped, poly, pad=8)
        crop_path = crops_dir / f"{image_path.stem}_{key}_crop.jpg"
        cv2.imwrite(str(crop_path), crop)
        crop_paths[key] = crop_path
        crop_urls[f"{key}_crop_url"] = f"/studio_results/{output_dir.name}/region_crops/{crop_path.name}"
        crop_dims[key] = {"width": int(crop.shape[1]), "height": int(crop.shape[0])}

    attempts = {
        "name": _run_ocr_attempts(crop_paths["name"], "name"),
        "number": _run_ocr_attempts(crop_paths["number"], "number"),
        "setcode": _run_ocr_attempts(crop_paths["setcode"], "setcode"),
    }
    for key, vals in attempts.items():
        (ocr_dir / f"{image_path.stem}_{key}_attempts.json").write_text(json.dumps(vals, indent=2), encoding="utf-8")

    ocr = {
        "name": _choose_best_name(attempts["name"]),
        "number": _choose_best_number(attempts["number"]),
        "setcode": _choose_best_setcode(attempts["setcode"]),
    }

    cfg = dict(config or {})
    sqlite_path = Path(cfg.get("sqlite_path", "database/putnam_pokemon_cloud_ready.sqlite"))
    if not sqlite_path.is_absolute():
        sqlite_path = ROOT / sqlite_path
    rows = _load_db(sqlite_path)
    match, candidates = _match_strict(rows, ocr["name"], ocr["number"])

    return {
        "status": match.get("status", "Needs Review"),
        "filename": image_path.name,
        "geometry_status": "PASS",
        "ocr": ocr,
        "ocr_attempts": attempts,
        "match": match,
        "candidates": candidates,
        "debug": {
            "warped_card_url": f"/studio_results/{output_dir.name}/warped_cards/{warped_path.name}",
            **crop_urls,
            "output_dir": str(output_dir),
            "ocr_debug_dir": str(ocr_dir),
            "target_label": str(target_label),
            "template_label": str(template_label),
            "crop_dimensions": crop_dims,
        },
        "label_source": "known_good_v0_7_geometry_locked",
        "label_path": str(target_label),
    }
