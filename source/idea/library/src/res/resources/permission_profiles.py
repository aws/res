#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import logging
from typing import Any, Dict, Optional

import res.exceptions as exceptions  # type: ignore
from res.utils import table_utils, time_utils  # type: ignore

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)

PERMISSION_PROFILE_DB_HASH_KEY = "profile_id"
PERMISSION_PROFILE_DB_TITLE_KEY = "title"
PERMISSION_PROFILE_DB_DESCRIPTION_KEY = "description"
PERMISSION_PROFILE_DB_CREATED_ON_KEY = "created_on"
PERMISSION_PROFILE_DB_UPDATED_ON_KEY = "updated_on"
PERMISSION_PROFILE_TABLE_NAME = "vdc.controller.permission-profiles"


def create_permission_profile(permission_profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a permission profile
    :param permission_profile: permission profile to create
    :return: created permission profile
    """
    if not permission_profile:
        raise Exception("Permission profile required")

    profile_id = permission_profile.get("profile_id", "")
    if not profile_id or not profile_id.strip():
        raise Exception("profile_id is required")
    profile_title = permission_profile.get("title", "")
    if not profile_title or not profile_title.strip():
        raise Exception("title is required")

    logger.info(f"Creating profile permission {profile_id}")

    try:
        if get_permission_profile(profile_id):
            raise Exception(f"profile_id: {profile_id} already exists.")
    except exceptions.PermissionProfileNotFound:
        pass

    current_time_ms = time_utils.current_time_ms()
    permission_profile[PERMISSION_PROFILE_DB_CREATED_ON_KEY] = current_time_ms
    permission_profile[PERMISSION_PROFILE_DB_UPDATED_ON_KEY] = current_time_ms

    created_permission_profile = table_utils.create_item(
        table_name=PERMISSION_PROFILE_TABLE_NAME, item=permission_profile
    )

    logger.info(f"Created permission profile {profile_id} successfully")

    return created_permission_profile


def get_permission_profile(profile_id: str) -> Optional[Dict[str, Any]]:
    """
    Get permission profile from DDB
    :param profile_id: profile_id of the permission profile
    :return permission profile
    """
    if not profile_id:
        raise Exception("Profile ID required")

    logger.info(
        f"Getting permission profile for {PERMISSION_PROFILE_DB_HASH_KEY}: {profile_id}"
    )

    permission_profile = table_utils.get_item(
        PERMISSION_PROFILE_TABLE_NAME,
        key={
            PERMISSION_PROFILE_DB_HASH_KEY: profile_id,
        },
    )

    if not permission_profile:
        raise exceptions.PermissionProfileNotFound(
            f"Permission profile not found for {PERMISSION_PROFILE_DB_HASH_KEY}: {profile_id}"
        )

    return permission_profile


def is_permission_profiles_table_empty() -> bool:
    """
    Check if permission profile DDB is empty
    :return whether permission profile DDB is empty
    """
    return table_utils.is_table_empty(PERMISSION_PROFILE_TABLE_NAME)
