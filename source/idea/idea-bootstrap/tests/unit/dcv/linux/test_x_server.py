#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from unittest.mock import Mock, call, patch
import pytest
from ideabootstrap.dcv.linux import x_server


def test_x_server_validated(monkeypatch) -> None:
    mock_ps = Mock(return_value="X -auth /tmp/xauth")
    mock_xhost = Mock(return_value="SI:localuser:dcv")

    monkeypatch.setattr(
        "subprocess.check_output",
        lambda cmd, **kwargs: mock_ps() if cmd[0] == "ps" else mock_xhost(),
    )

    assert x_server._x_server_validated() is True


@patch("time.sleep", return_value=None)
def test_verify_x_server_is_up_success(mock_sleep, monkeypatch) -> None:
    mock_validated = Mock(side_effect=[False, True])

    monkeypatch.setattr(x_server, "_x_server_validated", mock_validated)

    x_server._verify_x_server_is_up()

    assert mock_validated.call_count == 2
    assert mock_sleep.call_count == 2


@patch("time.sleep", return_value=None)
@patch("time.time", side_effect=[0, 130, 140])
def test_verify_x_server_timeout(mock_time, mock_sleep, monkeypatch) -> None:
    logs = []
    monkeypatch.setattr("ideabootstrap.dcv.linux.x_server.logger.info", logs.append)
    monkeypatch.setattr(x_server, "_x_server_validated", lambda: False)

    x_server._verify_x_server_is_up()

    assert "Max timeout for verify server reached" in logs[-1]


def test_start_x_server_already_started(monkeypatch) -> None:
    mock_run = Mock()
    monkeypatch.setattr(x_server, "_x_server_validated", lambda: True)
    monkeypatch.setattr("subprocess.run", mock_run)

    x_server._start_x_server()

    mock_run.assert_not_called()


def test_start_x_server_required(monkeypatch) -> None:
    mock_run = Mock()
    monkeypatch.setattr(x_server, "_x_server_validated", lambda: False)
    monkeypatch.setattr("subprocess.run", mock_run)

    x_server._start_x_server()

    mock_run.assert_called_once_with(
        ["sudo", "systemctl", "isolate", "graphical.target"], check=True
    )


def test_restart_x_server(monkeypatch) -> None:
    mock_run = Mock()
    monkeypatch.setattr("subprocess.run", mock_run)
    expected_calls = [
        call(["sudo", "systemctl", "isolate", "multi-user.target"], check=True),
        call(["sudo", "systemctl", "isolate", "graphical.target"], check=True),
    ]

    x_server._restart_x_server()

    mock_run.call_args_list == expected_calls

def test_configure_aarch64(monkeypatch) -> None:
    machine = "aarch64"
    monkeypatch.setenv("MACHINE", machine)
    mock_run = Mock()
    mock_start_x_server = Mock()
    monkeypatch.setattr("subprocess.run", mock_run)
    monkeypatch.setattr(x_server, "_start_and_validate_x_server", mock_start_x_server)

    x_server.configure()

    mock_run.assert_not_called()

def test_configure_x86_64(monkeypatch) -> None:
    monkeypatch.setenv("MACHINE", "x86_64")  
    monkeypatch.setenv("RES_BASE_OS", "amzn2")  
    
    mock_run = Mock()
    mock_start_x_server = Mock()
    monkeypatch.setattr("subprocess.run", mock_run)
    monkeypatch.setattr(x_server, "_start_and_validate_x_server", mock_start_x_server)

    x_server.configure()

    mock_run.assert_called_once_with(
        ["sudo", "systemctl", "set-default", "graphical.target"], check=True
    )
    mock_start_x_server.assert_called_once()
