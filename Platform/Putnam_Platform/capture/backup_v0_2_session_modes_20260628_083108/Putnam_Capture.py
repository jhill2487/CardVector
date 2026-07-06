#!/usr/bin/env python3
"""Putnam Capture v0.2.

Capture still JPEGs from an OBS scene through OBS WebSocket.
"""

from __future__ import annotations

import argparse
import base64
import csv
import getpass
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


APP_NAME = "Putnam Capture v0.2"
DEFAULT_OBS_HOST = "localhost"
DEFAULT_OBS_PORT = 4455
DEFAULT_OBS_SCENE = "03 - Card Capture"
CAPTURE_METHOD = "obs_scene_screenshot"
DEFAULT_CAPTURE_SETTINGS = {
    "obs_host": DEFAULT_OBS_HOST,
    "obs_port": DEFAULT_OBS_PORT,
    "obs_scene": DEFAULT_OBS_SCENE,
    "capture_method": CAPTURE_METHOD,
    "save_full_frame": True,
    "save_cropped_frame": False,
}


@dataclass
class ObsConnection:
    client: Any
    host: str
    port: int
    scene_name: str


def resolve_root() -> Path:
    user_environment = os.environ.get("USERENVIRONMENT")
    if user_environment:
        return Path(user_environment).expanduser()

    user_profile = os.environ.get("USERPROFILE")
    if user_profile:
        return Path(user_profile) / "OneDrive" / "PutnamCollectibles"

    return Path.home() / "OneDrive" / "PutnamCollectibles"


def capture_settings_path(root: Path) -> Path:
    return root / "Putnam_Platform" / "capture" / "capture_settings.json"


def load_capture_settings(root: Path) -> dict[str, Any]:
    path = capture_settings_path(root)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(DEFAULT_CAPTURE_SETTINGS, indent=2) + "\n", encoding="utf-8")
        return dict(DEFAULT_CAPTURE_SETTINGS)

    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        print(f"Could not read capture settings: {path}")
        print(f"Details: {exc}")
        print("Using built-in defaults for this run.")
        return dict(DEFAULT_CAPTURE_SETTINGS)

    settings = dict(DEFAULT_CAPTURE_SETTINGS)
    settings.update({k: v for k, v in data.items() if v is not None})
    return settings


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


def write_session_json(path: Path, data: dict[str, Any]) -> None:
    temp_path = path.with_suffix(".json.tmp")
    temp_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    temp_path.replace(path)


def next_image_path(images_dir: Path, counter: int) -> tuple[Path, int]:
    while True:
        candidate = images_dir / f"{counter:06d}.jpg"
        if not candidate.exists():
            return candidate, counter
        counter += 1


def parse_args(settings: dict[str, Any]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument("--host", default=os.environ.get("PUTNAM_OBS_HOST", str(settings.get("obs_host", DEFAULT_OBS_HOST))))
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PUTNAM_OBS_PORT", settings.get("obs_port", DEFAULT_OBS_PORT))),
    )
    parser.add_argument(
        "--password",
        default=os.environ.get("PUTNAM_OBS_PASSWORD", ""),
        help="OBS WebSocket password. Defaults to blank or PUTNAM_OBS_PASSWORD.",
    )
    parser.add_argument(
        "--password-prompt",
        action="store_true",
        help="Prompt for the OBS WebSocket password instead of using a blank/default password.",
    )
    parser.add_argument(
        "--scene",
        default=os.environ.get("PUTNAM_OBS_SCENE", str(settings.get("obs_scene", DEFAULT_OBS_SCENE))),
        help=f"OBS scene to capture. Defaults to '{DEFAULT_OBS_SCENE}'.",
    )
    parser.add_argument(
        "--no-scene-prompt",
        action="store_true",
        help="Use the configured/default scene without prompting to choose from available OBS scenes.",
    )
    parser.add_argument(
        "--jpeg-quality",
        type=int,
        default=95,
        help="JPEG quality passed to OBS, 1-100. Defaults to 95.",
    )
    return parser.parse_args()


def import_obsws_python() -> Any:
    try:
        import obsws_python as obs  # type: ignore
    except ImportError:
        print("obsws-python is required for Putnam Capture v0.2.")
        print("Install it with:")
        print("py -m pip install obsws-python")
        raise SystemExit(1)

    return obs


def response_value(response: Any, *names: str, default: Any = None) -> Any:
    for name in names:
        if hasattr(response, name):
            return getattr(response, name)

    if isinstance(response, dict):
        for name in names:
            if name in response:
                return response[name]

    return default


def scene_names(scene_list_response: Any) -> list[str]:
    scenes = response_value(scene_list_response, "scenes", default=[])
    names: list[str] = []

    for scene in scenes:
        name = response_value(scene, "sceneName", "scene_name")
        if name:
            names.append(str(name))

    return names


def current_scene_name(response: Any) -> str:
    return str(response_value(response, "currentProgramSceneName", "current_program_scene_name", default=""))


def choose_scene(default_scene: str, scenes: list[str], no_prompt: bool = False) -> str:
    if no_prompt:
        return default_scene

    print("")
    print("Available OBS scenes:")
    for name in scenes:
        marker = " (default)" if name == default_scene else ""
        print(f"  - {name}{marker}")
    print("")
    selected = input(f"OBS scene capture scene [{default_scene}]: ").strip()
    return selected or default_scene


def connect_to_obs(args: argparse.Namespace) -> ObsConnection:
    obs = import_obsws_python()
    password = getpass.getpass("OBS WebSocket password: ") if args.password_prompt else args.password

    try:
        client = obs.ReqClient(host=args.host, port=args.port, password=password, timeout=5)
        client.get_version()
    except Exception as exc:
        print("Could not connect to OBS through OBS WebSocket.")
        print(f"Host: {args.host}")
        print(f"Port: {args.port}")
        print("Make sure OBS is running and OBS WebSocket is enabled.")
        print(f"Details: {exc}")
        raise SystemExit(1) from exc

    scenes = scene_names(client.get_scene_list())
    selected_scene = choose_scene(args.scene, scenes, args.no_scene_prompt)
    if selected_scene not in scenes:
        print(f"OBS scene not found: {selected_scene}")
        print("Available scenes:")
        for name in scenes:
            print(f"  - {name}")
        raise SystemExit(1)

    try:
        client.set_current_program_scene(selected_scene)
        current_scene = current_scene_name(client.get_current_program_scene())
    except Exception as exc:
        print(f"Connected to OBS, but could not switch to scene: {selected_scene}")
        print(f"Details: {exc}")
        raise SystemExit(1) from exc

    print(f"Connected to OBS at {args.host}:{args.port}.")
    print(f"Current OBS scene capture scene: {current_scene}")
    return ObsConnection(client=client, host=args.host, port=args.port, scene_name=current_scene)


def decode_image_data(image_data: str) -> bytes:
    if "," in image_data and image_data.lstrip().startswith("data:"):
        image_data = image_data.split(",", 1)[1]

    return base64.b64decode(image_data)


def capture_scene_jpeg(client: Any, scene_name: str, jpeg_quality: int) -> bytes:
    try:
        response = client.get_source_screenshot(
            source_name=scene_name,
            image_format="jpg",
            image_compression_quality=jpeg_quality,
        )
    except TypeError:
        try:
            response = client.get_source_screenshot(
                sourceName=scene_name,
                imageFormat="jpg",
                imageCompressionQuality=jpeg_quality,
            )
        except TypeError:
            response = client.get_source_screenshot(scene_name, "jpg", None, None, jpeg_quality)

    image_data = response_value(response, "imageData", "image_data")
    if not image_data:
        raise RuntimeError("OBS returned an empty screenshot response.")

    return decode_image_data(str(image_data))


def read_key() -> str:
    if os.name == "nt":
        import msvcrt

        key = msvcrt.getch()
        if key in (b"\x00", b"\xe0"):
            msvcrt.getch()
            return ""
        if key == b"\x1b":
            return "esc"
        try:
            return key.decode("utf-8").lower()
        except UnicodeDecodeError:
            return ""

    value = input("Press SPACE to capture, Q to exit: ")
    return " " if value == "" else value[:1].lower()


def main() -> int:
    root = resolve_root()
    settings = load_capture_settings(root)
    args = parse_args(settings)
    args.jpeg_quality = max(1, min(100, args.jpeg_quality))

    obs_connection = connect_to_obs(args)

    session_dir = make_session_dir(root)
    images_dir = session_dir / "images"
    session_json = session_dir / "session.json"
    capture_log = session_dir / "capture_log.csv"
    start_time = iso_now()

    session_data: dict[str, Any] = {
        "app": APP_NAME,
        "start_time": start_time,
        "end_time": None,
        "obs_scene": obs_connection.scene_name,
        "output_folder": str(images_dir),
        "image_count": 0,
        "capture_method": CAPTURE_METHOD,
        "save_full_frame": bool(settings.get("save_full_frame", True)),
        "save_cropped_frame": bool(settings.get("save_cropped_frame", False)),
    }
    write_session_json(session_json, session_data)

    print("")
    print("OBS scene capture ready.")
    print("Controls: SPACE = capture JPEG, Q or ESC = exit")

    image_counter = 1
    with capture_log.open("w", newline="", encoding="utf-8") as log_file:
        writer = csv.DictWriter(
            log_file,
            fieldnames=["filename", "timestamp", "obs_scene", "status"],
        )
        writer.writeheader()

        try:
            while True:
                key = read_key()
                if key in ("q", "esc"):
                    break

                if key != " ":
                    continue

                image_path, image_counter = next_image_path(images_dir, image_counter)
                captured_at = iso_now()
                status = "captured"

                try:
                    image_bytes = capture_scene_jpeg(
                        obs_connection.client,
                        obs_connection.scene_name,
                        args.jpeg_quality,
                    )
                    image_path.write_bytes(image_bytes)
                    session_data["image_count"] += 1
                    print(f"Captured {image_path.name}")
                    image_counter += 1
                except Exception as exc:
                    status = f"error: {exc}"
                    print(f"Capture failed: {exc}")

                writer.writerow(
                    {
                        "filename": image_path.name,
                        "timestamp": captured_at,
                        "obs_scene": obs_connection.scene_name,
                        "status": status,
                    }
                )
                log_file.flush()
                write_session_json(session_json, session_data)
        finally:
            session_data["end_time"] = iso_now()
            write_session_json(session_json, session_data)
            print("")
            print(f"Output folder: {images_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
