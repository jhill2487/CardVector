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
import shutil
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


APP_NAME = "Putnam Capture v0.2"
DEFAULT_OBS_HOST = "localhost"
DEFAULT_OBS_PORT = 4455
DEFAULT_OBS_SCENE = "03 - Card Capture"
CAPTURE_METHOD = "obs_scene_screenshot"
VALID_MODES = {
    "front": "Front only",
    "back": "Back only",
    "pairs": "Front/back pairs",
}
DEFAULT_CAPTURE_SETTINGS = {
    "obs_host": DEFAULT_OBS_HOST,
    "obs_port": DEFAULT_OBS_PORT,
    "obs_scene": DEFAULT_OBS_SCENE,
    "capture_method": CAPTURE_METHOD,
    "save_full_frame": True,
    "save_cropped_frame": False,
    "crop_rectangle": {
        "left": 0,
        "top": 0,
        "right": 0,
        "bottom": 0,
    },
    "auto_capture_enabled": False,
    "auto_capture_min_delay_seconds": 2.0,
    "auto_capture_stable_seconds": 1.0,
    "thumbnail_preview": True,
}


@dataclass
class ObsConnection:
    client: Any
    host: str
    port: int
    scene_name: str


@dataclass
class CaptureRecord:
    filename: str
    path: Path
    timestamp: str
    side: str
    card_number: int
    obs_scene: str


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
    if not isinstance(settings.get("crop_rectangle"), dict):
        settings["crop_rectangle"] = dict(DEFAULT_CAPTURE_SETTINGS["crop_rectangle"])
    return settings


def save_capture_settings(root: Path, settings: dict[str, Any]) -> None:
    path = capture_settings_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")


def timestamp_for_folder() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H%M%S")


def iso_now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def safe_name(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in ("-", "_", " ") else "_" for ch in value.strip())
    return "_".join(cleaned.split())[:80]


def make_session_dir(root: Path, batch_name: str) -> Path:
    base = root / "Putnam_OS" / "Incoming Files" / "Capture_Sessions"
    base.mkdir(parents=True, exist_ok=True)

    stamp = timestamp_for_folder()
    suffix_name = safe_name(batch_name)
    folder_name = f"{stamp}_{suffix_name}" if suffix_name else stamp
    candidate = base / folder_name
    suffix = 1
    while candidate.exists():
        candidate = base / f"{folder_name}_{suffix:02d}"
        suffix += 1

    images_dir = candidate / "images"
    images_dir.mkdir(parents=True, exist_ok=False)
    return candidate


def write_session_json(path: Path, data: dict[str, Any]) -> None:
    temp_path = path.with_suffix(".json.tmp")
    temp_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    temp_path.replace(path)


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
    parser.add_argument("--mode", choices=sorted(VALID_MODES), default=None)
    parser.add_argument("--batch-name", default=None)
    parser.add_argument("--auto-capture", action="store_true", help="Start with auto-capture enabled.")
    parser.add_argument("--no-preview", action="store_true", help="Disable last-capture thumbnail preview.")
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


def choose_capture_mode(default_mode: str | None = None) -> str:
    if default_mode in VALID_MODES:
        return default_mode

    print("")
    print("Capture mode:")
    print("  1. Front only")
    print("  2. Back only")
    print("  3. Front/back pairs")
    selected = input("Choose mode [3]: ").strip().lower()
    if selected in ("1", "front", "f"):
        return "front"
    if selected in ("2", "back", "b"):
        return "back"
    return "pairs"


def prompt_batch_name(default_name: str | None = None) -> str:
    if default_name:
        return default_name
    value = input("Batch/session name [Putnam Capture]: ").strip()
    return value or "Putnam Capture"


class CaptureState:
    def __init__(self, mode: str):
        self.mode = mode
        self.card_number = 1
        self.next_side = "front" if mode in ("front", "pairs") else "back"
        self.records: list[CaptureRecord] = []

    @property
    def image_count(self) -> int:
        return len(self.records)

    @property
    def front_count(self) -> int:
        return sum(1 for r in self.records if r.side == "front")

    @property
    def back_count(self) -> int:
        return sum(1 for r in self.records if r.side == "back")

    def next_filename(self) -> str:
        return f"{self.card_number:06d}_{self.next_side}.jpg"

    def advance(self) -> None:
        if self.mode == "front":
            self.card_number += 1
            self.next_side = "front"
        elif self.mode == "back":
            self.card_number += 1
            self.next_side = "back"
        elif self.next_side == "front":
            self.next_side = "back"
        else:
            self.card_number += 1
            self.next_side = "front"

    def rewind_to_next_expected(self) -> None:
        if not self.records:
            self.card_number = 1
            self.next_side = "front" if self.mode in ("front", "pairs") else "back"
            return
        last = self.records[-1]
        self.card_number = last.card_number
        self.next_side = last.side
        self.advance()

    def add_record(self, record: CaptureRecord) -> None:
        self.records.append(record)
        self.advance()

    def undo_last(self) -> CaptureRecord | None:
        record = self.records.pop() if self.records else None
        if record:
            self.card_number = record.card_number
            self.next_side = record.side
        return record


class LastCapturePreview:
    def __init__(self, enabled: bool):
        self.enabled = enabled
        self.root = None
        self.label = None
        self.photo = None
        if not enabled:
            return
        try:
            import tkinter as tk

            self.tk = tk
            self.root = tk.Tk()
            self.root.title("Putnam Capture - Last Capture")
            self.root.geometry("360x280")
            self.label = tk.Label(self.root, text="No capture yet")
            self.label.pack(expand=True, fill="both")
            self.root.update()
        except Exception as exc:
            print(f"Thumbnail preview unavailable: {exc}")
            self.enabled = False
            self.root = None
            self.label = None

    def update(self, image_path: Path) -> None:
        if not self.enabled or self.root is None or self.label is None:
            return
        try:
            from PIL import Image, ImageTk

            image = Image.open(image_path)
            image.thumbnail((340, 240))
            self.photo = ImageTk.PhotoImage(image)
            self.label.configure(image=self.photo, text="")
            self.root.update()
        except Exception as exc:
            print(f"Thumbnail preview update failed: {exc}")

    def pump(self) -> None:
        if self.enabled and self.root is not None:
            try:
                self.root.update()
            except Exception:
                self.enabled = False

    def close(self) -> None:
        if self.root is not None:
            try:
                self.root.destroy()
            except Exception:
                pass


def frame_signature(image_bytes: bytes) -> Any:
    try:
        from PIL import Image
        import io

        image = Image.open(io.BytesIO(image_bytes)).convert("L").resize((16, 9))
        return tuple(image.getdata())
    except Exception:
        return None


def signature_distance(a: Any, b: Any) -> float:
    if a is None or b is None or len(a) != len(b):
        return 999999.0
    return sum(abs(int(x) - int(y)) for x, y in zip(a, b)) / max(1, len(a))


def write_image_file(image_path: Path, image_bytes: bytes, settings: dict[str, Any]) -> str:
    save_full = bool(settings.get("save_full_frame", True))
    save_cropped = bool(settings.get("save_cropped_frame", False))
    if not save_full and save_cropped:
        image_path.write_bytes(image_bytes)
        return "captured_full_frame_crop_not_implemented"
    if save_cropped:
        image_path.write_bytes(image_bytes)
        return "captured_full_frame_crop_not_implemented"
    image_path.write_bytes(image_bytes)
    return "captured"


def append_log_row(writer: csv.DictWriter, log_file, record: CaptureRecord, status: str) -> None:
    writer.writerow(
        {
            "filename": record.filename,
            "timestamp": record.timestamp,
            "side": record.side,
            "card_number": record.card_number,
            "obs_scene": record.obs_scene,
            "status": status,
        }
    )
    log_file.flush()


def update_session_data(session_data: dict[str, Any], state: CaptureState) -> None:
    session_data["image_count"] = state.image_count
    session_data["front_count"] = state.front_count
    session_data["back_count"] = state.back_count


def print_status(state: CaptureState, images_dir: Path, auto_capture_enabled: bool) -> None:
    auto_text = "ON" if auto_capture_enabled else "OFF"
    print(
        f"Count: {state.image_count} | Front: {state.front_count} | Back: {state.back_count} | "
        f"Auto: {auto_text} | Next: {state.next_filename()}"
    )
    print(f"Save folder: {images_dir}")


def read_keyboard_key() -> str | None:
    if os.name != "nt":
        return None
    import msvcrt

    if not msvcrt.kbhit():
        return None
    key = msvcrt.getch()
    if key in (b"\x00", b"\xe0"):
        msvcrt.getch()
        return None
    if key == b"\x1b":
        return "esc"
    try:
        return key.decode("utf-8").lower()
    except UnicodeDecodeError:
        return None


def capture_one(
    obs_connection: ObsConnection,
    state: CaptureState,
    images_dir: Path,
    settings: dict[str, Any],
    jpeg_quality: int,
    writer: csv.DictWriter,
    log_file,
    session_json: Path,
    session_data: dict[str, Any],
    preview: LastCapturePreview,
    image_bytes: bytes | None = None,
) -> CaptureRecord:
    filename = state.next_filename()
    image_path = images_dir / filename
    if image_path.exists():
        raise RuntimeError(f"Next capture file already exists: {image_path}")
    if image_bytes is None:
        image_bytes = capture_scene_jpeg(obs_connection.client, obs_connection.scene_name, jpeg_quality)
    status = write_image_file(image_path, image_bytes, settings)
    record = CaptureRecord(
        filename=filename,
        path=image_path,
        timestamp=iso_now(),
        side=state.next_side,
        card_number=state.card_number,
        obs_scene=obs_connection.scene_name,
    )
    state.add_record(record)
    append_log_row(writer, log_file, record, status)
    update_session_data(session_data, state)
    write_session_json(session_json, session_data)
    print(f"Captured {record.filename}")
    preview.update(image_path)
    print_status(state, images_dir, bool(settings.get("auto_capture_enabled", False)))
    return record


def undo_last_capture(
    state: CaptureState,
    session_dir: Path,
    writer: csv.DictWriter,
    log_file,
    session_json: Path,
    session_data: dict[str, Any],
    images_dir: Path,
) -> None:
    record = state.undo_last()
    if not record:
        print("Nothing to undo.")
        return
    undone_dir = session_dir / "undone"
    undone_dir.mkdir(exist_ok=True)
    if record.path.exists():
        destination = undone_dir / record.filename
        if destination.exists():
            destination = undone_dir / f"{record.path.stem}_{now_suffix()}{record.path.suffix}"
        shutil.move(str(record.path), str(destination))
    append_log_row(writer, log_file, record, "undone")
    update_session_data(session_data, state)
    write_session_json(session_json, session_data)
    print(f"Undid {record.filename}")
    print_status(state, images_dir, bool(session_data.get("auto_capture_enabled", False)))


def now_suffix() -> str:
    return datetime.now().strftime("%H%M%S")


def main() -> int:
    root = resolve_root()
    settings = load_capture_settings(root)
    args = parse_args(settings)
    args.jpeg_quality = max(1, min(100, args.jpeg_quality))
    settings["auto_capture_enabled"] = bool(settings.get("auto_capture_enabled", False) or args.auto_capture)
    save_capture_settings(root, settings)

    batch_name = prompt_batch_name(args.batch_name)
    mode = choose_capture_mode(args.mode)
    obs_connection = connect_to_obs(args)

    session_dir = make_session_dir(root, batch_name)
    images_dir = session_dir / "images"
    session_json = session_dir / "session.json"
    capture_log = session_dir / "capture_log.csv"
    start_time = iso_now()
    state = CaptureState(mode)

    session_data: dict[str, Any] = {
        "app": APP_NAME,
        "start_time": start_time,
        "end_time": None,
        "batch_name": batch_name,
        "mode": mode,
        "obs_scene": obs_connection.scene_name,
        "output_folder": str(images_dir),
        "image_count": 0,
        "front_count": 0,
        "back_count": 0,
        "capture_method": CAPTURE_METHOD,
        "save_full_frame": bool(settings.get("save_full_frame", True)),
        "save_cropped_frame": bool(settings.get("save_cropped_frame", False)),
        "crop_rectangle": settings.get("crop_rectangle", {}),
        "auto_capture_enabled": bool(settings.get("auto_capture_enabled", False)),
    }
    write_session_json(session_json, session_data)

    print("")
    print("OBS scene capture ready.")
    print(f"Batch: {batch_name}")
    print(f"Mode: {VALID_MODES[mode]}")
    print(f"Save folder: {images_dir}")
    print("Controls: SPACE = capture JPEG, U = undo last, A = toggle auto-capture, Q or ESC = exit")
    print("")

    preview = LastCapturePreview(bool(settings.get("thumbnail_preview", True)) and not args.no_preview)
    last_auto_time = 0.0
    last_seen_signature = None
    stable_since = None
    last_auto_capture_signature = None
    auto_capture_enabled = bool(settings.get("auto_capture_enabled", False))
    print_status(state, images_dir, auto_capture_enabled)

    with capture_log.open("w", newline="", encoding="utf-8") as log_file:
        writer = csv.DictWriter(
            log_file,
            fieldnames=["filename", "timestamp", "side", "card_number", "obs_scene", "status"],
        )
        writer.writeheader()

        try:
            while True:
                preview.pump()
                key = read_keyboard_key()
                if key in ("q", "esc"):
                    break
                if key == "u":
                    undo_last_capture(state, session_dir, writer, log_file, session_json, session_data, images_dir)
                    continue
                if key == "a":
                    auto_capture_enabled = not auto_capture_enabled
                    settings["auto_capture_enabled"] = auto_capture_enabled
                    session_data["auto_capture_enabled"] = auto_capture_enabled
                    write_session_json(session_json, session_data)
                    print(f"Auto-capture {'ON' if auto_capture_enabled else 'OFF'}")
                    print_status(state, images_dir, auto_capture_enabled)
                    continue
                if key == " ":
                    try:
                        record = capture_one(
                            obs_connection,
                            state,
                            images_dir,
                            settings,
                            args.jpeg_quality,
                            writer,
                            log_file,
                            session_json,
                            session_data,
                            preview,
                        )
                        last_auto_time = time.monotonic()
                        last_auto_capture_signature = frame_signature(record.path.read_bytes())
                    except Exception as exc:
                        print(f"Capture failed: {exc}")
                    continue

                if auto_capture_enabled:
                    now = time.monotonic()
                    min_delay = float(settings.get("auto_capture_min_delay_seconds", 2.0))
                    stable_seconds = float(settings.get("auto_capture_stable_seconds", 1.0))
                    if now - last_auto_time >= min_delay:
                        try:
                            image_bytes = capture_scene_jpeg(obs_connection.client, obs_connection.scene_name, args.jpeg_quality)
                            sig = frame_signature(image_bytes)
                            if sig is None:
                                time.sleep(0.1)
                                continue
                            if last_seen_signature is None or signature_distance(sig, last_seen_signature) > 2.0:
                                last_seen_signature = sig
                                stable_since = now
                            elif stable_since is not None and now - stable_since >= stable_seconds:
                                if last_auto_capture_signature is None or signature_distance(sig, last_auto_capture_signature) > 2.0:
                                    capture_one(
                                        obs_connection,
                                        state,
                                        images_dir,
                                        settings,
                                        args.jpeg_quality,
                                        writer,
                                        log_file,
                                        session_json,
                                        session_data,
                                        preview,
                                        image_bytes=image_bytes,
                                    )
                                    last_auto_time = now
                                    last_auto_capture_signature = sig
                        except Exception as exc:
                            print(f"Auto-capture check failed: {exc}")
                            auto_capture_enabled = False
                            settings["auto_capture_enabled"] = False
                            session_data["auto_capture_enabled"] = False
                            write_session_json(session_json, session_data)

                time.sleep(0.05)
        finally:
            preview.close()
            session_data["end_time"] = iso_now()
            update_session_data(session_data, state)
            write_session_json(session_json, session_data)
            save_capture_settings(root, settings)
            print("")
            print(f"Output folder: {images_dir}")
            try:
                os.startfile(str(session_dir))
            except Exception:
                pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
