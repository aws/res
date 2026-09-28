#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import subprocess
from unittest.mock import Mock, call, patch

import pytest
from ideabootstrap.dcv import constants
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
        ["systemctl", "isolate", "graphical.target"],
        check=True,
        timeout=constants.SUBPROCESS_TIMEOUT_SEC,
    )


def test_restart_x_server(monkeypatch) -> None:
    mock_run = Mock()
    monkeypatch.setattr("subprocess.run", mock_run)
    expected_calls = [
        call(
            ["systemctl", "isolate", "multi-user.target"],
            check=True,
            timeout=constants.SUBPROCESS_TIMEOUT_SEC,
        ),
        call(
            ["systemctl", "isolate", "graphical.target"],
            check=True,
            timeout=constants.SUBPROCESS_TIMEOUT_SEC,
        ),
    ]

    x_server._restart_x_server()

    assert mock_run.call_args_list == expected_calls


def test_configure_virtual_session_type(monkeypatch) -> None:
    monkeypatch.setenv("SESSION_TYPE", "VIRTUAL")
    mock_run = Mock()
    mock_start_x_server = Mock()
    monkeypatch.setattr("subprocess.run", mock_run)
    monkeypatch.setattr(x_server, "_start_and_validate_x_server", mock_start_x_server)

    x_server.configure()

    mock_run.assert_not_called()


def test_configure_console_session_type(monkeypatch) -> None:
    monkeypatch.setenv("SESSION_TYPE", "CONSOLE")
    monkeypatch.setenv("RES_BASE_OS", "amzn2")

    mock_run = Mock()
    mock_start_x_server = Mock()
    mock_divert = Mock()
    mock_ensure_xorg = Mock()
    monkeypatch.setattr("subprocess.run", mock_run)
    monkeypatch.setattr(x_server, "_start_and_validate_x_server", mock_start_x_server)
    monkeypatch.setattr(x_server, "_divert_xorg_to_xdcv", mock_divert)
    monkeypatch.setattr(x_server, "ensure_xorg_config", mock_ensure_xorg)

    x_server.configure()

    mock_ensure_xorg.assert_called_once()
    mock_divert.assert_called_once()
    mock_run.assert_called_once_with(
        ["systemctl", "set-default", "graphical.target"],
        check=True,
        timeout=constants.SUBPROCESS_TIMEOUT_SEC,
    )
    mock_start_x_server.assert_called_once()


class TestDivertXorgToXdcv:
    def test_skips_gpu_instance(self, monkeypatch) -> None:
        monkeypatch.setenv("RES_BASE_OS", "ubuntu2204")
        mock_run = Mock()
        monkeypatch.setattr("subprocess.run", mock_run)
        monkeypatch.setattr(
            "ideabootstrap.dcv.linux.x_server._is_gpu_instance_type", lambda: True
        )

        x_server._divert_xorg_to_xdcv()

        mock_run.assert_not_called()

    def test_skips_when_xdcv_console_missing(self, monkeypatch) -> None:
        monkeypatch.setenv("RES_BASE_OS", "ubuntu2204")
        mock_run = Mock()
        monkeypatch.setattr("subprocess.run", mock_run)
        monkeypatch.setattr(
            "ideabootstrap.dcv.linux.x_server._is_gpu_instance_type", lambda: False
        )
        monkeypatch.setattr("os.path.isfile", lambda p: False)

        x_server._divert_xorg_to_xdcv()

        mock_run.assert_not_called()

    def test_noop_for_non_ubuntu_os(self, monkeypatch) -> None:
        monkeypatch.setenv("RES_BASE_OS", "rhel9")
        mock_run = Mock()
        monkeypatch.setattr("subprocess.run", mock_run)
        monkeypatch.setattr(
            "ideabootstrap.dcv.linux.x_server._is_gpu_instance_type", lambda: False
        )
        monkeypatch.setattr("os.path.isfile", lambda p: True)

        x_server._divert_xorg_to_xdcv()

        mock_run.assert_not_called()

    def test_ubuntu_skips_when_already_diverted(self, monkeypatch) -> None:
        monkeypatch.setenv("RES_BASE_OS", "ubuntu2404")
        mock_run = Mock()
        monkeypatch.setattr("subprocess.run", mock_run)
        monkeypatch.setattr(
            "ideabootstrap.dcv.linux.x_server._is_gpu_instance_type", lambda: False
        )
        monkeypatch.setattr("os.path.isfile", lambda p: True)
        monkeypatch.setattr("os.path.islink", lambda p: True)
        monkeypatch.setattr("os.readlink", lambda p: "/usr/bin/Xdcv-console")

        x_server._divert_xorg_to_xdcv()

        mock_run.assert_not_called()

    def test_ubuntu2204_diverts(self, monkeypatch) -> None:
        monkeypatch.setenv("RES_BASE_OS", "ubuntu2204")
        mock_run = Mock()
        monkeypatch.setattr("subprocess.run", mock_run)
        monkeypatch.setattr(
            "ideabootstrap.dcv.linux.x_server._is_gpu_instance_type", lambda: False
        )
        monkeypatch.setattr("os.path.isfile", lambda p: True)
        monkeypatch.setattr("os.path.islink", lambda p: False)

        x_server._divert_xorg_to_xdcv()

        assert mock_run.call_count == 2
        mock_run.assert_any_call(
            [
                "dpkg-divert",
                "--package",
                "nice-xdcv",
                "--divert",
                "/usr/bin/Xorg.orig",
                "--rename",
                "/usr/bin/Xorg",
            ],
            check=True,
            timeout=constants.SUBPROCESS_TIMEOUT_SEC,
        )
        mock_run.assert_any_call(
            ["ln", "-sf", "/usr/bin/Xdcv-console", "/usr/bin/Xorg"],
            check=True,
            timeout=constants.SUBPROCESS_TIMEOUT_SEC,
        )

    def test_ubuntu2404_diverts(self, monkeypatch) -> None:
        monkeypatch.setenv("RES_BASE_OS", "ubuntu2404")
        mock_run = Mock()
        monkeypatch.setattr("subprocess.run", mock_run)
        monkeypatch.setattr(
            "ideabootstrap.dcv.linux.x_server._is_gpu_instance_type", lambda: False
        )
        monkeypatch.setattr("os.path.isfile", lambda p: True)
        monkeypatch.setattr("os.path.islink", lambda p: False)

        x_server._divert_xorg_to_xdcv()

        assert mock_run.call_count == 2

    def test_handles_error_gracefully(self, monkeypatch) -> None:
        monkeypatch.setenv("RES_BASE_OS", "ubuntu2404")
        monkeypatch.setattr(
            "ideabootstrap.dcv.linux.x_server._is_gpu_instance_type", lambda: False
        )
        monkeypatch.setattr("os.path.isfile", lambda p: True)
        monkeypatch.setattr("os.path.islink", lambda p: False)
        monkeypatch.setattr(
            "subprocess.run", Mock(side_effect=Exception("dpkg-divert failed"))
        )

        # Should not raise
        x_server._divert_xorg_to_xdcv()


class TestEnsureXorgConfig:
    def test_skips_non_gpu_instance(self, monkeypatch) -> None:
        mock_run = Mock()
        monkeypatch.setattr("subprocess.run", mock_run)
        monkeypatch.setattr(
            "ideabootstrap.dcv.linux.x_server._is_gpu_instance_type", lambda: False
        )

        x_server.ensure_xorg_config()

        mock_run.assert_not_called()

    def test_runs_nvidia_xconfig_on_gpu_instance(self, monkeypatch) -> None:
        mock_run = Mock()
        monkeypatch.setattr("subprocess.run", mock_run)
        monkeypatch.setattr(
            "ideabootstrap.dcv.linux.x_server._is_gpu_instance_type", lambda: True
        )

        x_server.ensure_xorg_config()

        mock_run.assert_called_once_with(
            ["nvidia-xconfig", "--preserve-busid", "--enable-all-gpus"],
            check=True,
            capture_output=True,
        )

    def test_handles_error_gracefully(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "ideabootstrap.dcv.linux.x_server._is_gpu_instance_type", lambda: True
        )
        monkeypatch.setattr(
            "subprocess.run",
            Mock(side_effect=FileNotFoundError("nvidia-xconfig not found")),
        )

        # Should not raise
        x_server.ensure_xorg_config()

    def test_handles_called_process_error(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "ideabootstrap.dcv.linux.x_server._is_gpu_instance_type", lambda: True
        )
        monkeypatch.setattr(
            "subprocess.run",
            Mock(side_effect=subprocess.CalledProcessError(1, "nvidia-xconfig")),
        )

        # Should not raise
        x_server.ensure_xorg_config()
