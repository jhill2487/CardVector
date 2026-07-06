"""
Putnam Template Region Crop Validator v0.6

Purpose:
  Validate template-projected OCR regions visually before OCR/matching.

Inputs:
  --template-label : one JSON label file containing card/name/number/setcode polygons
  --target-labels  : folder of target JSON labels containing card polygons
  --images         : folder containing original photos
  --output         : output folder

Outputs:
  output/projected_crops/<stem>_projected_name_crop.jpg
  output/projected_crops/<stem>_projected_number_crop.jpg
  output/projected_crops/<stem>_projected_setcode_crop.jpg
  output/projected_overlays/<stem>_projected_overlay.jpg
  output/projected_regions/<stem>_projected_regions.json
  output/crop_validator_summary.csv

No OCR. No database matching.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Dict, List, Tuple, Any

from PIL import Image, ImageDraw

Point = Dict[str, float]
Polygon = List[Point]

REGION_COLORS = {
    "card": (0, 220, 0),       # green
    "name": (0, 120, 255),     # blue
    "number": (255, 210, 0),   # yellow
    "setcode": (255, 0, 220),  # magenta
}

IMAGE_EXTS = [".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"]


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def p_to_tuple(p: Point) -> Tuple[float, float]:
    return float(p["x"]), float(p["y"])


def poly_to_tuples(poly: Polygon) -> List[Tuple[float, float]]:
    return [p_to_tuple(p) for p in poly]


def tuples_to_poly(points: List[Tuple[float, float]]) -> Polygon:
    return [{"x": round(float(x), 3), "y": round(float(y), 3)} for x, y in points]


def find_image(images_dir: Path, filename: str) -> Path | None:
    exact = images_dir / filename
    if exact.exists():
        return exact
    stem = Path(filename).stem.lower()
    for ext in IMAGE_EXTS:
        p = images_dir / f"{Path(filename).stem}{ext}"
        if p.exists():
            return p
    for p in images_dir.iterdir():
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS and p.stem.lower() == stem:
            return p
    return None


def bilinear(card: Polygon, u: float, v: float) -> Tuple[float, float]:
    # card order is tl, tr, br, bl
    tl, tr, br, bl = poly_to_tuples(card)
    x = (1-u)*(1-v)*tl[0] + u*(1-v)*tr[0] + u*v*br[0] + (1-u)*v*bl[0]
    y = (1-u)*(1-v)*tl[1] + u*(1-v)*tr[1] + u*v*br[1] + (1-u)*v*bl[1]
    return x, y


def invert_bilinear(card: Polygon, pt: Point, max_iter: int = 30) -> Tuple[float, float]:
    # Newton solve for u/v inside a quadrilateral bilinear patch.
    tl, tr, br, bl = poly_to_tuples(card)
    x, y = p_to_tuple(pt)
    u, v = 0.5, 0.5
    for _ in range(max_iter):
        bx, by = bilinear(card, u, v)
        fx, fy = bx - x, by - y
        if abs(fx) + abs(fy) < 1e-6:
            break
        # partial derivatives
        dxdu = -(1-v)*tl[0] + (1-v)*tr[0] + v*br[0] - v*bl[0]
        dydu = -(1-v)*tl[1] + (1-v)*tr[1] + v*br[1] - v*bl[1]
        dxdv = -(1-u)*tl[0] - u*tr[0] + u*br[0] + (1-u)*bl[0]
        dydv = -(1-u)*tl[1] - u*tr[1] + u*br[1] + (1-u)*bl[1]
        det = dxdu*dydv - dxdv*dydu
        if abs(det) < 1e-9:
            break
        du = (fx*dydv - dxdv*fy) / det
        dv = (dxdu*fy - fx*dydu) / det
        u -= du
        v -= dv
    return u, v


def template_region_uvs(template_regions: Dict[str, Polygon]) -> Dict[str, List[Tuple[float, float]]]:
    card = template_regions["card"]
    out: Dict[str, List[Tuple[float, float]]] = {}
    for key in ["name", "number", "setcode"]:
        out[key] = [invert_bilinear(card, p) for p in template_regions[key]]
    return out


def project_region(target_card: Polygon, region_uv: List[Tuple[float, float]]) -> Polygon:
    return tuples_to_poly([bilinear(target_card, u, v) for u, v in region_uv])


def safe_bbox(poly: Polygon, width: int, height: int, pad: int = 4) -> Tuple[int, int, int, int] | None:
    pts = poly_to_tuples(poly)
    xs = [x for x, _ in pts]
    ys = [y for _, y in pts]
    left = max(0, math.floor(min(xs)) - pad)
    right = min(width, math.ceil(max(xs)) + pad)
    top = max(0, math.floor(min(ys)) - pad)
    bottom = min(height, math.ceil(max(ys)) + pad)
    if right <= left or bottom <= top:
        return None
    return left, top, right, bottom


def crop_bbox(img: Image.Image, poly: Polygon, pad: int = 4) -> Image.Image | None:
    bbox = safe_bbox(poly, img.width, img.height, pad=pad)
    if bbox is None:
        return None
    return img.crop(bbox)


def draw_poly(draw: ImageDraw.ImageDraw, poly: Polygon, color: Tuple[int, int, int], width: int = 8) -> None:
    pts = [(float(p["x"]), float(p["y"])) for p in poly]
    if len(pts) >= 2:
        draw.line(pts + [pts[0]], fill=color, width=width)
    r = max(6, width + 2)
    for x, y in pts:
        draw.ellipse((x-r, y-r, x+r, y+r), fill=color)


def write_overlay(img: Image.Image, regions: Dict[str, Polygon], out_path: Path) -> None:
    overlay = img.copy().convert("RGB")
    draw = ImageDraw.Draw(overlay)
    for key in ["card", "name", "number", "setcode"]:
        if key in regions:
            draw_poly(draw, regions[key], REGION_COLORS[key], width=8 if key == "card" else 6)
            first = regions[key][0]
            draw.text((first["x"] + 12, first["y"] + 12), key, fill=REGION_COLORS[key])
    overlay.save(out_path, quality=92)


def main() -> None:
    ap = argparse.ArgumentParser(description="Putnam Template Region Crop Validator v0.6")
    ap.add_argument("--template-label", required=True)
    ap.add_argument("--target-labels", required=True)
    ap.add_argument("--images", required=True)
    ap.add_argument("--output", default="template_crop_validator_v0_6")
    ap.add_argument("--skip-template-source", action="store_true")
    args = ap.parse_args()

    template_path = Path(args.template_label)
    labels_dir = Path(args.target_labels)
    images_dir = Path(args.images)
    out_dir = Path(args.output)
    crops_dir = out_dir / "projected_crops"
    overlays_dir = out_dir / "projected_overlays"
    regions_dir = out_dir / "projected_regions"
    crops_dir.mkdir(parents=True, exist_ok=True)
    overlays_dir.mkdir(parents=True, exist_ok=True)
    regions_dir.mkdir(parents=True, exist_ok=True)

    template = load_json(template_path)
    template_regions = template.get("regions", {})
    required = ["card", "name", "number", "setcode"]
    missing = [k for k in required if k not in template_regions]
    if missing:
        raise SystemExit(f"Template missing regions: {missing}")

    region_uvs = template_region_uvs(template_regions)
    summary_rows = []

    target_files = sorted(labels_dir.glob("*.json"))
    for label_path in target_files:
        if args.skip_template_source and label_path.resolve() == template_path.resolve():
            continue
        try:
            label = load_json(label_path)
            filename = label.get("filename") or f"{label_path.stem}.JPG"
            img_path = find_image(images_dir, filename)
            if img_path is None:
                summary_rows.append({"label": label_path.name, "filename": filename, "status": "missing_image", "error": ""})
                print(f"{label_path.name}: missing image {filename}")
                continue
            target_regions = label.get("regions", {})
            if "card" not in target_regions:
                summary_rows.append({"label": label_path.name, "filename": filename, "status": "missing_card_region", "error": ""})
                print(f"{label_path.name}: missing card region")
                continue

            img = Image.open(img_path).convert("RGB")
            projected: Dict[str, Polygon] = {"card": target_regions["card"]}
            for key in ["name", "number", "setcode"]:
                projected[key] = project_region(target_regions["card"], region_uvs[key])

            stem = Path(filename).stem
            write_overlay(img, projected, overlays_dir / f"{stem}_projected_overlay.jpg")
            (regions_dir / f"{stem}_projected_regions.json").write_text(
                json.dumps({
                    "template": str(template_path),
                    "target_label": str(label_path),
                    "filename": filename,
                    "projected_regions": projected,
                }, indent=2),
                encoding="utf-8",
            )

            crop_status = []
            for key in ["name", "number", "setcode"]:
                crop = crop_bbox(img, projected[key], pad=4)
                if crop is None:
                    crop_status.append(f"{key}:bad_bbox")
                else:
                    crop.save(crops_dir / f"{stem}_projected_{key}_crop.jpg", quality=95)
                    crop_status.append(f"{key}:ok")

            summary_rows.append({
                "label": label_path.name,
                "filename": filename,
                "status": "ok",
                "error": ";".join(crop_status),
            })
            print(f"{label_path.name}: saved projected crops/overlay")
        except Exception as e:
            summary_rows.append({"label": label_path.name, "filename": "", "status": "error", "error": str(e)})
            print(f"{label_path.name}: ERROR {e}")

    with (out_dir / "crop_validator_summary.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["label", "filename", "status", "error"])
        writer.writeheader()
        writer.writerows(summary_rows)

    print(f"Done. Output: {out_dir}")
    print(f"Open projected crops: {crops_dir}")
    print(f"Open projected overlays: {overlays_dir}")


if __name__ == "__main__":
    main()
