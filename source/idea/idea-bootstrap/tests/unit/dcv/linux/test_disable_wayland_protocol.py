#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import tempfile
from unittest.mock import Mock, call
import pytest
from ideabootstrap.dcv import constants
from ideabootstrap.dcv.linux import disable_wayland_protocol


def test_configure_wayland() -> None:
    with tempfile.NamedTemporaryFile(mode="w", delete=True) as temp_file:
        temp_file_name = temp_file.name
        wayland_config = "WaylandEnable=false"
        temp_file_initial_content = f"#{wayland_config}"
        temp_file.write(temp_file_initial_content)
        temp_file.flush()
        disable_wayland_protocol._configure_wayland(wayland_config, temp_file_name)
        with open(temp_file_name, "r") as f:
            content = f.read()

    assert f"{wayland_config}\n" == content


@pytest.mark.parametrize(
    "base_os, config_path , service",
    [
        ("rhel9", constants.GDM_CONFIG_RHEL_PATH, "gdm"),
        ("rocky9", constants.GDM_CONFIG_RHEL_PATH, "gdm"),
        ("rhel8", constants.GDM_CONFIG_RHEL_PATH, "gdm"),
        ("ubuntu2204", constants.GDM_CONFIG_DEBIAN_PATH, "gdm3"),
    ],
)
def test_configure_wayland_different_os(
    monkeypatch, base_os, config_path, service
) -> None:
    monkeypatch.setenv("RES_BASE_OS", base_os)
    mock_wayland = Mock()
    mock_run = Mock()
    expected_calls = [
        call(["systemctl", "restart", service], check=True),
    ]

    monkeypatch.setattr(disable_wayland_protocol, "_configure_wayland", mock_wayland)
    monkeypatch.setattr("subprocess.run", mock_run)

    disable_wayland_protocol.configure()

    if base_os != "rhel8":
        mock_wayland.assert_called_once_with("WaylandEnable=false", config_path)
        mock_run.call_args_list == (expected_calls)
    else:
        mock_wayland.assert_not_called()
        mock_run.call_args_list == []
