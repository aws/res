#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import json
import subprocess
import time

from res.resources import cluster_settings
from res.resources.dcv import session_permissions as dcv_session_permissions
from res.utils import logging_utils
from ideabootstrap.bootstrap_common import update_session_state
from ideabootstrap.dcv import constants

logger = logging_utils.get_logger("bootstrap - dcv config")

BASE_OS = os.environ.get("RES_BASE_OS")
if BASE_OS == "windows":
    from ideabootstrap.dcv import windows as dcv
else:
    from ideabootstrap.dcv import linux as dcv


def configure() -> None:
    try:
        if BASE_OS == "windows":
            dcv.dcv_host.configure()
            dcv.post_bootstrap_reboot_task.configure()
            dcv.start_dcv_service.configure()
        else:
            dcv.disable_wayland_protocol.configure()
            dcv.dcv_host.configure()
            dcv.gl.configure()
            dcv.x_server.configure()
            dcv.start_dcv_service.configure()
    except Exception as e:
        logger.error(f"Failed to configure DCV for base_os {BASE_OS}: {e}")


def is_dcvserver_ready(timeout_seconds: int = 300, retry_interval: int = 5) -> bool:
    try:
        return dcv.start_dcv_service.is_dcvserver_ready(timeout_seconds, retry_interval)
    except Exception as e:
        logger.error(f"Failed to check whether the DCV server is ready: {e}")
        return False


def configure_automatic_console_session() -> bool:
    """Generate the permissions file, apply platform config, restart dcvserver, and transition session state.

    Returns True if the dcvserver restarted and is ready (state -> INITIALIZING),
    False on any failure (state -> ERROR).
    """
    logger.info("Configuring automatic console session ...")
    update_session_state("CREATING")
    try:
        session_owner = os.environ.get("IDEA_SESSION_OWNER")

        if BASE_OS == "windows":
            admin_username = "Administrator"
            newline = "\r\n"
            storage_root = f"C:\\session-storage\\{session_owner}"
            permissions_dir = constants.WINDOWS_DCV_PERMISSIONS_DIR
        else:
            admin_username = cluster_settings.get_setting("cluster.administrator_username")
            newline = "\n"
            storage_root = f"/home/{session_owner}/storage-root"
            permissions_dir = constants.DCV_PERMISSIONS_DIR

        session_id = os.environ.get("IDEA_SESSION_ID")
        permissions_content = dcv_session_permissions.generate_permissions_content(
            session_id=session_id,
            admin_username=admin_username,
            newline=newline,
        )
        os.makedirs(permissions_dir, exist_ok=True)
        permissions_file_path = f"{permissions_dir}{constants.DCV_PERMISSIONS_FILE_NAME}"
        with open(permissions_file_path, "w", newline="") as f:
            f.write(permissions_content)
        logger.info(f"Wrote permissions file to {permissions_file_path}")

        dcv.dcv_host.apply_automatic_console_session_config(
            session_owner=session_owner,
            storage_root=storage_root,
            permissions_file_path=permissions_file_path,
        )

        if is_dcvserver_ready():
            update_session_state("INITIALIZING")
            return True
        logger.error("DCV server not ready after restart")
        update_session_state("ERROR")
        return False
    except Exception as e:
        logger.error(f"Error configuring automatic console session: {e}")
        update_session_state("ERROR")
        return False


def poll_dcv_session_ready(timeout_seconds: int = 300, retry_interval: int = 5) -> str:
    """Poll dcv describe-session until the session is running.

    Args:
        timeout_seconds: Max time to wait for session.
        retry_interval: Seconds between polls.

    Returns:
        "READY" if session is running within timeout, "ERROR" if timeout reached.
    """

    session_id = constants.DCV_AUTOMATIC_CONSOLE_SESSION_ID
    logger.info("Polling DCV session '%s' with %ds timeout...", session_id, timeout_seconds)
    start_time = time.time()

    dcv_cmd = (
        [constants.WINDOWS_DCV_EXECUTABLE_PATH, "describe-session", session_id, "--json"]
        if BASE_OS == "windows"
        else ["dcv", "describe-session", session_id, "--json"]
    )

    while time.time() - start_time < timeout_seconds:
        try:
            result = subprocess.run(
                dcv_cmd, capture_output=True, text=True, check=False, timeout=10
            )
            if result.returncode == 0:
                session_info = json.loads(result.stdout)
                if session_info.get("status") == "running":
                    logger.info("DCV session '%s' is running", session_id)
                    return "READY"
        except subprocess.TimeoutExpired:
            logger.debug("dcv describe-session timed out")
        except Exception as e:
            logger.debug("Error polling DCV session: %s", e)

        logger.debug("DCV session not ready yet, retrying in %ds...", retry_interval)
        time.sleep(retry_interval)

    logger.error("DCV session readiness check timed out after %ds", timeout_seconds)
    return "ERROR"
