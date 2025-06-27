#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import glob
import os
import random
import shutil
import subprocess
import time
from typing import Dict

import ideabootstrap.file_system.linux.constants as constants
import ideabootstrap.common.constants as bootstrap_constants
from ideabootstrap.file_system import common
from ideabootstrap.file_system.linux import fsx_lustre_client_utils, s3_mount
from res.resources import cluster_settings
from res.utils import logging_utils

logger = logging_utils.get_logger("bootstrap")


def _add_fsx_lustre_to_fstab(
    fs_domain: str, mount_dir: str, mount_options: str = None, fs_mount_name: str = None
):
    if not mount_options:
        mount_options = "lustre defaults,noatime,flock,_netdev 0 0"

    if _mount_directory_exists(mount_dir):
        return

    with open(constants.FSTAB_PATH, "a") as f:
        f.write(f"{fs_domain}@tcp:/{fs_mount_name} {mount_dir}/ {mount_options}\n")


def _add_efs_to_fstab(fs_domain, mount_dir, mount_options=None):
    if not mount_options:
        mount_options = "nfs4 nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,noresvport 0 0"

    if _mount_directory_exists(mount_dir):
        return

    with open(constants.FSTAB_PATH, "a") as f:
        f.write(f"{fs_domain}:/ {mount_dir}/ {mount_options}\n")


def _add_fsx_netapp_ontap_to_fstab(
    fs_domain, mount_dir, mount_options=None, fs_volume_path=None
):
    if not mount_options:
        mount_options = "nfs4 nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,noresvport 0 0"

    if _mount_directory_exists(mount_dir):
        return

    with open(constants.FSTAB_PATH, "a") as f:
        f.write(f"{fs_domain}:{fs_volume_path} {mount_dir}/ {mount_options}\n")


def _mount_directory_exists(mount_dir: str):
    try:
        with open(constants.FSTAB_PATH, "r") as f:
            if any(f" {mount_dir}/" in line for line in f):
                return True
        return False
    except Exception as e:
        logger.error(f"Error reading file {constants.FSTAB_PATH}: {e}")
        return False


def _has_storage_provider(provider: str) -> bool:
    storage_config = cluster_settings.get_config("shared-storage")
    for name, storage in storage_config.items():
        if not isinstance(storage, Dict):
            continue
        if storage.get("provider") == provider:
            return True
    return False


def _copy_with_full_metadata(source_dir: str, dest_dir: str, pattern: str) -> None:
    # Find all matching files
    for src_path in glob.glob(os.path.join(source_dir, pattern), recursive=True):
        rel_path = os.path.relpath(src_path, source_dir)

        dst_path = os.path.join(dest_dir, rel_path)

        # Create destination directory structure with metadata
        dir_path = os.path.dirname(dst_path)
        if not os.path.exists(dir_path):
            src_dir = os.path.dirname(src_path)
            src_dir_stat = os.stat(src_dir)

            os.makedirs(dir_path, exist_ok=True)

            # Copy directory permissions and ownership
            try:
                os.chmod(dir_path, src_dir_stat.st_mode)
                os.chown(dir_path, src_dir_stat.st_uid, src_dir_stat.st_gid)
            except PermissionError:
                logger.warning(f"Unable to copy directory metadata for {dir_path}")

        # Copy file with metadata
        shutil.copy2(src_path, dst_path)

        # Copy file ownership
        try:
            src_stat = os.stat(src_path)
            os.chown(dst_path, src_stat.st_uid, src_stat.st_gid)
        except PermissionError:
            logger.warning(f"Unable to copy file ownership for {dst_path}")


def _mount_shared_storage() -> None:
    shared_storage = cluster_settings.get_config("shared-storage")
    for name, storage in shared_storage.items():
        if isinstance(storage, Dict) and common.eval_shared_storage_scope(
            shared_storage=storage
        ):
            # Create mount directory
            mount_dir = storage.get("mount_dir")
            os.makedirs(mount_dir, exist_ok=True)

            provider = storage.get("provider")
            if provider == "efs":
                logger.info(
                    f"Using Provider {provider} for {mount_dir} using options {storage.get('mount_options')}"
                )

                _add_efs_to_fstab(
                    storage.get("efs", {}).get("dns"),
                    mount_dir,
                    storage.get("mount_options"),
                )

            elif provider == "fsx_lustre":
                logger.info(
                    f"Using Provider {provider} for {mount_dir} using options {storage.get('mount_options')}"
                )

                _add_fsx_lustre_to_fstab(
                    storage.get("fsx_lustre", {}).get("dns"),
                    mount_dir,
                    storage.get("mount_options"),
                    storage.get("mount_name"),
                )

            elif provider == "fsx_netapp_ontap" and storage.get(
                "fsx_netapp_ontap", {}
            ).get("volume", {}).get("security_style"):
                logger.info(
                    f"Using Provider {provider} for {mount_dir} using options {storage.get('mount_options')}"
                )

                _add_fsx_netapp_ontap_to_fstab(
                    storage.get("fsx_netapp_ontap", {}).get("svm", {}).get("nfs_dns"),
                    mount_dir,
                    storage.get("mount_options"),
                    storage.get("fsx_netapp_ontap", {})
                    .get("volume", {})
                    .get("volume_path"),
                )

            elif provider == "s3_bucket":
                logger.info(f"Using Provider {provider} for {mount_dir}")

                try:
                    s3_mount.add_s3_bucket(
                        f"{bootstrap_constants.BOOTSTRAP_DIR}/latest/scripts/vdi-helper/custom_credential_broker.py",
                        cluster_settings.get_setting(
                            "vdc.custom_credential_broker_api_gateway_url"
                        ),
                        name,
                        mount_dir,
                        s3_mount.get_bucket_name(
                            storage.get(provider, {}).get("bucket_arn")
                        ),
                        storage.get(provider, {}).get("read_only"),
                        s3_mount.get_prefix_for_object_storage(
                            storage.get(provider, {}).get("bucket_arn"),
                            storage.get(provider, {}).get("read_only"),
                            storage.get(provider, {}).get("custom_bucket_prefix", ""),
                        ),
                    )
                except Exception as e:
                    logger.error(f"Error in add_s3_bucket: {str(e)}")

    # Mount filesystem with retries
    fs_mount_attempt = 0
    fs_mount_max_attempts = 5
    while fs_mount_attempt <= fs_mount_max_attempts:
        try:
            subprocess.run(["mount", "-a"], check=True)
            break
        except subprocess.CalledProcessError:
            sleep_time = random.randint(8, 40)
            logger.info(
                f"({fs_mount_attempt} of {fs_mount_max_attempts}) Failed to mount FS, retrying in {sleep_time} seconds ..."
            )
            time.sleep(sleep_time)
            fs_mount_attempt += 1


def configure() -> None:
    # Pre-reboot Lustre client tuning
    if _has_storage_provider("fsx_lustre"):
        fsx_lustre_client_utils.tune_fsx_lustre_pre_reboot()

    # Handle SSH authorized keys
    tmp_dir = f"/tmp/tmpdir.{os.getpid()}"
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir)
    os.makedirs(tmp_dir)

    _copy_with_full_metadata("/home", tmp_dir, "*/.ssh/authorized_keys")

    _mount_shared_storage()

    _copy_with_full_metadata(tmp_dir, "/home", "*/.ssh/authorized_keys")

    shutil.rmtree(tmp_dir)

    # Post-mount Lustre client tuning
    if _has_storage_provider("fsx_lustre"):
        fsx_lustre_client_utils.tune_fsx_lustre_post_mount()
