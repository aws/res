#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import shutil
import subprocess
import tempfile
from unittest.mock import Mock, call

from ideabootstrap.file_system.linux import constants, s3_mount


def test_get_bucket_name_valid_arn_return_bucket_name():
    assert s3_mount.get_bucket_name("arn:aws:s3:::bucket") == "bucket"


def test_get_bucket_name_invalid_arn_return_empty():
    assert s3_mount.get_bucket_name("arn:aws:s3:bucket::bucket") == ""


def test_get_prefix_for_object_storage_read_only_return_prefix():
    assert s3_mount.get_prefix_for_object_storage("arn:aws:s3:::bucket", True) == ""
    assert (
        s3_mount.get_prefix_for_object_storage("arn:aws:s3:::bucket/folder", True)
        == "folder/"
    )


def test_get_prefix_for_object_storage_read_write_no_custom_prefix_return_prefix():
    assert (
        s3_mount.get_prefix_for_object_storage(
            "arn:aws:s3:::bucket", False, constants.OBJECT_STORAGE_NO_CUSTOM_PREFIX
        )
        == ""
    )
    assert (
        s3_mount.get_prefix_for_object_storage(
            "arn:aws:s3:::bucket/folder",
            False,
            constants.OBJECT_STORAGE_NO_CUSTOM_PREFIX,
        )
        == "folder/"
    )


def test_get_prefix_for_object_storage_read_write_project_name_prefix_return_prefix(
    monkeypatch,
):
    monkeypatch.setenv("PROJECT_NAME", "project")

    assert (
        s3_mount.get_prefix_for_object_storage(
            "arn:aws:s3:::bucket",
            False,
            constants.OBJECT_STORAGE_CUSTOM_PROJECT_NAME_PREFIX,
        )
        == "project/"
    )
    assert (
        s3_mount.get_prefix_for_object_storage(
            "arn:aws:s3:::bucket/folder",
            False,
            constants.OBJECT_STORAGE_CUSTOM_PROJECT_NAME_PREFIX,
        )
        == "folder/project/"
    )


def test_get_prefix_for_object_storage_read_write_project_name_and_username_prefix_return_prefix(
    monkeypatch,
):
    monkeypatch.setenv("PROJECT_NAME", "project")
    monkeypatch.setenv("IDEA_SESSION_OWNER", "user")

    assert (
        s3_mount.get_prefix_for_object_storage(
            "arn:aws:s3:::bucket",
            False,
            constants.OBJECT_STORAGE_CUSTOM_PROJECT_NAME_AND_USERNAME_PREFIX,
        )
        == "project/user/"
    )
    assert (
        s3_mount.get_prefix_for_object_storage(
            "arn:aws:s3:::bucket/folder",
            False,
            constants.OBJECT_STORAGE_CUSTOM_PROJECT_NAME_AND_USERNAME_PREFIX,
        )
        == "folder/project/user/"
    )


def test_configure_aws_credentials_succeed(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "region")
    run_mock = Mock()
    monkeypatch.setattr(subprocess, "run", run_mock)

    s3_mount._configure_aws_credentials("script_location", "fs_name", "api_url")

    run_mock.assert_has_calls(
        [
            call(["aws", "configure", "set", "output", "json"], check=True),
            call(["aws", "configure", "set", "region", "region"], check=True),
            call(
                [
                    "aws",
                    "configure",
                    "set",
                    "credential_process",
                    "/opt/idea/python/latest/bin/idea_python script_location --filesystem-name fs_name --api-url api_url",
                    "--profile",
                    "fs_name-profile",
                ],
                check=True,
            ),
            call(
                [
                    "aws",
                    "configure",
                    "set",
                    "output",
                    "json",
                    "--profile",
                    "fs_name-profile",
                ],
                check=True,
            ),
            call(
                [
                    "aws",
                    "configure",
                    "set",
                    "region",
                    "region",
                    "--profile",
                    "fs_name-profile",
                ],
                check=True,
            ),
        ]
    )


def test_add_s3_bucket_ready_only_succeed(monkeypatch):
    monkeypatch.setattr(s3_mount, "_configure_aws_credentials", lambda x0, x1, x2: None)
    monkeypatch.setattr(shutil, "which", lambda _: "mount-s3")
    run_mock = Mock()
    monkeypatch.setattr(subprocess, "run", run_mock)
    monkeypatch.setattr(os.environ, "copy", lambda: {})

    with tempfile.TemporaryDirectory() as tmp_dir_name:
        monkeypatch.setattr(constants, "SYSTEMD_SERVICE_FILE_DIR", tmp_dir_name)
        s3_mount.add_s3_bucket(
            "script_location", "api_url", "fs_name", "mount_dir", "bucket", True
        )

        with open(os.path.join(tmp_dir_name, "fs_name-mount-s3.service"), "r") as f:
            lines = f.readlines()
            assert "AssertPathIsDirectory=mount_dir\n" in lines
            assert (
                "ExecStart=/bin/bash -c 'AWS_PROFILE=fs_name-profile mount-s3 bucket mount_dir --allow-other --read-only'\n"
                in lines
            )
            assert "ExecStop=/usr/bin/fusermount -u mount_dir\n" in lines

        run_mock.assert_has_calls(
            [
                call(
                    ["mount-s3", "bucket", "mount_dir", "--allow-other", "--read-only"],
                    env={"AWS_PROFILE": "fs_name-profile"},
                    check=True,
                ),
                call(["systemctl", "daemon-reload"], check=True),
                call(["systemctl", "enable", "fs_name-mount-s3.service"], check=True),
            ]
        )


def test_add_s3_bucket_ready_write_succeed(monkeypatch):
    monkeypatch.setattr(s3_mount, "_configure_aws_credentials", lambda x0, x1, x2: None)
    monkeypatch.setattr(shutil, "which", lambda _: "mount-s3")
    run_mock = Mock()
    monkeypatch.setattr(subprocess, "run", run_mock)
    monkeypatch.setattr(os.environ, "copy", lambda: {})

    with tempfile.TemporaryDirectory() as tmp_dir_name:
        monkeypatch.setattr(constants, "SYSTEMD_SERVICE_FILE_DIR", tmp_dir_name)
        s3_mount.add_s3_bucket(
            "script_location", "api_url", "fs_name", "mount_dir", "bucket", False
        )

        with open(os.path.join(tmp_dir_name, "fs_name-mount-s3.service"), "r") as f:
            lines = f.readlines()
            assert "AssertPathIsDirectory=mount_dir\n" in lines
            assert (
                "ExecStart=/bin/bash -c 'AWS_PROFILE=fs_name-profile mount-s3 bucket mount_dir --allow-other --allow-delete --allow-overwrite --dir-mode 0777 --file-mode 0777'\n"
                in lines
            )
            assert "ExecStop=/usr/bin/fusermount -u mount_dir\n" in lines

        run_mock.assert_has_calls(
            [
                call(
                    [
                        "mount-s3",
                        "bucket",
                        "mount_dir",
                        "--allow-other",
                        "--allow-delete",
                        "--allow-overwrite",
                        "--dir-mode",
                        "0777",
                        "--file-mode",
                        "0777",
                    ],
                    env={"AWS_PROFILE": "fs_name-profile"},
                    check=True,
                ),
                call(["systemctl", "daemon-reload"], check=True),
                call(["systemctl", "enable", "fs_name-mount-s3.service"], check=True),
            ]
        )


def test_add_s3_bucket_ready_write_with_prefix_succeed(monkeypatch):
    monkeypatch.setattr(s3_mount, "_configure_aws_credentials", lambda x0, x1, x2: None)
    monkeypatch.setattr(shutil, "which", lambda _: "mount-s3")
    run_mock = Mock()
    monkeypatch.setattr(subprocess, "run", run_mock)
    monkeypatch.setattr(os.environ, "copy", lambda: {})

    with tempfile.TemporaryDirectory() as tmp_dir_name:
        monkeypatch.setattr(constants, "SYSTEMD_SERVICE_FILE_DIR", tmp_dir_name)
        s3_mount.add_s3_bucket(
            "script_location",
            "api_url",
            "fs_name",
            "mount_dir",
            "bucket",
            False,
            "prefix",
        )

        with open(os.path.join(tmp_dir_name, "fs_name-mount-s3.service"), "r") as f:
            lines = f.readlines()
            assert "AssertPathIsDirectory=mount_dir\n" in lines
            assert (
                "ExecStart=/bin/bash -c 'AWS_PROFILE=fs_name-profile mount-s3 bucket mount_dir --allow-other --allow-delete --allow-overwrite --dir-mode 0777 --file-mode 0777 --prefix prefix'\n"
                in lines
            )
            assert "ExecStop=/usr/bin/fusermount -u mount_dir\n" in lines

        run_mock.assert_has_calls(
            [
                call(
                    [
                        "mount-s3",
                        "bucket",
                        "mount_dir",
                        "--allow-other",
                        "--allow-delete",
                        "--allow-overwrite",
                        "--dir-mode",
                        "0777",
                        "--file-mode",
                        "0777",
                        "--prefix",
                        "prefix",
                    ],
                    env={"AWS_PROFILE": "fs_name-profile"},
                    check=True,
                ),
                call(["systemctl", "daemon-reload"], check=True),
                call(["systemctl", "enable", "fs_name-mount-s3.service"], check=True),
            ]
        )
