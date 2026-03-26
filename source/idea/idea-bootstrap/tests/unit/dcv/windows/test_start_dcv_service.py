#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from unittest.mock import Mock, call
from ideabootstrap.dcv import constants
from ideabootstrap.dcv.windows import start_dcv_service


def test_configure(monkeypatch) -> None:
    mock_rmtree = Mock()
    mock_run = Mock()
    expected_calls = [
        call(
            ["powershell.exe", "-Command", "Start-Service -Name dcvserver"], check=True
        ),
        call(
            [
                "powershell.exe",
                "-Command",
                "Start-Service -Name DcvSessionManagerAgentService",
            ],
            check=True,
        ),
    ]

    monkeypatch.setattr("os.path.exists", lambda x: True)
    monkeypatch.setattr("shutil.rmtree", mock_rmtree)
    monkeypatch.setattr("subprocess.run", mock_run)

    start_dcv_service.configure()

    mock_rmtree.assert_called_once_with(constants.WINDOWS_DCV_CERT_DIR)
    mock_run.call_args_list == expected_calls


def test_configure_no_cert_dir(monkeypatch) -> None:
    mock_rmtree = Mock()
    mock_run = Mock()

    monkeypatch.setattr("os.path.exists", lambda x: False)
    monkeypatch.setattr("shutil.rmtree", mock_rmtree)
    monkeypatch.setattr("subprocess.run", mock_run)

    start_dcv_service.configure()

    mock_rmtree.call_count == 0
    mock_run.call_count == 2


def test_is_dcvserver_ready_success(monkeypatch) -> None:
    """Test successful DCV server readiness check on Windows"""
    mock_run = Mock()
    mock_run.side_effect = [
        Mock(returncode=0, stdout="Running\n"),
        Mock(returncode=0, stdout="DCV server is running\n")
    ]
    monkeypatch.setattr("subprocess.run", mock_run)
    monkeypatch.setattr("time.sleep", Mock())
    
    result = start_dcv_service.is_dcvserver_ready(timeout_seconds=10, retry_interval=1)
    
    assert result is True
    expected_calls = [
        call(["powershell.exe", "-Command", "Get-Service -Name dcvserver | Select-Object -ExpandProperty Status"], 
             capture_output=True, text=True, check=False),
        call([constants.WINDOWS_DCV_EXECUTABLE_PATH, "list-sessions"], 
             capture_output=True, text=True, check=False, timeout=10)
    ]
    assert mock_run.call_args_list == expected_calls


def test_is_dcvserver_ready_service_not_running(monkeypatch) -> None:
    """Test DCV server readiness check when Windows service is not running"""
    mock_run = Mock()
    mock_run.side_effect = [
        Mock(returncode=0, stdout="Stopped\n"),
        Mock(returncode=0, stdout="Stopped\n")
    ]
    monkeypatch.setattr("subprocess.run", mock_run)
    
    mock_time = Mock()
    mock_time.side_effect = [0, 1, 2, 5, 6, 7, 10, 11, 12, 15, 16, 17, 20, 21, 22]
    monkeypatch.setattr("time.time", mock_time)
    monkeypatch.setattr("time.sleep", Mock())
    
    result = start_dcv_service.is_dcvserver_ready(timeout_seconds=10, retry_interval=2)
    
    assert result is False


def test_is_dcvserver_ready_status_command_fails(monkeypatch) -> None:
    """Test DCV server readiness check when status command fails on Windows"""
    mock_run = Mock()
    mock_run.side_effect = [
        Mock(returncode=0, stdout="Running\n"),
        Mock(returncode=1, stderr="DCV server not responding\n"),
        Mock(returncode=0, stdout="Running\n"),
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
    """Test DCV server readiness check when subprocess times out on Windows"""
    import subprocess
    
    mock_run = Mock()
    mock_run.side_effect = [
        Mock(returncode=0, stdout="Running\n"),
        subprocess.TimeoutExpired("dcv.exe", 10),
        Mock(returncode=0, stdout="Running\n"),
        subprocess.TimeoutExpired("dcv.exe", 10)
    ]
    monkeypatch.setattr("subprocess.run", mock_run)
    
    mock_time = Mock()
    mock_time.side_effect = [0, 1, 2, 5, 6, 7, 10, 11, 12, 15, 16, 17, 20, 21, 22]
    monkeypatch.setattr("time.time", mock_time)
    monkeypatch.setattr("time.sleep", Mock())
    
    result = start_dcv_service.is_dcvserver_ready(timeout_seconds=10, retry_interval=2)
    
    assert result is False


def test_is_dcvserver_ready_service_command_fails(monkeypatch) -> None:
    """Test DCV server readiness check when PowerShell service command fails"""
    mock_run = Mock()
    mock_run.side_effect = [
        Mock(returncode=1, stderr="Service 'dcvserver' could not be found\n"),
        Mock(returncode=1, stderr="Service 'dcvserver' could not be found\n")
    ]
    monkeypatch.setattr("subprocess.run", mock_run)
    
    mock_time = Mock()
    mock_time.side_effect = [0, 1, 2, 5, 6, 7, 10, 11, 12, 15, 16, 17, 20, 21, 22]
    monkeypatch.setattr("time.time", mock_time)
    monkeypatch.setattr("time.sleep", Mock())
    
    result = start_dcv_service.is_dcvserver_ready(timeout_seconds=10, retry_interval=2)
    
    assert result is False
