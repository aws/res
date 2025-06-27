#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import subprocess
import tempfile
from unittest.mock import Mock

from ideabootstrap.file_system.windows import constants, shared_storage
from res.resources import cluster_settings


def test_mount_shared_storage_ontap_write_to_batch_file(monkeypatch):
    monkeypatch.setattr(cluster_settings, "get_setting", lambda _: "CORP")
    monkeypatch.setenv("SESSION_OWNER", "admin1")
    monkeypatch.setattr(os, "makedirs", lambda _, exist_ok: None)
    subprocess_run_mock = Mock()
    subprocess_run_mock.stdout = Mock()
    monkeypatch.setattr(subprocess, "run", lambda _, check, capture_output, text: subprocess_run_mock)
    monkeypatch.setattr(shared_storage.logger, "info", Mock())
    monkeypatch.setattr(
        cluster_settings,
        "get_config",
        lambda x: {
            "test_ontap": {
                "provider": "fsx_netapp_ontap",
                "mount_drive": "ontap_mount_drive",
                "fsx_netapp_ontap": {
                    'svm': {'smb_dns': "ontap_smb_dns"},
                    "volume": {
                        "cifs_share_name": "ontap_cifs_share_name",
                    },
                },
            },
        },
    )

    with tempfile.NamedTemporaryFile(mode="w", delete=True) as temp_file:
        temp_file_name = temp_file.name
        monkeypatch.setattr(constants, "BATCH_FILE_PATH", temp_file_name)

        shared_storage.mount_shared_storage()

        batch_commands = [
            "if not exist ontap_mount_drive: "
            '(net use ontap_mount_drive: \\\\ontap_smb_dns\\ontap_cifs_share_name /persistent:yes)'
        ]

        with open(constants.BATCH_FILE_PATH, "r") as f:
            assert "\n".join(batch_commands) in f.readlines()


def test_mount_shared_storage_file_system_write_to_batch_file(monkeypatch):
    monkeypatch.setattr(cluster_settings, "get_setting", lambda _: "CORP")
    monkeypatch.setenv("SESSION_OWNER", "admin1")
    monkeypatch.setattr(os, "makedirs", lambda _, exist_ok: None)
    subprocess_run_mock = Mock()
    subprocess_run_mock.stdout = Mock()
    monkeypatch.setattr(subprocess, "run", lambda _, check, capture_output, text: subprocess_run_mock)
    monkeypatch.setattr(shared_storage.logger, "info", Mock())
    monkeypatch.setattr(
        cluster_settings,
        "get_config",
        lambda x: {
            "test_file_server": {
                "provider": "fsx_windows_file_server",
                "mount_drive": "file_server_mount_drive",
                "fsx_windows_file_server": {
                    "dns": "file_server_dns",
                },
            }
        },
    )

    with tempfile.NamedTemporaryFile(mode="w", delete=True) as temp_file:
        temp_file_name = temp_file.name
        monkeypatch.setattr(constants, "BATCH_FILE_PATH", temp_file_name)

        shared_storage.mount_shared_storage()

        batch_commands = [
            "if not exist file_server_mount_drive: "
            '(net use file_server_mount_drive: \\\\file_server_dns\\share /persistent:yes)'
        ]

        with open(constants.BATCH_FILE_PATH, "r") as f:
            assert "\n".join(batch_commands) in f.readlines()
