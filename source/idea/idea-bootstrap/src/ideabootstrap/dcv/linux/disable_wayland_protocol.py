#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import re
import subprocess
import time

import ideabootstrap.dcv.constants as constants
from ideabootstrap.bootstrap_common import overwrite_file
from res.utils import logging_utils

logger = logging_utils.get_logger("bootstrap")


def _configure_wayland(pattern: str, file_path: str) -> None:
    try:
        with open(file_path, "r") as f:
            content = f.read()
        modified_content = re.sub(
            f"^#({pattern})$",
            r"\1",
            content,
            flags=re.MULTILINE,
        )
        overwrite_file(modified_content, file_path)
        logger.info(f"Successfully disabled wayland protocol")
    except Exception as e:
        logger.error(f"Error when disabling wayland protocol: {e}")


def configure() -> None:
    base_os = os.environ.get("RES_BASE_OS")
    try:
        if base_os in ("amzn2", "amzn2023", "rhel8", "rhel9", "rocky9"):
            if base_os == "amzn2023" or base_os == "rhel9" or base_os == "rocky9":
                _configure_wayland(
                    "WaylandEnable=false", constants.GDM_CONFIG_RHEL_PATH
                )
                # restart gdm
                subprocess.run(["systemctl", "restart", "gdm"], check=True)
            else:
                logger.info(f"OS is {base_os}, no need to disable the wayland protocol")

        elif base_os in ("ubuntu2204", "ubuntu2404"):
            _configure_wayland("WaylandEnable=false", constants.GDM_CONFIG_DEBIAN_PATH)
            # restart gdm3
            subprocess.run(["systemctl", "restart", "gdm3"], check=True)
        else:
            logger.error(f"Unsupported base OS {base_os}")
    except Exception as e:
        logger.error(f"Error when restart gdm: {e}")
