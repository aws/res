#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import subprocess
import psutil
from typing import Optional

from ideabootstrap import bootstrap_common
from ideabootstrap.file_system.linux import constants
from res.utils import logging_utils

logger = logging_utils.get_logger("bootstrap")


def _get_num_processors() -> Optional[int]:
    return psutil.cpu_count()


def _get_memory_gb() -> int:
    return int(psutil.virtual_memory().total / (1024 * 1024 * 1024))  # Convert bytes to GB


def _append_to_modprobe(content: str) -> None:
    try:
        with open(constants.MODPROBE_CONFIG_PATH, 'a') as f:
            f.write(content + '\n')
    except Exception as e:
        logger.error(f"Failed to write to modprobe.conf: {e}")


def tune_fsx_lustre_pre_reboot() -> None:
    base_os = os.environ.get('RES_BASE_OS', '')
    if base_os not in ["amzn2", "amzn2023", "rhel8", "rhel9", "rocky9"]:
        return

    nprocs = _get_num_processors()
    gb_mem = _get_memory_gb()

    logger.info(f"Detected {nprocs} CPUs / {gb_mem} GiB memory for Lustre performance tuning")

    # CPU-based tuning
    if nprocs >= 64:
        logger.info("Applying CPU count Lustre performance tuning")
        _append_to_modprobe("options ptlrpc ptlrpcd_per_cpt_max=32")
        _append_to_modprobe("options ksocklnd credits=2560")

        bootstrap_common.set_reboot_required("Lustre client tuning applied pre reboot")


def _lctl_set_param(param: str, value: str) -> None:
    cmd = ["lctl", "set_param", f"{param}={value}"]
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to set lctl parameter: {e}")


def tune_fsx_lustre_post_mount() -> None:
    base_os = os.environ.get('RES_BASE_OS', '')
    if base_os not in ["amzn2", "amzn2023", "rhel8", "rhel9", "rocky9"]:
        return

    nprocs = _get_num_processors()
    gb_mem = _get_memory_gb()

    logger.info(f"Detected {nprocs} CPUs / {gb_mem} GiB memory for Lustre performance tuning")

    # CPU-based tuning
    if nprocs >= 64:
        logger.info("Applying CPU count Lustre performance tuning")
        _lctl_set_param("osc.*OST*.max_rpcs_in_flight", "32")
        _lctl_set_param("mdc.*.max_rpcs_in_flight", "64")
        _lctl_set_param("mdc.*.max_mod_rpcs_in_flight", "50")

    # Memory-based tuning
    if gb_mem >= 64:
        logger.info("Applying memory size Lustre performance tuning")
        _lctl_set_param("ldlm.namespaces.*.lru_max_age", "600000")
