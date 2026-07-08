"""
Putnam Template Region Matcher Bulk v0.3

Applies one manually labeled modern Pokemon template to many target card labels/images.
Expected workflow:
  - You have border_training_labels/*.json from Border Trainer v0.6
  - You have original photos in input_photos
  - Pick one good template label, e.g. border_training_labels/IMG_7505.json

Example:
  python template_region_matcher_bulk_v0_3.py --template-label border_training_labels\IMG_7505.json --target-labels border_training_labels --images input_photos --sqlite database\putnam_pokemon_cloud_ready.sqlite --output template_bulk_test_v0_3
"""
from __future__ import annotations

import argparse, csv, json, os, re, sqlite3, shutil
from pathlib import Path
from difflib import SequenceMatcher
from typing import Dict, List, Tuple, Optional

try:
    from PIL import Image, ImageOps, ImageFilter, ImageEnhance
except Exception:
    Image = None
try:
    import pytesseract
    default_tesseract = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.path.exists(default_tesseract):
        pytesseract.pytesseract.tesseract_cmd = default_tesseract
except Exception:
    pytesseract = None

IMAGE_EXTS = {'.jpg','.jpeg','.png','.webp','.bmp','.tif','.tiff'}
SET_HINTS = {
    'BLK': 'Black Bolt', 'WHT': 'White Flare', 'CRI': 'Chaos Rising', 'PRE': 'Prismatic Evolutions',
    'PAL': 'Paldea Evolved', 'SVI': 'Scarlet & Violet', 'OBF': 'Obsidian Flames', 'PAR': 'Paradox Rift',
    'TEF': 'Temporal Forces', 'TWM': 'Twilight Masquerade', 'SCR': 'Stellar Crown', 'SSP': 'Surging Sparks',
    'PAF': 'Paldean Fates', 'MEW': 'Pokemon 151', 'SFA': 'Shrouded Fable',
}

def norm(s: str) -> str:
    s = str(s or '').lower().replace('é','e')
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))

def order_quad(points):
    # trainer order is already tl,tr,br,bl; preserve it
    return [(float(p['x']), float(p['y'])) for p in points]

def bilinear(card_quad, u, v):
    tl,tr,br,bl = card_quad
    x = (1-u)*(1-v)*tl[0] + u*(1-v)*tr[0] + u*v*br[0] + (1-u)*v*bl[0]
    y = (1-u)*(1-v)*tl[1] + u*(1-v)*tr[1] + u*v*br[1] + (1-u)*v*bl[1]
    return (x,y)

def invert_bilinear(card_quad, pt):
    # Newton solve for u,v in quadrilateral coordinate system
    x,y = float(pt[0]), float(pt[1])
    u,v = 0.5,0.5
    tl,tr,br,bl = card_quad
    for _ in range(20):
        bx,by = bilinear(card_quad,u,v)
        # derivatives
        dxdu = -(1-v)*tl[0] + (1-v)*tr[0] + v*br[0] - v*bl[0]
        dydu = -(1-v)*tl[1] + (1-v)*tr[1] + v*br[1] - v*bl[1]
        dxdv = -(1-u)*tl[0] - u*tr[0] + u*br[0] + (1-u)*bl[0]
        dydv = -(1-u)*tl[1] - u*tr[1] + u*br[1] + (1-u)*bl[1]
        ex,ey = bx-x, by-y
        det = dxdu*dydv - dxdv*dydu
        if abs(det) < 1e-9: break
        du = ( ex*dydv - dxdv*ey)/det
        dv = ( dxdu*ey - ex*dydu)/det
        u -= du; v -= dv
        if abs(du)+abs(dv) < 1e-7: break
    return (u,v)

def template_regions_uv(template_label):
    card = order_quad(template_label['regions']['card'])
    out = {}
    for key in ['name','number','setcode']:
        pts = order_quad(template_label['regions'][key])
        out[key] = [invert_bilinear(card, p) for p in pts]
    return out

def apply_template_uv(target_label, regions_uv):
    card = order_quad(target_label['regions']['card'])
    out = {}
    for key, uvs in regions_uv.items():
        out[key] = [bilinear(card,u,v) for u,v in uvs]
    return out

def crop_quad(img: Image.Image, quad, pad=4) -> Image.Image:
    # Robust bounding-box crop for a 4-point polygon.
    # v0.2 could crash if a projected template region landed outside the image
    # and clamping made lower < upper. v0.3 sorts/clamps safely and raises a
    # readable error for truly invalid regions instead of killing the whole run.
    xs = [float(p[0]) for p in quad]
    ys = [float(p[1]) for p in quad]
    raw_left = min(xs) - pad
    raw_right = max(xs) + pad
    raw_top = min(ys) - pad
    raw_bottom = max(ys) + pad

    left = max(0, min(img.width - 1, int(raw_left)))
    right = max(0, min(img.width, int(raw_right)))
    top = max(0, min(img.height - 1, int(raw_top)))
    bottom = max(0, min(img.height, int(raw_bottom)))

    # If a region was projected completely outside the image, make it invalid
    # instead of passing reversed coordinates into PIL.
    if right <= left or bottom <= top:
        raise ValueError(
            f"invalid projected crop: left={left}, top={top}, right={right}, bottom={bottom}, "
            f"image={img.width}x{img.height}, quad={quad}"
        )

    return img.crop((left, top, right, bottom))

def ocr_region(img: Image.Image, kind: str) -> str:
    if pytesseract is None or Image is None:
        return ''
    variants=[]
    variants.append(img.convert('RGB'))
    g=ImageOps.grayscale(img)
    variants.append(g)
    enh=ImageEnhance.Contrast(g).enhance(2.5).filter(ImageFilter.SHARPEN)
    scale=3 if kind in ('number','setcode') else 2
    variants.append(enh.resize((enh.width*scale, enh.height*scale)))
    if kind == 'name':
        configs=['--psm 7','--psm 6']
        whitelist=''
    elif kind == 'number':
        configs=['--psm 7 -c tessedit_char_whitelist=0123456789/','--psm 8 -c tessedit_char_whitelist=0123456789/']
        whitelist=''
    else:
        configs=['--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ','--psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ']
        whitelist=''
    best=''
    for v in variants:
        for cfg in configs:
            try:
                t=pytesseract.image_to_string(v, config=cfg).strip()
            except Exception:
                continue
            t=re.sub(r'\s+',' ',t).strip()
            if len(t)>len(best): best=t
    return best

def clean_number(t):
    m=re.search(r'(\d{1,3})\s*/\s*(\d{1,3})', t or '')
    if not m: return ''
    return f"{int(m.group(1))}/{int(m.group(2))}"

def clean_setcode(t):
    t=re.sub(r'[^A-Za-z]','', t or '').upper()
    for code in sorted(SET_HINTS, key=len, reverse=True):
        if t.startswith(code) or code in t:
            return code
    if len(t)>=3: return t[:3]
    return t

def load_db(sqlite_path: Path):
    con=sqlite3.connect(sqlite_path)
    con.row_factory=sqlite3.Row
    cur=con.cursor()
    cols=[r[1] for r in cur.execute('PRAGMA table_info(pokemon_cards)').fetchall()]
    def pick(options):
        for o in options:
            if o in cols: return o
        return None
    c_name=pick(['card_name','name','Card Name'])
    c_set=pick(['set_name','set','Set Name'])
    c_num=pick(['card_number','number','Card Number'])
    c_rarity=pick(['rarity','Rarity'])
    rows=[]
    for r in cur.execute('SELECT * FROM pokemon_cards').fetchall():
        rows.append({
            'card_name': str(r[c_name] or '') if c_name else '',
            'set_name': str(r[c_set] or '') if c_set else '',
            'card_number': str(r[c_num] or '') if c_num else '',
            'rarity': str(r[c_rarity] or '') if c_rarity else '',
        })
    con.close()
    return rows

def number_left(n):
    m=re.search(r'(\d{1,3})', str(n or ''))
    return str(int(m.group(1))) if m else ''

def match_card(rows, name_text, number_text, setcode_text):
    cn=clean_number(number_text); left=number_left(cn)
    sc=clean_setcode(setcode_text); set_hint=SET_HINTS.get(sc,'')
    name_n=norm(re.sub(r'[^A-Za-z0-9 éÉ\'\- ]',' ', name_text or ''))
    candidates=rows
    reasons=[]
    if set_hint:
        filtered=[r for r in candidates if norm(set_hint) in norm(r['set_name'])]
        if filtered:
            candidates=filtered; reasons.append(f'setcode {sc}->{set_hint}')
    if left:
        filtered=[r for r in candidates if number_left(r['card_number']) == left]
        if filtered:
            candidates=filtered; reasons.append(f'number {left}')
    best=None; best_score=-1
    for r in candidates:
        rn=norm(r['card_name'])
        sim=SequenceMatcher(None, name_n, rn).ratio() if name_n and rn else 0
        token_hits=0
        toks=[x for x in rn.split() if len(x)>=3]
        if toks:
            token_hits=sum(1 for x in toks if x in name_n)/len(toks)
        score=0
        if left and number_left(r['card_number'])==left: score+=0.45
        if set_hint and norm(set_hint) in norm(r['set_name']): score+=0.35
        score+=0.20*max(sim, token_hits)
        if score>best_score:
            best_score=score; best=r
    if not best:
        return None,0,'no candidates',cn,sc
    return best, min(best_score,0.99), ', '.join(reasons), cn, sc

def find_image(images_dir, stem):
    for ext in IMAGE_EXTS:
        for p in [images_dir/(stem+ext), images_dir/(stem+ext.upper())]:
            if p.exists(): return p
    for p in images_dir.iterdir():
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS and p.stem.lower()==stem.lower():
            return p
    return None

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--template-label', required=True)
    ap.add_argument('--target-labels', required=True, help='Folder of target JSON labels, or one JSON file')
    ap.add_argument('--images', required=True)
    ap.add_argument('--sqlite', required=True)
    ap.add_argument('--output', default='template_bulk_results_v0_3')
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--skip-template-source', action='store_true', help='Skip the image whose label is the template label')
    args=ap.parse_args()
    out=Path(args.output); crops=out/'region_crops'; debug=out/'ocr_debug'
    crops.mkdir(parents=True, exist_ok=True); debug.mkdir(parents=True, exist_ok=True)
    template=load_json(Path(args.template_label))
    regions_uv=template_regions_uv(template)
    labels_path=Path(args.target_labels)
    label_files=[labels_path] if labels_path.is_file() else sorted(labels_path.glob('*.json'))
    if args.skip_template_source:
        tpl_name = Path(args.template_label).resolve().name.lower()
        label_files = [p for p in label_files if p.resolve().name.lower() != tpl_name]
    if args.limit: label_files=label_files[:args.limit]
    rows=load_db(Path(args.sqlite))
    print(f'Database rows: {len(rows)}')
    results=[]
    for lf in label_files:
        lab=load_json(lf); fname=lab.get('filename') or (lf.stem+'.JPG')
        stem=Path(fname).stem
        img_path=find_image(Path(args.images), stem)
        if not img_path:
            print(f'{stem}: image not found')
            continue
        img=Image.open(img_path).convert('RGB')
        try:
            reg=apply_template_uv(lab, regions_uv)
            ocrs={}
            for key in ['name','number','setcode']:
                crop=crop_quad(img, reg[key])
                crop_path=crops/f'{stem}_{key}_template_crop.jpg'
                crop.save(crop_path, quality=95)
                ocrs[key]=ocr_region(crop,key)
        except Exception as e:
            print(f'{stem}: crop/template error: {e}')
            (debug/f'{stem}.txt').write_text(json.dumps({'error': str(e), 'label_file': str(lf)}, indent=2), encoding='utf-8')
            results.append({
                'image': stem, 'ocr_name': '', 'ocr_number': '', 'ocr_setcode': '',
                'clean_number': '', 'clean_setcode': '',
                'match_name': '', 'match_set': '', 'match_number': '', 'confidence': '0.00',
                'reason': 'crop/template error: ' + str(e)
            })
            continue
        match,conf,reason,cn,sc=match_card(rows, ocrs['name'], ocrs['number'], ocrs['setcode'])
        if match:
            print(f"{stem}: name='{ocrs['name']}' number='{ocrs['number']}' setcode='{ocrs['setcode']}'")
            print(f"  Match: {match['card_name']} | {match['set_name']} | {match['card_number']} | {conf:.2f}")
        else:
            print(f"{stem}: no match")
        (debug/f'{stem}.txt').write_text(json.dumps({'ocr':ocrs,'clean_number':cn,'clean_setcode':sc,'match':match,'confidence':conf,'reason':reason}, indent=2), encoding='utf-8')
        results.append({
            'image': stem, 'ocr_name': ocrs['name'], 'ocr_number': ocrs['number'], 'ocr_setcode': ocrs['setcode'],
            'clean_number': cn, 'clean_setcode': sc,
            'match_name': match['card_name'] if match else '', 'match_set': match['set_name'] if match else '',
            'match_number': match['card_number'] if match else '', 'confidence': f'{conf:.2f}', 'reason': reason
        })
    with (out/'template_region_bulk_results.csv').open('w', newline='', encoding='utf-8') as f:
        fieldnames=['image','ocr_name','ocr_number','ocr_setcode','clean_number','clean_setcode','match_name','match_set','match_number','confidence','reason']
        w=csv.DictWriter(f, fieldnames=fieldnames); w.writeheader(); w.writerows(results)
    print(f'Done. Output: {out}')

if __name__=='__main__': main()
