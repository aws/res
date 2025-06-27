#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import subprocess
from typing import Dict

from ideabootstrap.file_system import common
from ideabootstrap.file_system.windows import constants
from res.resources import cluster_settings
from res.utils import logging_utils

logger = logging_utils.get_logger("bootstrap")


def mount_shared_storage():
    domain_user_name = rf'{cluster_settings.get_setting("directoryservice.ad_short_name")}\{os.getenv("SESSION_OWNER")}'

    shares = []
    shared_storage = cluster_settings.get_config("shared-storage")
    for name, storage in shared_storage.items():
        if isinstance(storage, Dict) and common.eval_shared_storage_scope(
            shared_storage=storage
        ):
            if (
                storage["provider"] == "fsx_netapp_ontap"
                and "mount_drive" in storage
                and "cifs_share_name" in storage["fsx_netapp_ontap"]["volume"]
            ):
                shares.append(
                    {
                        "MountDrive": f"{storage['mount_drive']}:",
                        "Path": f"\\\\{storage['fsx_netapp_ontap']['svm']['smb_dns']}\\{storage['fsx_netapp_ontap']['volume']['cifs_share_name']}",
                    }
                )
            elif (
                storage["provider"] == "fsx_windows_file_server"
                and "mount_drive" in storage
            ):
                shares.append(
                    {
                        "MountDrive": f"{storage['mount_drive']}:",
                        "Path": f"\\\\{storage['fsx_windows_file_server']['dns']}\\share",
                    }
                )

    # Process shares only if any exist
    if shares:
        # Create directory if it doesn't exist
        os.makedirs(r"C:\IDEA\LocalScripts", exist_ok=True)

        # Create batch file content
        batch_commands = []
        for share in shares:
            batch_commands.append(
                f'if not exist {share["MountDrive"]} '
                f'(net use {share["MountDrive"]} {share["Path"]} /persistent:yes)'
            )

        # Write batch file
        with open(constants.BATCH_FILE_PATH, "w") as f:
            f.write("\n".join(batch_commands))

        # Create a scheduled task to execute after the domain user logs in
        ps_command = [
            "powershell.exe",
            "-Command",
            rf"""
            $action = New-ScheduledTaskAction -Execute {constants.BATCH_FILE_PATH}
            $trigger = New-ScheduledTaskTrigger -AtLogOn -User {domain_user_name}
            Register-ScheduledTask -Action $action -Trigger $trigger -TaskName "MountSharedStorage" -Description "Mount Shared Storage" -User {domain_user_name}
             """,
        ]
        try:
            result = subprocess.run(
                ps_command, check=True, capture_output=True, text=True
            )
            logger.info(result.stdout)
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to mount shared file system: {e.stderr}")


def configure() -> None:
    mount_shared_storage()
