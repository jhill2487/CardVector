from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from typing import Any, Mapping


AUTO_CAPTURE_DEFAULTS = {
    "auto_capture_enabled": False,
    "stability_delay_seconds": 1.0,
    "duplicate_lockout_seconds": 2.0,
    "frame_poll_interval_ms": 200,
    "sensitivity": "Medium",
}

AUTO_CAPTURE_THRESHOLDS = {
    "Low": {"present": 0.14, "empty": 0.07, "stable": 0.026, "changed": 0.085},
    "Medium": {"present": 0.10, "empty": 0.05, "stable": 0.018, "changed": 0.065},
    "High": {"present": 0.07, "empty": 0.035, "stable": 0.012, "changed": 0.045},
}


def normalize_auto_capture_settings(settings: Mapping[str, Any] | None) -> dict[str, Any]:
    normalized = dict(AUTO_CAPTURE_DEFAULTS)
    normalized.update(settings or {})
    normalized["auto_capture_enabled"] = bool(normalized.get("auto_capture_enabled"))
    try:
        normalized["stability_delay_seconds"] = max(
            0.25,
            min(5.0, float(normalized.get("stability_delay_seconds", 1.0))),
        )
    except Exception:
        normalized["stability_delay_seconds"] = AUTO_CAPTURE_DEFAULTS["stability_delay_seconds"]
    try:
        normalized["duplicate_lockout_seconds"] = max(
            0.5,
            min(10.0, float(normalized.get("duplicate_lockout_seconds", 2.0))),
        )
    except Exception:
        normalized["duplicate_lockout_seconds"] = AUTO_CAPTURE_DEFAULTS["duplicate_lockout_seconds"]
    try:
        normalized["frame_poll_interval_ms"] = max(
            100,
            min(2000, int(float(normalized.get("frame_poll_interval_ms", 200)))),
        )
    except Exception:
        normalized["frame_poll_interval_ms"] = AUTO_CAPTURE_DEFAULTS["frame_poll_interval_ms"]
    sensitivity = str(normalized.get("sensitivity", "Medium")).title()
    normalized["sensitivity"] = (
        sensitivity if sensitivity in AUTO_CAPTURE_THRESHOLDS else "Medium"
    )
    return normalized


def load_auto_capture_settings(path: Path) -> dict[str, Any]:
    settings = dict(AUTO_CAPTURE_DEFAULTS)
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
            if isinstance(data, dict):
                settings.update(
                    {
                        key: value
                        for key, value in data.items()
                        if key in settings
                    }
                )
        except Exception:
            pass
    return normalize_auto_capture_settings(settings)


def save_auto_capture_settings(path: Path, settings: Mapping[str, Any] | None) -> dict[str, Any]:
    normalized = normalize_auto_capture_settings(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(normalized, indent=2) + "\n", encoding="utf-8")
    return normalized


def capture_frame_signature(
    image_bytes: bytes,
    size: tuple[int, int] = (48, 48),
    *,
    error_factory: type[Exception] = RuntimeError,
) -> tuple[int, ...]:
    try:
        from PIL import Image, ImageOps

        with Image.open(BytesIO(image_bytes)) as source:
            image = ImageOps.exif_transpose(source).convert("L")
        image = image.resize(size)
        return tuple(image.getdata())
    except Exception as exc:
        raise error_factory(f"Could not analyze OBS frame: {exc}") from exc


def signature_difference(sig_a: Any, sig_b: Any) -> float:
    if not sig_a or not sig_b or len(sig_a) != len(sig_b):
        return 1.0
    total = sum(abs(int(a) - int(b)) for a, b in zip(sig_a, sig_b))
    return total / (len(sig_a) * 255)


def auto_capture_thresholds(settings: Mapping[str, Any]) -> dict[str, float]:
    sensitivity = str(settings.get("sensitivity", "Medium")).title()
    return AUTO_CAPTURE_THRESHOLDS.get(
        sensitivity,
        AUTO_CAPTURE_THRESHOLDS["Medium"],
    )


__all__ = [
    "AUTO_CAPTURE_DEFAULTS",
    "AUTO_CAPTURE_THRESHOLDS",
    "auto_capture_thresholds",
    "capture_frame_signature",
    "load_auto_capture_settings",
    "normalize_auto_capture_settings",
    "save_auto_capture_settings",
    "signature_difference",
]
