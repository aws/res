#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import shutil
import subprocess
import tempfile
from unittest.mock import Mock

from ideabootstrap.file_system.linux import (
    constants,
    fsx_lustre_client_utils,
    shared_storage,
    s3_mount,
)
from ideabootstrap.file_system import common
from res.resources import cluster_settings


def test_has_storage_provider_provider_exists_return_true(monkeypatch) -> None:
    monkeypatch.setattr(
        cluster_settings, "get_config", lambda x: {"test": {"provider": "provider"}}
    )
    assert shared_storage._has_storage_provider("provider")


def test_has_storage_provider_provider_does_not_exist_return_false(monkeypatch) -> None:
    monkeypatch.setattr(cluster_settings, "get_config", lambda x: {})
    assert not shared_storage._has_storage_provider("provider")


def test_eval_shared_storage_scope_cluster_scope_without_project_name_return_true(
    monkeypatch,
) -> None:
    assert common.eval_shared_storage_scope({"scope": ["cluster"]})


def test_eval_shared_storage_scope_cluster_scope_with_project_name_return_eval_project_result(
    monkeypatch,
) -> None:
    monkeypatch.setenv("PROJECT_NAME", "test")

    assert not common.eval_shared_storage_scope({"scope": ["cluster"]})
    assert common.eval_shared_storage_scope(
        {
            "scope": ["cluster"],
            "projects": ["test"],
        }
    )


def test_eval_shared_storage_scope_cluster_scope_with_project_name_return_eval_internal_filesystem_result(
    monkeypatch,
) -> None:
    monkeypatch.setenv("PROJECT_NAME", "test")

    assert common.eval_shared_storage_scope(
        {
            "scope": ["cluster"],
            "mount_dir": "/internal",
        }
    )
    assert not common.eval_shared_storage_scope(
        {
            "scope": ["cluster"],
        }
    )


def test_eval_shared_storage_scope_module_and_project_scope_return_eval_module_and_eval_project_result(
    monkeypatch,
) -> None:
    monkeypatch.setenv("PROJECT_NAME", "test")
    monkeypatch.setenv("IDEA_MODULE_NAME", "module")

    assert common.eval_shared_storage_scope(
        {
            "scope": ["module", "project"],
            "projects": ["test"],
            "modules": ["module"],
        }
    )
    assert common.eval_shared_storage_scope(
        {
            "scope": ["module", "project"],
            "projects": ["test"],
        }
    )
    assert not common.eval_shared_storage_scope(
        {
            "scope": ["module", "project"],
            "modules": ["module"],
        }
    )
    assert not common.eval_shared_storage_scope(
        {
            "scope": ["module", "project"],
            "projects": ["test"],
            "modules": ["another_module"],
        }
    )


def test_copy_with_full_metadata_mock() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir_name:
        src_dir_stat = os.stat(tmp_dir_name)
        temp_file_path = os.path.join(tmp_dir_name, "temp_file.txt")
        with open(temp_file_path, "w") as temp_file:
            temp_file.write("This is a temporary file.")

        with tempfile.TemporaryDirectory() as another_tmp_dir_name:
            shared_storage._copy_with_full_metadata(
                tmp_dir_name, another_tmp_dir_name, "temp_file.txt"
            )
            dist_dir_stat = os.stat(another_tmp_dir_name)

            assert dist_dir_stat.st_mode == src_dir_stat.st_mode
            assert dist_dir_stat.st_uid == src_dir_stat.st_uid
            assert dist_dir_stat.st_gid == src_dir_stat.st_gid

            dst_file_path = os.path.join(another_tmp_dir_name, "temp_file.txt")
            dst_file_stat = os.stat(dst_file_path)
            src_file_stat = os.stat(temp_file_path)

            assert dst_file_stat.st_uid == src_file_stat.st_uid
            assert dst_file_stat.st_gid == src_file_stat.st_gid


def test_mount_efs_succeed(monkeypatch) -> None:
    monkeypatch.setattr(
        cluster_settings,
        "get_config",
        lambda x: {
            "test_efs": {
                "provider": "efs",
                "mount_dir": "efs_mount_dir",
                "mount_options": "efs_mount_options",
                "efs": {
                    "dns": "efs_dns",
                },
            }
        },
    )
    monkeypatch.setattr(
        common, "eval_shared_storage_scope", lambda shared_storage: True
    )
    monkeypatch.setattr(os, "makedirs", lambda x, exist_ok: None)
    monkeypatch.setattr(subprocess, "run", lambda x, check: None)

    with tempfile.NamedTemporaryFile(mode="w", delete=True) as temp_file:
        temp_file_name = temp_file.name
        monkeypatch.setattr(constants, "FSTAB_PATH", temp_file_name)

        shared_storage._mount_shared_storage()
        with open(constants.FSTAB_PATH, "r") as f:
            assert "efs_dns:/ efs_mount_dir/ efs_mount_options\n" in f.readlines()
            assert shared_storage._mount_directory_exists("efs_mount_dir")


def test_mount_shared_lustre_succeed(monkeypatch) -> None:
    monkeypatch.setattr(
        cluster_settings,
        "get_config",
        lambda x: {
            "test_lustre": {
                "provider": "fsx_lustre",
                "mount_dir": "lustre_mount_dir",
                "mount_options": "lustre_mount_options",
                "fsx_lustre": {
                    "dns": "lustre_dns",
                },
                "mount_name": "lustre_mount_name",
            }
        },
    )
    monkeypatch.setattr(
        common, "eval_shared_storage_scope", lambda shared_storage: True
    )
    monkeypatch.setattr(os, "makedirs", lambda x, exist_ok: None)
    monkeypatch.setattr(subprocess, "run", lambda x, check: None)

    with tempfile.NamedTemporaryFile(mode="w", delete=True) as temp_file:
        temp_file_name = temp_file.name
        monkeypatch.setattr(constants, "FSTAB_PATH", temp_file_name)

        shared_storage._mount_shared_storage()
        with open(constants.FSTAB_PATH, "r") as f:
            assert "lustre_dns@tcp:/lustre_mount_name lustre_mount_dir/ lustre_mount_options\n" in f.readlines()
            assert shared_storage._mount_directory_exists("lustre_mount_dir")


def test_mount_ontap_succeed(monkeypatch) -> None:
    monkeypatch.setattr(
        cluster_settings,
        "get_config",
        lambda x: {
            "test_ontap": {
                "provider": "fsx_netapp_ontap",
                "mount_dir": "ontap_mount_dir",
                "mount_options": "ontap_mount_options",
                "fsx_netapp_ontap": {
                    "svm": {
                        "nfs_dns": "ontap_nfs_dns",
                    },
                    "volume": {
                        "volume_path": "ontap_volume_path",
                        "security_style": "ontap_security_style",
                    },
                },
            }
        },
    )
    monkeypatch.setattr(
        common, "eval_shared_storage_scope", lambda shared_storage: True
    )
    monkeypatch.setattr(os, "makedirs", lambda x, exist_ok: None)
    monkeypatch.setattr(subprocess, "run", lambda x, check: None)

    with tempfile.NamedTemporaryFile(mode="w", delete=True) as temp_file:
        temp_file_name = temp_file.name
        monkeypatch.setattr(constants, "FSTAB_PATH", temp_file_name)

        shared_storage._mount_shared_storage()
        with open(constants.FSTAB_PATH, "r") as f:
            assert "ontap_nfs_dns:ontap_volume_path ontap_mount_dir/ ontap_mount_options\n" in f.readlines()
            assert shared_storage._mount_directory_exists("ontap_mount_dir")


def test_mount_s3_succeed(monkeypatch) -> None:
    monkeypatch.setattr(
        cluster_settings,
        "get_config",
        lambda x: {
            "test_s3": {
                "provider": "s3_bucket",
                "mount_dir": "s3_mount_dir",
                "s3_bucket": {
                    "bucket_arn": "s3_bucket_arn",
                    "read_only": True,
                    "custom_bucket_prefix": "s3_custom_bucket_prefix",
                },
            }
        },
    )
    s3_mount_mock = Mock()
    monkeypatch.setattr(s3_mount, "add_s3_bucket", s3_mount_mock)
    get_bucket_name_mock = Mock()
    monkeypatch.setattr(s3_mount, "get_bucket_name", get_bucket_name_mock)
    get_prefix_for_object_storage_mock = Mock()
    monkeypatch.setattr(
        s3_mount, "get_prefix_for_object_storage", get_prefix_for_object_storage_mock
    )

    monkeypatch.setattr(os, "makedirs", lambda x, exist_ok: None)
    monkeypatch.setattr(subprocess, "run", lambda x, check: None)
    monkeypatch.setattr(cluster_settings, "get_setting", lambda x: "")

    shared_storage._mount_shared_storage()
    s3_mount_mock.assert_called_once()
    get_bucket_name_mock.assert_called_once()
    get_prefix_for_object_storage_mock.assert_called_once()


def test_mount_s3_configure(monkeypatch) -> None:
    monkeypatch.setattr(shared_storage, "_has_storage_provider", lambda x: True)

    tune_fsx_lustre_pre_reboot_mock = Mock()
    monkeypatch.setattr(
        fsx_lustre_client_utils,
        "tune_fsx_lustre_pre_reboot",
        tune_fsx_lustre_pre_reboot_mock,
    )
    tune_fsx_lustre_post_mount_mock = Mock()
    monkeypatch.setattr(
        fsx_lustre_client_utils,
        "tune_fsx_lustre_post_mount",
        tune_fsx_lustre_post_mount_mock,
    )
    copy_with_full_metadata_mock = Mock()
    monkeypatch.setattr(
        shared_storage, "_copy_with_full_metadata", copy_with_full_metadata_mock
    )
    mount_shared_storage_mock = Mock()
    monkeypatch.setattr(
        shared_storage, "_mount_shared_storage", mount_shared_storage_mock
    )
    monkeypatch.setattr(shutil, "rmtree", lambda x: None)
    monkeypatch.setattr(os, "makedirs", lambda x: None)

    shared_storage.configure()

    tune_fsx_lustre_pre_reboot_mock.assert_called_once()
    tune_fsx_lustre_post_mount_mock.assert_called_once()
    assert copy_with_full_metadata_mock.call_count == 2
    mount_shared_storage_mock.assert_called_once()
