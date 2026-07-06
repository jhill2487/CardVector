#!/usr/bin/env python3
"""
Putnam Template Region Warp Matcher v0.7

Fixes the previous raw-photo projection problem by:
1) reading the card polygon from each target label JSON
2) perspective-warping the card into an upright normalized card image
3) converting the template label regions into normalized card-space coordinates
4) applying those regions to each warped card crop
5) exporting projected region crops and overlays

No OCR/database required in this validator. Geometry first.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, List, Tuple

import cv2
import numpy as np

IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tif', '.tiff'}
REGIONS = ['name', 'number', 'setcode']


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def pts_array(points: List[dict]) -> np.ndarray:
    return np.array([[float(p['x']), float(p['y'])] for p in points], dtype=np.float32)


def order_quad(pts: np.ndarray) -> np.ndarray:
    """Return points ordered TL, TR, BR, BL."""
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
    # Pokemon card aspect is portrait. If user labeled corners in a rotated order,
    # force a portrait-ish output by swapping dimensions only when needed.
    # The homography still uses ordered corners; this keeps card-space consistent.
    if w > h:
        w, h = h, w
    return max(w, 200), max(h, 300)


def warp_card(img: np.ndarray, card_pts: np.ndarray, out_w: int | None = None, out_h: int | None = None) -> Tuple[np.ndarray, np.ndarray]:
    src = order_quad(card_pts)
    if out_w is None or out_h is None:
        out_w, out_h = card_size_from_quad(src)
    dst = np.array([[0, 0], [out_w - 1, 0], [out_w - 1, out_h - 1], [0, out_h - 1]], dtype=np.float32)
    M = cv2.getPerspectiveTransform(src, dst)
    warped = cv2.warpPerspective(img, M, (out_w, out_h))
    return warped, M


def transform_points(points: np.ndarray, M: np.ndarray) -> np.ndarray:
    pts = points.reshape(-1, 1, 2).astype(np.float32)
    out = cv2.perspectiveTransform(pts, M).reshape(-1, 2)
    return out


def template_normalized_regions(template: dict, template_img_path: Path | None = None) -> Tuple[Dict[str, np.ndarray], Tuple[int, int]]:
    """Warp template card, convert template regions to normalized card-space polygons."""
    card_pts = pts_array(template['regions']['card'])
    # Use template card polygon dimensions as canonical output size.
    w, h = card_size_from_quad(card_pts)
    # If a real template image is supplied, warp matrix from original card to card-space.
    # Otherwise create M by mapping from card pts to canonical dst without needing image.
    src = order_quad(card_pts)
    dst = np.array([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]], dtype=np.float32)
    M = cv2.getPerspectiveTransform(src, dst)

    norm: Dict[str, np.ndarray] = {}
    for key in REGIONS:
        rpts = pts_array(template['regions'][key])
        card_space = transform_points(rpts, M)
        n = card_space.copy()
        n[:, 0] /= float(w)
        n[:, 1] /= float(h)
        norm[key] = n
    return norm, (w, h)


def denormalize_region(norm_pts: np.ndarray, w: int, h: int) -> np.ndarray:
    pts = norm_pts.copy().astype(np.float32)
    pts[:, 0] *= float(w)
    pts[:, 1] *= float(h)
    return pts


def crop_polygon_from_warped(warped: np.ndarray, poly: np.ndarray, pad: int = 8) -> np.ndarray:
    h, w = warped.shape[:2]
    xs = poly[:, 0]
    ys = poly[:, 1]
    left = int(np.floor(xs.min())) - pad
    right = int(np.ceil(xs.max())) + pad
    top = int(np.floor(ys.min())) - pad
    bottom = int(np.ceil(ys.max())) + pad
    left = max(0, min(left, w - 1))
    right = max(1, min(right, w))
    top = max(0, min(top, h - 1))
    bottom = max(1, min(bottom, h))
    if right <= left or bottom <= top:
        raise ValueError(f'bad crop bounds left={left} top={top} right={right} bottom={bottom}')
    return warped[top:bottom, left:right].copy()


def find_image(images_dir: Path, filename: str) -> Path | None:
    candidate = images_dir / filename
    if candidate.exists():
        return candidate
    stem = Path(filename).stem.lower()
    for p in images_dir.iterdir():
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS and p.stem.lower() == stem:
            return p
    return None


def draw_poly(img: np.ndarray, pts: np.ndarray, color: Tuple[int, int, int], thickness: int = 3) -> None:
    p = np.round(pts).astype(np.int32).reshape(-1, 1, 2)
    cv2.polylines(img, [p], True, color, thickness, lineType=cv2.LINE_AA)
    for x, y in p.reshape(-1, 2):
        cv2.circle(img, (int(x), int(y)), 5, color, -1, lineType=cv2.LINE_AA)


def main() -> None:
    ap = argparse.ArgumentParser(description='Warp card first, then apply normalized template OCR regions.')
    ap.add_argument('--template-label', required=True, help='Template JSON label, e.g. border_training_labels\\IMG_7505.json')
    ap.add_argument('--target-labels', required=True, help='Folder of target label JSON files')
    ap.add_argument('--images', required=True, help='Folder with original images')
    ap.add_argument('--output', required=True, help='Output folder')
    ap.add_argument('--skip-template-source', action='store_true')
    ap.add_argument('--card-width', type=int, default=734, help='Normalized warped card width')
    ap.add_argument('--card-height', type=int, default=1024, help='Normalized warped card height')
    args = ap.parse_args()

    template_path = Path(args.template_label)
    labels_dir = Path(args.target_labels)
    images_dir = Path(args.images)
    out_dir = Path(args.output)
    crops_dir = out_dir / 'projected_crops'
    overlays_dir = out_dir / 'projected_overlays'
    warped_dir = out_dir / 'warped_cards'
    for d in [out_dir, crops_dir, overlays_dir, warped_dir]:
        d.mkdir(parents=True, exist_ok=True)

    template = load_json(template_path)
    norm_regions, _ = template_normalized_regions(template)

    rows = []
    for label_path in sorted(labels_dir.glob('*.json')):
        if args.skip_template_source and label_path.resolve() == template_path.resolve():
            continue
        try:
            label = load_json(label_path)
            filename = label.get('filename') or (label_path.stem + '.jpg')
            img_path = find_image(images_dir, filename)
            if not img_path:
                raise FileNotFoundError(f'image not found for {filename}')
            img = cv2.imread(str(img_path))
            if img is None:
                raise ValueError(f'could not read image {img_path}')
            card_pts = pts_array(label['regions']['card'])
            warped, _ = warp_card(img, card_pts, args.card_width, args.card_height)
            stem = Path(filename).stem
            cv2.imwrite(str(warped_dir / f'{stem}_warped_card.jpg'), warped)

            overlay = warped.copy()
            colors = {
                'name': (255, 0, 0),      # blue BGR
                'number': (0, 255, 255),  # yellow
                'setcode': (255, 0, 255), # magenta
            }
            region_meta = {}
            for key in REGIONS:
                poly = denormalize_region(norm_regions[key], args.card_width, args.card_height)
                draw_poly(overlay, poly, colors[key], 2)
                crop = crop_polygon_from_warped(warped, poly)
                crop_path = crops_dir / f'{stem}_{key}_projected.jpg'
                cv2.imwrite(str(crop_path), crop)
                region_meta[key] = [[round(float(x), 3), round(float(y), 3)] for x, y in poly]
            cv2.imwrite(str(overlays_dir / f'{stem}_warped_overlay.jpg'), overlay)
            (out_dir / f'{stem}_warped_regions.json').write_text(json.dumps({
                'template': str(template_path),
                'target_label': str(label_path),
                'filename': filename,
                'card_space': {'width': args.card_width, 'height': args.card_height},
                'projected_regions_on_warped_card': region_meta,
            }, indent=2), encoding='utf-8')
            print(f'{stem}: OK')
            rows.append({'file': filename, 'status': 'ok', 'error': '', 'warped_card': str(warped_dir / f'{stem}_warped_card.jpg')})
        except Exception as e:
            print(f'{label_path.name}: ERROR {e}')
            rows.append({'file': label_path.name, 'status': 'error', 'error': str(e), 'warped_card': ''})

    with (out_dir / 'warp_crop_validator_summary.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['file', 'status', 'error', 'warped_card'])
        writer.writeheader()
        writer.writerows(rows)
    print(f'Done. Output: {out_dir}')
    print(f'Open crops: {crops_dir}')
    print(f'Open overlays: {overlays_dir}')


if __name__ == '__main__':
    main()
