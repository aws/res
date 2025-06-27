#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import configparser
import os
import shutil
import pwd
import time

import ideabootstrap.dcv.constants as constants
from res.resources import cluster_settings
from ideabootstrap.dcv import dcv_utils
from res.utils import logging_utils

logger = logging_utils.get_logger("bootstrap")


def _configure_storage_root() -> None:
    logger.info("Creating storage root ...")
    session_owner = os.environ.get("IDEA_SESSION_OWNER")
    dcv_storage_root = f"/home/{session_owner}/storage-root"

    if os.path.islink(dcv_storage_root):
        error_msg = "something fishy is going on here. a sym-link should not exist. check with the session owner for bad actor or unwarranted usage of system."
        logger.error(error_msg)
        return

    try:
        if not os.path.exists(dcv_storage_root):
            os.makedirs(dcv_storage_root, exist_ok=True)
            uid = pwd.getpwnam(session_owner).pw_uid
            gid = pwd.getpwnam(session_owner).pw_gid
            os.chown(dcv_storage_root, uid, gid)
            logger.info(
                f"Created storage root: {dcv_storage_root} for session_owner: {session_owner}"
            )
    except Exception as e:
        logger.error(
            f"Error when creating storage root {dcv_storage_root} for session owner {session_owner}: {e}"
        )


def _configure_dcv_conf() -> None:
    logger.info("Configuring dcv.conf ...")
    try:
        internal_alb_endpoint = dcv_utils.get_cluster_internal_endpoint()
        idle_timeout = cluster_settings.get_setting(constants.IDLE_TIMEOUT_KEY)
        idle_timeout_warning = cluster_settings.get_setting(
            constants.IDLE_TIMEOUT_WARNING_KEY
        )
        broker_agent_connection_port = cluster_settings.get_setting(
            constants.AGENT_COMMUNICATION_PORT_KEY
        )

        # Backup existing dcv.conf if it exists
        if os.path.exists(constants.DCV_CONFIG_FILE_PATH):
            timestamp = int(time.time())
            shutil.move(
                constants.DCV_CONFIG_FILE_PATH,
                f"{constants.DCV_CONFIG_FILE_PATH}.{timestamp}",
            )

        config = configparser.ConfigParser()
        config["license"] = {}
        config["log"] = {"level": "debug"}
        config["session-management"] = {"virtual-session-xdcv-args": '"-listen tcp"'}
        config["session-management/defaults"] = {}
        config["session-management/automatic-console-session"] = {}
        config["display"] = {"cuda-devices": '["0"]'}
        config["display/linux"] = {
            "gl-displays": f'["{constants.GL_DISPLAYS_VALUE}"]',
            "use-glx-fallback-provider": "true",
        }
        config["connectivity"] = {
            "enable-quic-frontend": "true",
            "idle-timeout": str(idle_timeout),
            "idle-timeout-warning": str(idle_timeout_warning),
        }
        config["security"] = {
            "supervision-control": '"enforced"',
            "auth-token-verifier": f'"{internal_alb_endpoint}:{broker_agent_connection_port}/agent/validate-authentication-token"',
            "no-tls-strict": "true",
            "os-auto-lock": "false",
            "administrators": '["dcvsmagent"]',
        }
        config["windows"] = {"disable-display-sleep": "true"}

        # Write the configuration to file
        with open(constants.DCV_CONFIG_FILE_PATH, "w") as configfile:
            config.write(configfile)
        logger.info("Successfully configured dcv.conf")
    except Exception as e:
        logger.error(f"Error when configuring dcv.conf: {e}")


def configure() -> None:
    logger.info("Configuring dcv host ...")
    _configure_storage_root()
    _configure_dcv_conf()
    logger.info("Successfully configured dcv host")
