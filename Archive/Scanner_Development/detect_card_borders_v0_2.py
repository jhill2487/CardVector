"""
Putnam Card Border Detector v0.2

More forgiving than v0.1:
- tries multiple preprocessing modes
- accepts rounded/soft card rectangles
- includes fallback min-area rectangle detection
- writes debug overlay, crop, and CSV results

Usage:
  python detect_card_borders_v0_2.py --input input_photos --output border_debug_v0_2
  python detect_card_borders_v0_2.py --input input_photos\IMG_7492.JPG --output border_debug_v0_2
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tif', '.tiff'}


def order_points(pts: np.ndarray) -> np.ndarray:
    pts = pts.reshape(4, 2).astype('float32')
    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1).reshape(-1)
    rect = np.zeros((4, 2), dtype='float32')
    rect[0] = pts[np.argmin(s)]      # top-left
    rect[2] = pts[np.argmax(s)]      # bottom-right
    rect[1] = pts[np.argmin(diff)]   # top-right
    rect[3] = pts[np.argmax(diff)]   # bottom-left
    return rect


def four_point_transform(image: np.ndarray, pts: np.ndarray) -> np.ndarray:
    rect = order_points(pts)
    (tl, tr, br, bl) = rect
    width_a = np.linalg.norm(br - bl)
    width_b = np.linalg.norm(tr - tl)
    max_width = int(max(width_a, width_b))
    height_a = np.linalg.norm(tr - br)
    height_b = np.linalg.norm(tl - bl)
    max_height = int(max(height_a, height_b))
    dst = np.array([
        [0, 0],
        [max_width - 1, 0],
        [max_width - 1, max_height - 1],
        [0, max_height - 1]
    ], dtype='float32')
    m = cv2.getPerspectiveTransform(rect, dst)
    return cv2.warpPerspective(image, m, (max_width, max_height))


def resize_for_detection(image: np.ndarray, max_dim: int = 1400) -> Tuple[np.ndarray, float]:
    h, w = image.shape[:2]
    scale = 1.0
    largest = max(h, w)
    if largest > max_dim:
        scale = max_dim / float(largest)
        image = cv2.resize(image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    return image, scale


def contour_score(contour: np.ndarray, image_shape: Tuple[int, int, int]) -> float:
    h, w = image_shape[:2]
    img_area = h * w
    area = cv2.contourArea(contour)
    if area <= 0:
        return -1
    area_ratio = area / img_area
    if area_ratio < 0.08 or area_ratio > 0.95:
        return -1

    peri = cv2.arcLength(contour, True)
    approx = cv2.approxPolyDP(contour, 0.025 * peri, True)
    x, y, bw, bh = cv2.boundingRect(contour)
    aspect = max(bw, bh) / max(1, min(bw, bh))
    # Pokemon card is about 1.4 tall/wide when upright, but perspective/photo crop can vary.
    aspect_score = 1.0 - min(abs(aspect - 1.40) / 1.0, 1.0)
    rect_area = bw * bh
    fill = area / max(1, rect_area)
    corner_bonus = 0.25 if len(approx) == 4 else 0.0
    return area_ratio * 2.0 + aspect_score * 0.8 + fill * 0.6 + corner_bonus


def preprocess_variants(image: np.ndarray) -> List[Tuple[str, np.ndarray]]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    variants: List[Tuple[str, np.ndarray]] = []

    edges = cv2.Canny(blur, 40, 120)
    variants.append(('canny_40_120', edges))

    edges2 = cv2.Canny(blur, 20, 80)
    variants.append(('canny_20_80', edges2))

    # Adaptive threshold helps when border is dark against mixed background.
    th = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                               cv2.THRESH_BINARY, 31, 7)
    variants.append(('adaptive_threshold', th))

    # Morphological gradient emphasizes large rectangular boundaries.
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
    grad = cv2.morphologyEx(blur, cv2.MORPH_GRADIENT, kernel)
    _, grad_th = cv2.threshold(grad, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    variants.append(('morph_gradient', grad_th))

    return variants


def find_card_quad(image: np.ndarray) -> Tuple[Optional[np.ndarray], str, float]:
    small, scale = resize_for_detection(image)
    best_quad = None
    best_method = 'none'
    best_score = -1.0

    for method, mask in preprocess_variants(small):
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        closed = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:20]

        for c in contours:
            score = contour_score(c, small.shape)
            if score < 0:
                continue
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.025 * peri, True)
            if len(approx) == 4:
                quad = approx.reshape(4, 2).astype('float32')
            else:
                rect = cv2.minAreaRect(c)
                box = cv2.boxPoints(rect).astype('float32')
                quad = box
                score -= 0.10

            if score > best_score:
                best_score = score
                best_method = method
                best_quad = quad

    if best_quad is None:
        return None, best_method, best_score

    if scale != 1.0:
        best_quad = best_quad / scale
    return best_quad.astype('float32'), best_method, best_score


def draw_overlay(image: np.ndarray, quad: Optional[np.ndarray], status: str, method: str, score: float) -> np.ndarray:
    out = image.copy()
    label = f'{status} | {method} | score={score:.2f}'
    if quad is not None:
        pts = order_points(quad).astype(int)
        cv2.polylines(out, [pts], True, (0, 255, 0), 6)
        for i, (x, y) in enumerate(pts):
            cv2.circle(out, (int(x), int(y)), 12, (0, 0, 255), -1)
            cv2.putText(out, str(i + 1), (int(x) + 10, int(y) - 10), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
    cv2.rectangle(out, (10, 10), (min(out.shape[1]-10, 900), 60), (255, 255, 255), -1)
    cv2.putText(out, label, (20, 48), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    return out


def process_image(path: Path, output_dir: Path) -> dict:
    image = cv2.imread(str(path))
    if image is None:
        return {'file': path.name, 'status': 'error', 'method': '', 'score': '', 'crop': '', 'message': 'Could not read image'}

    quad, method, score = find_card_quad(image)
    status = 'border_found' if quad is not None and score >= 0.45 else 'weak_or_no_border'

    overlay = draw_overlay(image, quad, status, method, score)
    overlay_path = output_dir / f'{path.stem}_border_overlay.jpg'
    cv2.imwrite(str(overlay_path), overlay)

    crop_path = ''
    if quad is not None:
        crop = four_point_transform(image, quad)
        # Rotate to portrait if needed.
        ch, cw = crop.shape[:2]
        if cw > ch:
            crop = cv2.rotate(crop, cv2.ROTATE_90_CLOCKWISE)
        crop_file = output_dir / f'{path.stem}_card_crop.jpg'
        cv2.imwrite(str(crop_file), crop)
        crop_path = str(crop_file)

    return {
        'file': path.name,
        'status': status,
        'method': method,
        'score': f'{score:.3f}',
        'crop': crop_path,
        'message': 'Review overlay. If green outline follows the card, crop is usable.' if quad is not None else 'No usable rectangle found.'
    }


def iter_images(input_path: Path) -> List[Path]:
    if input_path.is_file():
        return [input_path] if input_path.suffix.lower() in IMAGE_EXTENSIONS else []
    input_path.mkdir(exist_ok=True)
    return sorted([p for p in input_path.iterdir() if p.suffix.lower() in IMAGE_EXTENSIONS])


def main() -> None:
    parser = argparse.ArgumentParser(description='Putnam card border detector v0.2')
    parser.add_argument('--input', required=True, help='Image file or folder of card photos')
    parser.add_argument('--output', default='border_debug_v0_2', help='Output folder')
    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(exist_ok=True)

    images = iter_images(input_path)
    print(f'Border detector v0.2: {len(images)} image(s)')
    results = []
    for img in images:
        print(f'Processing {img.name}...')
        result = process_image(img, output_dir)
        print(f"  {result['status']}: method={result['method']} score={result['score']}")
        results.append(result)

    csv_path = output_dir / 'border_results.csv'
    with csv_path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['file', 'status', 'method', 'score', 'crop', 'message'])
        writer.writeheader()
        writer.writerows(results)

    print(f'Done. Results saved to: {output_dir}')
    print(f'Summary CSV: {csv_path}')


if __name__ == '__main__':
    main()
