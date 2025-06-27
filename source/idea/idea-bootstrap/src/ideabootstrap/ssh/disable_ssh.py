#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import subprocess

from res.utils import logging_utils

logger = logging_utils.get_logger("bootstrap")

def configure() -> None:
    """
    Disable SSH socket and socket
    """
    try:
        commands = [
            ["systemctl", "disable", "sshd.socket"],
            ["systemctl", "disable", "sshd.service"],
            ["systemctl", "stop", "sshd.socket"],
            ["systemctl", "stop", "sshd.service"],
        ]

        for cmd in commands:
            subprocess.run(cmd, check=True)
        logger.info("SSH disabled Successfully")
    except Exception as e:
        logger.error(f"Error when disabling SSH: {str(e)}")
