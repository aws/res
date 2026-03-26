#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import tempfile
from unittest.mock import Mock, call
from ideabootstrap.dcv import constants
from ideabootstrap.dcv.linux import start_dcv_service


def test_start_and_configure_dcv_service(monkeypatch) -> None:
    mock_run = Mock()
    monkeypatch.setattr("subprocess.run", mock_run)
    expected_calls = [
        call(["sudo", "systemctl", "enable", "dcvserver"], check=True),
        call(["sudo", "systemctl", "daemon-reload"], check=True),
        call(["sudo", "systemctl", "restart", "dcvserver"], check=True),
    ]

    with tempfile.NamedTemporaryFile(mode="w", delete=True) as temp_file:
        temp_file_name = temp_file.name
        monkeypatch.setattr(constants, "DCV_SERVER_SERVICE_PATH", temp_file_name)

        start_dcv_service._start_and_configure_dcv_service()
        with open(temp_file_name, "r") as f:
            content = f.read()

    assert "NICE DCV server daemon" in content
    assert mock_run.call_args_list == expected_calls


def test_start_and_configure_dcv_agent_service(monkeypatch) -> None:
    mock_run = Mock()
    monkeypatch.setattr("subprocess.run", mock_run)
    expected_calls = [
        call(["sudo", "systemctl", "enable", "dcv-session-manager-agent"], check=True),
        call(["sudo", "systemctl", "daemon-reload"], check=True),
        call(["sudo", "systemctl", "restart", "dcv-session-manager-agent"], check=True),
    ]

    with tempfile.NamedTemporaryFile(mode="w", delete=True) as temp_file:
        temp_file_name = temp_file.name
        monkeypatch.setattr(constants, "DCV_AGENT_SERVICE_PATH", temp_file_name)

        start_dcv_service._start_and_configure_dcv_agent_service()
        with open(temp_file_name, "r") as f:
            content = f.read()

    assert "DCV Session Manager" in content
    assert mock_run.call_args_list == expected_calls


def test_is_dcvserver_ready_success(monkeypatch) -> None:
    """Test successful DCV server readiness check"""
    mock_run = Mock()
    mock_run.side_effect = [
        Mock(returncode=0, stdout="active\n"),
        Mock(returncode=0, stdout="DCV server is running\n")
    ]
    monkeypatch.setattr("subprocess.run", mock_run)
    monkeypatch.setattr("time.sleep", Mock())

    result = start_dcv_service.is_dcvserver_ready(timeout_seconds=10, retry_interval=1)

    assert result is True
    expected_calls = [
        call(["sudo", "systemctl", "is-active", "dcvserver"], capture_output=True, text=True, check=False),
        call(["dcv", "list-sessions"], capture_output=True, text=True, check=False, timeout=10)
    ]
    assert mock_run.call_args_list == expected_calls


def test_is_dcvserver_ready_service_not_active(monkeypatch) -> None:
    """Test DCV server readiness check when service is not active"""
    mock_run = Mock()
    mock_run.side_effect = [
        Mock(returncode=1, stdout="inactive\n"),
        Mock(returncode=1, stdout="inactive\n")
    ]
    monkeypatch.setattr("subprocess.run", mock_run)
    
    mock_time = Mock()
    mock_time.side_effect = [0, 1, 2, 5, 6, 7, 10, 11, 12, 15, 16, 17, 20, 21, 22]
    monkeypatch.setattr("time.time", mock_time)
    monkeypatch.setattr("time.sleep", Mock())
    
    result = start_dcv_service.is_dcvserver_ready(timeout_seconds=10, retry_interval=2)
    
    assert result is False


def test_is_dcvserver_ready_status_command_fails(monkeypatch) -> None:
    """Test DCV server readiness check when status command fails"""
    mock_run = Mock()
    mock_run.side_effect = [
        Mock(returncode=0, stdout="active\n"),
        Mock(returncode=1, stderr="DCV server not responding\n"),
        Mock(returncode=0, stdout="active\n"),
        Mock(returncode=1, stderr="DCV server not responding\n")
    ]
    monkeypatch.setattr("subprocess.run", mock_run)
    
    mock_time = Mock()
    mock_time.side_effect = [0, 1, 2, 5, 6, 7, 10, 11, 12, 15, 16, 17, 20, 21, 22]
    monkeypatch.setattr("time.time", mock_time)
    monkeypatch.setattr("time.sleep", Mock())
    
    result = start_dcv_service.is_dcvserver_ready(timeout_seconds=10, retry_interval=2)
    
    assert result is False


def test_is_dcvserver_ready_subprocess_timeout(monkeypatch) -> None:
    """Test DCV server readiness check when subprocess times out"""
    import subprocess
    
    mock_run = Mock()
    mock_run.side_effect = [
        Mock(returncode=0, stdout="active\n"),
        subprocess.TimeoutExpired("dcv", 10),
        Mock(returncode=0, stdout="active\n"),
        subprocess.TimeoutExpired("dcv", 10)
    ]
    monkeypatch.setattr("subprocess.run", mock_run)
    
    mock_time = Mock()
    mock_time.side_effect = [0, 1, 2, 5, 6, 7, 10, 11, 12, 15, 16, 17, 20, 21, 22]
    monkeypatch.setattr("time.time", mock_time)
    monkeypatch.setattr("time.sleep", Mock())
    
    result = start_dcv_service.is_dcvserver_ready(timeout_seconds=10, retry_interval=2)
    
    assert result is False


def test_configure_calls_both_services(monkeypatch) -> None:
    """Test that configure function calls both DCV service and agent configuration"""
    mock_dcv_service = Mock()
    mock_agent_service = Mock()

    monkeypatch.setattr("ideabootstrap.dcv.linux.start_dcv_service._start_and_configure_dcv_service", mock_dcv_service)
    monkeypatch.setattr("ideabootstrap.dcv.linux.start_dcv_service._start_and_configure_dcv_agent_service", mock_agent_service)

    start_dcv_service.configure()

    mock_dcv_service.assert_called_once()
    mock_agent_service.assert_called_once()
