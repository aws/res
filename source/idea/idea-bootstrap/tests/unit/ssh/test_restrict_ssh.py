#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import tempfile
from unittest.mock import Mock, call
import pytest
from ideabootstrap.ssh import constants, restrict_ssh
from res.resources import cluster_settings


@pytest.mark.parametrize(
    "base_os, expected_user",
    [("rhel8", "ec2-user"), ("ubuntu", "")],
)
def test_default_system_user(monkeypatch, base_os, expected_user) -> None:
    monkeypatch.setenv("RES_BASE_OS", base_os)
    system_user = restrict_ssh._default_system_user()

    assert system_user == expected_user


@pytest.mark.parametrize(
    "session_owner, base_os, content_exists",
    [
        (True, "rhel8", False),
        (True, "rhel8", True),
        (False, "ubuntu", False),
        (True, "ubuntu", False),
    ],
)
def test_restrict_ssh(monkeypatch, session_owner, base_os, content_exists) -> None:

    mock_run = Mock()
    expected_calls = [
        call(["systemctl", "restart", "sshd"], check=True),
    ]
    monkeypatch.setenv("RES_BASE_OS", base_os)
    monkeypatch.setenv("IDEA_SESSION_OWNER", "user1")
    monkeypatch.setattr(
        "ideabootstrap.ssh.restrict_ssh.file_content_exists",
        lambda content, path: content_exists,
    )
    monkeypatch.setattr(cluster_settings, "get_setting", lambda key: "admin")
    monkeypatch.setattr("subprocess.run", mock_run)

    with tempfile.NamedTemporaryFile(mode="w", delete=True) as temp_file:
        temp_file_name = temp_file.name
        monkeypatch.setattr(constants, "SSHD_CONFIG_PATH", temp_file_name)

        restrict_ssh.configure(session_owner)

        with open(temp_file_name, "r") as f:
            content = f.read()
            if not content_exists:
                if session_owner:
                    assert "AllowUsers user1" in content
                else:
                    if base_os == "rhel8":
                        assert (
                            "AllowGroups ec2-user ssm-user admin-user-group" in content
                        )
                    else:
                        assert "AllowGroups" not in content
                assert mock_run.call_args_list == (expected_calls)
            else:
                assert content == ""
                assert mock_run.call_args_list == []
