#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import tempfile
from unittest.mock import Mock
from ideabootstrap.dcv import constants
from ideabootstrap.dcv.linux import dcv_host


def test_configure_storage_root(monkeypatch) -> None:
    monkeypatch.setenv("IDEA_SESSION_OWNER", "test-user")
    mock_makedirs = Mock()
    mock_chown = Mock()
    mock_pwd = Mock()
    mock_pwd.return_value = Mock(pw_uid=1000, pw_gid=1000)

    monkeypatch.setattr("os.path.exists", lambda x: False)
    monkeypatch.setattr("os.makedirs", mock_makedirs)
    monkeypatch.setattr("os.chown", mock_chown)
    monkeypatch.setattr("pwd.getpwnam", mock_pwd)

    dcv_host._configure_storage_root()

    mock_makedirs.assert_called_once_with("/home/test-user/storage-root", exist_ok=True)
    mock_chown.assert_called_once_with("/home/test-user/storage-root", 1000, 1000)


def test_configure_dcv_conf(monkeypatch) -> None:
    mock_settings = {
        constants.IDLE_TIMEOUT_KEY: 3600,
        constants.IDLE_TIMEOUT_WARNING_KEY: 300,
        constants.AGENT_COMMUNICATION_PORT_KEY: 8443,
    }
    mock_get_setting = Mock(side_effect=lambda x: mock_settings[x])

    monkeypatch.setattr(
        "ideabootstrap.dcv.dcv_utils.get_cluster_internal_endpoint",
        lambda: "internal-alb.example.com",
    )
    monkeypatch.setattr("res.resources.cluster_settings.get_setting", mock_get_setting)
    monkeypatch.setattr("os.path.exists", lambda x: False)

    with tempfile.NamedTemporaryFile(mode="w", delete=True) as temp_file:
        temp_file_name = temp_file.name
        monkeypatch.setattr(constants, "DCV_CONFIG_FILE_PATH", temp_file_name)
        dcv_host._configure_dcv_conf()

        with open(temp_file_name, "r") as f:
            content = f.read()

    assert "idle-timeout = 3600" in content
    assert "idle-timeout-warning = 300" in content
    assert "internal-alb.example.com:8443" in content


def test_configure_all(monkeypatch) -> None:
    mock_storage = Mock()
    mock_dcv = Mock()
    monkeypatch.setattr(dcv_host, "_configure_storage_root", mock_storage)
    monkeypatch.setattr(dcv_host, "_configure_dcv_conf", mock_dcv)

    dcv_host.configure()

    mock_storage.assert_called_once()
    mock_dcv.assert_called_once()
