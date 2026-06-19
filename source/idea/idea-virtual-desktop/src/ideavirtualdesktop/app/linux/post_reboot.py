#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from ideabootstrap.common.constants import (
    LINUX_VDI_CONFIG_HOST_READY_LOCK,
    BOOTSTRAP_DIR
)

from res.utils import logging_utils

from ideabootstrap import bootstrap_common
from ideabootstrap.dcv import dcv

import tempfile
import os
import subprocess
import time

from ideabootstrap.bootstrap_common import update_session_host_info, update_session_state

logger = logging_utils.get_logger("bootstrap")

def run():
    if os.path.isfile(LINUX_VDI_CONFIG_HOST_READY_LOCK):
        logger.info(f"Instance Ready Lock File Already Exists: {LINUX_VDI_CONFIG_HOST_READY_LOCK}")

        update_session_host_info()

        if dcv.configure_automatic_console_session():
            session_state = dcv.poll_dcv_session_ready()
            update_session_state(session_state)
        return

    logger.info(f"Running post reboot process: {LINUX_VDI_CONFIG_HOST_READY_LOCK}")
    bootstrap_common.set_reboot_required("no")

    IDEA_SERVICES_PATH="/opt/idea/.services"
    AWS_REGION = os.environ.get("AWS_REGION", "")
    IDEA_SERVICES_LOGS_PATH=f"{IDEA_SERVICES_PATH}/logs"
    IDEA_CLUSTER_NAME = os.environ.get("environment_name", "")

    if not AWS_REGION:
        logger.warning(f"Environment variables AWS_REGION is not set")

    os.makedirs(IDEA_SERVICES_PATH, exist_ok=True)
    os.makedirs(IDEA_SERVICES_LOGS_PATH, exist_ok=True)

    try:
        logger.info("Scheduling VDI Idle Check task")

        vdi_idle_check_path = os.path.join(BOOTSTRAP_DIR, "latest", "scripts", "virtual-desktop-host", "linux", "vdi_idle_check.sh")

        crontab_list = subprocess.run(['crontab', '-l'], capture_output=True, text=True, check=False)
        current_crontab = crontab_list.stdout if crontab_list.returncode == 0 else ""

        cron_job = f"*/1 * * * * /bin/bash {vdi_idle_check_path} -r {AWS_REGION} -n {IDEA_CLUSTER_NAME}"

        vdi_idle_check_crontab = current_crontab + cron_job + "\n"

        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_file.write(vdi_idle_check_crontab)
            temp_file_path = temp_file.name

        subprocess.run(['crontab', temp_file_path])

        os.unlink(temp_file_path)
        logger.info("Crontab entry added successfully")
    except subprocess.SubprocessError as e:
        logger.error(f"Failed to update crontab: {e}")

    current_time = str(int(time.time()))
    with open(LINUX_VDI_CONFIG_HOST_READY_LOCK, 'w') as f:
        f.write(current_time)

    logger.info(f"Created instance ready lock file: {LINUX_VDI_CONFIG_HOST_READY_LOCK}")

    update_session_host_info()

    if dcv.configure_automatic_console_session():
        session_state = dcv.poll_dcv_session_ready()
        update_session_state(session_state)
        logger.info("DCV session placement complete with state: %s", session_state)
