#!/usr/bin/env python3
"""Putnam Capture v0.1.

Small OpenCV desktop capture tool for camera-based intake sessions.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Iterable

try:
    import cv2
except ImportError as exc:  # pragma: no cover - runtime dependency guard
    raise SystemExit(
        "OpenCV is required. Install it with: python -m pip install opencv-python"
    ) from exc


APP_NAME = "Putnam Capture v0.1"
MAX_CAMERA_INDEX = 9


def resolve_root() -> Path:
    user_environment = os.environ.get("USERENVIRONMENT")
    if user_environment:
        return Path(user_environment).expanduser()

    user_profile = os.environ.get("USERPROFILE")
    if user_profile:
        return Path(user_profile) / "OneDrive" / "PutnamCollectibles"

    return Path.home() / "OneDrive" / "PutnamCollectibles"


def timestamp_for_folder() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H%M%S")


def iso_now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def make_session_dir(root: Path) -> Path:
    base = root / "Putnam_OS" / "Incoming Files" / "Capture_Sessions"
    base.mkdir(parents=True, exist_ok=True)

    stamp = timestamp_for_folder()
    candidate = base / stamp
    suffix = 1
    while candidate.exists():
        candidate = base / f"{stamp}_{suffix:02d}"
        suffix += 1

    images_dir = candidate / "images"
    images_dir.mkdir(parents=True, exist_ok=False)
    return candidate


def available_camera_indices(indices: Iterable[int]) -> list[int]:
    available: list[int] = []
    for index in indices:
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap.release()
            continue

        ok, frame = cap.read()
        cap.release()
        if ok and frame is not None:
            available.append(index)

    return available


def next_image_path(images_dir: Path, counter: int) -> tuple[Path, int]:
    while True:
        candidate = images_dir / f"{counter:06d}.jpg"
        if not candidate.exists():
            return candidate, counter
        counter += 1


def write_session_json(path: Path, data: dict) -> None:
    temp_path = path.with_suffix(".json.tmp")
    temp_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    temp_path.replace(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument(
        "--camera",
        type=int,
        default=None,
        help="Camera index to use. Defaults to the first available camera.",
    )
    parser.add_argument(
        "--max-camera-index",
        type=int,
        default=MAX_CAMERA_INDEX,
        help="Highest camera index to scan when --camera is not provided.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = resolve_root()
    session_dir = make_session_dir(root)
    images_dir = session_dir / "images"
    session_json = session_dir / "session.json"
    capture_log = session_dir / "capture_log.csv"
    start_time = iso_now()

    if args.camera is None:
        cameras = available_camera_indices(range(args.max_camera_index + 1))
        if not cameras:
            print("No available camera sources found.")
            print(f"Output folder: {images_dir}")
            return 1
        camera_index = cameras[0]
        print(f"Available cameras: {', '.join(str(i) for i in cameras)}")
    else:
        camera_index = args.camera

    session_data = {
        "app": APP_NAME,
        "start_time": start_time,
        "end_time": None,
        "output_folder": str(images_dir),
        "camera_index": camera_index,
        "image_count": 0,
    }
    write_session_json(session_json, session_data)

    with capture_log.open("w", newline="", encoding="utf-8") as log_file:
        writer = csv.DictWriter(log_file, fieldnames=["filename", "timestamp"])
        writer.writeheader()

        cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            session_data["end_time"] = iso_now()
            write_session_json(session_json, session_data)
            print(f"Could not open camera index {camera_index}.")
            print(f"Output folder: {images_dir}")
            return 1

        image_counter = 1
        window_name = f"{APP_NAME} - camera {camera_index}"
        print("Spacebar captures. Escape exits.")

        try:
            while True:
                ok, frame = cap.read()
                if not ok or frame is None:
                    print("Camera frame read failed.")
                    break

                cv2.imshow(window_name, frame)
                key = cv2.waitKey(1) & 0xFF

                if key == 27:
                    break

                if key == 32:
                    image_path, image_counter = next_image_path(images_dir, image_counter)
                    if not cv2.imwrite(str(image_path), frame):
                        print(f"Failed to save: {image_path}")
                        continue

                    captured_at = iso_now()
                    writer.writerow(
                        {
                            "filename": image_path.name,
                            "timestamp": captured_at,
                        }
                    )
                    log_file.flush()
                    session_data["image_count"] += 1
                    write_session_json(session_json, session_data)
                    print(f"Captured {image_path.name}")
                    image_counter += 1
        finally:
            cap.release()
            cv2.destroyAllWindows()
            session_data["end_time"] = iso_now()
            write_session_json(session_json, session_data)
            print(f"Output folder: {images_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
