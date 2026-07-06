from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable


OBS_CONNECTED = "connected"
OBS_DISCONNECTED = "disconnected"
OBS_RECONNECTING = "reconnecting"
OBS_ERROR = "error"


@dataclass
class OBSConnectionStatus:
    state: str
    message: str
    host: str = ""
    port: int = 0
    scene: str = ""
    error_type: str = ""
    updated_at: str = ""

    @property
    def connected(self) -> bool:
        return self.state == OBS_CONNECTED


def _response_value(response: Any, *names: str, default: Any = None) -> Any:
    for name in names:
        if hasattr(response, name):
            return getattr(response, name)
    if isinstance(response, dict):
        for name in names:
            if name in response:
                return response[name]
    return default


class OBSConnectionManager:
    """Shared OBS WebSocket connection manager for Capture Studio.

    The manager owns the cached ReqClient so status checks, manual capture, and
    future automation all use the same host/port/password and reconnect path.
    """

    def __init__(
        self,
        settings_loader: Callable[[], dict[str, Any]],
        password_loader: Callable[[dict[str, Any] | None], str],
        obs_module_loader: Callable[[], Any],
        error_factory: type[Exception] = RuntimeError,
        auth_missing_message: str = "OBS authentication is enabled, but no OBS password is configured.",
        default_host: str = "127.0.0.1",
        default_port: int = 4455,
    ):
        self.settings_loader = settings_loader
        self.password_loader = password_loader
        self.obs_module_loader = obs_module_loader
        self.error_factory = error_factory
        self.auth_missing_message = auth_missing_message
        self.default_host = default_host
        self.default_port = default_port
        self._client: Any | None = None
        self._client_key: tuple[str, int, str] | None = None
        self._status = OBSConnectionStatus(
            state=OBS_DISCONNECTED,
            message="OBS status: disconnected.",
            updated_at=self._now(),
        )

    def status(self, check: bool = False, timeout: int = 3) -> OBSConnectionStatus:
        if not check:
            return self._status
        try:
            scene = self.current_program_scene(timeout=timeout)
            host, port, _password = self.connection_values()
            return self._set_status(
                OBS_CONNECTED,
                f"OBS status: connected at {host}:{port}. Current scene: {scene}",
                host=host,
                port=port,
                scene=scene,
            )
        except Exception:
            return self._status

    def status_text(self, check: bool = False, timeout: int = 3) -> str:
        return self.status(check=check, timeout=timeout).message

    def connection_values(self, settings: dict[str, Any] | None = None) -> tuple[str, int, str]:
        settings = settings or self.settings_loader()
        host = str(settings.get("obs_host", self.default_host) or self.default_host).strip() or self.default_host
        try:
            port = int(settings.get("obs_port", self.default_port) or self.default_port)
        except Exception:
            port = self.default_port
        password = self.password_loader(settings)
        return host, port, password

    def get_client(self, settings: dict[str, Any] | None = None, timeout: int = 5, force_reconnect: bool = False) -> Any:
        settings = settings or self.settings_loader()
        host, port, password = self.connection_values(settings)
        key = (host, port, password)
        if not password:
            status = self._set_status(
                OBS_ERROR,
                f"OBS status: auth missing. {self.auth_missing_message}",
                host=host,
                port=port,
                error_type="auth_missing",
            )
            raise self.error_factory(status.message)
        if self._client is not None and self._client_key == key and not force_reconnect:
            return self._client
        if self._client is not None or force_reconnect:
            self._set_status(OBS_RECONNECTING, f"OBS status: reconnecting to {host}:{port}.", host=host, port=port)
        try:
            obs = self.obs_module_loader()
            client = obs.ReqClient(host=host, port=port, password=password, timeout=timeout)
        except Exception as exc:
            self._client = None
            self._client_key = None
            status = self._classify_error(exc, host, port)
            raise self.error_factory(status.message) from exc
        self._client = client
        self._client_key = key
        self._set_status(OBS_CONNECTED, f"OBS status: connected at {host}:{port}.", host=host, port=port)
        return client

    def request(
        self,
        method_name: str,
        *args: Any,
        settings: dict[str, Any] | None = None,
        timeout: int = 5,
        retry_once: bool = True,
    ) -> Any:
        settings = settings or self.settings_loader()
        client = self.get_client(settings=settings, timeout=timeout)
        try:
            return getattr(client, method_name)(*args)
        except Exception as first_exc:
            if not retry_once:
                host, port, _password = self.connection_values(settings)
                self._client = None
                self._client_key = None
                status = self._classify_error(first_exc, host, port)
                raise self.error_factory(status.message) from first_exc
            host, port, _password = self.connection_values(settings)
            self._client = None
            self._client_key = None
            self._set_status(OBS_RECONNECTING, f"OBS status: reconnecting to {host}:{port}.", host=host, port=port)
            try:
                client = self.get_client(settings=settings, timeout=timeout, force_reconnect=True)
                return getattr(client, method_name)(*args)
            except Exception as second_exc:
                self._client = None
                self._client_key = None
                status = self._classify_error(second_exc, host, port)
                raise self.error_factory(status.message) from second_exc

    def current_program_scene(self, settings: dict[str, Any] | None = None, timeout: int = 5) -> str:
        response = self.request("get_current_program_scene", settings=settings, timeout=timeout)
        scene = str(_response_value(response, "currentProgramSceneName", "current_program_scene_name", default="") or "")
        if scene:
            host, port, _password = self.connection_values(settings)
            self._set_status(
                OBS_CONNECTED,
                f"OBS status: connected at {host}:{port}. Current scene: {scene}",
                host=host,
                port=port,
                scene=scene,
            )
        return scene

    def source_screenshot(self, scene_name: str, image_format: str, width: Any, height: Any, quality: int, settings: dict[str, Any] | None = None) -> Any:
        return self.request(
            "get_source_screenshot",
            scene_name,
            image_format,
            width,
            height,
            quality,
            settings=settings,
            timeout=5,
        )

    def reset(self) -> None:
        self._client = None
        self._client_key = None
        self._set_status(OBS_DISCONNECTED, "OBS status: disconnected.")

    def _classify_error(self, exc: Exception, host: str, port: int) -> OBSConnectionStatus:
        message = str(exc or "").strip()
        lower = message.lower()
        if message == self.auth_missing_message or "no password provided" in lower:
            return self._set_status(
                OBS_ERROR,
                f"OBS status: auth missing. {self.auth_missing_message}",
                host=host,
                port=port,
                error_type="auth_missing",
            )
        if isinstance(exc, ImportError) or "obsws-python is not installed" in lower or "no module named" in lower:
            return self._set_status(
                OBS_ERROR,
                "OBS status: error. obsws-python is not installed.",
                host=host,
                port=port,
                error_type="missing_dependency",
            )
        if "authentication" in lower and ("failed" in lower or "invalid" in lower or "denied" in lower):
            return self._set_status(
                OBS_ERROR,
                "OBS status: auth failed. Check the OBS password configured in CardVector OS.",
                host=host,
                port=port,
                error_type="auth_failed",
            )
        if "auth" in lower and ("failed" in lower or "invalid" in lower or "denied" in lower):
            return self._set_status(
                OBS_ERROR,
                "OBS status: auth failed. Check the OBS password configured in CardVector OS.",
                host=host,
                port=port,
                error_type="auth_failed",
            )
        friendly = f"OBS status: OBS not running / unavailable at {host}:{port}."
        if message:
            friendly = f"{friendly} {message}"
        return self._set_status(
            OBS_DISCONNECTED,
            friendly,
            host=host,
            port=port,
            error_type="websocket_unavailable",
        )

    def _set_status(
        self,
        state: str,
        message: str,
        host: str = "",
        port: int = 0,
        scene: str = "",
        error_type: str = "",
    ) -> OBSConnectionStatus:
        self._status = OBSConnectionStatus(
            state=state,
            message=message,
            host=host,
            port=port,
            scene=scene,
            error_type=error_type,
            updated_at=self._now(),
        )
        return self._status

    @staticmethod
    def _now() -> str:
        return datetime.now().isoformat(timespec="seconds")
