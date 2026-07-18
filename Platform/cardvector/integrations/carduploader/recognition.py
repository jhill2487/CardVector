from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Mapping


@dataclass(frozen=True)
class RecognitionHandoff:
    provider: str
    status: str
    capture_folder: str
    capture_session_id: str
    provider_url: str
    prepared_at: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CardUploaderRecognitionAdapter:
    """Describes the handoff to CardUploader without performing recognition."""

    def __init__(self, url_loader: Callable[[], str] | None = None) -> None:
        self._url_loader = url_loader or (lambda: "")

    def prepare_handoff(
        self,
        *,
        capture_folder: str | Path = "",
        capture_session_id: str = "",
        metadata: Mapping[str, Any] | None = None,
    ) -> RecognitionHandoff:
        return RecognitionHandoff(
            provider="CardUploader",
            status="Ready for CardUploader",
            capture_folder=str(capture_folder or ""),
            capture_session_id=str(capture_session_id or ""),
            provider_url=str(self._url_loader() or "").strip(),
            prepared_at=datetime.now().isoformat(timespec="seconds"),
            metadata=dict(metadata or {}),
        )


__all__ = ["CardUploaderRecognitionAdapter", "RecognitionHandoff"]
