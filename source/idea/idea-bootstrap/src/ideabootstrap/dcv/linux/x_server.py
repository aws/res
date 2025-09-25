#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import re
import subprocess
import time

import ideabootstrap.dcv.constants as constants
from res.utils import logging_utils

logger = logging_utils.get_logger("bootstrap")


def _x_server_validated():
    try:
        ps_output = subprocess.check_output(["ps", "aux"], text=True)
        auth_pattern = r"X.*-auth ([^ ]+)"
        matches = re.findall(auth_pattern, ps_output)
        if not matches:
            return False

        xauth_file = matches[0]
        env = os.environ.copy()
        env.update({"DISPLAY": ":0", "XAUTHORITY": xauth_file})
        xhost_output = subprocess.check_output(["xhost"], env=env, text=True)

        return "SI:localuser:dcv" in xhost_output
    except Exception as e:
        logger.error(f"Error in validating x server: {e}")
        return False


def _verify_x_server_is_up():
    start_time = time.time()
    logger.info("Validating if x server is running ...")
    time.sleep(10)
    validated = _x_server_validated()
    count = 0

    while not validated:
        logger.info(
            f"Waiting for X Server to come up.. sleeping for 10 more seconds; {count} seconds already slept"
        )
        count += 10
        time.sleep(10)
        validated = _x_server_validated()

        if validated:
            logger.info("x server is up and running....")
            break

        if count % 50 == 0:
            logger.info(
                "Waited 5 times in a row. Was unsuccessful. trying to restart x server again..."
            )
            _restart_x_server()

        current_time = time.time()
        elapsed = int(current_time - start_time)
        if elapsed >= constants.X_SERVER_MAX_TIMEOUT_SEC:
            logger.info(
                f"Max timeout for verify server reached after {elapsed} seconds"
            )
            break

    current_time = time.time()
    elapsed = int(current_time - start_time)
    if elapsed < constants.X_SERVER_MAX_TIMEOUT_SEC:
        logger.info("x server is up and running....")


def _start_x_server():
    if not _x_server_validated():
        logger.info("# start x server ...")
        try:
            subprocess.run(
                ["sudo", "systemctl", "isolate", "graphical.target"], check=True
            )
            logger.info("Wait for x server to start ...")
        except Exception as e:
            logger.error(f"Error starting X server: {e}")


def _restart_x_server():
    logger.info("Restart x server ...")
    try:
        subprocess.run(
            ["sudo", "systemctl", "isolate", "multi-user.target"], check=True
        )
        subprocess.run(["sudo", "systemctl", "isolate", "graphical.target"], check=True)
        logger.info("# wait for x server to start ...")
    except Exception as e:
        logger.error(f"Error restarting X server: {e}")


def _start_and_validate_x_server():
    _start_x_server()
    _verify_x_server_is_up()


def configure():
    session_type = os.getenv("SESSION_TYPE")

    if session_type == "VIRTUAL":
        logger.info(f"{session_type} session type, skipping x server configuration...")
        return

    logger.info("Configuring X Server")

    try:
        subprocess.run(
            ["sudo", "systemctl", "set-default", "graphical.target"], check=True
        )
        _start_and_validate_x_server()
    except Exception as e:
        logger.error(f"Error when start and validate x_server: {e}")
