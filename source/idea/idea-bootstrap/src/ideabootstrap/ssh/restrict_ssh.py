#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import subprocess

import ideabootstrap.ssh.constants as constants
from res.resources import cluster_settings
from ideabootstrap.bootstrap_common import file_content_exists, append_to_file
from res.utils import logging_utils

logger = logging_utils.get_logger("bootstrap")


def _default_system_user() -> str:
    """
    Return default system user
    """
    base_os = os.environ.get("RES_BASE_OS")
    if base_os in ("amzn2", "amzn2023", "rhel8", "rhel9", "rocky9"):
        return "ec2-user"
    logger.error(f"unknown system user name for base_os: {base_os}")
    return ""


def configure(session_owner: bool = False) -> None:
    """
    Restrict SSH access to the session owner or default system user by modifying sshd_config
    """
    try:
        # Restrict SSH to session owner, used for VDIs
        if session_owner:
            username = os.environ.get("IDEA_SESSION_OWNER")
            if file_content_exists(
                f"AllowUsers {username}", constants.SSHD_CONFIG_PATH
            ):
                return
            append_to_file(f"AllowUsers {username}", constants.SSHD_CONFIG_PATH)
        # Restrict SSH to administrator, used for infra hosts
        else:
            username = cluster_settings.get_setting("cluster.administrator_username")
            if file_content_exists(
                f"{username}-user-group", constants.SSHD_CONFIG_PATH
            ):
                return
            system_user = _default_system_user()
            if system_user:
                append_to_file(
                    f"AllowGroups {_default_system_user()} ssm-user {username}-user-group",
                    constants.SSHD_CONFIG_PATH,
                )

        subprocess.run(["systemctl", "restart", "sshd"], check=True)
        logger.info("Restricted SSH access successfully")
    except Exception as e:
        logger.error(f"Failed to restrict SSH access: {str(e)}")
