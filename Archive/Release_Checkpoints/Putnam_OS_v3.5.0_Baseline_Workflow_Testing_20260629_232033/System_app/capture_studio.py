from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


def _bootstrap_repo_import_path() -> None:
    current = Path(__file__).resolve()
    for candidate in [current.parent, *current.parents]:
        if (
            (candidate / ".putnam_root").exists()
            or ((candidate / "AGENTS.md").exists() and (candidate / "Docs" / "AGENTS.md").exists())
        ):
            if str(candidate) not in sys.path:
                sys.path.insert(0, str(candidate))
            return


_bootstrap_repo_import_path()

from Platform.putnam_paths import PUTNAM_PLATFORM_DIR, ROOT


CAPTURE_ROOT = ROOT / "Capture"
SETTINGS_PATH = PUTNAM_PLATFORM_DIR / "capture" / "capture_settings.json"
DEFAULT_OBS_HOST = "localhost"
DEFAULT_OBS_PORT = 4455
DEFAULT_OBS_SCENE = "03 - Card Capture"
DEFAULT_JPEG_QUALITY = 95

# Tiny valid JPEG used only for explicit test/placeholder mode. Real Capture
# Studio work should come from OBS WebSocket screenshots.
PLACEHOLDER_JPEG = base64.b64decode(
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////"
    "////////////////////////////////////////////////////2wBDAf//////////////////////////////////////////////////////////////"
    "////////////////////////////////////////wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAX/xAAUEAEAAAAAAAAA"
    "AAAAAAAAAAAA/9oADAMBAAIQAxAAAAF//8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABBQJ//8QAFBEBAAAAAAAAAAAAAAAAAAAAAP/a"
    "AAgBAwEBPwF//8QAFBEBAAAAAAAAAAAAAAAAAAAAAP/aAAgBAgEBPwF//8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQAGPwJ//8QAFBAB"
    "AAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPyF//9k="
)


class CaptureStudioError(RuntimeError):
    pass


@dataclass
class CaptureResult:
    path: Path
    side: str
    card_number: int
    capture_mode: str


def _response_value(response: Any, *names: str, default: Any = None) -> Any:
    for name in names:
        if hasattr(response, name):
            return getattr(response, name)
    if isinstance(response, dict):
        for name in names:
            if name in response:
                return response[name]
    return default


def _decode_image_data(image_data: str) -> bytes:
    if "," in image_data and image_data.lstrip().startswith("data:"):
        image_data = image_data.split(",", 1)[1]
    return base64.b64decode(image_data)


def load_capture_settings() -> dict[str, Any]:
    defaults = {
        "obs_host": DEFAULT_OBS_HOST,
        "obs_port": DEFAULT_OBS_PORT,
        "obs_scene": DEFAULT_OBS_SCENE,
        "jpeg_quality": DEFAULT_JPEG_QUALITY,
    }
    if not SETTINGS_PATH.exists():
        return defaults
    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8-sig"))
    except Exception:
        return defaults
    defaults.update({key: value for key, value in data.items() if value not in (None, "")})
    return defaults


def _today_folder_name(now: datetime | None = None) -> str:
    return (now or datetime.now()).strftime("%m.%d.%y")


def next_session_folder(capture_root: Path = CAPTURE_ROOT, now: datetime | None = None) -> Path:
    capture_root.mkdir(parents=True, exist_ok=True)
    base_name = _today_folder_name(now)
    candidate = capture_root / base_name
    suffix = 0
    while candidate.exists():
        suffix += 1
        candidate = capture_root / f"{base_name}.{suffix}"
    return candidate


def _iso_now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class CaptureStudioService:
    def __init__(self, capture_root: Path = CAPTURE_ROOT, allow_placeholder: bool | None = None):
        self.capture_root = Path(capture_root)
        self.allow_placeholder = (
            os.environ.get("PUTNAM_CAPTURE_PLACEHOLDER", "").strip() == "1"
            if allow_placeholder is None
            else allow_placeholder
        )

    def start_session(self) -> dict[str, Any]:
        session_dir = next_session_folder(self.capture_root)
        session_dir.mkdir(parents=False, exist_ok=False)
        session = {
            "started_at": _iso_now(),
            "finished_at": None,
            "folder": str(session_dir),
            "capture_mode": "OBS WebSocket",
            "current_card_number": 1,
            "photos_captured": 0,
            "records": [],
        }
        self._save_session(session)
        return session

    def capture(self, session: dict[str, Any], side: str) -> CaptureResult:
        if side not in {"front", "back"}:
            raise CaptureStudioError(f"Unsupported capture side: {side}")
        session_dir = Path(session["folder"])
        card_number = int(session.get("current_card_number") or 1)
        image_path = session_dir / f"{card_number:06d}_{side}.jpg"
        if image_path.exists():
            raise CaptureStudioError(f"Capture already exists: {image_path.name}")

        capture_mode = "OBS WebSocket"
        try:
            image_bytes = self.capture_obs_jpeg()
        except Exception as exc:
            if not self.allow_placeholder:
                raise CaptureStudioError(
                    "OBS capture is unavailable. Start OBS, enable OBS WebSocket, "
                    "then use OBS Status before capturing. No photo was saved."
                ) from exc
            image_bytes = PLACEHOLDER_JPEG
            capture_mode = "Placeholder test mode"

        image_path.write_bytes(image_bytes)
        record = {
            "filename": image_path.name,
            "path": str(image_path),
            "side": side,
            "card_number": card_number,
            "captured_at": _iso_now(),
            "capture_mode": capture_mode,
        }
        session.setdefault("records", []).append(record)
        session["photos_captured"] = len(session["records"])
        session["capture_mode"] = capture_mode
        if side == "back":
            session["current_card_number"] = card_number + 1
        else:
            session["current_card_number"] = card_number
        self._save_session(session)
        return CaptureResult(image_path, side, card_number, capture_mode)

    def retake_last(self, session: dict[str, Any]) -> Path | None:
        records = session.get("records") or []
        if not records:
            return None
        record = records.pop()
        source = Path(record["path"])
        session_dir = Path(session["folder"])
        retakes_dir = session_dir / "_retakes"
        retakes_dir.mkdir(exist_ok=True)
        destination = retakes_dir / source.name
        if destination.exists():
            destination = retakes_dir / f"{source.stem}_{datetime.now().strftime('%H%M%S')}{source.suffix}"
        if source.exists():
            shutil.move(str(source), str(destination))
        session["photos_captured"] = len(records)
        session["current_card_number"] = int(record["card_number"])
        session["capture_mode"] = record.get("capture_mode", session.get("capture_mode", "OBS WebSocket"))
        self._save_session(session)
        return destination

    def finish_session(self, session: dict[str, Any]) -> None:
        session["finished_at"] = _iso_now()
        self._save_session(session)

    def obs_status(self) -> str:
        settings = load_capture_settings()
        host = str(settings.get("obs_host", DEFAULT_OBS_HOST))
        port = int(settings.get("obs_port", DEFAULT_OBS_PORT))
        scene = str(settings.get("obs_scene", DEFAULT_OBS_SCENE))
        try:
            obs = self._obs_module()
            client = obs.ReqClient(
                host=host,
                port=port,
                password=os.environ.get("PUTNAM_OBS_PASSWORD", ""),
                timeout=3,
            )
            current = client.get_current_program_scene()
            current_scene = _response_value(current, "currentProgramSceneName", "current_program_scene_name", default="")
            return f"OBS connected at {host}:{port}. Current scene: {current_scene or scene}"
        except Exception as exc:
            return f"OBS unavailable at {host}:{port}. {exc}"

    def launch_obs(self) -> Path:
        candidates = []
        for env_name in ("ProgramFiles", "ProgramFiles(x86)"):
            base = os.environ.get(env_name)
            if base:
                candidates.append(Path(base) / "obs-studio" / "bin" / "64bit" / "obs64.exe")
        candidates.append(Path("obs64.exe"))
        for candidate in candidates:
            try:
                if candidate.name == "obs64.exe" and not candidate.is_absolute():
                    subprocess.Popen([str(candidate)])
                    return candidate
                if candidate.exists():
                    subprocess.Popen([str(candidate)], cwd=str(candidate.parent))
                    return candidate
            except Exception:
                continue
        raise CaptureStudioError("OBS executable was not found. Open OBS manually, then use OBS Status.")

    def capture_obs_jpeg(self) -> bytes:
        settings = load_capture_settings()
        obs = self._obs_module()
        client = obs.ReqClient(
            host=str(settings.get("obs_host", DEFAULT_OBS_HOST)),
            port=int(settings.get("obs_port", DEFAULT_OBS_PORT)),
            password=os.environ.get("PUTNAM_OBS_PASSWORD", ""),
            timeout=5,
        )
        scene_name = str(settings.get("obs_scene", DEFAULT_OBS_SCENE))
        jpeg_quality = int(settings.get("jpeg_quality", DEFAULT_JPEG_QUALITY))
        try:
            response = client.get_source_screenshot(
                source_name=scene_name,
                image_format="jpg",
                image_compression_quality=max(1, min(100, jpeg_quality)),
            )
        except TypeError:
            response = client.get_source_screenshot(
                sourceName=scene_name,
                imageFormat="jpg",
                imageCompressionQuality=max(1, min(100, jpeg_quality)),
            )
        image_data = _response_value(response, "imageData", "image_data")
        if not image_data:
            raise CaptureStudioError("OBS returned an empty screenshot response.")
        return _decode_image_data(str(image_data))

    def _obs_module(self) -> Any:
        try:
            import obsws_python as obs  # type: ignore
        except ImportError as exc:
            raise CaptureStudioError("obsws-python is not installed.") from exc
        return obs

    def _save_session(self, session: dict[str, Any]) -> None:
        session_dir = Path(session["folder"])
        session_dir.mkdir(parents=True, exist_ok=True)
        temp = session_dir / "capture_session.json.tmp"
        final = session_dir / "capture_session.json"
        temp.write_text(json.dumps(session, indent=2) + "\n", encoding="utf-8")
        temp.replace(final)
