#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import re
from res.utils import logging_utils
import os
import subprocess

from ideabootstrap.common.constants import (
    REBOOT_REQUIRED_FILE_PATH
)

logger = logging_utils.get_logger("bootstrap")

def source_launch_env_file(file_path):
    try:
        with open(file_path, 'r') as file:
            for line in file:
                if line.strip().startswith('#') or not line.strip() or '[BEGIN]' in line or '[END]' in line:
                    continue

                match = re.match(r'^([A-Za-z0-9_]+)=(.*)$', line.strip())
                if match:
                    key, value = match.groups()
                    value = value.strip('"\'')
                    os.environ[key] = value
    except Exception as e:
        print(f"Error reading environment file: {e}")

def get_base_os():
    return os.environ.get('RES_BASE_OS')

def disable_strict_host_check():
    base_os = get_base_os()
    logger.info(f"Disabling Strict Host for OS: {base_os}")
    if base_os in ["amzn2", "amzn2023", "rhel8", "rhel9", "rocky9"]:
        try:
            with open('/etc/ssh/ssh_config', 'a') as f:
                f.write("StrictHostKeyChecking no\n")
                f.write("UserKnownHostsFile /dev/null\n")
                logger.info("Successfully updated /etc/ssh/ssh_config with StrictHostKeyChecking no")
        except Exception as e:
            logger.error(f"Error updating '/etc/ssh/ssh_config': {str(e)}")

def disable_ulimit():
    base_os = get_base_os()
    logger.info(f"Disabling U Limit for OS: {base_os}")
    if base_os in ["amzn2", "amzn2023", "rhel8", "rhel9", "rocky9"]:
        try:
            with open('/etc/security/limits.conf', 'a') as limits_file:
                limits_file.write("\n")
                limits_file.write("* hard memlock unlimited\n")
                limits_file.write("* soft memlock unlimited\n")

            logger.info("Successfully updated /etc/security/limits.conf with unlimited memlock settings")
        except Exception as e:
            logger.error(f"Failed to update /etc/security/limits.conf: {str(e)}")
    else:
        logger.error(f"OS {base_os} not supported for ulimit configuration")

def disable_se_linux():
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    base_os = get_base_os()
    logger.info(f"Disabling SE Linux")

    if base_os in ["amzn2", "amzn2023", "rhel8", "rhel9", "rocky9"]:
        logger.info(f"Disabling SE Linux on {base_os}")
        try:
            sestatus_process = subprocess.run(['sestatus'], capture_output=True, text=True, check=False)
            grep_process = subprocess.run(["grep", "disabled"], input=sestatus_process.stdout, text=True, capture_output=True)

            if grep_process.returncode != 0:
                subprocess.run(['sestatus', '0'], capture_output=True, text=True, check=True)
                selinux_config_path = "/etc/selinux/config"

                if os.path.exists(selinux_config_path):
                    try:
                        with open(selinux_config_path, 'r') as file:
                            content = file.read()

                        # Replace SELINUX=enforcing with SELINUX=disabled
                        modified_content = re.sub(r'SELINUX=enforcing', 'SELINUX=disabled', content)

                        # Write the modified content back
                        with open(selinux_config_path, 'w') as file:
                            file.write(modified_content)

                        logger.info(f"Modified {selinux_config_path}: SELINUX=enforcing → SELINUX=disabled")
                    except Exception as e:
                        logger.error(f"Error modifying SELinux config: {selinux_config_path}")
                    set_reboot_required("no")
        except Exception as e:
            logger.error(f"Error checking SE Linux status {e}")

def set_reboot_required(message):
    logger.info(f"Reboot required: {message}")
    try:
        with open(REBOOT_REQUIRED_FILE_PATH, 'w') as f:
            f.write(message + '\n')
    except Exception as e:
        logger.error(f"Failed to set reboot required: {e}")

def file_content_exists(value: str, file_path: str) -> bool:
    try:
        with open(file_path, "r") as f:
            content = f.read()
        if re.search(value, content, re.MULTILINE):
            return True
        return False
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        return False

def append_to_file(value: str, file_path_str: str) -> None:
    try:
        with open(file_path_str, "a") as f:
            f.write(f"{value}\n")
    except Exception as e:
        logger.error(f"Error appending to file {file_path_str}: {e}")


def overwrite_file(value: str, file_path_str: str) -> None:
    try:
        with open(file_path_str, "w") as f:
            f.write(f"{value}\n")
        logger.info(f"Updated file: {file_path_str}")
    except Exception as e:
        logger.error(f"Error overwriting file {file_path_str}: {e}")

def check_reboot_required() -> bool:
    try:
        with open(REBOOT_REQUIRED_FILE_PATH, 'r') as f:
            reboot_required = f.read().strip()

        if reboot_required == "no":
            return False
        else:
            subprocess.run(["reboot"], check=True)
            return True
    except FileNotFoundError as e:
        logger.error(f"Error: reading file {REBOOT_REQUIRED_FILE_PATH}: {e}")
        return False
    except Exception as e:
        logger.error(f"Error checking reboot status: {e}")
        return False
