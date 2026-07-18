from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol


class DesktopCaptureOperations(Protocol):
    allow_placeholder: bool
    obs_manager: Any

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

    def capture_next(self, session: dict[str, Any]) -> Any: ...

    def retake_last(self, session: dict[str, Any]) -> Path | None: ...

    def finish_session(self, session: dict[str, Any]) -> None: ...

    def obs_status(self) -> str: ...

    def launch_obs(self) -> Path: ...

    def capture_obs_jpeg(self) -> bytes: ...

    def _save_session(self, session: dict[str, Any]) -> None: ...


class MobileCaptureOperations(Protocol):
    current_workstation: str

    def environment_ready(self) -> tuple[bool, str]: ...

    def list_queue(
        self,
        include_diagnostics: bool = True,
        limit: int = 100,
    ) -> list[dict[str, Any]]: ...

    def sync_locations(self, strict: bool = True) -> dict[str, Any]: ...

    def process(self, session_id: str) -> dict[str, Any]: ...

    def process_next_pending(self) -> dict[str, Any] | None: ...

    def process_all_pending(self, limit: int = 25) -> list[dict[str, Any]]: ...

    def complete(self, session_id: str) -> dict[str, Any]: ...

    def fail(self, session_id: str, message: str) -> dict[str, Any]: ...

    def retry_failed(self, session_id: str) -> dict[str, Any]: ...

    def local_folder(self, session_id: str) -> Path | None: ...


class DesktopCaptureFactory(Protocol):
    def __call__(
        self,
        *,
        capture_root: Path,
        allow_placeholder: bool,
        obs_manager: Any,
    ) -> DesktopCaptureOperations: ...


class CaptureService:
    """Canonical Capture facade over the proven desktop and mobile services."""

    def __init__(
        self,
        *,
        desktop: DesktopCaptureOperations,
        mobile: MobileCaptureOperations,
        desktop_factory: DesktopCaptureFactory | None = None,
    ) -> None:
        self._desktop = desktop
        self._mobile = mobile
        self._desktop_factory = desktop_factory

    @property
    def allow_placeholder(self) -> bool:
        return self._desktop.allow_placeholder

    @property
    def obs_manager(self) -> Any:
        return self._desktop.obs_manager

    @property
    def current_workstation(self) -> str:
        return self._mobile.current_workstation

    def start_session(self) -> dict[str, Any]:
        return self._desktop.start_session()

    def capture(self, session: dict[str, Any], side: str) -> Any:
        return self._desktop.capture(session, side)

    def capture_bytes(
        self,
        session: dict[str, Any],
        side: str,
        image_bytes: bytes,
        capture_mode: str = "OBS WebSocket",
    ) -> Any:
        return self._desktop.capture_bytes(
            session,
            side,
            image_bytes,
            capture_mode=capture_mode,
        )

    def next_capture_side(self, session: dict[str, Any]) -> str:
        return self._desktop.next_capture_side(session)

    def capture_next(self, session: dict[str, Any]) -> Any:
        return self._desktop.capture_next(session)

    def retake_last(self, session: dict[str, Any]) -> Path | None:
        return self._desktop.retake_last(session)

    def finish_session(self, session: dict[str, Any]) -> None:
        self._desktop.finish_session(session)

    def obs_status(self) -> str:
        return self._desktop.obs_status()

    def launch_obs(self) -> Path:
        return self._desktop.launch_obs()

    def capture_obs_jpeg(self) -> bytes:
        return self._desktop.capture_obs_jpeg()

    def save_session(self, session: dict[str, Any]) -> None:
        self._desktop._save_session(session)

    def _save_session(self, session: dict[str, Any]) -> None:
        self.save_session(session)

    def create_desktop_service(self, capture_root: Path) -> DesktopCaptureOperations:
        if self._desktop_factory is None:
            raise RuntimeError("A desktop Capture service factory is not configured.")
        return self._desktop_factory(
            capture_root=Path(capture_root),
            allow_placeholder=self.allow_placeholder,
            obs_manager=self.obs_manager,
        )

    def environment_ready(self) -> tuple[bool, str]:
        return self._mobile.environment_ready()

    def list_queue(
        self,
        include_diagnostics: bool = True,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        return self._mobile.list_queue(
            include_diagnostics=include_diagnostics,
            limit=limit,
        )

    def sync_locations(self, strict: bool = True) -> dict[str, Any]:
        return self._mobile.sync_locations(strict=strict)

    def process(self, session_id: str) -> dict[str, Any]:
        return self._mobile.process(session_id)

    def process_next_pending(self) -> dict[str, Any] | None:
        return self._mobile.process_next_pending()

    def process_all_pending(self, limit: int = 25) -> list[dict[str, Any]]:
        return self._mobile.process_all_pending(limit=limit)

    def complete(self, session_id: str) -> dict[str, Any]:
        return self._mobile.complete(session_id)

    def fail(self, session_id: str, message: str) -> dict[str, Any]:
        return self._mobile.fail(session_id, message)

    def retry_failed(self, session_id: str) -> dict[str, Any]:
        return self._mobile.retry_failed(session_id)

    def local_folder(self, session_id: str) -> Path | None:
        return self._mobile.local_folder(session_id)


__all__ = [
    "CaptureService",
    "DesktopCaptureFactory",
    "DesktopCaptureOperations",
    "MobileCaptureOperations",
]
