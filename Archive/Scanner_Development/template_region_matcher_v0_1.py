from __future__ import annotations

import argparse, json, csv, re, sqlite3, subprocess, shutil
from pathlib import Path
from typing import Dict, List, Tuple, Optional

try:
    import cv2
    import numpy as np
except Exception as e:
    raise SystemExit('Missing opencv/numpy. Run: python -m pip install opencv-python numpy') from e

try:
    import pytesseract
    from PIL import Image
    import os
    default_tess = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    if os.path.exists(default_tess):
        pytesseract.pytesseract.tesseract_cmd = default_tess
except Exception:
    pytesseract = None
    Image = None

OUT_W, OUT_H = 734, 1024  # standard normalized card canvas
IMG_EXTS = {'.jpg','.jpeg','.png','.webp','.bmp','.tif','.tiff'}

def order_points(pts):
    pts = np.array([[p['x'], p['y']] if isinstance(p, dict) else p for p in pts], dtype='float32')
    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1).reshape(-1)
    rect = np.zeros((4,2), dtype='float32')
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect

def warp_poly(img, poly, w, h):
    src = order_points(poly)
    dst = np.array([[0,0],[w-1,0],[w-1,h-1],[0,h-1]], dtype='float32')
    M = cv2.getPerspectiveTransform(src, dst)
    return cv2.warpPerspective(img, M, (w,h))

def load_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))

def norm_regions_from_template(label):
    card = order_points(label['regions']['card'])
    # Map original image -> normalized card canvas, then transform each OCR region into normalized coords.
    dst = np.array([[0,0],[OUT_W-1,0],[OUT_W-1,OUT_H-1],[0,OUT_H-1]], dtype='float32')
    M = cv2.getPerspectiveTransform(card, dst)
    out = {}
    for key in ['name','number','setcode']:
        pts = np.array([[p['x'], p['y']] for p in label['regions'][key]], dtype='float32').reshape(-1,1,2)
        trans = cv2.perspectiveTransform(pts, M).reshape(-1,2)
        out[key] = [{'x': float(x)/(OUT_W-1), 'y': float(y)/(OUT_H-1)} for x,y in trans]
    return out

def poly_from_norm(norm_poly):
    return [{'x': p['x']*(OUT_W-1), 'y': p['y']*(OUT_H-1)} for p in norm_poly]

def crop_region(card_img, norm_poly, pad=0):
    poly = poly_from_norm(norm_poly)
    pts = order_points(poly)
    width = int(max(np.linalg.norm(pts[1]-pts[0]), np.linalg.norm(pts[2]-pts[3])))
    height = int(max(np.linalg.norm(pts[3]-pts[0]), np.linalg.norm(pts[2]-pts[1])))
    width = max(width + pad*2, 10)
    height = max(height + pad*2, 10)
    return warp_poly(card_img, poly, width, height)

def preprocess_for_ocr(img, mode):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape)==3 else img
    # upscale small text
    scale = 3 if mode in ('number','setcode') else 2
    gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    gray = cv2.GaussianBlur(gray, (3,3), 0)
    if mode == 'setcode':
        # set code often white letters on dark box: invert after threshold sometimes helps
        _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
        inv = 255 - th
        return [gray, th, inv]
    if mode == 'number':
        _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
        return [gray, th]
    # name region: mostly dark letters on lighter background
    _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    return [gray, th]

def ocr_img(img, mode):
    if pytesseract is None or Image is None:
        return ''
    configs = {
        'name': ['--psm 7', '--psm 8', '--psm 6'],
        'number': ['--psm 7 -c tessedit_char_whitelist=0123456789/', '--psm 8 -c tessedit_char_whitelist=0123456789/'],
        'setcode': ['--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 ', '--psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789']
    }[mode]
    texts=[]
    for var in preprocess_for_ocr(img, mode):
        pil = Image.fromarray(var)
        for cfg in configs:
            try:
                t = pytesseract.image_to_string(pil, config=cfg).strip()
                if t:
                    texts.append(t)
            except Exception:
                pass
    # choose best heuristic
    if not texts: return ''
    if mode == 'number':
        for t in texts:
            m = re.search(r'\d{1,3}\s*/\s*\d{1,3}', t)
            if m: return re.sub(r'\s+','',m.group(0))
    if mode == 'setcode':
        cleaned = [re.sub(r'[^A-Za-z0-9 ]+', '', t).strip().upper() for t in texts]
        cleaned = [c for c in cleaned if c]
        return max(cleaned, key=len) if cleaned else texts[0]
    # name
    cleaned = [re.sub(r'[^A-Za-z0-9 éÉ\.\'\-]+',' ',t).strip() for t in texts]
    cleaned = [c for c in cleaned if len(c)>=2]
    return max(cleaned, key=len) if cleaned else texts[0]

def find_image(images_dir: Path, filename: str):
    p = images_dir / filename
    if p.exists(): return p
    stem = Path(filename).stem.lower()
    for q in images_dir.rglob('*'):
        if q.suffix.lower() in IMG_EXTS and q.stem.lower()==stem:
            return q
    return None

def normalize_num(s):
    m = re.search(r'(\d{1,3})\s*/\s*(\d{1,3})', s or '')
    if not m: return ''
    return str(int(m.group(1))) + '/' + str(int(m.group(2)))

def set_hint(s):
    s = (s or '').upper()
    # Common codes from current tests; raw code is still used in matching output.
    hints = {'BLK':'Black Bolt','WHT':'White Flare','CRI':'Chaos Rising','PRE':'Prismatic Evolutions','PAL':'Paldea Evolved','SVI':'Scarlet & Violet'}
    for k,v in hints.items():
        if k in s: return k, v
    return '', ''

def load_db(sqlite_path: Path):
    if not sqlite_path or not sqlite_path.exists(): return []
    con = sqlite3.connect(str(sqlite_path)); con.row_factory=sqlite3.Row
    cur = con.cursor()
    tables = [r[0] for r in cur.execute("select name from sqlite_master where type='table'").fetchall()]
    table = 'pokemon_cards' if 'pokemon_cards' in tables else tables[0]
    cols = [r[1] for r in cur.execute(f'pragma table_info({table})').fetchall()]
    def col(*names):
        lower={c.lower():c for c in cols}
        for n in names:
            if n.lower() in lower: return lower[n.lower()]
        return None
    c_name=col('card_name','name'); c_set=col('set_name','set'); c_num=col('card_number','number'); c_rarity=col('rarity')
    rows=[]
    for r in cur.execute(f'select * from {table}').fetchall():
        rows.append({
            'Card Name': str(r[c_name] if c_name else ''),
            'Set Name': str(r[c_set] if c_set else ''),
            'Card Number': str(r[c_num] if c_num else ''),
            'Rarity': str(r[c_rarity] if c_rarity else '')
        })
    con.close(); return rows

def match_db(rows, name, number, setcode):
    nnum = normalize_num(number)
    left = nnum.split('/')[0] if '/' in nnum else ''
    code, setname = set_hint(setcode)
    name_norm = re.sub(r'[^a-z0-9]+',' ', name.lower()).strip()
    cands = rows
    if setname:
        cands = [r for r in cands if setname.lower() in r['Set Name'].lower()]
    if left:
        cands2 = [r for r in cands if re.sub(r'^0+','', re.split(r'/', r['Card Number'])[0] if r['Card Number'] else '') == left]
        if cands2: cands = cands2
    # exact/contains name tie-break
    if name_norm:
        named = [r for r in cands if name_norm == re.sub(r'[^a-z0-9]+',' ', r['Card Name'].lower()).strip() or name_norm in re.sub(r'[^a-z0-9]+',' ', r['Card Name'].lower()).strip()]
        if named: cands = named
    if len(cands)==1:
        r=cands[0]; return r, 0.99, 'unique match from template OCR regions'
    if cands:
        r=cands[0]; return r, 0.65, f'{len(cands)} candidates; first shown'
    return None, 0.0, 'no match'

def main():
    ap=argparse.ArgumentParser(description='Putnam Template Region OCR Matcher v0.1')
    ap.add_argument('--template-label', required=True, help='JSON label to use as normalized OCR region template')
    ap.add_argument('--target-label', help='Optional card-border-only target JSON. If omitted, uses all JSON labels except template.')
    ap.add_argument('--labels', default='border_training_labels')
    ap.add_argument('--images', default='input_photos')
    ap.add_argument('--sqlite', default='database/putnam_pokemon_cloud_ready.sqlite')
    ap.add_argument('--output', default='template_region_results_v0_1')
    args=ap.parse_args()
    out=Path(args.output); crops=out/'region_crops'; out.mkdir(exist_ok=True); crops.mkdir(exist_ok=True)
    template=load_json(Path(args.template_label))
    norm=norm_regions_from_template(template)
    dbrows=load_db(Path(args.sqlite))
    print(f'Database rows: {len(dbrows)}')
    targets=[]
    if args.target_label:
        targets=[Path(args.target_label)]
    else:
        labels_dir=Path(args.labels)
        template_name=Path(args.template_label).resolve()
        targets=[p for p in sorted(labels_dir.glob('*.json')) if p.resolve()!=template_name]
    results=[]
    for labpath in targets:
        lab=load_json(labpath)
        imgpath=find_image(Path(args.images), lab.get('filename',''))
        if not imgpath:
            print(f'{labpath.name}: image not found')
            continue
        img=cv2.imread(str(imgpath))
        card=warp_poly(img, lab['regions']['card'], OUT_W, OUT_H)
        stem=Path(lab.get('filename', labpath.stem)).stem
        cv2.imwrite(str(crops/f'{stem}_card_from_target_border.jpg'), card)
        ocrs={}
        for key in ['name','number','setcode']:
            crop=crop_region(card, norm[key])
            cv2.imwrite(str(crops/f'{stem}_{key}_from_template.jpg'), crop)
            ocrs[key]=ocr_img(crop, key)
        match, conf, reason = match_db(dbrows, ocrs['name'], ocrs['number'], ocrs['setcode'])
        print(f"{stem}: name='{ocrs['name']}' number='{ocrs['number']}' setcode='{ocrs['setcode']}'")
        if match:
            print(f"  Match: {match['Card Name']} | {match['Set Name']} | {match['Card Number']} | {conf:.2f}")
        else:
            print('  Match: needs review')
        results.append({
            'file': lab.get('filename', labpath.name), 'ocr_name':ocrs['name'], 'ocr_number':ocrs['number'], 'ocr_setcode':ocrs['setcode'],
            'match_name': match['Card Name'] if match else '', 'match_set': match['Set Name'] if match else '', 'match_number': match['Card Number'] if match else '', 'confidence': conf, 'reason': reason
        })
    with open(out/'template_region_results.csv','w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f, fieldnames=list(results[0].keys()) if results else ['file'])
        w.writeheader(); w.writerows(results)
    print(f'Done. Output: {out}')

if __name__=='__main__': main()
