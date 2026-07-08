from datetime import datetime
from pathlib import Path

import capture_studio
from capture_studio import CaptureStudioService, next_session_folder


def test_session_folder_names(tmp_path: Path) -> None:
    now = datetime(2026, 6, 29, 12, 0, 0)
    assert next_session_folder(tmp_path, now).name == "06.29.26"
    (tmp_path / "06.29.26").mkdir()
    assert next_session_folder(tmp_path, now).name == "06.29.26.1"
    (tmp_path / "06.29.26.1").mkdir()
    assert next_session_folder(tmp_path, now).name == "06.29.26.2"


def test_front_back_two_cards_and_retake(tmp_path: Path) -> None:
    service = CaptureStudioService(capture_root=tmp_path, allow_placeholder=True)
    service.capture_obs_jpeg = lambda: capture_studio.PLACEHOLDER_JPEG
    session = service.start_session()

    first_front = service.capture(session, "front")
    first_back = service.capture(session, "back")
    second_front = service.capture(session, "front")
    second_back = service.capture(session, "back")

    assert first_front.path.name == "000001_front.jpg"
    assert first_back.path.name == "000001_back.jpg"
    assert second_front.path.name == "000002_front.jpg"
    assert second_back.path.name == "000002_back.jpg"
    assert session["current_card_number"] == 3
    assert session["photos_captured"] == 4

    moved = service.retake_last(session)
    assert moved is not None
    assert moved.name == "000002_back.jpg"
    assert not second_back.path.exists()
    assert session["current_card_number"] == 2
    assert session["photos_captured"] == 3

    replacement_back = service.capture(session, "back")
    assert replacement_back.path.name == "000002_back.jpg"
    assert replacement_back.path.exists()
    assert session["current_card_number"] == 3
    assert session["photos_captured"] == 4


def test_capture_next_alternates_front_back_pairs(tmp_path: Path) -> None:
    service = CaptureStudioService(capture_root=tmp_path, allow_placeholder=True)
    service.capture_obs_jpeg = lambda: capture_studio.PLACEHOLDER_JPEG
    session = service.start_session()

    captures = [service.capture_next(session) for _ in range(4)]

    assert [capture.path.name for capture in captures] == [
        "000001_front.jpg",
        "000001_back.jpg",
        "000002_front.jpg",
        "000002_back.jpg",
    ]
    assert [capture.side for capture in captures] == ["front", "back", "front", "back"]
    assert session["current_card_number"] == 3
    assert session["photos_captured"] == 4


def test_obs_status_uses_configured_password(tmp_path: Path) -> None:
    settings_path = tmp_path / "capture_settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(
        '{"obs_host": "127.0.0.1", "obs_port": 4455, "obs_password": "configured", "obs_scene": "Scene"}',
        encoding="utf-8",
    )
    original_settings_path = capture_studio.SETTINGS_PATH
    original_obs_config_path = capture_studio.OBS_CONFIG_PATH
    original_env_password = capture_studio.os.environ.pop("PUTNAM_OBS_PASSWORD", None)
    passwords = []

    class FakeClient:
        def __init__(self, host, port, password, timeout):
            passwords.append(password)

        def get_current_program_scene(self):
            return {"currentProgramSceneName": "Scene"}

    class FakeObs:
        ReqClient = FakeClient

    service = CaptureStudioService(capture_root=tmp_path, allow_placeholder=True)
    service._obs_module = lambda: FakeObs()
    try:
        capture_studio.SETTINGS_PATH = settings_path
        capture_studio.OBS_CONFIG_PATH = tmp_path / "missing_obs_config.json"
        assert service.obs_status().startswith("OBS status: connected")
        assert passwords == ["configured"]
    finally:
        capture_studio.SETTINGS_PATH = original_settings_path
        capture_studio.OBS_CONFIG_PATH = original_obs_config_path
        if original_env_password is not None:
            capture_studio.os.environ["PUTNAM_OBS_PASSWORD"] = original_env_password


def test_obs_status_uses_local_putnam_os_obs_config(tmp_path: Path) -> None:
    obs_config_path = tmp_path / "obs_config.json"
    obs_config_path.parent.mkdir(parents=True, exist_ok=True)
    obs_config_path.write_text(
        '{"obs": {"host": "127.0.0.1", "port": 4455, "password": "local-config"}}',
        encoding="utf-8",
    )
    original_obs_config_path = capture_studio.OBS_CONFIG_PATH
    original_settings_path = capture_studio.SETTINGS_PATH
    original_env_password = capture_studio.os.environ.pop("PUTNAM_OBS_PASSWORD", None)
    passwords = []

    class FakeClient:
        def __init__(self, host, port, password, timeout):
            passwords.append(password)

        def get_current_program_scene(self):
            return {"currentProgramSceneName": "Scene"}

    class FakeObs:
        ReqClient = FakeClient

    service = CaptureStudioService(capture_root=tmp_path, allow_placeholder=True)
    service._obs_module = lambda: FakeObs()
    try:
        capture_studio.OBS_CONFIG_PATH = obs_config_path
        capture_studio.SETTINGS_PATH = tmp_path / "missing_capture_settings.json"
        assert service.obs_status().startswith("OBS status: connected")
        assert passwords == ["local-config"]
    finally:
        capture_studio.OBS_CONFIG_PATH = original_obs_config_path
        capture_studio.SETTINGS_PATH = original_settings_path
        if original_env_password is not None:
            capture_studio.os.environ["PUTNAM_OBS_PASSWORD"] = original_env_password


def test_obs_status_and_capture_use_same_obs_config(tmp_path: Path) -> None:
    obs_config_path = tmp_path / "obs_config.json"
    obs_config_path.parent.mkdir(parents=True, exist_ok=True)
    obs_config_path.write_text(
        '{"obs": {"host": "127.0.0.1", "port": 4455, "password": "same-config"}}',
        encoding="utf-8",
    )
    original_obs_config_path = capture_studio.OBS_CONFIG_PATH
    original_settings_path = capture_studio.SETTINGS_PATH
    original_env_password = capture_studio.os.environ.pop("PUTNAM_OBS_PASSWORD", None)
    connections = []
    screenshot_args = []

    class FakeClient:
        def __init__(self, host, port, password, timeout):
            connections.append((host, port, password))

        def get_current_program_scene(self):
            return {"currentProgramSceneName": "Live Capture Scene"}

        def get_source_screenshot(self, *args):
            screenshot_args.append(args)
            image_data = capture_studio.base64.b64encode(capture_studio.PLACEHOLDER_JPEG).decode("ascii")
            return {"imageData": image_data}

    class FakeObs:
        ReqClient = FakeClient

    service = CaptureStudioService(capture_root=tmp_path / "captures", allow_placeholder=False)
    service._obs_module = lambda: FakeObs()
    try:
        capture_studio.OBS_CONFIG_PATH = obs_config_path
        capture_studio.SETTINGS_PATH = tmp_path / "missing_capture_settings.json"
        assert "OBS status: connected" in service.obs_status()
        session = service.start_session()
        front = service.capture(session, "front")
        back = service.capture(session, "back")
        assert front.path.exists()
        assert back.path.exists()
        assert connections == [
            ("127.0.0.1", 4455, "same-config"),
            ("127.0.0.1", 4455, "same-config"),
            ("127.0.0.1", 4455, "same-config"),
        ]
        assert screenshot_args == [
            ("Live Capture Scene", "jpg", None, None, 95),
            ("Live Capture Scene", "jpg", None, None, 95),
        ]
    finally:
        capture_studio.OBS_CONFIG_PATH = original_obs_config_path
        capture_studio.SETTINGS_PATH = original_settings_path
        if original_env_password is not None:
            capture_studio.os.environ["PUTNAM_OBS_PASSWORD"] = original_env_password


def test_capture_reports_actual_screenshot_exception(tmp_path: Path) -> None:
    obs_config_path = tmp_path / "obs_config.json"
    obs_config_path.parent.mkdir(parents=True, exist_ok=True)
    obs_config_path.write_text(
        '{"obs": {"host": "127.0.0.1", "port": 4455, "password": "same-config"}}',
        encoding="utf-8",
    )
    original_obs_config_path = capture_studio.OBS_CONFIG_PATH
    original_settings_path = capture_studio.SETTINGS_PATH
    original_env_password = capture_studio.os.environ.pop("PUTNAM_OBS_PASSWORD", None)

    class FakeClient:
        def __init__(self, host, port, password, timeout):
            pass

        def get_current_program_scene(self):
            return {"currentProgramSceneName": "Live Capture Scene"}

        def get_source_screenshot(self, *args):
            raise RuntimeError("source screenshot failed for test")

    class FakeObs:
        ReqClient = FakeClient

    service = CaptureStudioService(capture_root=tmp_path / "captures", allow_placeholder=False)
    service._obs_module = lambda: FakeObs()
    try:
        capture_studio.OBS_CONFIG_PATH = obs_config_path
        capture_studio.SETTINGS_PATH = tmp_path / "missing_capture_settings.json"
        session = service.start_session()
        try:
            service.capture(session, "front")
        except capture_studio.CaptureStudioError as exc:
            message = str(exc)
            assert message.startswith("Failed to capture screenshot:")
            assert "source screenshot failed for test" in message
        else:
            raise AssertionError("Capture should report the screenshot exception.")
    finally:
        capture_studio.OBS_CONFIG_PATH = original_obs_config_path
        capture_studio.SETTINGS_PATH = original_settings_path
        if original_env_password is not None:
            capture_studio.os.environ["PUTNAM_OBS_PASSWORD"] = original_env_password


def test_obs_status_reports_missing_password(tmp_path: Path) -> None:
    settings_path = tmp_path / "capture_settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text('{"obs_host": "127.0.0.1", "obs_port": 4455}', encoding="utf-8")
    original_settings_path = capture_studio.SETTINGS_PATH
    original_obs_config_path = capture_studio.OBS_CONFIG_PATH
    original_env_password = capture_studio.os.environ.pop("PUTNAM_OBS_PASSWORD", None)
    service = CaptureStudioService(capture_root=tmp_path, allow_placeholder=True)
    service._obs_module = lambda: (_ for _ in ()).throw(AssertionError("OBS should not be contacted"))
    try:
        capture_studio.SETTINGS_PATH = settings_path
        capture_studio.OBS_CONFIG_PATH = tmp_path / "missing_obs_config.json"
        assert (
            service.obs_status()
            == "OBS status: auth missing. OBS authentication is enabled, but no OBS password is configured in CardVector OS."
        )
    finally:
        capture_studio.SETTINGS_PATH = original_settings_path
        capture_studio.OBS_CONFIG_PATH = original_obs_config_path
        if original_env_password is not None:
            capture_studio.os.environ["PUTNAM_OBS_PASSWORD"] = original_env_password


if __name__ == "__main__":
    import tempfile

    root = Path(tempfile.mkdtemp(prefix="putnam_capture_test_"))
    test_session_folder_names(root / "folders")
    test_front_back_two_cards_and_retake(root / "captures")
    test_capture_next_alternates_front_back_pairs(root / "capture_next")
    test_obs_status_uses_configured_password(root / "obs_password")
    test_obs_status_uses_local_putnam_os_obs_config(root / "local_obs_config")
    test_obs_status_and_capture_use_same_obs_config(root / "same_obs_config")
    test_capture_reports_actual_screenshot_exception(root / "screenshot_exception")
    test_obs_status_reports_missing_password(root / "obs_missing_password")
    print(f"CardVector Capture Studio v2 smoke test passed: {root}")
