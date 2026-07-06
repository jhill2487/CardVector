#!/usr/bin/env python3
"""
Putnam Scanner V2.2.0 Region OCR

Pipeline:
  original photo
  -> card border polygon from Border Trainer label JSON
  -> perspective warp into upright card space
  -> apply one reusable region template
  -> OCR only name / number / set-code regions
  -> database match

This intentionally does NOT use full-card OCR for the card name, so attack names like
"Focused Wish", "Venoshock", or "Snap Inspection" cannot become the likely card name.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sqlite3
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
import pandas as pd

try:
    import pytesseract
    DEFAULT_TESSERACT = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.path.exists(DEFAULT_TESSERACT):
        pytesseract.pytesseract.tesseract_cmd = DEFAULT_TESSERACT
except Exception:
    pytesseract = None

IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tif', '.tiff'}
REGIONS = ['name', 'number', 'setcode']
REQUIRED_COLS = ['Set Name', 'Card Name', 'Card Number', 'Rarity']

SET_CODE_HINTS = {
    'BLK': 'Black Bolt',
    'WHT': 'White Flare',
    'CRI': 'Chaos Rising',
    'PRE': 'Prismatic Evolutions',
    'PAL': 'Paldea Evolved',
    'SVI': 'Scarlet & Violet',
    'OBF': 'Obsidian Flames',
    'MEG': 'Mega Evolution',
}

COLUMN_ALIASES = {
    'Set Name': ['Set Name','set_name','setName','set','Set','groupName','Group Name','expansion','Expansion','series','Series'],
    'Card Name': ['Card Name','card_name','name','Name','productName','Product Name','cardName','CardName','title','Title'],
    'Card Number': ['Card Number','card_number','number','Number','cardNumber','CardNumber','collectorNumber','Collector Number','extNumber','Ext Number','number_printed'],
    'Rarity': ['Rarity','rarity','rarityName','Rarity Name','rarity_name','subTypeName'],
}

@dataclass
class RegionOCR:
    name_text: str
    number_text: str
    setcode_text: str
    name_clean: str
    number_clean: str
    set_code: str

@dataclass
class MatchResult:
    status: str
    card_name: str = ''
    set_name: str = ''
    card_number: str = ''
    rarity: str = ''
    confidence: float = 0.0
    reason: str = ''
    candidate_count: int = 0


def normalize_text(value: str) -> str:
    value = str(value or '').lower()
    value = value.replace('é', 'e').replace('’', "'").replace('‘', "'")
    value = re.sub(r"[^a-z0-9/' ]+", ' ', value)
    return re.sub(r'\s+', ' ', value).strip()


def normalize_col_name(value: str) -> str:
    return re.sub(r'[^a-z0-9]+', '', str(value or '').lower())


def canonical_card_number(value: str) -> str:
    raw = str(value or '').upper().strip().replace('#', '')
    raw = re.sub(r'\s+', '', raw)
    if not raw:
        return ''
    def clean(part: str) -> str:
        m = re.fullmatch(r'([A-Z]*)(\d+)([A-Z]*)', part)
        if not m:
            return part
        prefix, digits, suffix = m.groups()
        return f'{prefix}{int(digits)}{suffix}'
    if '/' in raw:
        left, right = raw.split('/', 1)
        return f'{clean(left)}/{clean(right)}'
    return clean(raw)


def card_number_left(value: str) -> str:
    c = canonical_card_number(value)
    return c.split('/', 1)[0] if c else ''


def map_columns(df: pd.DataFrame) -> pd.DataFrame:
    norm_to_actual = {normalize_col_name(c): c for c in df.columns}
    mapped = {}
    for target, aliases in COLUMN_ALIASES.items():
        actual = None
        for alias in aliases:
            key = normalize_col_name(alias)
            if key in norm_to_actual:
                actual = norm_to_actual[key]
                break
        mapped[target] = df[actual] if actual else pd.Series([''] * len(df))
    out = pd.DataFrame(mapped)
    for col in REQUIRED_COLS:
        out[col] = out[col].fillna('').astype(str).str.strip()
    out = out[out['Card Name'].astype(str).str.strip() != ''].copy()
    out['Card Number Key'] = out['Card Number'].map(canonical_card_number)
    out['Card Number Left Key'] = out['Card Number'].map(card_number_left)
    out['Card Name Key'] = out['Card Name'].map(normalize_text)
    out['Set Name Key'] = out['Set Name'].map(normalize_text)
    return out.reset_index(drop=True)


def sqlite_tables(con: sqlite3.Connection) -> List[str]:
    return [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()]


def load_lookup_from_sqlite(path: Path, table: Optional[str] = None) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f'SQLite database not found: {path}')
    con = sqlite3.connect(path)
    try:
        tables = sqlite_tables(con)
        preferred = ['pokemon_cards', 'cards', 'pokemon_lookup', 'products']
        selected = table or next((t for t in preferred if t in tables), None)
        if not selected:
            for t in tables:
                info = pd.read_sql_query(f'PRAGMA table_info("{t}")', con)
                cols = {normalize_col_name(c) for c in info['name'].tolist()}
                if {'cardname'} & cols or {'name','productname'} & cols:
                    selected = t
                    break
        if not selected:
            raise ValueError(f'Could not find card table. Tables found: {tables}')
        df = pd.read_sql_query(f'SELECT * FROM "{selected}"', con)
        out = map_columns(df)
        if out.empty:
            raise ValueError(f'Table {selected} loaded but no rows mapped.')
        return out
    finally:
        con.close()


def load_lookup(path: Path, table: Optional[str] = None) -> pd.DataFrame:
    if path.suffix.lower() in {'.sqlite', '.db'}:
        return load_lookup_from_sqlite(path, table)
    if path.suffix.lower() == '.csv':
        return map_columns(pd.read_csv(path, dtype=str))
    if path.suffix.lower() in {'.xlsx', '.xlsm', '.xls'}:
        return map_columns(pd.read_excel(path, dtype=str))
    raise ValueError(f'Unsupported lookup file: {path}')


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def pts_array(points: List[dict]) -> np.ndarray:
    return np.array([[float(p['x']), float(p['y'])] for p in points], dtype=np.float32)


def order_quad(pts: np.ndarray) -> np.ndarray:
    pts = np.asarray(pts, dtype=np.float32)
    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1).reshape(-1)
    tl = pts[np.argmin(s)]
    br = pts[np.argmax(s)]
    tr = pts[np.argmin(diff)]
    bl = pts[np.argmax(diff)]
    return np.array([tl, tr, br, bl], dtype=np.float32)


def card_size_from_quad(card_pts: np.ndarray) -> Tuple[int, int]:
    tl, tr, br, bl = order_quad(card_pts)
    width_top = np.linalg.norm(tr - tl)
    width_bottom = np.linalg.norm(br - bl)
    height_right = np.linalg.norm(br - tr)
    height_left = np.linalg.norm(bl - tl)
    w = int(round(max(width_top, width_bottom)))
    h = int(round(max(height_right, height_left)))
    if w > h:
        w, h = h, w
    return max(w, 200), max(h, 300)


def transform_points(points: np.ndarray, M: np.ndarray) -> np.ndarray:
    return cv2.perspectiveTransform(points.reshape(-1, 1, 2).astype(np.float32), M).reshape(-1, 2)


def template_normalized_regions(template: dict) -> Dict[str, np.ndarray]:
    card_pts = pts_array(template['regions']['card'])
    w, h = card_size_from_quad(card_pts)
    src = order_quad(card_pts)
    dst = np.array([[0,0], [w-1,0], [w-1,h-1], [0,h-1]], dtype=np.float32)
    M = cv2.getPerspectiveTransform(src, dst)
    norm: Dict[str, np.ndarray] = {}
    for key in REGIONS:
        card_space = transform_points(pts_array(template['regions'][key]), M)
        n = card_space.copy()
        n[:, 0] /= float(w)
        n[:, 1] /= float(h)
        norm[key] = n
    return norm


def warp_card(img: np.ndarray, card_pts: np.ndarray, out_w: int, out_h: int) -> np.ndarray:
    src = order_quad(card_pts)
    dst = np.array([[0,0], [out_w-1,0], [out_w-1,out_h-1], [0,out_h-1]], dtype=np.float32)
    M = cv2.getPerspectiveTransform(src, dst)
    return cv2.warpPerspective(img, M, (out_w, out_h))


def denormalize_region(norm_pts: np.ndarray, w: int, h: int) -> np.ndarray:
    pts = norm_pts.copy().astype(np.float32)
    pts[:, 0] *= float(w)
    pts[:, 1] *= float(h)
    return pts


def crop_region(warped: np.ndarray, poly: np.ndarray, pad: int = 8) -> np.ndarray:
    h, w = warped.shape[:2]
    left = max(0, int(np.floor(poly[:,0].min())) - pad)
    right = min(w, int(np.ceil(poly[:,0].max())) + pad)
    top = max(0, int(np.floor(poly[:,1].min())) - pad)
    bottom = min(h, int(np.ceil(poly[:,1].max())) + pad)
    if right <= left or bottom <= top:
        raise ValueError(f'bad crop bounds left={left} top={top} right={right} bottom={bottom}')
    return warped[top:bottom, left:right].copy()


def find_image(images_dir: Path, filename: str) -> Optional[Path]:
    p = images_dir / filename
    if p.exists():
        return p
    stem = Path(filename).stem.lower()
    for q in images_dir.iterdir():
        if q.is_file() and q.suffix.lower() in IMAGE_EXTS and q.stem.lower() == stem:
            return q
    return None


def preprocess_for_ocr(crop: np.ndarray, scale: int = 3, threshold: bool = False) -> np.ndarray:
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if crop.ndim == 3 else crop.copy()
    gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    gray = cv2.GaussianBlur(gray, (3,3), 0)
    if threshold:
        return cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 9)
    return gray


def ocr_crop(crop: np.ndarray, kind: str, debug_dir: Optional[Path] = None, stem: str = '') -> str:
    if pytesseract is None:
        return ''
    variants = [crop, preprocess_for_ocr(crop, 3, False), preprocess_for_ocr(crop, 3, True)]
    if kind == 'name':
        configs = ['--psm 7', '--psm 8', '--psm 6']
    elif kind == 'number':
        configs = ['--psm 7 -c tessedit_char_whitelist=0123456789/ABCDEFGHIJKLMNOPQRSTUVWXYZ', '--psm 8 -c tessedit_char_whitelist=0123456789/ABCDEFGHIJKLMNOPQRSTUVWXYZ']
    else:
        configs = ['--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ', '--psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ']
    best = ''
    best_score = -1
    all_text = []
    for vi, img in enumerate(variants):
        for cfg in configs:
            try:
                text = pytesseract.image_to_string(img, config=cfg).strip()
            except Exception:
                text = ''
            all_text.append(f'[{kind} variant={vi} cfg={cfg}]\n{text}')
            score = score_ocr_text(text, kind)
            if score > best_score:
                best_score = score
                best = text
    if debug_dir:
        debug_dir.mkdir(parents=True, exist_ok=True)
        (debug_dir / f'{stem}_{kind}_ocr.txt').write_text('\n\n'.join(all_text), encoding='utf-8')
    return best


def score_ocr_text(text: str, kind: str) -> int:
    t = str(text or '').strip()
    if not t:
        return -100
    if kind == 'number':
        score = 0
        if re.search(r'\d{1,3}\s*/\s*\d{1,3}', t): score += 100
        score += sum(ch.isdigit() for ch in t)
        score -= len(re.sub(r'[0-9/A-Z\s]', '', t)) * 3
        return score
    if kind == 'setcode':
        letters = re.sub(r'[^A-Z]', '', t.upper())
        score = len(letters)
        if any(code in letters for code in SET_CODE_HINTS): score += 100
        if letters.endswith('EN'): score += 10
        return score
    # name
    norm = normalize_text(t)
    score = len(norm)
    if 2 <= len(norm.split()) <= 4: score += 10
    if re.search(r'\d{1,3}\s*/\s*\d{1,3}', t): score -= 50
    return score


def clean_name(text: str) -> str:
    lines = [l.strip() for l in str(text or '').splitlines() if l.strip()]
    if not lines:
        return ''
    # pick the line with the most letters, usually the card name line
    line = max(lines, key=lambda s: sum(ch.isalpha() for ch in s))
    line = re.sub(r'[^A-Za-z0-9 éÉ\-\'\. ]+', ' ', line)
    line = re.sub(r'\s+', ' ', line).strip(' .')
    # remove tiny OCR tail like "Yamask. 2" -> "Yamask"
    line = re.sub(r'\s*[\. ]+\d+$', '', line).strip()
    return line


def extract_number(text: str) -> str:
    t = str(text or '').upper().replace('O', '0').replace('I', '1').replace('L', '1')
    m = re.search(r'(\d{1,3})\s*/\s*(\d{1,3})', t)
    if m:
        return canonical_card_number(f'{m.group(1)}/{m.group(2)}')
    m = re.search(r'\d{1,3}', t)
    return canonical_card_number(m.group(0)) if m else ''


def extract_set_code(text: str) -> str:
    letters = re.sub(r'[^A-Z]', '', str(text or '').upper())
    # common OCR output: WHTE, WHTEN, BLKEN, CRIEN
    for code in SET_CODE_HINTS:
        if letters.startswith(code) or code in letters:
            return code
    # Fix WHTE -> WHT, BLKEN -> BLK by trying first 3 letters
    if len(letters) >= 3 and letters[:3] in SET_CODE_HINTS:
        return letters[:3]
    return ''


def row_to_result(row: pd.Series, confidence: float, reason: str, status: str, count: int) -> MatchResult:
    return MatchResult(status=status, card_name=str(row['Card Name']), set_name=str(row['Set Name']), card_number=str(row['Card Number']), rarity=str(row['Rarity']), confidence=confidence, reason=reason, candidate_count=count)


def match_region_ocr(ocr: RegionOCR, lookup: pd.DataFrame) -> MatchResult:
    candidates = lookup
    reasons = []
    set_name = SET_CODE_HINTS.get(ocr.set_code, '')
    if set_name:
        set_key = normalize_text(set_name)
        candidates = candidates[candidates['Set Name Key'] == set_key]
        reasons.append(f'set code {ocr.set_code}->{set_name}')
    number_left = card_number_left(ocr.number_clean)
    if number_left:
        candidates = candidates[candidates['Card Number Left Key'] == number_left]
        reasons.append(f'card number left {number_left}')
    name_key = normalize_text(ocr.name_clean)

    if candidates.empty:
        # fallback: try number globally, then score by name/set
        candidates = lookup
        if number_left:
            candidates = candidates[candidates['Card Number Left Key'] == number_left]
        if candidates.empty:
            return MatchResult(status='review', confidence=0.0, reason='no candidates after set/number filters; OCR=' + repr(ocr))

    # Score candidate names with the OCR name; set+number already narrowed candidates.
    best_row = None
    best_score = -1.0
    for _, row in candidates.iterrows():
        db_name = row['Card Name Key']
        if name_key and db_name:
            sim = SequenceMatcher(None, name_key, db_name).ratio()
            token_hits = sum(1 for t in db_name.split() if len(t) >= 3 and t in name_key)
            score = sim + 0.2 * token_hits
        else:
            score = 0.0
        if score > best_score:
            best_score = score
            best_row = row

    if best_row is None:
        return MatchResult(status='review', confidence=0.0, reason='no scorable candidates')

    count = int(len(candidates))
    has_set = bool(set_name)
    has_number = bool(number_left)
    has_name = bool(name_key)
    name_ok = best_score >= 0.72 or (name_key and normalize_text(str(best_row['Card Name'])) in name_key)

    if has_set and has_number and has_name and name_ok:
        return row_to_result(best_row, 0.99, ', '.join(reasons + [f'name match score {best_score:.2f}']), 'auto_match', count)
    if has_set and has_number and count == 1:
        return row_to_result(best_row, 0.82, ', '.join(reasons + ['unique set+number candidate; name weak/missing']), 'candidate_review', count)
    if has_number and has_name and name_ok and count <= 3:
        return row_to_result(best_row, 0.86, ', '.join(reasons + [f'name+number score {best_score:.2f}']), 'likely_match', count)
    if has_name and name_ok:
        return row_to_result(best_row, 0.60, f'name-only match score {best_score:.2f}', 'review', count)
    return row_to_result(best_row, 0.35, ', '.join(reasons + [f'weak name score {best_score:.2f}', f'candidate count {count}']), 'review', count)


def draw_poly(img: np.ndarray, pts: np.ndarray, color: Tuple[int,int,int], thickness: int = 2) -> None:
    p = np.round(pts).astype(np.int32).reshape(-1,1,2)
    cv2.polylines(img, [p], True, color, thickness, lineType=cv2.LINE_AA)


def process_one(label_path: Path, template_regions: Dict[str, np.ndarray], images_dir: Path, lookup: pd.DataFrame, out_dir: Path, card_w: int, card_h: int, save_crops: bool, save_debug: bool) -> Dict[str, str]:
    label = load_json(label_path)
    filename = label.get('filename') or (label_path.stem + '.jpg')
    img_path = find_image(images_dir, filename)
    if not img_path:
        raise FileNotFoundError(f'image not found for {filename}')
    img = cv2.imread(str(img_path))
    if img is None:
        raise ValueError(f'could not read image {img_path}')
    stem = Path(filename).stem
    warped = warp_card(img, pts_array(label['regions']['card']), card_w, card_h)

    crops_dir = out_dir / 'region_crops'
    warped_dir = out_dir / 'warped_cards'
    overlay_dir = out_dir / 'overlays'
    debug_dir = out_dir / 'ocr_debug' if save_debug else None
    if save_crops:
        crops_dir.mkdir(parents=True, exist_ok=True)
        warped_dir.mkdir(parents=True, exist_ok=True)
        overlay_dir.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(warped_dir / f'{stem}_warped_card.jpg'), warped)

    overlay = warped.copy()
    colors = {'name': (255,0,0), 'number': (0,255,255), 'setcode': (255,0,255)}
    raw_texts = {}
    clean = {}
    for key in REGIONS:
        poly = denormalize_region(template_regions[key], card_w, card_h)
        crop = crop_region(warped, poly, pad=8)
        if save_crops:
            cv2.imwrite(str(crops_dir / f'{stem}_{key}_crop.jpg'), crop)
            draw_poly(overlay, poly, colors[key], 2)
        raw = ocr_crop(crop, key, debug_dir, stem)
        raw_texts[key] = raw
    if save_crops:
        cv2.imwrite(str(overlay_dir / f'{stem}_region_overlay.jpg'), overlay)

    region_ocr = RegionOCR(
        name_text=raw_texts['name'],
        number_text=raw_texts['number'],
        setcode_text=raw_texts['setcode'],
        name_clean=clean_name(raw_texts['name']),
        number_clean=extract_number(raw_texts['number']),
        set_code=extract_set_code(raw_texts['setcode']),
    )
    match = match_region_ocr(region_ocr, lookup)
    print(f"{stem}: name='{region_ocr.name_clean}' number='{region_ocr.number_clean}' setcode='{region_ocr.set_code}' -> {match.status}: {match.card_name} | {match.set_name} | {match.card_number} | {match.confidence:.2f}")
    return {
        'file': filename,
        'status': match.status,
        'matched_card_name': match.card_name,
        'matched_set_name': match.set_name,
        'matched_card_number': match.card_number,
        'matched_rarity': match.rarity,
        'confidence': f'{match.confidence:.2f}',
        'reason': match.reason,
        'candidate_count': str(match.candidate_count),
        'ocr_name_clean': region_ocr.name_clean,
        'ocr_number_clean': region_ocr.number_clean,
        'ocr_set_code': region_ocr.set_code,
        'ocr_name_raw': region_ocr.name_text.replace('\n',' | '),
        'ocr_number_raw': region_ocr.number_text.replace('\n',' | '),
        'ocr_setcode_raw': region_ocr.setcode_text.replace('\n',' | '),
        'error': '',
    }


def main() -> None:
    ap = argparse.ArgumentParser(description='Putnam Scanner V2.2.0 Region OCR: border warp + template regions + DB match.')
    ap.add_argument('--template-label', required=True, help='One good template JSON, e.g. border_training_labels\\IMG_7505.json')
    ap.add_argument('--target-labels', required=True, help='Folder containing border trainer JSON labels for target images')
    ap.add_argument('--images', default='input_photos', help='Folder containing original photos')
    ap.add_argument('--sqlite', required=True, help='SQLite database path, e.g. database\\putnam_pokemon_cloud_ready.sqlite')
    ap.add_argument('--sqlite-table', default=None)
    ap.add_argument('--output', default='region_ocr_v2_2_0_results')
    ap.add_argument('--skip-template-source', action='store_true')
    ap.add_argument('--card-width', type=int, default=734)
    ap.add_argument('--card-height', type=int, default=1024)
    ap.add_argument('--no-save-crops', action='store_true')
    ap.add_argument('--save-ocr-text', action='store_true')
    args = ap.parse_args()

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    lookup = load_lookup(Path(args.sqlite), args.sqlite_table)
    print(f'Database rows: {len(lookup):,}')
    template_path = Path(args.template_label)
    template = load_json(template_path)
    template_regions = template_normalized_regions(template)

    rows = []
    for label_path in sorted(Path(args.target_labels).glob('*.json')):
        if args.skip_template_source and label_path.resolve() == template_path.resolve():
            continue
        try:
            row = process_one(label_path, template_regions, Path(args.images), lookup, out_dir, args.card_width, args.card_height, not args.no_save_crops, args.save_ocr_text)
        except Exception as e:
            print(f'{label_path.name}: ERROR {e}')
            row = {'file': label_path.name, 'status': 'error', 'matched_card_name': '', 'matched_set_name': '', 'matched_card_number': '', 'matched_rarity': '', 'confidence': '0.00', 'reason': '', 'candidate_count': '0', 'ocr_name_clean': '', 'ocr_number_clean': '', 'ocr_set_code': '', 'ocr_name_raw': '', 'ocr_number_raw': '', 'ocr_setcode_raw': '', 'error': str(e)}
        rows.append(row)

    csv_path = out_dir / 'putnam_region_ocr_results.csv'
    fieldnames = ['file','status','matched_card_name','matched_set_name','matched_card_number','matched_rarity','confidence','reason','candidate_count','ocr_name_clean','ocr_number_clean','ocr_set_code','ocr_name_raw','ocr_number_raw','ocr_setcode_raw','error']
    with csv_path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f'Done. Results: {csv_path}')

if __name__ == '__main__':
    main()
