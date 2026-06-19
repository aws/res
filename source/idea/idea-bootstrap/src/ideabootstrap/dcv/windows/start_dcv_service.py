#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import shutil
import subprocess
import time

from ideabootstrap.dcv import constants
from res.utils import logging_utils

logger = logging_utils.get_logger("bootstrap")


def is_dcvserver_ready(timeout_seconds: int, retry_interval: int) -> bool:
    """
    Check if the DCV server is ready and operational on Windows.

    This method performs two checks to ensure the DCV server is fully operational:
    1. Verifies the Windows service is running
    2. Queries DCV server status to confirm it's ready for connections

    Args:
        timeout_seconds (int): Maximum time to wait for server readiness
        retry_interval (int): Time between retry attempts in seconds

    Returns:
        bool: True if DCV server is ready and operational, False otherwise
    """
    logger.info(f"Checking DCV server readiness with {timeout_seconds}s timeout...")

    start_time = time.time()

    while time.time() - start_time < timeout_seconds:
        try:
            # Check 1: Verify Windows service is running
            logger.debug("Checking if dcvserver Windows service is running...")
            result = subprocess.run(
                ["powershell.exe", "-Command", "Get-Service -Name dcvserver | Select-Object -ExpandProperty Status"],
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode != 0 or result.stdout.strip() != "Running":
                logger.debug(f"DCV server service not running: {result.stdout.strip()}")
                time.sleep(retry_interval)
                continue

            # Check 2: Query DCV server status to confirm readiness
            logger.debug("Attempting to query DCV server status...")
            result = subprocess.run(
                [constants.WINDOWS_DCV_EXECUTABLE_PATH, "list-sessions"],
                capture_output=True,
                text=True,
                check=False,
                timeout=10
            )

            if result.returncode == 0:
                logger.info("DCV server is ready and operational")
                return True
            else:
                logger.debug(f"DCV server status check failed: {result.stderr.strip()}")

        except subprocess.TimeoutExpired:
            logger.debug("DCV server status check timed out")
        except Exception as e:
            logger.debug(f"Error during DCV server readiness check: {e}")

        logger.debug(f"DCV server not ready yet, retrying in {retry_interval} seconds...")
        time.sleep(retry_interval)

    logger.warning(f"DCV server readiness check timed out after {timeout_seconds} seconds")
    return False


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
        logger.info("Successfully started DCV services")
    except Exception as e:
        logger.error(f"Error when starting DCV services: {e}")
