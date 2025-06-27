#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import tempfile
from unittest.mock import Mock, call

import pytest
from ideabootstrap.dcv import constants
from ideabootstrap.dcv import dcv_agent


@pytest.mark.parametrize(
    "base_os",
    [
        ("windows"),
        ("rhel8"),
    ],
)
def test_configure_usb_remotization(monkeypatch, base_os) -> None:

    monkeypatch.setattr(
        "res.resources.cluster_settings.get_setting",
        Mock(return_value=["device1", "device2"]),
    )
    monkeypatch.setattr("ideabootstrap.dcv.dcv_agent.BASE_OS", base_os)

    with tempfile.NamedTemporaryFile(mode="w", delete=True) as temp_file:
        temp_file_name = temp_file.name
        if base_os == "windows":
            monkeypatch.setattr(
                constants, "WINDOWS_USB_DEVICES_CONF_FILE_PATH", temp_file_name
            )
        else:
            monkeypatch.setattr(constants, "USB_DEVICES_CONF_FILE_PATH", temp_file_name)

        dcv_agent._configure_usb_remotization()

        with open(temp_file_name, "r") as f:
            content = f.read()

    assert "device1" in content
    assert "device2" in content


@pytest.mark.parametrize(
    "base_os",
    [
        ("windows"),
        ("rhel8"),
    ],
)
def test_configure_agent_conf(monkeypatch, base_os) -> None:
    monkeypatch.setattr(
        "ideabootstrap.dcv.dcv_utils.get_cluster_internal_endpoint",
        lambda: "https://internal-alb.example.com",
    )
    monkeypatch.setattr("res.resources.cluster_settings.get_setting", lambda x: 8443)
    monkeypatch.setattr("os.path.exists", lambda x: False)
    monkeypatch.setattr("ideabootstrap.dcv.dcv_agent.BASE_OS", base_os)

    with tempfile.NamedTemporaryFile(mode="w", delete=True) as temp_file:
        temp_file_name = temp_file.name
        if base_os == "windows":
            monkeypatch.setattr(
                constants, "WINDOWS_DCV_AGENT_CONFIG_FILE_PATH", temp_file_name
            )
        else:
            monkeypatch.setattr(constants, "DCV_AGENT_CONFIG_FILE_PATH", temp_file_name)

        dcv_agent._configure_agent_conf()
        with open(temp_file_name, "r") as f:
            content = f.read()

    assert "broker_host = 'internal-alb.example.com'" in content
    assert "broker_port = 8443" in content
    if base_os == "windows":
        assert constants.WINDOWS_DCV_AGENT_TAGS_DIR in content
    else:
        assert constants.DCV_AGENT_TAGS_DIR in content


@pytest.mark.parametrize(
    "base_os",
    [
        ("windows"),
        ("rhel8"),
    ],
)
def test_configure_tags(monkeypatch, base_os) -> None:
    monkeypatch.setenv("IDEA_SESSION_ID", "test-session")
    mock_makedirs = Mock()
    mock_write = Mock()

    monkeypatch.setattr("os.makedirs", mock_makedirs)
    monkeypatch.setattr("os.path.exists", lambda x: True)
    monkeypatch.setattr("os.rename", Mock())
    monkeypatch.setattr("ideabootstrap.dcv.dcv_agent.overwrite_file", mock_write)
    monkeypatch.setattr("time.time", lambda: 123456)
    monkeypatch.setattr("ideabootstrap.dcv.dcv_agent.BASE_OS", base_os)

    dcv_agent._configure_tags()

    tags_dir = (
        constants.WINDOWS_DCV_AGENT_TAGS_DIR
        if base_os == "windows"
        else constants.DCV_AGENT_TAGS_DIR
    )
    archive_tags_dir = (
        constants.WINDOWS_DCV_AGENT_ARCHIVE_TAGS_DIR
        if base_os == "windows"
        else constants.DCV_AGENT_ARCHIVE_TAGS_DIR
    )
    mock_makedirs.assert_has_calls(
        [
            call(tags_dir, exist_ok=True),
            call(archive_tags_dir, exist_ok=True),
        ]
    )
    mock_write.assert_called_once_with(
        'idea_session_id="test-session"',
        os.path.join(tags_dir, constants.DCV_AGENT_TAGS_FILE_NAME),
    )

@pytest.mark.parametrize(
    "base_os",
    [
        ("windows"),
        ("rhel8"),
    ],
)
def test_configure(monkeypatch, base_os) -> None:
    mock_run = Mock()
    mock_config_helper = Mock()
    expected_calls = [
        call(
            [
                "powershell.exe",
                "-Command",
                "Set-Service -Name DcvSessionManagerAgentService -StartupType Automatic",
            ],
            check=True,
        )
    ]

    monkeypatch.setattr(dcv_agent, "_configure_tags", mock_config_helper)
    monkeypatch.setattr(dcv_agent, "_configure_agent_conf", mock_config_helper)
    monkeypatch.setattr(dcv_agent, "_configure_usb_remotization", mock_config_helper)
    monkeypatch.setattr("subprocess.run", mock_run)
    monkeypatch.setattr("ideabootstrap.dcv.dcv_agent.BASE_OS", base_os)

    dcv_agent.configure()

    mock_config_helper.call_count == 3
    if base_os == "windows":
        assert mock_run.call_args_list == expected_calls
    else:
        assert mock_run.call_args_list == []