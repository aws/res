#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from ideabootstrap.common.constants import (
    WINDOWS_VDI_CONFIG_HOST_READY_LOCK,
    WINDOWS_BOOTSTRAP_DIR,
)

from ideabootstrap.dcv import dcv

from res.utils import logging_utils

import os
import subprocess
import time

from ideabootstrap.bootstrap_common import update_session_host_info, update_session_state

logger = logging_utils.get_logger("bootstrap")

def run():
    if os.path.isfile(WINDOWS_VDI_CONFIG_HOST_READY_LOCK):
        logger.info(f"Config lock file already exists {WINDOWS_VDI_CONFIG_HOST_READY_LOCK}")

        update_session_host_info()

        if dcv.configure_automatic_console_session():
            session_state = dcv.poll_dcv_session_ready()
            update_session_state(session_state)
        return

    AWS_REGION = os.environ.get("AWS_REGION", "")
    ENVIRONMENT_NAME = os.environ.get("ENVIRONMENT_NAME", "")

    logger.info("Scheduling VDI Idle Check task")
    idle_check_file_path = os.path.join(WINDOWS_BOOTSTRAP_DIR, "scripts", "virtual-desktop-host", "windows", "VDIIdleCheck.ps1")

    schtasks_command = ["schtasks", "/create", "/sc", "minute", "/mo", "1", "/tn", "RunVDIIdleCheckScriptEveryMinute",
                        "/tr", f"powershell -File {idle_check_file_path} -AWSRegion {AWS_REGION} -EnvName {ENVIRONMENT_NAME}",
                        "/ru", "system",
                        "/f"]
    subprocess.run(schtasks_command, check=True)

    current_time = str(int(time.time()))
    with open(WINDOWS_VDI_CONFIG_HOST_READY_LOCK, 'w') as f:
        f.write(current_time)

    logger.info("Finished running Post Reboot Configuration")
    update_session_host_info()

    if dcv.configure_automatic_console_session():
        session_state = dcv.poll_dcv_session_ready()
        update_session_state(session_state)
        logger.info("DCV session placement complete with state: %s", session_state)

