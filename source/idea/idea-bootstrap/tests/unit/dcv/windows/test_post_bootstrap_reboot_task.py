#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import tempfile
from unittest.mock import Mock
from ideabootstrap import bootstrap_common
from ideabootstrap.dcv import constants
from ideabootstrap.dcv.windows import post_bootstrap_reboot_task
from res.resources import cluster_settings


def test_configure_not_ad(monkeypatch) -> None:
    mock_overwrite = Mock()
    mock_run = Mock()

    monkeypatch.setenv("IDEA_SESSION_OWNER", "testuser")
    monkeypatch.setattr(cluster_settings, "get_setting", lambda x: "test")
    monkeypatch.setattr(bootstrap_common, "overwrite_file", mock_overwrite)
    monkeypatch.setattr("subprocess.run", mock_run)

    post_bootstrap_reboot_task.configure()

    mock_run.assert_not_called()
    mock_overwrite.assert_not_called()


def test_configure_success(monkeypatch) -> None:
    mock_run = Mock()

    monkeypatch.setenv("IDEA_SESSION_OWNER", "testuser")
    monkeypatch.setattr(cluster_settings, "get_setting", lambda x: "activedirectory")
    monkeypatch.setattr("subprocess.run", mock_run)

    with tempfile.NamedTemporaryFile(mode="w", delete=True) as temp_file:
        temp_file_name = temp_file.name
        monkeypatch.setattr(constants, "POST_REBOOT_SCRIPT_PATH", temp_file_name)
        post_bootstrap_reboot_task.configure()

        with open(temp_file_name, "r") as f:
            content = f.read()

    assert "PostBootstrapRebootExecuteOnce" in content
    assert mock_run.call_count == 1
