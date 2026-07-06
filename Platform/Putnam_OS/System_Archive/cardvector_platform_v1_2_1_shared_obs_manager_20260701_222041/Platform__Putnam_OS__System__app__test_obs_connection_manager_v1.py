from pathlib import Path

import obs_connection_manager


def test_obs_manager_reuses_connected_client() -> None:
    created = []

    class FakeClient:
        def __init__(self, host, port, password, timeout):
            created.append((host, port, password, timeout))

        def get_current_program_scene(self):
            return {"currentProgramSceneName": "Card Capture"}

    class FakeObs:
        ReqClient = FakeClient

    manager = obs_connection_manager.OBSConnectionManager(
        settings_loader=lambda: {"obs_host": "127.0.0.1", "obs_port": 4455, "obs_password": "secret"},
        password_loader=lambda settings=None: (settings or {}).get("obs_password", ""),
        obs_module_loader=lambda: FakeObs(),
    )

    assert manager.status(check=True).connected
    manager.get_client()
    manager.get_client()
    assert created == [("127.0.0.1", 4455, "secret", 3)]


def test_obs_manager_reports_missing_password_without_connecting() -> None:
    contacted = False

    def load_obs():
        nonlocal contacted
        contacted = True
        raise AssertionError("OBS should not be contacted without a password.")

    manager = obs_connection_manager.OBSConnectionManager(
        settings_loader=lambda: {"obs_host": "127.0.0.1", "obs_port": 4455, "obs_password": ""},
        password_loader=lambda settings=None: "",
        obs_module_loader=load_obs,
        auth_missing_message="Password required.",
    )

    status = manager.status(check=True)
    assert status.state == obs_connection_manager.OBS_ERROR
    assert status.error_type == "auth_missing"
    assert "auth missing" in status.message
    assert contacted is False


def test_obs_manager_reconnects_after_request_failure() -> None:
    clients = []

    class FakeClient:
        def __init__(self, host, port, password, timeout):
            self.number = len(clients)
            clients.append(self)

        def get_source_screenshot(self, *args):
            if self.number == 0:
                raise RuntimeError("temporary websocket failure")
            return {"imageData": "abc"}

    class FakeObs:
        ReqClient = FakeClient

    manager = obs_connection_manager.OBSConnectionManager(
        settings_loader=lambda: {"obs_host": "127.0.0.1", "obs_port": 4455, "obs_password": "secret"},
        password_loader=lambda settings=None: (settings or {}).get("obs_password", ""),
        obs_module_loader=lambda: FakeObs(),
    )

    assert manager.source_screenshot("Scene", "jpg", None, None, 95) == {"imageData": "abc"}
    assert len(clients) == 2
    assert manager.status().state == obs_connection_manager.OBS_CONNECTED


if __name__ == "__main__":
    test_obs_manager_reuses_connected_client()
    test_obs_manager_reports_missing_password_without_connecting()
    test_obs_manager_reconnects_after_request_failure()
    print(f"OBS connection manager smoke test passed: {Path.cwd()}")
