#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
from unittest.mock import Mock
from ideabootstrap.dcv import constants

import pytest


@pytest.fixture(autouse=True)
def set_base_os(monkeypatch):
    """Default to linux for tests; override per-test as needed."""
    monkeypatch.setenv("RES_BASE_OS", "rhel8")


def _import_dcv():
    """Import dcv module fresh (after env is set)."""
    import importlib
    import ideabootstrap.dcv.dcv as dcv_mod

    importlib.reload(dcv_mod)
    return dcv_mod


class TestPollDcvSessionReady:
    def test_session_running(self, monkeypatch):
        dcv_mod = _import_dcv()
        session_json = json.dumps({"status": "running"})
        mock_result = Mock(returncode=0, stdout=session_json)
        monkeypatch.setattr("subprocess.run", Mock(return_value=mock_result))

        result = dcv_mod.poll_dcv_session_ready(timeout_seconds=5, retry_interval=1)

        assert result == "READY"

    def test_session_timeout(self, monkeypatch):
        dcv_mod = _import_dcv()
        mock_result = Mock(returncode=1, stdout="")
        monkeypatch.setattr("subprocess.run", Mock(return_value=mock_result))
        monkeypatch.setattr("time.sleep", Mock())

        result = dcv_mod.poll_dcv_session_ready(timeout_seconds=0, retry_interval=1)

        assert result == "ERROR"

    def test_session_not_running_then_running(self, monkeypatch):
        dcv_mod = _import_dcv()
        not_running = Mock(returncode=0, stdout=json.dumps({"status": "creating"}))
        running = Mock(returncode=0, stdout=json.dumps({"status": "running"}))
        mock_run = Mock(side_effect=[not_running, running])
        monkeypatch.setattr("subprocess.run", mock_run)
        monkeypatch.setattr("time.sleep", Mock())

        result = dcv_mod.poll_dcv_session_ready(timeout_seconds=30, retry_interval=1)

        assert result == "READY"
        assert mock_run.call_count == 2

    def test_uses_windows_path(self, monkeypatch):
        monkeypatch.setenv("RES_BASE_OS", "windows")
        dcv_mod = _import_dcv()

        session_json = json.dumps({"status": "running"})
        mock_result = Mock(returncode=0, stdout=session_json)
        mock_run = Mock(return_value=mock_result)
        monkeypatch.setattr("subprocess.run", mock_run)

        dcv_mod.poll_dcv_session_ready(timeout_seconds=5, retry_interval=1)

        cmd = mock_run.call_args[0][0]

        assert cmd[0] == constants.WINDOWS_DCV_EXECUTABLE_PATH


class TestConfigureAutomaticConsoleSession:
    def test_linux_success(self, monkeypatch, tmp_path):
        monkeypatch.setenv("IDEA_SESSION_OWNER", "test-user")
        monkeypatch.setenv("IDEA_SESSION_ID", "session-123")
        permissions_dir = str(tmp_path) + "/console/"
        monkeypatch.setattr(constants, "DCV_PERMISSIONS_DIR", permissions_dir)
        monkeypatch.setattr(constants, "DCV_PERMISSIONS_FILE_NAME", "idea.perm")
        monkeypatch.setattr(
            "res.resources.cluster_settings.get_setting", lambda x: "clusteradmin"
        )

        dcv_mod = _import_dcv()
        monkeypatch.setattr(
            dcv_mod.dcv_session_permissions,
            "generate_permissions_content",
            lambda session_id, admin_username, newline="\n": "[permissions]\n%owner% allow builtin\n",
        )
        monkeypatch.setattr(dcv_mod, "is_dcvserver_ready", lambda: True)

        mock_apply = Mock()
        monkeypatch.setattr(
            "ideabootstrap.dcv.linux.dcv_host.apply_automatic_console_session_config",
            mock_apply,
        )
        states = []
        monkeypatch.setattr(
            "ideabootstrap.dcv.dcv.update_session_state",
            lambda s: states.append(s),
        )

        result = dcv_mod.configure_automatic_console_session()

        assert result is True
        with open(permissions_dir + "idea.perm") as f:
            assert "%owner% allow builtin" in f.read()
        mock_apply.assert_called_once_with(
            session_owner="test-user",
            storage_root="/home/test-user/storage-root",
            permissions_file_path=permissions_dir + "idea.perm",
        )
        assert states == ["CREATING", "INITIALIZING"]

    def test_windows_success(self, monkeypatch, tmp_path):
        monkeypatch.setenv("RES_BASE_OS", "windows")
        monkeypatch.setenv("IDEA_SESSION_OWNER", "test-user")
        monkeypatch.setenv("IDEA_SESSION_ID", "session-123")
        permissions_dir = str(tmp_path) + "\\console\\"
        monkeypatch.setattr(constants, "WINDOWS_DCV_PERMISSIONS_DIR", permissions_dir)
        monkeypatch.setattr(constants, "DCV_PERMISSIONS_FILE_NAME", "idea.perm")

        dcv_mod = _import_dcv()
        monkeypatch.setattr(
            dcv_mod.dcv_session_permissions,
            "generate_permissions_content",
            lambda session_id, admin_username, newline="\r\n": "[permissions]\r\n",
        )
        monkeypatch.setattr(dcv_mod, "is_dcvserver_ready", lambda: True)

        mock_apply = Mock()
        monkeypatch.setattr(
            "ideabootstrap.dcv.windows.dcv_host.apply_automatic_console_session_config",
            mock_apply,
        )
        states = []
        monkeypatch.setattr(
            "ideabootstrap.dcv.dcv.update_session_state",
            lambda s: states.append(s),
        )

        result = dcv_mod.configure_automatic_console_session()

        assert result is True
        mock_apply.assert_called_once_with(
            session_owner="test-user",
            storage_root="C:\\session-storage\\test-user",
            permissions_file_path=permissions_dir + "idea.perm",
        )
        assert states == ["CREATING", "INITIALIZING"]

    def test_server_not_ready(self, monkeypatch, tmp_path):
        monkeypatch.setenv("IDEA_SESSION_OWNER", "test-user")
        permissions_dir = str(tmp_path) + "/console/"
        monkeypatch.setattr(constants, "DCV_PERMISSIONS_DIR", permissions_dir)
        monkeypatch.setattr(constants, "DCV_PERMISSIONS_FILE_NAME", "idea.perm")
        monkeypatch.setattr(
            "res.resources.cluster_settings.get_setting", lambda x: "clusteradmin"
        )

        dcv_mod = _import_dcv()
        monkeypatch.setattr(
            dcv_mod.dcv_session_permissions,
            "generate_permissions_content",
            lambda session_id, admin_username, newline="\n": "[]",
        )
        monkeypatch.setattr(dcv_mod, "is_dcvserver_ready", lambda: False)
        monkeypatch.setattr(
            "ideabootstrap.dcv.linux.dcv_host.apply_automatic_console_session_config",
            Mock(),
        )
        states = []
        monkeypatch.setattr(
            "ideabootstrap.dcv.dcv.update_session_state",
            lambda s: states.append(s),
        )

        result = dcv_mod.configure_automatic_console_session()

        assert result is False
        assert states == ["CREATING", "ERROR"]

    def test_exception(self, monkeypatch):
        monkeypatch.setenv("IDEA_SESSION_OWNER", "test-user")
        monkeypatch.setattr(constants, "DCV_PERMISSIONS_DIR", "/nonexistent/")
        monkeypatch.setattr(constants, "DCV_PERMISSIONS_FILE_NAME", "idea.perm")
        monkeypatch.setattr(
            "res.resources.cluster_settings.get_setting", lambda x: "clusteradmin"
        )

        dcv_mod = _import_dcv()
        monkeypatch.setattr(
            dcv_mod.dcv_session_permissions,
            "generate_permissions_content",
            Mock(side_effect=Exception("DDB error")),
        )
        states = []
        monkeypatch.setattr(
            "ideabootstrap.dcv.dcv.update_session_state",
            lambda s: states.append(s),
        )

        result = dcv_mod.configure_automatic_console_session()

        assert result is False
        assert states == ["CREATING", "ERROR"]
