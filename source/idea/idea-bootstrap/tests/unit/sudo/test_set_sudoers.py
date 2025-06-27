#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import tempfile
from ideabootstrap.sudo import constants, set_sudoers
from res.resources import accounts, cluster_settings


def test_set_sudoers(monkeypatch) -> None:
    monkeypatch.setattr(
        accounts,
        "list_users",
        lambda admin: [
            {"username": "user1", "additional_groups": ["sudo_group"]},
            {"username": "user2", "additional_groups": []},
        ],
    )
    monkeypatch.setattr(cluster_settings, "get_setting", lambda key: "sudo_group")
    monkeypatch.setattr(set_sudoers, "file_content_exists", lambda value, path: False)

    with tempfile.NamedTemporaryFile(mode="w", delete=True) as temp_file:
        temp_file_name = temp_file.name
        monkeypatch.setattr(constants, "SUDOERS_FILE", temp_file_name)
        monkeypatch.setattr(constants, "NSSWITCH_FILE", temp_file_name)

        set_sudoers.configure()

        with open(temp_file_name, "r") as f:
            content = f.read()
            assert "sudo_group" in content
            assert "user2" in content
            assert "user1" not in content
            assert "sudoers: files" in content
