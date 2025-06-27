#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import shutil
import subprocess
import time

from ideabootstrap.bootstrap_common import append_to_file, overwrite_file
import ideabootstrap.dcv.constants as constants
from res.resources import cluster_settings
from ideabootstrap.dcv import dcv_utils
from res.utils import logging_utils

logger = logging_utils.get_logger("bootstrap")

BASE_OS = os.environ.get("RES_BASE_OS")


def _configure_usb_remotization() -> None:
    logger.info("Searching for USB Remotization configurations...")
    usb_config_path = constants.USB_DEVICES_CONF_FILE_PATH
    if BASE_OS == "windows":
        usb_config_path = constants.WINDOWS_USB_DEVICES_CONF_FILE_PATH

    try:
        usb_config_list = cluster_settings.get_setting(constants.USB_REMOTIZATION_KEY)

        for usb_info in usb_config_list:
            append_to_file(usb_info, usb_config_path)
        logger.info("Successfully configured USB Remotization")
    except Exception as e:
        logger.error(f"Error when configuring USB devices: {e}")


def _configure_agent_conf() -> None:
    logger.info("Configuring agent.conf ...")
    agent_config_file_path = constants.DCV_AGENT_CONFIG_FILE_PATH
    agent_tags_dir = constants.DCV_AGENT_TAGS_DIR
    if BASE_OS == "windows":
        agent_config_file_path = constants.WINDOWS_DCV_AGENT_CONFIG_FILE_PATH
        agent_tags_dir = constants.WINDOWS_DCV_AGENT_TAGS_DIR

    try:
        broker_hostname = dcv_utils.get_cluster_internal_endpoint().replace(
            "https://", ""
        )
        broker_agent_connection_port = cluster_settings.get_setting(
            constants.AGENT_COMMUNICATION_PORT_KEY
        )

        # Backup existing agent.conf if it exists
        if os.path.exists(agent_config_file_path):
            timestamp = int(time.time())
            shutil.move(
                agent_config_file_path,
                f"{agent_config_file_path}.{timestamp}",
            )

        agent_conf_content = f"""version = '0.1'
[agent]
# hostname or IP of the broker. This parameter is mandatory.
broker_host = '{broker_hostname}'
# The port of the broker. Default: 8445
broker_port = {broker_agent_connection_port}
tls_strict = false
# Folder on the file system from which the tag files are read.
tags_folder = '{agent_tags_dir}'
broker_update_interval = 15
[log]
level = 'debug'
rotation = 'daily'
"""
        overwrite_file(agent_conf_content, agent_config_file_path)
        logger.info("Successfully configured agent.conf")
    except Exception as e:
        logger.error(f"Error when configuring agent.conf: {e}")


def _configure_tags() -> None:
    logger.info("Configuring dcv agent tags ...")
    session_id = os.environ.get("IDEA_SESSION_ID")
    tags_dir = constants.DCV_AGENT_TAGS_DIR
    tags_archive_dir = constants.DCV_AGENT_ARCHIVE_TAGS_DIR
    if BASE_OS == "windows":
        tags_dir = constants.WINDOWS_DCV_AGENT_TAGS_DIR
        tags_archive_dir = constants.WINDOWS_DCV_AGENT_ARCHIVE_TAGS_DIR

    try:
        os.makedirs(tags_dir, exist_ok=True)
        tags_file = os.path.join(tags_dir, constants.DCV_AGENT_TAGS_FILE_NAME)
        if os.path.exists(tags_file):
            os.makedirs(tags_archive_dir, exist_ok=True)
            timestamp = int(time.time())
            os.rename(
                tags_file,
                os.path.join(tags_archive_dir, f"idea_tags.toml.{timestamp}"),
            )

        overwrite_file(f'idea_session_id="{session_id}"', tags_file)
        logger.info("Successfully configured dcv agent tags")
    except Exception as e:
        logger.error(f"Error when configuring dcv agent tags: {e}")

def configure() -> None:
    logger.info("Configuring dcv agent ...")
    _configure_tags()
    _configure_agent_conf()
    _configure_usb_remotization()
    if BASE_OS == "windows":
        try:
            # DCVSessionManagerAgentService is usually disabled on the system. Need to enable it.
            command = [
                "powershell.exe",
                "-Command",
                "Set-Service -Name DcvSessionManagerAgentService -StartupType Automatic",
            ]
            subprocess.run(
                command,
                check=True,
            )
        except Exception as e:
            logger.error(f"Error when enabling DCVSessionManagerAgentService: {e}")
    logger.info("Successfully configured dcv agent")