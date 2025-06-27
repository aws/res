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
