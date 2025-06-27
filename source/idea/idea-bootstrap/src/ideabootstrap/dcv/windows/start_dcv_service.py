#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import shutil
import subprocess

from ideabootstrap.dcv import constants
from res.utils import logging_utils

logger = logging_utils.get_logger("bootstrap")


def configure() -> None:
    try:
        # Remove the existing self-signed certificate that's used to secure traffic between the NICE DCV client and NICE DCV server
        # since the cert from base AMI might have been expired. The DCV server will regenerate the cert at launch.
        if os.path.exists(constants.WINDOWS_DCV_CERT_DIR):
            shutil.rmtree(constants.WINDOWS_DCV_CERT_DIR)

        # Restart services
        subprocess.run(
            ["powershell.exe", "-Command", "Start-Service -Name dcvserver"], check=True
        )
        subprocess.run(
            [
                "powershell.exe",
                "-Command",
                "Start-Service -Name DcvSessionManagerAgentService",
            ],
            check=True,
        )
        logger.info("Successfully started DCV services")
    except Exception as e:
        logger.error(f"Error when starting DCV services: {e}")
