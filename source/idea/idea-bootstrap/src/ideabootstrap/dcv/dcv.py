#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os

from res.utils import logging_utils
from ideabootstrap.dcv import dcv_agent

logger = logging_utils.get_logger("bootstrap - dcv config")

BASE_OS = os.environ.get("RES_BASE_OS")
if BASE_OS == "windows":
    from ideabootstrap.dcv import windows as dcv
else:
    from ideabootstrap.dcv import linux as dcv


def configure() -> None:
    try:
        if BASE_OS == "windows":
            dcv.dcv_host.configure()
            dcv_agent.configure()
            dcv.post_bootstrap_reboot_task.configure()
            dcv.start_dcv_service.configure()
        else:
            dcv.disable_wayland_protocol.configure()
            dcv.dcv_host.configure()
            dcv_agent.configure()
            dcv.gl.configure()
            dcv.x_server.configure()
            dcv.start_dcv_service.configure()
    except Exception as e:
        logger.error(f"Failed to configure DCV for base_os {BASE_OS}: {e}")
