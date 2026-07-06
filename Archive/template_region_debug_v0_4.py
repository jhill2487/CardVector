"""
Putnam Template Region Debugger v0.4

Purpose:
  Debug reusable OCR region templates visually before OCR/matching.

What it does:
  1. Reads one template JSON that contains card/name/number/setcode polygons.
  2. Converts template regions into normalized card coordinates.
  3. Reads target JSON labels containing target card border polygons.
  4. Projects template name/number/setcode regions onto each target card polygon.
  5. Saves visual overlay images and projected crop files.

No OCR. No matching. This version is only to confirm geometry.

Example:
  python template_region_debug_v0_4.py --template-label border_training_labels\IMG_7505.json --target-labels border_training_labels --images input_photos --output template_debug_v0_4 --skip-template-source
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, List, Tuple, Any

from PIL import Image, ImageDraw, ImageFont

Point = Tuple[float, float]
Poly = List[Point]

IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tif', '.tiff'}

COLORS = {
    'card': (0, 255, 0),
    'name': (0, 180, 255),
    'number': (255, 220, 0),
    'setcode': (255, 80, 255),
}


def read_label(path: Path) -> Dict[str, Any]:
    with path.open('r', encoding='utf-8') as f:
        return json.load(f)


def points_from_region(region: List[Dict[str, float]]) -> Poly:
    return [(float(p['x']), float(p['y'])) for p in region]


def lerp(a: Point, b: Point, t: float) -> Point:
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def bilinear(card: Poly, u: float, v: float) -> Point:
    """Map normalized card coordinate (u,v) onto quadrilateral card poly.
    card order expected: TL, TR, BR, BL.
    """
    tl, tr, br, bl = card
    top = lerp(tl, tr, u)
    bottom = lerp(bl, br, u)
    return lerp(top, bottom, v)


def invert_bilinear_approx(card: Poly, p: Point, steps: int = 80) -> Point:
    """Approx inverse for a mostly rectangular card quadrilateral.

    This is intentionally robust/simple: it finds the normalized (u,v) whose projected
    point is closest to p. Template labels are small, so this is accurate enough and
    avoids fragile homography math.
    """
    best_u = 0.0
    best_v = 0.0
    best_d = float('inf')

    # coarse grid
    for i in range(steps + 1):
        u = i / steps
        for j in range(steps + 1):
            v = j / steps
            q = bilinear(card, u, v)
            d = (q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2
            if d < best_d:
                best_d = d
                best_u = u
                best_v = v

    # local refine
    span = 1.0 / steps
    for refine in range(3):
        local_steps = 10
        start_u = max(0.0, best_u - span)
        end_u = min(1.0, best_u + span)
        start_v = max(0.0, best_v - span)
        end_v = min(1.0, best_v + span)
        for i in range(local_steps + 1):
            u = start_u + (end_u - start_u) * i / local_steps
            for j in range(local_steps + 1):
                v = start_v + (end_v - start_v) * j / local_steps
                q = bilinear(card, u, v)
                d = (q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2
                if d < best_d:
                    best_d = d
                    best_u = u
                    best_v = v
        span *= 0.35

    return (best_u, best_v)


def normalize_region(template_card: Poly, region_poly: Poly) -> Poly:
    return [invert_bilinear_approx(template_card, p) for p in region_poly]


def project_region(target_card: Poly, norm_poly: Poly) -> Poly:
    return [bilinear(target_card, u, v) for u, v in norm_poly]


def poly_bounds(poly: Poly, w: int, h: int) -> Tuple[int, int, int, int]:
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    left = int(max(0, min(xs)))
    right = int(min(w, max(xs)))
    top = int(max(0, min(ys)))
    bottom = int(min(h, max(ys)))
    if right <= left:
        right = min(w, left + 1)
    if bottom <= top:
        bottom = min(h, top + 1)
    return left, top, right, bottom


def find_image(images_dir: Path, filename: str) -> Path | None:
    direct = images_dir / filename
    if direct.exists():
        return direct
    stem = Path(filename).stem.lower()
    for p in images_dir.rglob('*'):
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS and p.stem.lower() == stem:
            return p
    return None


def draw_poly(draw: ImageDraw.ImageDraw, poly: Poly, color: Tuple[int, int, int], width: int = 8):
    pts = [(int(x), int(y)) for x, y in poly]
    draw.line(pts + [pts[0]], fill=color, width=width)
    r = max(6, width + 2)
    for x, y in pts:
        draw.ellipse((x-r, y-r, x+r, y+r), outline=color, width=max(2, width//2))


def save_overlay(img: Image.Image, out_path: Path, label_name: str, projected: Dict[str, Poly], target_card: Poly):
    overlay = img.convert('RGB').copy()
    draw = ImageDraw.Draw(overlay)

    draw_poly(draw, target_card, COLORS['card'], width=10)
    for key in ('name', 'number', 'setcode'):
        draw_poly(draw, projected[key], COLORS[key], width=8)

    # text legend
    legend = [
        f"{label_name}",
        "green = target card border",
        "blue = projected name",
        "yellow = projected number",
        "magenta = projected set code",
    ]
    x, y = 30, 30
    for line in legend:
        draw.rectangle((x-8, y-6, x + 680, y + 34), fill=(0, 0, 0))
        draw.text((x, y), line, fill=(255,255,255))
        y += 42

    overlay.save(out_path, quality=95)


def main() -> None:
    ap = argparse.ArgumentParser(description='Putnam Template Region Debugger v0.4')
    ap.add_argument('--template-label', required=True, help='Template JSON label, e.g. border_training_labels\\IMG_7505.json')
    ap.add_argument('--target-labels', required=True, help='Folder of target JSON labels')
    ap.add_argument('--images', required=True, help='Folder containing original input photos')
    ap.add_argument('--output', default='template_debug_v0_4', help='Output folder')
    ap.add_argument('--skip-template-source', action='store_true', help='Skip target with same filename as template')
    args = ap.parse_args()

    template_path = Path(args.template_label)
    target_labels_dir = Path(args.target_labels)
    images_dir = Path(args.images)
    out_dir = Path(args.output)
    overlay_dir = out_dir / 'overlays'
    crop_dir = out_dir / 'projected_crops'
    overlay_dir.mkdir(parents=True, exist_ok=True)
    crop_dir.mkdir(parents=True, exist_ok=True)

    template = read_label(template_path)
    t_regions = template['regions']
    template_card = points_from_region(t_regions['card'])

    normalized = {}
    for key in ('name', 'number', 'setcode'):
        normalized[key] = normalize_region(template_card, points_from_region(t_regions[key]))

    # Save the normalized template for inspection.
    norm_out = {
        'source_template': str(template_path),
        'source_filename': template.get('filename', ''),
        'normalized_regions': {
            k: [{'u': round(u, 6), 'v': round(v, 6)} for u, v in poly]
            for k, poly in normalized.items()
        }
    }
    (out_dir / 'normalized_template.json').write_text(json.dumps(norm_out, indent=2), encoding='utf-8')

    rows = []
    labels = sorted(target_labels_dir.glob('*.json'))
    if not labels:
        print(f'No JSON labels found in {target_labels_dir}')
        return

    template_filename = str(template.get('filename', '')).lower()

    for label_path in labels:
        try:
            target = read_label(label_path)
            filename = target.get('filename') or f'{label_path.stem}.JPG'
            if args.skip_template_source and filename.lower() == template_filename:
                continue

            img_path = find_image(images_dir, filename)
            if not img_path:
                rows.append({'label': label_path.name, 'filename': filename, 'status': 'missing_image'})
                print(f'{label_path.name}: missing image {filename}')
                continue

            img = Image.open(img_path).convert('RGB')
            w, h = img.size
            target_card = points_from_region(target['regions']['card'])
            projected = {k: project_region(target_card, normalized[k]) for k in ('name','number','setcode')}

            # Save overlay
            overlay_path = overlay_dir / f'{Path(filename).stem}_projected_overlay.jpg'
            save_overlay(img, overlay_path, label_path.stem, projected, target_card)

            # Save simple bounding crops for quick visual check.
            crop_paths = {}
            for key in ('name','number','setcode'):
                left, top, right, bottom = poly_bounds(projected[key], w, h)
                crop = img.crop((left, top, right, bottom))
                cp = crop_dir / f'{Path(filename).stem}_{key}_projected_crop.jpg'
                crop.save(cp, quality=95)
                crop_paths[key] = str(cp)

            row = {
                'label': label_path.name,
                'filename': filename,
                'status': 'ok',
                'overlay': str(overlay_path),
                'name_crop': crop_paths['name'],
                'number_crop': crop_paths['number'],
                'setcode_crop': crop_paths['setcode'],
            }
            # Include projected point coordinates for debugging.
            for key in ('name','number','setcode'):
                for i, (x,y) in enumerate(projected[key]):
                    row[f'{key}_{i}_x'] = round(x, 2)
                    row[f'{key}_{i}_y'] = round(y, 2)
            rows.append(row)
            print(f'{filename}: overlay saved -> {overlay_path}')
        except Exception as e:
            rows.append({'label': label_path.name, 'filename': '', 'status': f'error: {e}'})
            print(f'{label_path.name}: ERROR {e}')

    csv_path = out_dir / 'template_region_debug_results.csv'
    all_keys = []
    for r in rows:
        for k in r.keys():
            if k not in all_keys:
                all_keys.append(k)
    with csv_path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=all_keys)
        writer.writeheader()
        writer.writerows(rows)

    print(f'Done. Output: {out_dir}')
    print(f'Open overlays in: {overlay_dir}')


if __name__ == '__main__':
    main()
