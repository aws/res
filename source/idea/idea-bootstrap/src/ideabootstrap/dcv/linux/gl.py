#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import subprocess
from shutil import which

from ideabootstrap.bootstrap_common import append_to_file, overwrite_file
from ideabootstrap.dcv import constants
from res.resources import cluster_settings
from res.utils import logging_utils

logger = logging_utils.get_logger("bootstrap")


def _is_gpu_instance_type() -> bool:
    instance_family = os.environ.get("INSTANCE_FAMILY")
    gpu_instance_families = cluster_settings.get_setting(
        "global-settings.gpu_settings.instance_families"
    )
    return instance_family in gpu_instance_families


def _configure_gl(base_os: str) -> None:
    if base_os == "amzn2" or base_os == "amzn2023":
        logger.info(f"OS is {base_os}, no need for this configuration. NO-OP...")
        return

    if os.environ.get("MACHINE") != "x86_64":
        return

    logger.info("Detected GPU instance, configuring GL...")
    try:
        os.makedirs(constants.IDEA_SERVICES_LOGS_PATH, exist_ok=True)
        dcvgladmin = which("dcvgladmin")

        gl_log_redirect = f"{constants.IDEA_SERVICES_LOGS_PATH}/idea-reboot-do-not-edit-or-delete-idea-gl.log 2>&1"
        script_content = f"""#!/bin/bash
echo "GLADMIN START" >> {gl_log_redirect}
echo $(date) >> {gl_log_redirect}
{dcvgladmin} disable >> {gl_log_redirect}
{dcvgladmin} enable >> {gl_log_redirect}
echo $(date) >> {gl_log_redirect}
echo "GLADMIN END" >> {gl_log_redirect}"""
        if base_os == "ubuntu2204":
            rc_path = constants.RC_LOCAL_DEBIAN_PATH
            overwrite_file(script_content, rc_path)
            os.chmod(rc_path, 0o755)
            _configure_rc_service(rc_path)
        else:
            rc_path = constants.RC_LOCAL_RHEL_PATH
            append_to_file(script_content, rc_path)
            os.chmod(rc_path, 0o755)
            subprocess.run(["systemctl", "enable", "rc-local"], check=True)
        logger.info("Successfully configured GL")
    except Exception as e:
        logger.error(f"Error when configuring GL: {e}")


def _configure_rc_service(rc_path: str) -> None:
    logger.info("Configuring rc-local.service")
    try:
        service_content = f"""[Unit]
Description=Local Startup Script
ConditionPathExists={rc_path}

[Service]
Type=forking
ExecStart={rc_path} start
TimeoutSec=0
StandardOutput=tty
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
"""
        overwrite_file(service_content, constants.RC_LOCAL_SERVICE_PATH)
        os.chmod(constants.RC_LOCAL_SERVICE_PATH, 0o755)
        subprocess.run(["systemctl", "enable", "rc-local.service"], check=True)
        logger.info("Successfully configured rc-local.service")
    except Exception as e:
        logger.error(f"Error when configuring rc-local.service: {e}")


def configure() -> None:
    """
    Configure GL settings based on the operating system type.
    """
    base_os = os.environ.get("RES_BASE_OS")
    if base_os not in ("amzn2", "amzn2023", "rhel8", "rhel9", "ubuntu2204", "rocky9"):
        logger.info("Base OS not supported.")
        return
    if not _is_gpu_instance_type():
        logger.info(
            f"OS is {base_os}, BUT not a GL Machine. No need for this configuration. NO-OP..."
        )
        return

    _configure_gl(base_os)
