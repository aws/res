#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import Any, Dict, List, Optional, Tuple

import res.exceptions as exceptions  # type: ignore
from res.clients.events import events_client  # type: ignore
from res.resources import cluster_settings, sessions  # type: ignore
from res.utils import logging_utils, table_utils, time_utils  # type: ignore

PERMISSION_PROFILE_DB_HASH_KEY = "profile_id"
PERMISSION_PROFILE_DB_TITLE_KEY = "title"
PERMISSION_PROFILE_DB_DESCRIPTION_KEY = "description"
PERMISSION_PROFILE_DB_CREATED_ON_KEY = "created_on"
PERMISSION_PROFILE_DB_UPDATED_ON_KEY = "updated_on"
PERMISSION_PROFILE_TABLE_NAME = "vdc.controller.permission-profiles"
DEFAULT_PROFILE_FIELDS = {
    "profile_id",
    "title",
    "description",
    "created_on",
    "updated_on",
}

logger = logging_utils.get_logger(PERMISSION_PROFILE_TABLE_NAME)


def create_permission_profile(permission_profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a permission profile
    :param permission_profile: permission profile to create
    :return: created permission profile
    """
    if not permission_profile:
        raise Exception("Permission profile required")

    profile_id = permission_profile["profile_id"]

    logger.info(f"Creating profile permission {profile_id}")

    current_time_ms = time_utils.current_time_ms()
    permission_profile[PERMISSION_PROFILE_DB_CREATED_ON_KEY] = current_time_ms
    permission_profile[PERMISSION_PROFILE_DB_UPDATED_ON_KEY] = current_time_ms

    created_permission_profile = table_utils.create_item(
        table_name=PERMISSION_PROFILE_TABLE_NAME,
        item=permission_profile,
        attribute_names_to_check=[PERMISSION_PROFILE_DB_HASH_KEY],
    )

    logger.info(f"Created permission profile {profile_id} successfully")

    return created_permission_profile


def update_permission_profile(permission_profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update a permission profile
    :param permission_profile: permission profile to update
    :return: updated permission profile
    """
    if not permission_profile:
        raise Exception("Permission profile required")

    profile_id = permission_profile["profile_id"]
    existing_permission_profile = get_permission_profile(profile_id=profile_id)

    logger.info(f"Updating profile permission {profile_id}")

    current_time_ms = time_utils.current_time_ms()
    permission_profile[PERMISSION_PROFILE_DB_UPDATED_ON_KEY] = current_time_ms
    permission_profile.pop(PERMISSION_PROFILE_DB_CREATED_ON_KEY, None)

    updated_permission_profile = table_utils.update_item(
        table_name=PERMISSION_PROFILE_TABLE_NAME,
        key={
            PERMISSION_PROFILE_DB_HASH_KEY: profile_id,
        },
        item=permission_profile,
    )

    events_client.publish_update_event(
        updated_permission_profile[PERMISSION_PROFILE_DB_HASH_KEY],
        "",
        old_entry=existing_permission_profile,
        new_entry=updated_permission_profile,
        table_name=PERMISSION_PROFILE_TABLE_NAME,
    )
    _propagate_globally_disabled_desktop_permissions(updated_permission_profile)

    logger.info(f"Updated permission profile {profile_id} successfully")

    return updated_permission_profile


def _propagate_globally_disabled_desktop_permissions(
    global_profile: Dict[str, Any],
):
    # Check whether global admin profile has been updated
    admin_profile_id = cluster_settings.get_setting(
        "vdc.dcv_session.default_profiles.admin"
    )
    if admin_profile_id == global_profile["profile_id"]:
        # All sharing profiles must be updated to propagate globally disabled desktop permissions
        permission_profiles_cursor = None
        while True:
            all_permission_profiles, permission_profiles_cursor = (
                list_permission_profiles_paginated(
                    next_token=permission_profiles_cursor,
                )
            )
            for sharing_permission_profile in all_permission_profiles:
                if admin_profile_id == sharing_permission_profile["profile_id"]:
                    continue

                for key, value in sharing_permission_profile.items():
                    if key in DEFAULT_PROFILE_FIELDS:
                        continue

                    if sharing_permission_profile[key] and not global_profile[key]:
                        sharing_permission_profile[key] = False

                update_permission_profile(sharing_permission_profile)

            if not permission_profiles_cursor:
                break

        # All current sessions must be updated to propagate globally disabled desktop permissions
        sessions_cursor = None
        while True:
            all_sessions, sessions_cursor = sessions.list_sessions_paginated(
                next_token=sessions_cursor
            )
            for session_dict in all_sessions:
                events_client.publish_enforce_session_permissions_event(
                    session_dict["idea_session_id"],
                    session_dict["owner"],
                )

            if not sessions_cursor:
                break


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


def delete_permission_profile(profile_id: str) -> None:
    """
    Delete permission profile from DDB
    :param profile_id: profile_id of the permission profile
    """
    if not profile_id:
        raise Exception("Profile ID required")

    logger.info(
        f"Deleting permission profile for {PERMISSION_PROFILE_DB_HASH_KEY}: {profile_id}"
    )

    get_permission_profile(profile_id)

    table_utils.delete_item(
        PERMISSION_PROFILE_TABLE_NAME,
        key={
            PERMISSION_PROFILE_DB_HASH_KEY: profile_id,
        },
    )


def is_permission_profiles_table_empty() -> bool:
    """
    Check if permission profile DDB is empty
    :return whether permission profile DDB is empty
    """
    return table_utils.is_table_empty(PERMISSION_PROFILE_TABLE_NAME)


def list_permission_profiles_paginated(
    profile_id: Optional[str] = None,
    next_token: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    List permission profiles with optional filtering and pagination
    :param profile_id: Filter by profile id
    :param next_token: Pagination token
    :return: tuple of (list of permission profiles, next_token)
    """
    filter_expression = table_utils.construct_filter_expression(
        {
            PERMISSION_PROFILE_DB_HASH_KEY: profile_id,
        },
    )
    logger.info(f"Listing permission profiles with filter: {filter_expression}")
    return table_utils.list_items_paginated(
        PERMISSION_PROFILE_TABLE_NAME,
        filter_expression=filter_expression,
        next_token=next_token,
    )
