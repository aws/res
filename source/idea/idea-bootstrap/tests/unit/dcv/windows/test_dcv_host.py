#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from unittest.mock import Mock
from res.resources import cluster_settings
from ideabootstrap.dcv import constants
from ideabootstrap.dcv.windows import dcv_host


def test_configure_dcv_connectivity_registry(monkeypatch) -> None:
    mock_create_key = Mock()
    mock_set_value = Mock()
    mock_close = Mock()

    monkeypatch.setattr("winreg.CreateKeyEx", mock_create_key)
    monkeypatch.setattr("winreg.SetValueEx", mock_set_value)
    monkeypatch.setattr("winreg.CloseKey", mock_close)
    monkeypatch.setattr(cluster_settings, "get_setting", lambda x: 1)

    dcv_host._configure_dcv_connectivity_registry()

    mock_create_key.assert_called_once()
    assert mock_set_value.call_count == 3
    mock_close.assert_called_once()


def test_remove_dcv_session_management_registry_not_found(monkeypatch, caplog) -> None:
    logs = []
    mock_open = Mock(side_effect=Exception("Not found"))
    monkeypatch.setattr("winreg.OpenKey", mock_open)
    monkeypatch.setattr("ideabootstrap.dcv.windows.dcv_host.logger.info", logs.append)

    dcv_host._remove_dcv_session_management_registry()

    assert "skipping" in logs[-1]


def test_configure_dcv_security_registry(monkeypatch) -> None:
    mock_create_key = Mock()
    mock_set_value = Mock()
    mock_close = Mock()

    monkeypatch.setattr("winreg.CreateKeyEx", mock_create_key)
    monkeypatch.setattr("winreg.SetValueEx", mock_set_value)
    monkeypatch.setattr("winreg.CloseKey", mock_close)
    monkeypatch.setattr(
        "ideabootstrap.dcv.dcv_utils.get_cluster_internal_endpoint",
        lambda: "internal-alb.example.com",
    )
    monkeypatch.setenv("IDEA_SESSION_ID", "ses-test-456")

    dcv_host._configure_dcv_security_registry()

    mock_create_key.assert_called_once()
    auth_verifier_call = mock_set_value.call_args_list[0]
    assert auth_verifier_call[0][1] == "auth-token-verifier"
    assert auth_verifier_call[0][4] == "internal-alb.example.com/externalAuth/ses-test-456"
    mock_close.assert_called_once()


def test_configure_dcv_security_registry_missing_session_id(monkeypatch) -> None:
    import pytest

    monkeypatch.setattr("winreg.CreateKeyEx", Mock())
    monkeypatch.setattr("winreg.SetValueEx", Mock())
    monkeypatch.setattr("winreg.CloseKey", Mock())
    monkeypatch.setattr(
        "ideabootstrap.dcv.dcv_utils.get_cluster_internal_endpoint",
        lambda: "internal-alb.example.com",
    )
    monkeypatch.delenv("IDEA_SESSION_ID", raising=False)

    with pytest.raises(ValueError, match="IDEA_SESSION_ID"):
        dcv_host._configure_dcv_security_registry()


def test_configure(monkeypatch) -> None:
    mock_run = Mock()
    mock_registry = Mock()
    mock_storage = Mock()

    monkeypatch.setattr("subprocess.run", mock_run)
    monkeypatch.setattr(dcv_host, "_configure_dcv_connectivity_registry", mock_registry)
    monkeypatch.setattr(dcv_host, "_configure_dcv_security_registry", mock_registry)
    monkeypatch.setattr(dcv_host, "_configure_dcv_windows_registry", mock_registry)
    monkeypatch.setattr(
        dcv_host, "_remove_dcv_session_management_registry", mock_registry
    )
    monkeypatch.setattr(dcv_host, "_configure_storage_root", mock_storage)

    dcv_host.configure()

    assert mock_run.call_count == 2
    mock_registry.call_count == 4
    mock_storage.assert_called_once()


def test_apply_automatic_console_session_config(monkeypatch) -> None:
    mock_create_key = Mock()
    mock_set_value = Mock()
    mock_close = Mock()
    mock_run = Mock()

    monkeypatch.setattr("winreg.CreateKeyEx", mock_create_key)
    monkeypatch.setattr("winreg.SetValueEx", mock_set_value)
    monkeypatch.setattr("winreg.CloseKey", mock_close)
    monkeypatch.setattr("subprocess.run", mock_run)

    dcv_host.apply_automatic_console_session_config(
        session_owner="test-user",
        storage_root="C:\\session-storage\\test-user",
        permissions_file_path="C:\\Program Files\\NICE\\DCV\\console\\idea.perm",
    )

    # 2 CreateKeyEx (session-management + automatic-console-session)
    assert mock_create_key.call_count == 2
    # create-session DWORD + owner + storage-root + permissions-file = 4 SetValueEx
    assert mock_set_value.call_count == 4
    assert mock_close.call_count == 2
    mock_run.assert_called_once_with(
        ["powershell.exe", "-Command", "Restart-Service dcvserver"], check=True
    )
