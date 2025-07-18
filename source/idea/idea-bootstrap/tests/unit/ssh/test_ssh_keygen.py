#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import tempfile
from unittest.mock import Mock, call
import pytest
from ideabootstrap.ssh import constants, ssh_keygen
from res.resources import cluster_settings


@pytest.mark.parametrize(
    "base_os, content_exists",
    [("rhel8", False), ("ubuntu2204", True), ("ubuntu2404", True), ("invalid_os", False)],
)
def test_ssh_keygen(monkeypatch, base_os, content_exists) -> None:

    mock_run = Mock()
    expected_calls = [
        call(["su", "-", "user1", "-c", "exit"], check=True),
    ]
    monkeypatch.setenv("RES_BASE_OS", base_os)
    monkeypatch.setenv("IDEA_SESSION_OWNER", "user1")
    monkeypatch.setattr(
        "ideabootstrap.ssh.ssh_keygen.file_content_exists",
        lambda content, path: content_exists,
    )
    monkeypatch.setattr(cluster_settings, "get_setting", lambda key: "admin")
    monkeypatch.setattr("subprocess.run", mock_run)

    with tempfile.NamedTemporaryFile(mode="w", delete=True) as temp_file:
        temp_file_name = temp_file.name
        temp_file_initial_content = "session\n"
        temp_file.write(temp_file_initial_content)
        temp_file.flush()
        monkeypatch.setattr(constants, "UBUNTU_PAM_FILE_PATH", temp_file_name)
        monkeypatch.setattr(constants, "RED_HAT_PAM_FILES_PATH", [temp_file_name])
        ssh_keygen.configure()

        with open(temp_file_name, "r") as f:
            content = f.read()
            if content_exists:
                assert content == temp_file_initial_content
                assert mock_run.call_args_list == (expected_calls)
            else:
                if base_os == "invalid_os":
                    assert content == temp_file_initial_content
                    assert mock_run.call_args_list == []
                else:
                    assert "ssh_keygen" in content
                    assert mock_run.call_args_list == (expected_calls)


def test_setup_pam_exist(monkeypatch):
    with tempfile.NamedTemporaryFile(mode="w", delete=True) as temp_file:
        temp_file_name = temp_file.name
        temp_file_initial_content = "session\toptional\tssh_keygen.so\n"
        temp_file.write(temp_file_initial_content)
        temp_file.flush()
        ssh_keygen._setup_pam(temp_file_name)

        with open(temp_file_name, "r") as f:
            content = f.read()
            assert content == temp_file_initial_content
