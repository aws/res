#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import re
import subprocess
import time

import ideabootstrap.dcv.constants as constants
from ideabootstrap.dcv.linux.gl import _is_gpu_instance_type
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
                ["systemctl", "isolate", "graphical.target"],
                check=True,
                timeout=constants.SUBPROCESS_TIMEOUT_SEC,
            )
            logger.info("Wait for x server to start ...")
        except Exception as e:
            logger.error(f"Error starting X server: {e}")


def _restart_x_server():
    logger.info("Restart x server ...")
    try:
        subprocess.run(
            ["systemctl", "isolate", "multi-user.target"],
            check=True,
            timeout=constants.SUBPROCESS_TIMEOUT_SEC,
        )
        subprocess.run(
            ["systemctl", "isolate", "graphical.target"],
            check=True,
            timeout=constants.SUBPROCESS_TIMEOUT_SEC,
        )
        logger.info("# wait for x server to start ...")
    except Exception as e:
        logger.error(f"Error restarting X server: {e}")


def _start_and_validate_x_server():
    _start_x_server()
    _verify_x_server_is_up()


def _divert_xorg_to_xdcv():
    base_os = os.environ.get("RES_BASE_OS", "")

    if _is_gpu_instance_type():
        return

    xdcv_console = "/usr/bin/Xdcv-console"

    if not os.path.isfile(xdcv_console):
        logger.info(f"{xdcv_console} not found, skipping Xdcv-console configuration")
        return

    if base_os in ("ubuntu2204", "ubuntu2404"):
        _divert_xdcv_ubuntu(xdcv_console)
    # TODO: Add RHEL/Rocky and AL2023 support


def _divert_xdcv_ubuntu(xdcv_console: str):
    """Ubuntu: dpkg-divert + symlink to replace Xorg with Xdcv-console."""
    xorg = "/usr/bin/Xorg"

    if os.path.islink(xorg) and os.readlink(xorg) == xdcv_console:
        logger.info("Xorg already diverted to Xdcv-console")
        return

    logger.info("Diverting Xorg to Xdcv-console for non-GPU Ubuntu instance")
    try:
        subprocess.run(
            [
                "dpkg-divert",
                "--package",
                "nice-xdcv",
                "--divert",
                "/usr/bin/Xorg.orig",
                "--rename",
                xorg,
            ],
            check=True,
            timeout=constants.SUBPROCESS_TIMEOUT_SEC,
        )
        subprocess.run(
            ["ln", "-sf", xdcv_console, xorg],
            check=True,
            timeout=constants.SUBPROCESS_TIMEOUT_SEC,
        )
        logger.info("Successfully diverted Xorg to Xdcv-console")
    except Exception as e:
        logger.error(f"Error diverting Xorg to Xdcv-console: {e}")


def ensure_xorg_config():
    """Ensure xorg.conf has the correct GPU PCI BusID.

    Re-runs nvidia-xconfig on every boot for GPU instances to handle the case
    where a VDI's instance type is changed across GPU families (e.g., g4dn/T4
    to g6/L4). nvidia-xconfig --preserve-busid is idempotent and always writes
    the correct BusID for the current GPU.
    """
    if not _is_gpu_instance_type():
        return

    try:
        subprocess.run(
            ["nvidia-xconfig", "--preserve-busid", "--enable-all-gpus"],
            check=True,
            capture_output=True,
        )
        logger.info("nvidia-xconfig completed successfully")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logger.error(f"Failed to run nvidia-xconfig: {e}")


def configure():
    session_type = os.getenv("SESSION_TYPE")

    if session_type == "VIRTUAL":
        logger.info(f"{session_type} session type, skipping x server configuration...")
        return

    logger.info("Configuring X Server")

    ensure_xorg_config()
    _divert_xorg_to_xdcv()

    try:
        subprocess.run(
            ["systemctl", "set-default", "graphical.target"],
            check=True,
            timeout=constants.SUBPROCESS_TIMEOUT_SEC,
        )
        _start_and_validate_x_server()
    except Exception as e:
        logger.error(f"Error when start and validate x_server: {e}")
