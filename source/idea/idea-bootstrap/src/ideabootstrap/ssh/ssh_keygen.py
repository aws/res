#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import subprocess

import ideabootstrap.ssh.constants as constants
from ideabootstrap.bootstrap_common import file_content_exists
from res.utils import logging_utils

logger = logging_utils.get_logger("bootstrap")


def _setup_pam(pam_file_path: str) -> None:
    # Check if the file already contains the required line
    if file_content_exists("^session.*ssh_keygen", pam_file_path):
        logger.info(f"File {pam_file_path} already contains the required line. Skip.")
        return

    new_lines = [
        "session\toptional\tssh_keygen.so\n",
        "session\toptional\tpam_mkhomedir.so silent skel=/etc/skel umask=0077\n",
    ]

    try:
        with open(pam_file_path, "r") as f:
            lines = f.readlines()

        for index, line in enumerate(lines):
            if line.startswith("session"):
                for new_line in new_lines:
                    lines.insert(index, new_line)
                break

        with open(pam_file_path, "w") as f:
            f.writelines(lines)

        logger.info(f"File {pam_file_path} updated successfully.")
    except Exception as e:
        logger.error(f"Failed to setup pam file {pam_file_path}: {str(e)}")


def configure() -> None:
    """
    Configure SSH keygen in PAM and trigger it for the current user.
    """

    base_os = os.environ.get("RES_BASE_OS")
    username = os.environ.get("IDEA_SESSION_OWNER")
        
    try:
        if base_os == "ubuntu2204":
            _setup_pam(constants.UBUNTU_PAM_FILE_PATH)
        elif base_os in ("amzn2", "amzn2023", "rhel8", "rhel9", "rocky9"):
            for pam_file in constants.RED_HAT_PAM_FILES_PATH:
                _setup_pam(pam_file)
        else:
            logger.error(f"Unsupported OS: {base_os}")
            return

        subprocess.run(["su", "-", username, "-c", "exit"], check=True)
        
        logger.info(f"PAM module triggered for user {username}")
    except Exception as e:
        logger.error(f"Failed to trigger PAM module for user {username}")
