#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import subprocess
import winreg

from res.resources import cluster_settings
from ideabootstrap.dcv import constants, dcv_utils
from ideabootstrap.bootstrap_common import append_to_file
from res.utils import logging_utils

logger = logging_utils.get_logger("bootstrap")


def _configure_storage_root() -> None:
    logger.info("Creating storage root ...")
    local_user = os.environ.get("IDEA_SESSION_OWNER")
    os.makedirs(f"C:\\session-storage\\{local_user}", exist_ok=True)


def _configure_dcv_connectivity_registry() -> None:
    logger.info("Configuring DCV connectivity registry ...")
    try:
        idle_timeout = cluster_settings.get_setting(constants.IDLE_TIMEOUT_KEY)
        idle_timeout_warning = cluster_settings.get_setting(
            constants.IDLE_TIMEOUT_WARNING_KEY
        )
        key = winreg.CreateKeyEx(
            winreg.HKEY_USERS,
            f"{constants.DCV_REGISTRY_PATH}\\connectivity",
            0,
            winreg.KEY_ALL_ACCESS,
        )
        winreg.SetValueEx(key, "idle-timeout", 0, winreg.REG_DWORD, idle_timeout)
        winreg.SetValueEx(
            key, "idle-timeout-warning", 0, winreg.REG_DWORD, idle_timeout_warning
        )
        winreg.SetValueEx(key, "enable-quic-frontend", 0, winreg.REG_DWORD, 1)
        winreg.CloseKey(key)
        logger.info("Successfully configured DCV connectivity registry")
    except Exception as e:
        logger.error(f"Failed to configure DCV connectivity registry: {e}")


def _configure_dcv_security_registry() -> None:
    logger.info("Configuring DCV security registry ...")
    try:
        internal_alb_endpoint = dcv_utils.get_cluster_internal_endpoint()
        broker_agent_port = cluster_settings.get_setting(
            constants.AGENT_COMMUNICATION_PORT_KEY
        )
        key = winreg.CreateKeyEx(
            winreg.HKEY_USERS,
            f"{constants.DCV_REGISTRY_PATH}\\security",
            0,
            winreg.KEY_ALL_ACCESS,
        )
        winreg.SetValueEx(
            key,
            "auth-token-verifier",
            0,
            winreg.REG_SZ,
            f"{internal_alb_endpoint}:{broker_agent_port}/agent/validate-authentication-token",
        )
        winreg.SetValueEx(key, "no-tls-strict", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, "os-auto-lock", 0, winreg.REG_DWORD, 0)
        winreg.CloseKey(key)
        logger.info("Successfully configured DCV security registry")
    except Exception as e:
        logger.error(f"Failed to configure DCV security registry: {e}")


def _configure_dcv_windows_registry() -> None:
    logger.info("Configuring DCV windows registry ...")
    try:
        key = winreg.CreateKeyEx(
            winreg.HKEY_USERS,
            f"{constants.DCV_REGISTRY_PATH}\\windows",
            0,
            winreg.KEY_ALL_ACCESS,
        )
        winreg.SetValueEx(key, "disable-display-sleep", 0, winreg.REG_DWORD, 1)
        winreg.CloseKey(key)
        logger.info("Successfully configured DCV windows registry")
    except Exception as e:
        logger.error(f"Failed to configure DCV windows registry: {e}")


def _remove_dcv_session_management_registry() -> None:
    logger.info("Removing DCV session management registry ...")
    try:
        key = winreg.OpenKey(
            winreg.HKEY_USERS,
            f"{constants.DCV_REGISTRY_PATH}\\session-management",
            0,
            winreg.KEY_READ,
        )
        winreg.CloseKey(key)
    except Exception as e:
        logger.info(f"Session management registry not found: {e}, skipping deletion")
        return

    try:
        command = [
            "powershell.exe",
            "-Command",
            f'Remove-Item -Path "{constants.WINDOWS_DCV_REGISTRY_PATH}\\session-management" -Recurse -Force -Confirm:$false',
        ]
        subprocess.run(
            command,
            check=True,
        )
        logger.info("Successfully removed DCV session management registry")
    except Exception as e:
        logger.error(f"Failed to remove session management registry: {e}")


def configure() -> None:
    logger.info("Configuring dcv host ...")
    try:
        subprocess.run(
            [
                constants.WINDOWS_DCV_EXECUTABLE_PATH,
                "close-session",
                "console",
            ],
            check=True,
        )

        # Stop DCV services
        subprocess.run(
            ["powershell.exe", "-Command", "Stop-Service dcvserver"], check=True
        )
        subprocess.run(
            [
                "powershell.exe",
                "-Command",
                "Stop-Service DcvSessionManagerAgentService",
            ],
            check=True,
        )
        logger.info("Succesffully stopped DCV services")

        # Configure DCV Registry
        _configure_dcv_connectivity_registry()
        _configure_dcv_security_registry()
        _configure_dcv_windows_registry()
        _remove_dcv_session_management_registry()
        logger.info("Successfully configured all DCV registry")

        # Configure storage root
        _configure_storage_root()

        logger.info("Successfully configured dcv host")
    except Exception as e:
        logger.error(f"Error when configuring DCV host: {e}")
