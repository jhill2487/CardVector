"""
Putnam Template Region Debugger v0.5

Purpose:
  Geometry-only test. Projects name/number/setcode regions from one manually
  labeled template card onto other manually bordered target cards, then saves
  overlay images. No OCR. No crop extraction. No matching.

Example:
  python template_region_debug_v0_5.py --template-label border_training_labels\IMG_7505.json --target-labels border_training_labels --images input_photos --output template_debug_v0_5 --skip-template-source

Colors:
  green   = target card border
  blue    = projected name region
  yellow  = projected number region
  magenta = projected set code region
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple

from PIL import Image, ImageDraw, ImageFont

Point = Tuple[float, float]
Quad = List[Point]

CANONICAL_CARD: Quad = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
REGION_KEYS = ["name", "number", "setcode"]
COLORS = {
    "card": (0, 255, 0),
    "name": (0, 90, 255),
    "number": (255, 220, 0),
    "setcode": (255, 0, 255),
}


def load_label(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def quad_from_json(label: dict, key: str) -> Quad:
    pts = label.get("regions", {}).get(key)
    if not pts or len(pts) != 4:
        raise ValueError(f"Missing or invalid region: {key}")
    return [(float(p["x"]), float(p["y"])) for p in pts]


def find_image(images_dir: Path, filename: str) -> Path | None:
    direct = images_dir / filename
    if direct.exists():
        return direct
    stem = Path(filename).stem.lower()
    for p in images_dir.iterdir():
        if p.is_file() and p.stem.lower() == stem and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}:
            return p
    return None


def solve_homography(src: Quad, dst: Quad) -> List[List[float]]:
    """Return 3x3 homography H mapping src points to dst points.
    Pure Python Gaussian elimination to avoid requiring cv2/numpy for this debug utility.
    """
    # H has h33 = 1. Unknowns: h11,h12,h13,h21,h22,h23,h31,h32
    A = []
    b = []
    for (x, y), (u, v) in zip(src, dst):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        b.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y])
        b.append(v)

    # Augmented matrix
    M = [row[:] + [rhs] for row, rhs in zip(A, b)]
    n = 8
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(M[r][col]))
        if abs(M[pivot][col]) < 1e-12:
            raise ValueError("Degenerate homography; card points may be invalid")
        M[col], M[pivot] = M[pivot], M[col]
        div = M[col][col]
        M[col] = [v / div for v in M[col]]
        for r in range(n):
            if r == col:
                continue
            factor = M[r][col]
            if factor:
                M[r] = [rv - factor * cv for rv, cv in zip(M[r], M[col])]
    h = [M[i][-1] for i in range(n)]
    return [
        [h[0], h[1], h[2]],
        [h[3], h[4], h[5]],
        [h[6], h[7], 1.0],
    ]


def apply_h(H: List[List[float]], pt: Point) -> Point:
    x, y = pt
    den = H[2][0] * x + H[2][1] * y + H[2][2]
    if abs(den) < 1e-12:
        raise ValueError("Projection denominator too small")
    u = (H[0][0] * x + H[0][1] * y + H[0][2]) / den
    v = (H[1][0] * x + H[1][1] * y + H[1][2]) / den
    return (u, v)


def project_template_regions(template_label: dict, target_label: dict) -> Dict[str, Quad]:
    template_card = quad_from_json(template_label, "card")
    target_card = quad_from_json(target_label, "card")

    # Template original-photo coords -> normalized card coords
    H_template_to_norm = solve_homography(template_card, CANONICAL_CARD)
    # Normalized card coords -> target original-photo coords
    H_norm_to_target = solve_homography(CANONICAL_CARD, target_card)

    projected: Dict[str, Quad] = {}
    for key in REGION_KEYS:
        reg = quad_from_json(template_label, key)
        norm_pts = [apply_h(H_template_to_norm, p) for p in reg]
        target_pts = [apply_h(H_norm_to_target, p) for p in norm_pts]
        projected[key] = target_pts
    projected["card"] = target_card
    return projected


def draw_poly(draw: ImageDraw.ImageDraw, pts: Quad, color: Tuple[int, int, int], width: int = 8) -> None:
    xy = [(float(x), float(y)) for x, y in pts]
    draw.line(xy + [xy[0]], fill=color, width=width)
    r = max(8, width * 2)
    for x, y in xy:
        draw.ellipse((x - r, y - r, x + r, y + r), outline=color, width=max(3, width // 2))


def label_text(draw: ImageDraw.ImageDraw, pts: Quad, text: str, color: Tuple[int, int, int]) -> None:
    x = min(p[0] for p in pts)
    y = min(p[1] for p in pts) - 40
    try:
        font = ImageFont.truetype("arial.ttf", 36)
    except Exception:
        font = None
    draw.rectangle((x, y, x + 230, y + 42), fill=(0, 0, 0))
    draw.text((x + 8, y + 5), text, fill=color, font=font)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--template-label", required=True)
    ap.add_argument("--target-labels", required=True, help="Folder of target JSON label files or one JSON file")
    ap.add_argument("--images", required=True, help="Folder containing original photos")
    ap.add_argument("--output", required=True)
    ap.add_argument("--skip-template-source", action="store_true")
    args = ap.parse_args()

    template_path = Path(args.template_label)
    targets_path = Path(args.target_labels)
    images_dir = Path(args.images)
    out_dir = Path(args.output)
    overlay_dir = out_dir / "overlays"
    data_dir = out_dir / "projected_regions"
    overlay_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    template_label = load_label(template_path)
    template_filename = template_label.get("filename", "")

    if targets_path.is_file():
        target_files = [targets_path]
    else:
        target_files = sorted(targets_path.glob("*.json"))

    rows = []
    for target_path in target_files:
        try:
            target_label = load_label(target_path)
            target_filename = target_label.get("filename", target_path.with_suffix(".JPG").name)
            if args.skip_template_source and Path(target_filename).stem.lower() == Path(template_filename).stem.lower():
                continue
            img_path = find_image(images_dir, target_filename)
            if img_path is None:
                raise FileNotFoundError(f"Image not found for label filename: {target_filename}")

            projected = project_template_regions(template_label, target_label)

            img = Image.open(img_path).convert("RGB")
            draw = ImageDraw.Draw(img)
            draw_poly(draw, projected["card"], COLORS["card"], width=10)
            for key in REGION_KEYS:
                draw_poly(draw, projected[key], COLORS[key], width=7)
                label_text(draw, projected[key], key, COLORS[key])

            out_img = overlay_dir / f"{Path(target_filename).stem}_template_overlay.jpg"
            img.save(out_img, quality=95)

            out_json = data_dir / f"{Path(target_filename).stem}_projected_regions.json"
            with out_json.open("w", encoding="utf-8") as f:
                json.dump({
                    "template": str(template_path),
                    "target_label": str(target_path),
                    "filename": target_filename,
                    "projected_regions": {
                        k: [{"x": round(x, 3), "y": round(y, 3)} for x, y in v]
                        for k, v in projected.items()
                    },
                }, f, indent=2)

            print(f"{target_path.name}: OK -> {out_img}")
            rows.append(f"{target_path.name},OK,{out_img}\n")
        except Exception as e:
            print(f"{target_path.name}: ERROR {e}")
            rows.append(f"{target_path.name},ERROR,{str(e).replace(',', ';')}\n")

    (out_dir / "template_region_debug_summary.csv").write_text("label,status,detail\n" + "".join(rows), encoding="utf-8")
    print(f"Done. Output: {out_dir}")
    print(f"Open overlays in: {overlay_dir}")


if __name__ == "__main__":
    main()
