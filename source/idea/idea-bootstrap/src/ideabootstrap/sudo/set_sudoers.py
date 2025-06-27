#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from res.resources import accounts, cluster_settings
import ideabootstrap.sudo.constants as constants
from ideabootstrap.bootstrap_common import file_content_exists, append_to_file
from res.utils import logging_utils

logger = logging_utils.get_logger("bootstrap")


def _set_sudoer_group(group_name: str) -> None:
    ad_domain_name = cluster_settings.get_setting("directoryservice.name")
    append_to_file(
        f'## Add the "{group_name}" group from the ${ad_domain_name} domain.\n%{group_name} ALL=(ALL:ALL) ALL',
        constants.SUDOERS_FILE,
    )


def _set_sudoer_users(sudoer_group_name: str) -> None:
    admins = accounts.list_users(admin=True)
    append_to_file("## Add RES admins to sudoers", constants.SUDOERS_FILE)
    for admin in admins:
        username = admin.get("username", "")
        additional_groups = admin.get("additional_groups", [])
        if sudoer_group_name:
            if sudoer_group_name not in additional_groups:
                append_to_file(f"{username} ALL=(ALL:ALL) ALL", constants.SUDOERS_FILE)
        else:
            append_to_file(f"{username} ALL=(ALL:ALL) ALL", constants.SUDOERS_FILE)


def configure() -> None:
    """
    Configure sudoers settings
    """
    try:
        sudoers_group_name = cluster_settings.get_setting(
            "directoryservice.sudoers.group_name"
        )
        # Set up sudoers group permission in configured in cluster setting
        if sudoers_group_name:
            group_name_escaped = sudoers_group_name.replace(" ", "\ ")
            if not file_content_exists(
                f"%{group_name_escaped}", constants.SUDOERS_FILE
            ):
                _set_sudoer_group(group_name_escaped)

        if not file_content_exists(
            "## Add RES admins to sudoers", constants.SUDOERS_FILE
        ):
            _set_sudoer_users(sudoers_group_name)
        if not file_content_exists("sudoers: files", constants.NSSWITCH_FILE):
            append_to_file("sudoers: files", constants.NSSWITCH_FILE)

        logger.info("Setup Sudoers successfully")
    except Exception as e:
        logger.error(f"Failed to setup sudoers: {str(e)}")
