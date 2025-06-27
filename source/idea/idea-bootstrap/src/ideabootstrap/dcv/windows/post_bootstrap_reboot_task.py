#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import subprocess
from ideabootstrap.bootstrap_common import overwrite_file
from ideabootstrap.dcv import constants
from res.resources import cluster_settings
from res.utils import logging_utils

logger = logging_utils.get_logger("bootstrap")

def configure() -> None:
    logger.info("Configuring PostBootstrapRebootExecuteOnce.ps1 ...")
    local_user = os.environ.get("IDEA_SESSION_OWNER")
    try:
        directory_provider = cluster_settings.get_setting("directoryservice.provider")
        ad_short_name = cluster_settings.get_setting("directoryservice.ad_short_name")
        if directory_provider and directory_provider == "activedirectory":
            # if ActiveDirectory, add the user to local Administrators group.
            # todo: need to have a broader discussion with the group on this. this will work well as long as no shared storage is mounted automatically.
            # once support for NETAPP OnTAP is added and if NETAPP OnTAP is used for /internal, this potentially introduces a data security risk.
            post_bootstrap_reboot_content = f"""
# Add user to local Administrators group  (commenting this for now, until we have decision. may be make  this configurable via eVDI settings ...)
# Add-LocalGroupMember -Group Administrators -Member "{ad_short_name}\\{local_user}"

# Set session owner to the one in Domain
New-Item -Path "{constants.WINDOWS_DCV_REGISTRY_PATH}" -Name "session-management\\automatic-console-session" -Force
New-ItemProperty -Path "{constants.WINDOWS_DCV_REGISTRY_PATH}\\session-management\\automatic-console-session" -Name "owner" -PropertyType "String" -Value "{ad_short_name}\\{local_user}" -Force
New-ItemProperty -Path "{constants.WINDOWS_DCV_REGISTRY_PATH}\\session-management\\automatic-console-session" -Name "storage-root" -PropertyType "String" -Value "C:\\session-storage\\{local_user}" -Force

# remove scheduled task after executing once
schtasks /delete /tn PostBootstrapRebootExecuteOnce /f
"""
            os.makedirs(constants.IDEA_SCRIPTS_DIR, exist_ok=True)
            
            logger.info(f"Overwritting files: {constants.POST_REBOOT_SCRIPT_PATH}")
            overwrite_file(
                post_bootstrap_reboot_content, constants.POST_REBOOT_SCRIPT_PATH
            )

            command = ['schtasks', '/create', '/sc', 'onstart', '/tn', 'PostBootstrapRebootExecuteOnce',
                '/tr', f'"powershell -ExecutionPolicy Bypass -File {constants.POST_REBOOT_SCRIPT_PATH}"',
                '/ru', 'system', '/f']

            subprocess.run(
                command,
                check=True,
            )
            logger.info(
                "Successfully configured PostBootstrapRebootExecuteOnce.ps1 and setup task"
            )
    except Exception as e:
        logger.error(f"Error when configuring PostBootstrapRebootExecuteOnce.ps1: {e}")
