#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import subprocess
from unittest.mock import Mock, call

import pytest
from ideabootstrap.ssh import disable_ssh


@pytest.mark.parametrize(
    "success, log_msg",
    [(True, "Success"), (False, "Error")],
)
def test_configure_ssh(monkeypatch, success, log_msg) -> None:
    logs = []
    mock_run = Mock()
    expected_calls = [
        call(["systemctl", "disable", "sshd.socket"], check=True),
        call(["systemctl", "disable", "sshd.service"], check=True),
        call(["systemctl", "stop", "sshd.socket"], check=True),
        call(["systemctl", "stop", "sshd.service"], check=True),
    ]

    if not success:
        mock_run.side_effect = subprocess.CalledProcessError(1, "cmd")

    monkeypatch.setattr("ideabootstrap.ssh.disable_ssh.logger.info", logs.append)
    monkeypatch.setattr("ideabootstrap.ssh.disable_ssh.logger.error", logs.append)
    monkeypatch.setattr("subprocess.run", mock_run)

    disable_ssh.configure()

    assert log_msg in logs[0]
    assert mock_run.call_args_list == (
        expected_calls if success else expected_calls[:1]
    )
