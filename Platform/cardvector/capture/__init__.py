"""Canonical Capture APIs.

The package owns capture contracts and rules while compatibility
implementations continue to perform the proven OBS and Supabase operations.
"""

from .auto_capture import (
    AUTO_CAPTURE_DEFAULTS,
    AUTO_CAPTURE_THRESHOLDS,
    auto_capture_thresholds,
    capture_frame_signature,
    load_auto_capture_settings,
    normalize_auto_capture_settings,
    save_auto_capture_settings,
    signature_difference,
)
from .pairing import (
    capture_cards_completed,
    capture_pair_rows,
    capture_pair_status,
    load_capture_session_file,
    resolve_capture_record_image,
)
from .service import (
    CaptureService,
    DesktopCaptureFactory,
    DesktopCaptureOperations,
    MobileCaptureOperations,
)

__all__ = [
    "AUTO_CAPTURE_DEFAULTS",
    "AUTO_CAPTURE_THRESHOLDS",
    "CaptureService",
    "DesktopCaptureFactory",
    "DesktopCaptureOperations",
    "MobileCaptureOperations",
    "auto_capture_thresholds",
    "capture_cards_completed",
    "capture_frame_signature",
    "capture_pair_rows",
    "capture_pair_status",
    "load_auto_capture_settings",
    "load_capture_session_file",
    "normalize_auto_capture_settings",
    "resolve_capture_record_image",
    "save_auto_capture_settings",
    "signature_difference",
]
