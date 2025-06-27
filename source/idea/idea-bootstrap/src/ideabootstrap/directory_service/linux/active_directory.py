#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import logging
import subprocess
from typing import Any, Dict

from res.utils import sssd_utils


def join_active_directory(auth_entry: Dict[str, Any], logger: logging.Logger) -> None:
    otp = auth_entry["otp"]
    domain_controller = auth_entry["domain_controller"]
    hostname = auth_entry["hostname"]

    cmd = [
        "realm",
        "join",
        "--one-time-password",
        otp,
        "--computer-name",
        hostname.upper(),
        "--client-software",
        "sssd",
        "--server-software",
        "active-directory",
        "--membership-software",
        "adcli",
        "--verbose",
        domain_controller,
    ]

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info(result.stdout)
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to join AD: {e.stderr}")
        return

    configure_sssd(logger)


def is_in_active_directory(_logger: logging.Logger) -> bool:
    return sssd_utils.is_in_active_directory()


def configure_sssd(logger: logging.Logger):
    try:
        sssd_utils.restart_sssd()
    except Exception as e:
        # Avoid throwing exceptions in the long-running application.
        # The application should continue monitoring and trying to restart SSSD upon SSSD config updates.
        logger.error(f"Failed to restart SSSD: {e}")
