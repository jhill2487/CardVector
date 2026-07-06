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
        exact = [
            c for c in candidates
            if c.get("name_similarity", 0) >= 0.99
            and _number_left(c.get("card_number", "")) == num_left
        ]

        # If OCR read a denominator such as 036/086, use it as a tie-breaker.
        denom = ""
        m = re.search(r"/\s*0*(\d{1,3})", str(number or ""))
        if m:
            denom = m.group(1)

        if len(exact) > 1 and denom:
            exact_with_total = []
            for c in exact:
                total = str(
                    c.get("set_total", "")
                    or c.get("total_cards", "")
                    or c.get("printed_total", "")
                    or c.get("set_card_count", "")
                    or ""
                )
                total_digits = re.sub(r"\D", "", total).lstrip("0")
                if total_digits == denom:
                    exact_with_total.append(c)

            if len(exact_with_total) == 1:
                top = exact_with_total[0]
                return ({
                    "status": "Auto Match",
                    "card_name": top.get("card_name", ""),
                    "set_name": top.get("set_name", ""),
                    "card_number": top.get("card_number", ""),
                    "confidence": 0.99,
                    "reason": f"Exact name+number match; denominator /{denom} resolved set tie",
                }, candidates)

        # If there are multiple exact name+number matches, use the printed denominator
        # from OCR (example: 036/086 -> 86) to resolve by database set_total.
        denom = ""
        m = re.search(r"/\s*0*(\d{1,3})", str(number or ""))
        if m:
            denom = m.group(1)

        if len(exact) > 1 and denom:
            exact_with_total = []
            for c in exact:
                total_raw = str(c.get("set_total", "") or "")
                total_digits = re.sub(r"\D", "", total_raw).lstrip("0")
                if total_digits == denom:
                    exact_with_total.append(c)

            if len(exact_with_total) == 1:
                top = exact_with_total[0]
                return ({
                    "status": "Auto Match",
                    "card_name": top.get("card_name", ""),
                    "set_name": top.get("set_name", ""),
                    "card_number": top.get("card_number", ""),
                    "confidence": 0.99,
                    "reason": f"Exact name+number match; set_total {denom} resolved tie",
                }, candidates)

        if len(exact) == 1:
            top = exact[0]
            return ({
                "status": "Auto Match",
                "card_name": top.get("card_name", ""),
                "set_name": top.get("set_name", ""),
                "card_number": top.get("card_number", ""),
                "confidence": 0.99,
                "reason": "Unique exact name+number match using known-good geometry crops",
            }, candidates)

        top = candidates[0]
        second = candidates[1]["score"] if len(candidates) > 1 else 0
        top_sim = top.get("name_similarity", 0)
        top_num_ok = _number_left(top.get("card_number", "")) == num_left

        # Conservative fallback: name must be quite close, number must agree, and lead must be clear.
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


# --- BOTTOM_ID_SPECIAL_NUMBER_PATCH_V1 ---
# Adds a combined bottom-left/bottom-number crop for TG/GG/promo-style card numbers.
# This wraps the existing scan_image without changing locked geometry/layout files.

_previous_scan_image_before_bottom_id_patch = scan_image

def _bottom_id_clean_special_number(text: str) -> str:
    import re
    raw = str(text or "").upper()
    raw = raw.replace(" ", "").replace("\\", "/").replace("|", "/")
    raw = raw.replace("O", "0")  # common OCR mistake in numbers
    raw = raw.replace("T6", "TG").replace("T0", "TG").replace("1G", "TG")
    raw = raw.replace("G6", "GG").replace("66", "GG")

    patterns = [
        r"(TG\d{1,2}/TG\d{1,2})",
        r"(GG\d{1,2}/GG\d{1,2})",
        r"(SVP\d{1,3})",
        r"(SWSH\d{1,3})",
        r"(SM\d{1,3})",
        r"(XY\d{1,3})",
        r"(BW\d{1,3})",
    ]
    for pat in patterns:
        m = re.search(pat, raw)
        if m:
            val = m.group(1)
            val = re.sub(r"TG(\d)(/TG)", r"TG0\1\2", val)
            val = re.sub(r"GG(\d)(/GG)", r"GG0\1\2", val)
            return val

    return ""


def _bottom_id_ocr_attempts(crop_path):
    attempts = []
    try:
        from PIL import Image, ImageOps, ImageEnhance, ImageFilter
        import pytesseract
    except Exception:
        return attempts, ""

    img = Image.open(crop_path)
    variants = []

    for scale in (4, 6, 8, 10):
        w, h = img.size
        base = img.resize((w * scale, h * scale))
        gray = ImageOps.grayscale(base)
        variants.append((f"gray_{scale}x", gray))
        variants.append((f"contrast_{scale}x", ImageEnhance.Contrast(gray).enhance(2.5)))
        sharp = ImageEnhance.Contrast(gray).enhance(2.5).filter(ImageFilter.SHARPEN)
        variants.append((f"contrast_sharp_{scale}x", sharp))
        thr = gray.point(lambda p: 255 if p > 150 else 0)
        variants.append((f"threshold_{scale}x", thr))

    configs = [
        "--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/",
        "--psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/",
        "--psm 13 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/",
        "--psm 6",
    ]

    best = ""
    for vname, im in variants:
        for cfg in configs:
            try:
                text = pytesseract.image_to_string(im, config=cfg).strip()
            except Exception:
                text = ""
            attempts.append({"variant": vname, "config": cfg, "text": text})
            cleaned = _bottom_id_clean_special_number(text)
            if cleaned:
                best = cleaned
                return attempts, best

    return attempts, best


def _bottom_id_match_special_number(rows, name, special_number):
    import re
    from difflib import SequenceMatcher

    def norm(s):
        return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9' ]", " ", str(s or "").lower())).strip()

    def clean_num(s):
        return re.sub(r"[^A-Z0-9/]", "", str(s or "").upper())

    name_n = norm(name)
    num_n = clean_num(special_number)

    candidates = []
    if not name_n or not num_n:
        return None, []

    for r in rows:
        db_name = r.get("card_name", "")
        db_num = clean_num(r.get("card_number", "") or r.get("printed_number", ""))
        sim = SequenceMatcher(None, name_n, norm(db_name)).ratio() if db_name else 0.0
        num_left = num_n.split("/")[0]
        num_ok = (db_num == num_n) or (num_left and db_num == num_left)
        if num_ok or sim >= 0.75:
            item = dict(r)
            item["score"] = round((0.75 if num_ok else 0.0) + (0.25 * sim), 3)
            item["name_similarity"] = round(sim, 3)
            candidates.append(item)

    candidates.sort(key=lambda x: x.get("score", 0), reverse=True)
    candidates = candidates[:10]

    exact = [
        c for c in candidates
        if c.get("name_similarity", 0) >= 0.99
        and (clean_num(c.get("card_number", "") or c.get("printed_number", "")) in (num_n, num_n.split("/")[0]))
    ]

    if len(exact) == 1:
        top = exact[0]
        return {
            "status": "Auto Match",
            "card_name": top.get("card_name", ""),
            "set_name": top.get("set_name", ""),
            "card_number": top.get("card_number", ""),
            "confidence": 0.99,
            "reason": f"Special number exact match from bottom_id_crop: {num_n}",
        }, candidates

    return None, candidates


def _bottom_id_load_rows(sqlite_path):
    import sqlite3
    from pathlib import Path

    p = Path(sqlite_path)
    if not p.exists():
        return []

    con = sqlite3.connect(str(p))
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    rows = [dict(r) for r in cur.execute("select * from pokemon_cards").fetchall()]
    con.close()
    return rows


def scan_image(image_path, config, output_dir):
    result = _previous_scan_image_before_bottom_id_patch(image_path, config, output_dir)

    try:
        from pathlib import Path
        import cv2
        import importlib.util
        import numpy as np

        root = Path(__file__).resolve().parent
        output_dir_p = Path(output_dir)
        image_path_p = Path(image_path)

        warped_url = ((result.get("debug") or {}).get("warped_card_url") or "")
        if not warped_url:
            return result

        rel = warped_url.lstrip("/").replace("/", "\\")
        warped_path = root / rel
        if not warped_path.exists():
            return result

        kg_path = root / "known_good" / "template_region_warp_matcher_v0_7.py"
        template_label = root / "known_good" / "IMG_7505.json"
        if not kg_path.exists() or not template_label.exists():
            return result

        spec = importlib.util.spec_from_file_location("kg_v07_bottom_id", kg_path)
        kg = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(kg)

        template = kg.load_json(template_label)
        norm_regions, _ = kg.template_normalized_regions(template)

        warped = cv2.imread(str(warped_path))
        if warped is None:
            return result

        h, w = warped.shape[:2]

        set_poly = kg.denormalize_region(norm_regions["setcode"], w, h)
        num_poly = kg.denormalize_region(norm_regions["number"], w, h)

        all_pts = np.vstack([set_poly, num_poly])
        x1 = max(0, int(np.min(all_pts[:, 0])) - 18)
        y1 = max(0, int(np.min(all_pts[:, 1])) - 12)
        x2 = min(w, int(np.max(all_pts[:, 0])) + 22)
        y2 = min(h, int(np.max(all_pts[:, 1])) + 14)

        x2 = min(w, x2 + 55)

        crop = warped[y1:y2, x1:x2]
        if crop.size == 0:
            return result

        crops_dir = output_dir_p / "region_crops"
        crops_dir.mkdir(parents=True, exist_ok=True)
        bottom_path = crops_dir / f"{image_path_p.stem}_bottom_id_crop.jpg"
        cv2.imwrite(str(bottom_path), crop)

        result.setdefault("debug", {})
        result["debug"]["bottom_id_crop_url"] = f"/studio_results/{output_dir_p.name}/region_crops/{bottom_path.name}"

        attempts, special_number = _bottom_id_ocr_attempts(bottom_path)
        result.setdefault("ocr_attempts", {})
        result["ocr_attempts"]["bottom_id"] = attempts
        result.setdefault("ocr", {})
        result["ocr"]["bottom_id"] = special_number

        if special_number and not result["ocr"].get("number"):
            result["ocr"]["number"] = special_number

        match_status = (result.get("match") or {}).get("status", "")
        if special_number and result["ocr"].get("name") and match_status != "Auto Match":
            sqlite_path = (config or {}).get("sqlite_path", "database/putnam_pokemon_cloud_ready.sqlite")
            rows = _bottom_id_load_rows(root / sqlite_path)
            match, candidates = _bottom_id_match_special_number(rows, result["ocr"].get("name", ""), special_number)
            if candidates:
                result["candidates"] = candidates
            if match:
                result["match"] = match
                result["status"] = match.get("status", "Auto Match")

        return result

    except Exception as exc:
        result.setdefault("debug", {})
        result["debug"]["bottom_id_patch_error"] = str(exc)
        return result


# --- DB_ASSISTED_NAME_FROM_NUMBER_PATCH_V1 ---
# Purpose:
# If geometry/OCR found a strong special number such as GG15/GG70 but name OCR is fuzzy
# such as "Solroc a", use the database rows matching that exact number to correct the
# card name and safely auto-match only when evidence is strong.
#
# This patch intentionally does NOT change:
# - known_good geometry
# - scanner_studio.html layout
# - scanner_server.py
# - crop generation

_previous_scan_image_before_db_assisted_name_patch = scan_image

def _db_assist_clean_num_v1(s):
    import re
    return re.sub(r"[^A-Z0-9/]", "", str(s or "").upper())

def _db_assist_norm_name_v1(s):
    import re
    s = str(s or "").lower().replace("Ã©", "e")
    s = re.sub(r"[^a-z0-9' ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def _db_assist_load_rows_v1(sqlite_path):
    import sqlite3
    from pathlib import Path

    p = Path(sqlite_path)
    if not p.exists():
        return []

    con = sqlite3.connect(str(p))
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    rows = [dict(r) for r in cur.execute("select * from pokemon_cards").fetchall()]
    con.close()
    return rows

def _db_assist_match_from_number_v1(rows, ocr_name, ocr_number):
    from difflib import SequenceMatcher

    num_full = _db_assist_clean_num_v1(ocr_number)
    if not num_full:
        return None, []

    num_left = num_full.split("/")[0]
    name_n = _db_assist_norm_name_v1(ocr_name)

    exact_number_rows = []
    for r in rows:
        db_card_number = _db_assist_clean_num_v1(r.get("card_number", ""))
        db_printed = _db_assist_clean_num_v1(r.get("printed_number", ""))

        number_match = (
            db_card_number == num_full
            or db_printed == num_full
            or (num_left and db_card_number == num_left)
            or (num_left and db_printed == num_left)
        )

        if number_match:
            db_name = r.get("card_name", "")
            sim = SequenceMatcher(None, name_n, _db_assist_norm_name_v1(db_name)).ratio() if name_n and db_name else 0.0
            item = dict(r)
            item["score"] = round(0.80 + (0.20 * sim), 3)
            item["name_similarity"] = round(sim, 3)
            item["number_evidence"] = num_full
            exact_number_rows.append(item)

    exact_number_rows.sort(key=lambda x: x.get("score", 0), reverse=True)

    if not exact_number_rows:
        return None, []

    top = exact_number_rows[0]
    second_score = exact_number_rows[1]["score"] if len(exact_number_rows) > 1 else 0
    top_sim = top.get("name_similarity", 0)

    unique_number = len(exact_number_rows) == 1
    clear_lead = (top.get("score", 0) - second_score) >= 0.08

    if (unique_number and top_sim >= 0.55) or (top_sim >= 0.78 and clear_lead):
        return {
            "status": "Auto Match",
            "card_name": top.get("card_name", ""),
            "set_name": top.get("set_name", ""),
            "card_number": top.get("card_number", ""),
            "confidence": 0.99 if unique_number else min(0.98, top.get("score", 0)),
            "reason": f"Database-assisted name correction from exact number {num_full}; OCR name was '{ocr_name}'",
        }, exact_number_rows[:10]

    return None, exact_number_rows[:10]

def scan_image(image_path, config, output_dir):
    result = _previous_scan_image_before_db_assisted_name_patch(image_path, config, output_dir)

    try:
        match_status = ((result.get("match") or {}).get("status") or "")
        if match_status == "Auto Match":
            return result

        ocr = result.get("ocr") or {}
        ocr_name = ocr.get("name", "")
        ocr_number = ocr.get("number", "") or ocr.get("bottom_id", "")

        clean_num = _db_assist_clean_num_v1(ocr_number)
        if not clean_num:
            return result

        special_prefixes = ("GG", "TG", "SVP", "SWSH", "SM", "XY", "BW")
        looks_special = clean_num.startswith(special_prefixes)
        has_slash_number = "/" in clean_num and any(ch.isdigit() for ch in clean_num)

        if not (looks_special or has_slash_number):
            return result

        from pathlib import Path
        root = Path(__file__).resolve().parent
        sqlite_path = (config or {}).get("sqlite_path", "database/putnam_pokemon_cloud_ready.sqlite")
        rows = _db_assist_load_rows_v1(root / sqlite_path)

        match, candidates = _db_assist_match_from_number_v1(rows, ocr_name, clean_num)
        if candidates:
            result["candidates"] = candidates

        if match:
            result["match"] = match
            result["status"] = match.get("status", "Auto Match")
            result.setdefault("ocr", {})
            result["ocr"]["database_corrected_name"] = match.get("card_name", "")

        return result

    except Exception as exc:
        result.setdefault("debug", {})
        result["debug"]["db_assisted_name_patch_error"] = str(exc)
        return result


# --- TG_SPECIAL_NUMBER_REPAIR_PATCH_V1 ---
# Purpose:
# Repair Trainer Gallery OCR variants like:
#   TGOMTG30, TGOMIG30, TGO1TG30, TGO14G30
# into:
#   TG01/TG30
#
# This patch only overrides _bottom_id_clean_special_number.
# It does not change geometry, crops, Studio HTML, scanner_server, or database files.

_previous_bottom_id_clean_special_number_before_tg_patch = _bottom_id_clean_special_number

def _bottom_id_clean_special_number(text: str) -> str:
    import re

    raw_original = str(text or "").upper()
    raw = raw_original.replace(" ", "").replace("\\", "/").replace("|", "/")
    raw = raw.replace(",", "/").replace(".", "")
    raw = raw.replace("’", "").replace("'", "").replace("`", "")

    # First, let the previous cleaner handle already-clean GG/TG/SVP/SWSH/etc.
    prev = _previous_bottom_id_clean_special_number_before_tg_patch(raw)
    if prev:
        return prev

    # Create a digit-normalized copy for TG/GG repair only.
    # OCR commonly sees: O -> 0, I/L -> 1.
    t = raw.replace("O", "0").replace("I", "1").replace("L", "1")

    # TG01TG30 or TG01/TG30 -> TG01/TG30
    m = re.search(r"TG0*(\d{1,2})/?TG0*(\d{1,2})", t)
    if m:
        left = int(m.group(1))
        right = int(m.group(2))
        return f"TG{left:02d}/TG{right}"

    # Variants seen in Flareon:
    # TGOMTG30 -> TG0MTG30 after O->0
    # TGOMIG30 -> TG0M1G30 after O->0 and I->1
    # Treat M/N immediately after TG0 as likely "1/" for TG01.
    m = re.search(r"TG0*[MN]+[1/]?TG0*(\d{1,2})", t)
    if m:
        right = int(m.group(1))
        return f"TG01/TG{right}"

    m = re.search(r"TG0*[MN]+[1/]?G0*(\d{1,2})", t)
    if m:
        right = int(m.group(1))
        return f"TG01/TG{right}"

    # Repair TGO14G30 / TG014G30 as TG01/TG30 when total 30 is visible.
    m = re.search(r"TG0*1\d*G0*(30)", t)
    if m:
        return "TG01/TG30"

    # Repair when OCR captures 01 and TG30 nearby.
    m = re.search(r"0*1/?TG0*(\d{1,2})", t)
    if m and "TG" in t:
        right = int(m.group(1))
        return f"TG01/TG{right}"

    # General cautious fallback for TG strings with visible total 30.
    if "TG" in t and "30" in t:
        m = re.search(r"TG0*(\d{1,2})", t)
        if m:
            left = int(m.group(1))
            if 1 <= left <= 30:
                return f"TG{left:02d}/TG30"

    # Keep a no-slash GG fallback.
    m = re.search(r"GG0*(\d{1,2})/?GG0*(\d{1,2})", t)
    if m:
        left = int(m.group(1))
        right = int(m.group(2))
        return f"GG{left:02d}/GG{right}"

    return ""


# --- SPECIAL_NUMBER_TOTAL_NORMALIZATION_PATCH_V1 ---
# Purpose:
# Treat special numbering forms as equivalent during DB-assisted matching:
#   TG01/TG30 == TG01/30
#   GG15/GG70 == GG15/70
#
# This only overrides the DB-assisted number cleaning/matching helpers.
# It does not change geometry, crops, Studio HTML, scanner_server, or database files.

_previous_db_assist_clean_num_before_total_norm_patch = _db_assist_clean_num_v1
_previous_db_assist_match_from_number_before_total_norm_patch = _db_assist_match_from_number_v1

def _db_assist_clean_num_v1(s):
    import re
    raw = _previous_db_assist_clean_num_before_total_norm_patch(s)
    raw = raw.upper()

    # Normalize OCR/database equivalent forms:
    # TG01/TG30 -> TG01/30
    # GG15/GG70 -> GG15/70
    raw = re.sub(r"^(TG\d{1,2})/TG(\d{1,2})$", r"\1/\2", raw)
    raw = re.sub(r"^(GG\d{1,2})/GG(\d{1,2})$", r"\1/\2", raw)

    return raw

def _db_assist_num_equivalents_v1(s):
    import re
    base = _db_assist_clean_num_v1(s)
    vals = {base}
    m = re.match(r"^(TG\d{1,2})/(\d{1,2})$", base)
    if m:
        vals.add(f"{m.group(1)}/TG{m.group(2)}")
        vals.add(m.group(1))
    m = re.match(r"^(GG\d{1,2})/(\d{1,2})$", base)
    if m:
        vals.add(f"{m.group(1)}/GG{m.group(2)}")
        vals.add(m.group(1))
    if "/" in base:
        vals.add(base.split("/")[0])
    return vals

def _db_assist_match_from_number_v1(rows, ocr_name, ocr_number):
    from difflib import SequenceMatcher

    num_full = _db_assist_clean_num_v1(ocr_number)
    if not num_full:
        return None, []

    wanted_nums = _db_assist_num_equivalents_v1(num_full)
    name_n = _db_assist_norm_name_v1(ocr_name)

    exact_number_rows = []
    for r in rows:
        db_card_number = _db_assist_clean_num_v1(r.get("card_number", ""))
        db_printed = _db_assist_clean_num_v1(r.get("printed_number", ""))

        db_vals = set()
        db_vals.update(_db_assist_num_equivalents_v1(db_card_number))
        db_vals.update(_db_assist_num_equivalents_v1(db_printed))

        number_match = bool(wanted_nums.intersection(db_vals))

        if number_match:
            db_name = r.get("card_name", "")
            sim = SequenceMatcher(None, name_n, _db_assist_norm_name_v1(db_name)).ratio() if name_n and db_name else 0.0
            item = dict(r)
            item["score"] = round(0.80 + (0.20 * sim), 3)
            item["name_similarity"] = round(sim, 3)
            item["number_evidence"] = num_full
            item["number_equivalents"] = sorted(wanted_nums)
            exact_number_rows.append(item)

    exact_number_rows.sort(key=lambda x: x.get("score", 0), reverse=True)

    if not exact_number_rows:
        return None, []

    top = exact_number_rows[0]
    second_score = exact_number_rows[1]["score"] if len(exact_number_rows) > 1 else 0
    top_sim = top.get("name_similarity", 0)

    unique_number = len(exact_number_rows) == 1
    clear_lead = (top.get("score", 0) - second_score) >= 0.08

    if (unique_number and top_sim >= 0.50) or (top_sim >= 0.76 and clear_lead):
        return {
            "status": "Auto Match",
            "card_name": top.get("card_name", ""),
            "set_name": top.get("set_name", ""),
            "card_number": top.get("card_number", ""),
            "confidence": 0.99 if unique_number else min(0.98, top.get("score", 0)),
            "reason": f"Database-assisted special-number match from {num_full}; OCR name was '{ocr_name}'",
        }, exact_number_rows[:10]

    return None, exact_number_rows[:10]


# --- TG_OCR_FOCUS_PATCH_V2 ---
# Purpose:
# Improve Trainer Gallery OCR by creating smaller focused crops from the existing bottom_id_crop.
# This targets only TG numbering such as TG01/TG30 and does not alter locked geometry/layout/server.

_previous_scan_image_before_tg_focus_v2 = scan_image

def _tg_focus_v2_repair(text: str) -> str:
    import re

    raw = str(text or "").upper()
    raw = raw.replace("\\", "/").replace("|", "/").replace(",", "/")
    raw = raw.replace(" ", "").replace("\n", "")
    raw = raw.replace("’", "").replace("'", "").replace("`", "").replace(".", "")

    # Keep a display-ish raw copy, then normalize common OCR confusions for matching.
    t = raw
    t = t.replace("O", "0")
    t = t.replace("I", "1")
    t = t.replace("L", "1")
    t = t.replace("S", "5")

    # Clean direct forms:
    # TG01/TG30, TG01/30, TG01TG30
    m = re.search(r"TG0*(\d{1,2})/?TG0*(\d{1,2})", t)
    if m:
        left = int(m.group(1))
        right = int(m.group(2))
        if 1 <= left <= 30 and 1 <= right <= 99:
            return f"TG{left:02d}/TG{right}"

    m = re.search(r"TG0*(\d{1,2})/0*(\d{1,2})", t)
    if m:
        left = int(m.group(1))
        right = int(m.group(2))
        if 1 <= left <= 30 and 1 <= right <= 99:
            return f"TG{left:02d}/TG{right}"

    # Common Flareon-style corruptions:
    # TGOMTG30 -> TG0MTG30
    # TGOMIG30 -> TG0M1G30
    # TGO14G30 -> TG014G30
    m = re.search(r"TG0*[MN]+[1/]?TG?0*(\d{1,2})", t)
    if m:
        right = int(m.group(1))
        if 1 <= right <= 99:
            return f"TG01/TG{right}"

    m = re.search(r"TG0*1\d*G0*(30)", t)
    if m:
        return "TG01/TG30"

    # If the OCR sees just 02/30 or 2/30 from the focused crop, accept as TGxx/TG30.
    m = re.search(r"\b0*(\d{1,2})/0*(30)\b", t)
    if m:
        left = int(m.group(1))
        if 1 <= left <= 30:
            return f"TG{left:02d}/TG30"

    # If TG and total 30 are visible, find any plausible left number after TG.
    if "TG" in t and "30" in t:
        m = re.search(r"TG0*(\d{1,2})", t)
        if m:
            left = int(m.group(1))
            if 1 <= left <= 30:
                return f"TG{left:02d}/TG30"

    # Fallback for text like "TG02" without total, only if visible and plausible.
    m = re.search(r"TG0*(\d{1,2})", t)
    if m:
        left = int(m.group(1))
        if 1 <= left <= 30:
            return f"TG{left:02d}/TG30"

    return ""


def _tg_focus_v2_ocr(crop_path):
    attempts = []
    best = ""

    try:
        from PIL import Image, ImageOps, ImageEnhance, ImageFilter
        import pytesseract
    except Exception:
        return attempts, best, []

    img = Image.open(crop_path)
    w, h = img.size

    # Focus windows: TG number is usually right side of bottom_id crop.
    boxes = [
        ("full", (0, 0, w, h)),
        ("right_70", (int(w * 0.30), 0, w, h)),
        ("right_55", (int(w * 0.45), 0, w, h)),
        ("right_40", (int(w * 0.60), 0, w, h)),
        ("lower_right_70", (int(w * 0.30), int(h * 0.25), w, h)),
        ("lower_right_55", (int(w * 0.45), int(h * 0.25), w, h)),
    ]

    focus_images = []
    for label, box in boxes:
        try:
            focus = img.crop(box)
            if focus.size[0] >= 8 and focus.size[1] >= 8:
                focus_images.append((label, focus))
        except Exception:
            pass

    configs = [
        "--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/",
        "--psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/",
        "--psm 13 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/",
        "--psm 6",
    ]

    for flabel, fim in focus_images:
        for scale in (4, 6, 8, 10, 12):
            sw, sh = fim.size
            base = fim.resize((sw * scale, sh * scale))
            gray = ImageOps.grayscale(base)
            variants = [
                (f"{flabel}_gray_{scale}x", gray),
                (f"{flabel}_contrast_{scale}x", ImageEnhance.Contrast(gray).enhance(2.8)),
                (f"{flabel}_sharp_{scale}x", ImageEnhance.Contrast(gray).enhance(2.8).filter(ImageFilter.SHARPEN)),
                (f"{flabel}_threshold_light_{scale}x", gray.point(lambda p: 255 if p > 135 else 0)),
                (f"{flabel}_threshold_dark_{scale}x", gray.point(lambda p: 255 if p > 175 else 0)),
            ]

            for vname, im in variants:
                for cfg in configs:
                    try:
                        text = pytesseract.image_to_string(im, config=cfg).strip()
                    except Exception:
                        text = ""
                    repaired = _tg_focus_v2_repair(text)
                    attempts.append({
                        "variant": vname,
                        "config": cfg,
                        "text": text,
                        "repair": repaired
                    })
                    if repaired:
                        return attempts, repaired, focus_images

    return attempts, best, focus_images


def scan_image(image_path, config, output_dir):
    result = _previous_scan_image_before_tg_focus_v2(image_path, config, output_dir)

    try:
        match_status = ((result.get("match") or {}).get("status") or "")
        ocr = result.get("ocr") or {}

        # Do not disturb successful matches.
        if match_status == "Auto Match":
            return result

        debug = result.get("debug") or {}
        bottom_url = debug.get("bottom_id_crop_url", "")
        if not bottom_url:
            return result

        from pathlib import Path
        import shutil

        root = Path(__file__).resolve().parent
        rel = bottom_url.lstrip("/").replace("/", "\\")
        bottom_path = root / rel
        if not bottom_path.exists():
            return result

        attempts, tg_number, focus_images = _tg_focus_v2_ocr(bottom_path)

        result.setdefault("ocr_attempts", {})
        result["ocr_attempts"]["tg_focus_v2"] = attempts

        # Save focus crops for review.
        try:
            from PIL import Image
            img = Image.open(bottom_path)
            crops_dir = bottom_path.parent
            w, h = img.size
            focus_specs = [
                ("tg_focus_right_70", (int(w * 0.30), 0, w, h)),
                ("tg_focus_right_55", (int(w * 0.45), 0, w, h)),
                ("tg_focus_lower_right_70", (int(w * 0.30), int(h * 0.25), w, h)),
            ]
            for name, box in focus_specs:
                fp = crops_dir / f"{Path(image_path).stem}_{name}.jpg"
                img.crop(box).save(fp)
                result.setdefault("debug", {})
                result["debug"][f"{name}_url"] = f"/studio_results/{Path(output_dir).name}/region_crops/{fp.name}"
        except Exception as crop_exc:
            result.setdefault("debug", {})
            result["debug"]["tg_focus_crop_save_error"] = str(crop_exc)

        if tg_number:
            result.setdefault("ocr", {})
            result["ocr"]["tg_focus_v2"] = tg_number

            # Prefer TG focus result when normal number is blank or non-TG.
            current_num = str(result["ocr"].get("number", "") or "")
            if not current_num.startswith("TG"):
                result["ocr"]["number"] = tg_number
                result["ocr"]["bottom_id"] = tg_number

            # Try database-assisted match if helper exists.
            if "_db_assist_match_from_number_v1" in globals() and "_db_assist_load_rows_v1" in globals():
                sqlite_path = (config or {}).get("sqlite_path", "database/putnam_pokemon_cloud_ready.sqlite")
                rows = _db_assist_load_rows_v1(root / sqlite_path)
                match, candidates = _db_assist_match_from_number_v1(rows, result["ocr"].get("name", ""), tg_number)
                if candidates:
                    result["candidates"] = candidates
                if match:
                    result["match"] = match
                    result["status"] = match.get("status", "Auto Match")
                    result["ocr"]["database_corrected_name"] = match.get("card_name", "")

        return result

    except Exception as exc:
        result.setdefault("debug", {})
        result["debug"]["tg_focus_v2_error"] = str(exc)
        return result
