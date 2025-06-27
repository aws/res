#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import subprocess

import ideabootstrap.dcv.constants as constants
from ideabootstrap.bootstrap_common import overwrite_file
from res.utils import logging_utils

logger = logging_utils.get_logger("bootstrap")


def _start_and_configure_dcv_service():
    """Helper function to start and configure DCV server service"""
    logger.info("Start dcv server ...")
    try:
        subprocess.run(["sudo", "systemctl", "enable", "dcvserver"], check=True)

        dcv_service_content = """#  This file is part of systemd.
#  AGENT
#  systemd is free software; you can redistribute it and/or modify it
#  under the terms of the GNU Lesser General Public License as published by
#  the Free Software Foundation; either version 2.1 of the License, or
#  (at your option) any later version.

[Unit]
Description=NICE DCV server daemon
DefaultDependencies=no
Conflicts=umount.target
After=network-online.target remote-fs.target
Before=umount.target

[Service]
PermissionsStartOnly=true
ExecStartPre=-/sbin/modprobe eveusb
ExecStart=/usr/bin/dcvserver -d --service
Restart=always
BusName=com.nicesoftware.DcvServer
User=dcv
Group=dcv

[Install]
WantedBy=multi-user.target"""
        overwrite_file(dcv_service_content, constants.DCV_SERVER_SERVICE_PATH)

        # Because we have modified the .service file we need to tell systemctl to reload and recreate the dependency tree again.
        # This is necessary because we are introducing a dependency on network.targets.
        # Refer - https://serverfault.com/questions/700862/do-systemd-unit-files-have-to-be-reloaded-when-modified
        subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
        subprocess.run(["sudo", "systemctl", "restart", "dcvserver"], check=True)
        logger.info("Successfully configured and started dcv server")
    except Exception as e:
        logger.error(f"Error in starting and configuring dcv service: {e}")


def _start_and_configure_dcv_agent_service():
    logger.info("Start dcv session manager agent ...")
    try:
        subprocess.run(
            ["sudo", "systemctl", "enable", "dcv-session-manager-agent"], check=True
        )

        agent_service_content = """#  This file is part of systemd.
#  AGENT
#  systemd is free software; you can redistribute it and/or modify it
#  under the terms of the GNU Lesser General Public License as published by
#  the Free Software Foundation; either version 2.1 of the License, or
#  (at your option) any later version.

[Unit]
Description=Agent component of DCV Session Manager
DefaultDependencies=no
Conflicts=umount.target
After=network-online.target remote-fs.target
Before=umount.target

[Service]
Type=simple
ExecStart=/usr/libexec/dcv-session-manager-agent/dcvsessionmanageragent
User=dcvsmagent
Group=dcvsmagent

[Install]
WantedBy=multi-user.target"""
        overwrite_file(agent_service_content, constants.DCV_AGENT_SERVICE_PATH)

        # Because we have modified the .service file we need to tell systemctl to reload and recreate the dependency tree again.
        # This is necessary because we are introducing a dependency on network.targets.
        # Refer - https://serverfault.com/questions/700862/do-systemd-unit-files-have-to-be-reloaded-when-modified
        subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
        subprocess.run(
            ["sudo", "systemctl", "restart", "dcv-session-manager-agent"], check=True
        )
        logger.info("Successfully configured started dcv session manager agent")
    except Exception as e:
        logger.error(f"Error in starting and configuring dcv agent service: {e}")


def configure() -> None:
    _start_and_configure_dcv_service()
    _start_and_configure_dcv_agent_service()
