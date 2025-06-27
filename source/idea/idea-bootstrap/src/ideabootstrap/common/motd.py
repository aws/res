#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from ideabootstrap.bootstrap_common import get_base_os

from res.utils import logging_utils

import os
import subprocess
import re

logger = logging_utils.get_logger("bootstrap")

def update(messages=None):
    """
    Updates the /etc/motd file with RES ASCII art and custom messages
    for supported operating systems (Amazon Linux 2, Amazon Linux 2023, RHEL 8, RHEL 9, Rocky 9).

    Args:
        messages (list, optional): List of messages to include in the MOTD
    """

    base_os = get_base_os()

    try:
        if re.match(r'^(amzn2|amzn2023|rhel8|rhel9|rocky9)$', base_os):
            motd_content = """
  ____  _____ ____
 |  _ \| ____/ ___|
 | |_) |  _| \___ \\
 |  _ <| |___ ___| |
 |_| \_\_____|____/
"""
            if messages:
                for message in messages:
                    motd_content += f"{message}\n"

            motd_content += "> source /etc/environment to load RES paths\n"

            with open('/etc/motd', 'w') as motd_file:
                motd_file.write(motd_content)

            logger.info("MOTD updated successfully.")
        else:
            logger.info(f"MOTD not updated: Unsupported OS '{base_os}'")

    except Exception as e:
        logger.error(f"Error updating MOTD: {str(e)}")


def disable_update():
    base_os = get_base_os()
    logger.info(f"Disable Motd Update")
    if base_os in ["amzn2", "amzn2023"]:
        try:
            subprocess.run(["/usr/sbin/update-motd", "--disable"], check=True)

            if os.path.exists("/etc/cron.d/update-motd"):
                logger.warning("Removing: /etc/cron.d/update-motd")
                os.remove("/etc/cron.d/update-motd")
            else:
                logger.warning("Cron file /etc/cron.d/update-motd does not exist")

            motd_dir = "/etc/update-motd.d/"
            logger.info(f"Removing all files in: {motd_dir}")
            if os.path.isdir(motd_dir):
                files = os.listdir(motd_dir)
                for file in files:
                    file_path = os.path.join(motd_dir, file)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        logger.info(f"Removed: {file_path}")
            else:
                logger.error(f"Directory {motd_dir} does not exist")
            logger.info("MOTD successfully disabled")
        except Exception as e:
            logger.error(f"Error disabling MOTD: {str(e)}")
