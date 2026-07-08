from __future__ import annotations

import tempfile
from io import BytesIO
from pathlib import Path

from PIL import Image

from capture_studio import CaptureStudioService
from putnam_os import (
    capture_frame_signature,
    capture_pair_rows,
    normalize_auto_capture_settings,
    signature_difference,
)


def jpeg_bytes(color: str) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (360, 520), color).save(buffer, format="JPEG")
    return buffer.getvalue()


def run():
    root = Path(tempfile.mkdtemp(prefix="cardvector_auto_capture_"))
    service = CaptureStudioService(capture_root=root, allow_placeholder=True)
    session = service.start_session()

    front = jpeg_bytes("red")
    back = jpeg_bytes("blue")
    front_result = service.capture_bytes(session, "front", front, capture_mode="OBS Auto Capture")
    back_result = service.capture_bytes(session, "back", back, capture_mode="OBS Auto Capture")

    assert front_result.path.name == "000001_front.jpg"
    assert back_result.path.name == "000001_back.jpg"
    assert Path(session["folder"], "000001_front.jpg").exists()
    assert Path(session["folder"], "000001_back.jpg").exists()
    assert session["current_card_number"] == 2

    pairs = capture_pair_rows(session["folder"])
    assert len(pairs) == 1
    assert pairs[0]["status"] == "Complete"

    front_sig = capture_frame_signature(front)
    front_sig_again = capture_frame_signature(front)
    back_sig = capture_frame_signature(back)
    assert signature_difference(front_sig, front_sig_again) == 0
    assert signature_difference(front_sig, back_sig) > 0.05

    settings = normalize_auto_capture_settings(
        {
            "auto_capture_enabled": True,
            "stability_delay_seconds": "1.25",
            "duplicate_lockout_seconds": "2.5",
            "frame_poll_interval_ms": "250",
            "sensitivity": "High",
        }
    )
    assert settings["auto_capture_enabled"] is True
    assert settings["stability_delay_seconds"] == 1.25
    assert settings["duplicate_lockout_seconds"] == 2.5
    assert settings["frame_poll_interval_ms"] == 250
    assert settings["sensitivity"] == "High"

    print(f"CardVector Capture Studio v2.1 auto-capture smoke test passed: {root}")


if __name__ == "__main__":
    run()
