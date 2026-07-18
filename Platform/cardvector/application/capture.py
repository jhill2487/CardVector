from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Protocol

from .runtime import ExecutionContext


class CaptureOperations(Protocol):
    allow_placeholder: bool
    obs_manager: Any
    current_workstation: str

    def start_session(self) -> dict[str, Any]: ...

    def capture(self, session: dict[str, Any], side: str) -> Any: ...

    def capture_bytes(
        self,
        session: dict[str, Any],
        side: str,
        image_bytes: bytes,
        capture_mode: str = "OBS WebSocket",
    ) -> Any: ...

    def next_capture_side(self, session: dict[str, Any]) -> str: ...

    def retake_last(self, session: dict[str, Any]) -> Path | None: ...

    def finish_session(self, session: dict[str, Any]) -> None: ...

    def obs_status(self) -> str: ...

    def launch_obs(self) -> Path: ...

    def capture_obs_jpeg(self) -> bytes: ...

    def save_session(self, session: dict[str, Any]) -> None: ...

    def create_desktop_service(self, capture_root: Path) -> Any: ...

    def environment_ready(self) -> tuple[bool, str]: ...

    def list_queue(
        self,
        include_diagnostics: bool = True,
        limit: int = 100,
    ) -> list[dict[str, Any]]: ...

    def sync_locations(self, strict: bool = True) -> dict[str, Any]: ...

    def process_next_pending(self) -> dict[str, Any] | None: ...

    def complete(self, session_id: str) -> dict[str, Any]: ...

    def fail(self, session_id: str, message: str) -> dict[str, Any]: ...

    def retry_failed(self, session_id: str) -> dict[str, Any]: ...

    def local_folder(self, session_id: str) -> Path | None: ...


class RecognitionHandoffOperations(Protocol):
    def prepare_handoff(
        self,
        *,
        capture_folder: str | Path = "",
        capture_session_id: str = "",
        metadata: Mapping[str, Any] | None = None,
    ) -> Any: ...


class CaptureApplication:
    """Coordinates Capture operations and the external recognition handoff."""

    def __init__(
        self,
        capture: CaptureOperations,
        recognition: RecognitionHandoffOperations,
    ) -> None:
        self._capture = capture
        self._recognition = recognition

    @property
    def allow_placeholder(self) -> bool:
        return self._capture.allow_placeholder

    @property
    def obs_manager(self) -> Any:
        return self._capture.obs_manager

    @property
    def current_workstation(self) -> str:
        return self._capture.current_workstation

    def start_session(
        self,
        context: ExecutionContext | None = None,
    ) -> dict[str, Any]:
        execution = context or ExecutionContext.create()
        execution.cancellation.raise_if_cancelled()
        execution.report("capture_session_starting")
        session = self._capture.start_session()
        execution.publish(
            "capture.session_started",
            folder=str(session.get("folder") or ""),
        )
        return session

    def capture(
        self,
        session: dict[str, Any],
        side: str,
        context: ExecutionContext | None = None,
    ) -> Any:
        execution = context or ExecutionContext.create()
        execution.cancellation.raise_if_cancelled()
        execution.report("capture_image", message=str(side))
        result = self._capture.capture(session, side)
        execution.publish(
            "capture.image_captured",
            path=str(getattr(result, "path", "")),
            side=str(getattr(result, "side", side)),
        )
        return result

    def capture_bytes(
        self,
        session: dict[str, Any],
        side: str,
        image_bytes: bytes,
        capture_mode: str = "OBS WebSocket",
        context: ExecutionContext | None = None,
    ) -> Any:
        execution = context or ExecutionContext.create()
        execution.cancellation.raise_if_cancelled()
        result = self._capture.capture_bytes(
            session,
            side,
            image_bytes,
            capture_mode=capture_mode,
        )
        execution.publish(
            "capture.image_captured",
            path=str(getattr(result, "path", "")),
            side=str(getattr(result, "side", side)),
        )
        return result

    def next_capture_side(self, session: dict[str, Any]) -> str:
        return self._capture.next_capture_side(session)

    def retake_last(self, session: dict[str, Any]) -> Path | None:
        return self._capture.retake_last(session)

    def finish_session(
        self,
        session: dict[str, Any],
        context: ExecutionContext | None = None,
    ) -> None:
        self._capture.finish_session(session)
        execution = context or ExecutionContext.create()
        execution.publish(
            "capture.session_finished",
            folder=str(session.get("folder") or ""),
        )

    def obs_status(self) -> str:
        return self._capture.obs_status()

    def launch_obs(self) -> Path:
        return self._capture.launch_obs()

    def capture_obs_jpeg(self) -> bytes:
        return self._capture.capture_obs_jpeg()

    def save_session(self, session: dict[str, Any]) -> None:
        self._capture.save_session(session)

    def _save_session(self, session: dict[str, Any]) -> None:
        self.save_session(session)

    def create_desktop_service(self, capture_root: Path) -> Any:
        return self._capture.create_desktop_service(capture_root)

    def environment_ready(self) -> tuple[bool, str]:
        return self._capture.environment_ready()

    def list_queue(
        self,
        include_diagnostics: bool = True,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        return self._capture.list_queue(
            include_diagnostics=include_diagnostics,
            limit=limit,
        )

    def sync_locations(self, strict: bool = True) -> dict[str, Any]:
        return self._capture.sync_locations(strict=strict)

    def process_next_pending(
        self,
        context: ExecutionContext | None = None,
    ) -> dict[str, Any] | None:
        execution = context or ExecutionContext.create()
        execution.cancellation.raise_if_cancelled()
        execution.report("mobile_capture_queue_check")
        result = self._capture.process_next_pending()
        if result:
            execution.publish(
                "capture.mobile_session_staged",
                capture_folder=str(result.get("capture_folder") or ""),
            )
        return result

    def complete(self, session_id: str) -> dict[str, Any]:
        return self._capture.complete(session_id)

    def fail(self, session_id: str, message: str) -> dict[str, Any]:
        return self._capture.fail(session_id, message)

    def retry_failed(self, session_id: str) -> dict[str, Any]:
        return self._capture.retry_failed(session_id)

    def local_folder(self, session_id: str) -> Path | None:
        return self._capture.local_folder(session_id)

    def prepare_recognition_handoff(
        self,
        *,
        capture_folder: str | Path = "",
        capture_session_id: str = "",
        metadata: Mapping[str, Any] | None = None,
    ) -> Any:
        return self._recognition.prepare_handoff(
            capture_folder=capture_folder,
            capture_session_id=capture_session_id,
            metadata=metadata,
        )


__all__ = [
    "CaptureApplication",
    "CaptureOperations",
    "RecognitionHandoffOperations",
]
