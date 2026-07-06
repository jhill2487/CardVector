#!/usr/bin/env python3
"""OBS Capture Auto Crop Pipeline v0.1.

Batch-process JPEGs produced by Putnam Capture / OBS WebSocket sessions and
save portrait card crops, debug overlays, and metadata JSON for scanner or
overlay consumers.
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import cv2
    import numpy as np
except ImportError as exc:  # pragma: no cover - exercised by operator environment
    print("OpenCV is required for OBS Capture Auto Crop Pipeline v0.1.")
    print("Install it with: python -m pip install opencv-python")
    raise SystemExit(1) from exc


APP_NAME = "OBS Capture Auto Crop Pipeline v0.1"
IMAGE_EXTENSIONS = {".jpg", ".jpeg"}
DEFAULT_INPUT = Path("captures")
DEFAULT_OUTPUT = Path("processed") / "obs_autocrop"
CARD_ASPECT = 2.5 / 3.5
ASPECT_TOLERANCE = (0.55, 0.85)
MIN_CONTOUR_AREA_RATIO = 0.005
MAX_PROCESS_SIDE = 1200
WATCH_INTERVAL_SECONDS = 1.0


def iso_now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def safe_stem(path: Path) -> str:
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in path.stem)[:100]


def image_files(input_dir: Path) -> list[Path]:
    if not input_dir.exists():
        return []
    return sorted(p for p in input_dir.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS)


def order_quad(points: Any) -> Any:
    pts = np.asarray(points, dtype=np.float32).reshape(4, 2)
    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1).reshape(-1)
    tl = pts[np.argmin(s)]
    br = pts[np.argmax(s)]
    tr = pts[np.argmin(diff)]
    bl = pts[np.argmax(diff)]
    return np.array([tl, tr, br, bl], dtype=np.float32)


def quad_dimensions(quad: Any) -> tuple[int, int]:
    tl, tr, br, bl = order_quad(quad)
    width_top = np.linalg.norm(tr - tl)
    width_bottom = np.linalg.norm(br - bl)
    height_right = np.linalg.norm(br - tr)
    height_left = np.linalg.norm(bl - tl)
    width = int(round(max(width_top, width_bottom)))
    height = int(round(max(height_right, height_left)))
    return max(width, 1), max(height, 1)


def normalized_aspect(width: float, height: float) -> float:
    short_side = min(width, height)
    long_side = max(width, height)
    return short_side / max(long_side, 1.0)


def contour_score(area: float, image_area: float, aspect: float, extent: float, boundary_penalty: float) -> float:
    # OBS tabletop frames may include boxes, mats, and card stacks. Prefer a
    # card-sized rectangle near the target aspect ratio over the largest scene
    # rectangle, especially when the larger rectangle touches the frame edge.
    area_ratio = area / max(image_area, 1.0)
    aspect_score = max(0.0, 1.0 - (abs(aspect - CARD_ASPECT) / 0.18))
    area_score = max(0.0, 1.0 - (abs(area_ratio - 0.16) / 0.22))
    return (aspect_score * 3.0) + area_score + extent - (boundary_penalty * 1.2)


def preprocess_for_edges(image: Any) -> tuple[Any, float]:
    height, width = image.shape[:2]
    scale = 1.0
    max_side = max(width, height)
    working = image
    if max_side > MAX_PROCESS_SIDE:
        scale = MAX_PROCESS_SIDE / float(max_side)
        working = cv2.resize(image, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_AREA)

    gray = cv2.cvtColor(working, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    median = float(np.median(blur))
    lower = int(max(30, 0.66 * median))
    upper = int(min(220, 1.33 * median + 40))
    edges = cv2.Canny(blur, lower, upper)
    kernel = np.ones((5, 5), np.uint8)
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)
    edges = cv2.dilate(edges, kernel, iterations=1)
    return edges, scale


def find_card_candidate(image: Any) -> dict[str, Any] | None:
    edges, scale = preprocess_for_edges(image)
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    image_area = float(edges.shape[0] * edges.shape[1])
    best: dict[str, Any] | None = None

    for contour in contours:
        area = float(cv2.contourArea(contour))
        if area < image_area * MIN_CONTOUR_AREA_RATIO:
            continue

        perimeter = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.025 * perimeter, True)
        status = "cropped" if len(approx) == 4 else "fallback_crop"
        if len(approx) == 4:
            quad = approx.reshape(4, 2).astype(np.float32)
        else:
            rect = cv2.minAreaRect(contour)
            quad = cv2.boxPoints(rect).astype(np.float32)

        width, height = quad_dimensions(quad)
        aspect = normalized_aspect(width, height)
        if not ASPECT_TOLERANCE[0] <= aspect <= ASPECT_TOLERANCE[1]:
            continue

        rect_area = float(width * height)
        extent = area / max(rect_area, 1.0)
        if extent < 0.35:
            continue

        edge_margin = 3.0
        max_x = float(edges.shape[1] - 1)
        max_y = float(edges.shape[0] - 1)
        boundary_hits = sum(
            1
            for x, y in quad
            if x <= edge_margin or y <= edge_margin or x >= max_x - edge_margin or y >= max_y - edge_margin
        )
        candidate = {
            "quad": order_quad(quad) / max(scale, 1e-6),
            "status": status,
            "area": area / max(scale * scale, 1e-6),
            "aspect": aspect,
            "score": contour_score(area, image_area, aspect, extent, float(boundary_hits)),
        }
        if best is None or candidate["score"] > best["score"]:
            best = candidate

    return best


def warp_card(image: Any, quad: Any) -> Any:
    src = order_quad(quad)
    width, height = quad_dimensions(src)
    if width > height:
        width, height = height, width
    dst = np.array(
        [[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]],
        dtype=np.float32,
    )
    matrix = cv2.getPerspectiveTransform(src, dst)
    return cv2.warpPerspective(image, matrix, (width, height))


def bounding_rect_crop(image: Any, quad: Any) -> Any:
    height, width = image.shape[:2]
    xs = np.asarray(quad)[:, 0]
    ys = np.asarray(quad)[:, 1]
    pad = int(max(width, height) * 0.01)
    left = max(0, int(np.floor(xs.min())) - pad)
    right = min(width, int(np.ceil(xs.max())) + pad)
    top = max(0, int(np.floor(ys.min())) - pad)
    bottom = min(height, int(np.ceil(ys.max())) + pad)
    return image[top:bottom, left:right].copy()


def rotate_to_portrait(crop: Any) -> tuple[Any, bool]:
    height, width = crop.shape[:2]
    if width > height:
        return cv2.rotate(crop, cv2.ROTATE_90_CLOCKWISE), True
    return crop, False


def draw_debug(image: Any, quad: Any | None, status: str) -> Any:
    debug = image.copy()
    if quad is not None:
        pts = np.round(order_quad(quad)).astype(np.int32).reshape(-1, 1, 2)
        cv2.polylines(debug, [pts], True, (0, 255, 0), 4, lineType=cv2.LINE_AA)
        for idx, (x, y) in enumerate(pts.reshape(-1, 2), 1):
            cv2.circle(debug, (int(x), int(y)), 8, (0, 255, 255), -1, lineType=cv2.LINE_AA)
            cv2.putText(debug, str(idx), (int(x) + 10, int(y) + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
    cv2.putText(debug, status, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
    return debug


def identify_card_from_crop(cropped_path: Path) -> None:
    """Integration hook for the scanner/overlay identifier.

    TODO: connect this to the active scanner identifier once its callable
    interface is restored outside Archive. Keep this function side-effect free
    until the scanner contract is clear.
    """
    print(f"Identifier hook ready for: {cropped_path}")


def metadata_template(source_file: Path, card_file: Path | None, debug_file: Path | None) -> dict[str, Any]:
    return {
        "source_file": str(source_file),
        "status": "error",
        "output_card_file": str(card_file) if card_file else "",
        "debug_file": str(debug_file) if debug_file else "",
        "detected_contour_points": [],
        "aspect_ratio": None,
        "rotation_applied": False,
        "width": None,
        "height": None,
        "timestamp": iso_now(),
    }


def process_image(source_file: Path, output_dir: Path, debug: bool = False, run_identifier: bool = False) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = safe_stem(source_file)
    card_file = output_dir / f"{stem}_card.jpg"
    debug_file = output_dir / f"{stem}_debug.jpg" if debug else None
    metadata_file = output_dir / f"{stem}_metadata.json"
    metadata = metadata_template(source_file, card_file, debug_file)

    try:
        image = cv2.imread(str(source_file))
        if image is None:
            raise ValueError(f"Could not read image: {source_file}")

        candidate = find_card_candidate(image)
        if candidate is None:
            metadata["status"] = "no_card_found"
            metadata["output_card_file"] = ""
            if debug_file:
                cv2.imwrite(str(debug_file), draw_debug(image, None, "no_card_found"))
            return write_metadata(metadata_file, metadata)

        quad = candidate["quad"]
        crop = warp_card(image, quad) if candidate["status"] == "cropped" else bounding_rect_crop(image, quad)
        crop, rotation_applied = rotate_to_portrait(crop)
        crop_height, crop_width = crop.shape[:2]
        aspect_ratio = round(normalized_aspect(crop_width, crop_height), 4)

        if not cv2.imwrite(str(card_file), crop):
            raise RuntimeError(f"Could not write crop: {card_file}")
        if debug_file:
            cv2.imwrite(str(debug_file), draw_debug(image, quad, candidate["status"]))

        metadata.update(
            {
                "status": candidate["status"],
                "output_card_file": str(card_file),
                "debug_file": str(debug_file) if debug_file else "",
                "detected_contour_points": [[round(float(x), 3), round(float(y), 3)] for x, y in order_quad(quad)],
                "aspect_ratio": aspect_ratio,
                "rotation_applied": rotation_applied,
                "width": int(crop_width),
                "height": int(crop_height),
            }
        )
        result = write_metadata(metadata_file, metadata)
        if run_identifier:
            identify_card_from_crop(card_file)
        return result
    except Exception as exc:
        metadata["status"] = "error"
        metadata["error"] = str(exc)
        metadata["output_card_file"] = ""
        if debug_file and source_file.exists():
            image = cv2.imread(str(source_file))
            if image is not None:
                cv2.imwrite(str(debug_file), draw_debug(image, None, "error"))
        return write_metadata(metadata_file, metadata)


def write_metadata(path: Path, metadata: dict[str, Any]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return metadata


def process_folder(input_dir: Path, output_dir: Path, debug: bool = False, run_identifier: bool = False) -> list[dict[str, Any]]:
    files = image_files(input_dir)
    print(APP_NAME)
    print(f"Input folder: {input_dir}")
    print(f"Output folder: {output_dir}")
    print(f"JPEGs found: {len(files)}")
    results: list[dict[str, Any]] = []
    for path in files:
        result = process_image(path, output_dir, debug=debug, run_identifier=run_identifier)
        results.append(result)
        print(f"{path.name}: {result.get('status')}")
    return results


def process_watch(input_dir: Path, output_dir: Path, debug: bool = False, run_identifier: bool = False) -> int:
    try:
        import watchdog  # noqa: F401
    except ImportError:
        print("Watch mode requires watchdog, which is not installed.")
        print("Install it with: python -m pip install watchdog")
        print("Batch mode is still available without watchdog.")
        return 1

    print(APP_NAME)
    print(f"Watching: {input_dir}")
    print(f"Output folder: {output_dir}")
    print("Press Ctrl+C to stop.")
    seen = {p.resolve() for p in image_files(input_dir)}
    try:
        while True:
            for path in image_files(input_dir):
                resolved = path.resolve()
                if resolved in seen:
                    continue
                time.sleep(0.25)
                result = process_image(path, output_dir, debug=debug, run_identifier=run_identifier)
                seen.add(resolved)
                print(f"{path.name}: {result.get('status')}")
            time.sleep(WATCH_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("Watch stopped.")
        return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="Folder containing OBS JPEG captures.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Folder for cropped cards, debug images, and metadata.")
    parser.add_argument("--debug", action="store_true", help="Write debug JPEGs showing detected borders.")
    parser.add_argument("--watch", action="store_true", help="Watch input folder for new JPEGs. Requires watchdog.")
    parser.add_argument("--identify", action="store_true", help="Call the scanner/overlay identifier hook after each crop.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_dir = Path(args.input).expanduser()
    output_dir = Path(args.output).expanduser()
    if args.watch:
        return process_watch(input_dir, output_dir, debug=args.debug, run_identifier=args.identify)
    process_folder(input_dir, output_dir, debug=args.debug, run_identifier=args.identify)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
