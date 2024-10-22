#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import logging
import os
import pwd
import re
from typing import Any, Dict, List, Optional

import res.constants as constants
import res.exceptions as exceptions
from res.resources import role_assignments  # type: ignore
from res.utils import auth_utils, table_utils, time_utils  # type: ignore

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)

GROUPS_TABLE_NAME = "accounts.groups"
USERS_TABLE_NAME = "accounts.users"
GROUP_MEMBERS_TABLE_NAME = "accounts.group-members"


def list_groups() -> List[Dict[str, Any]]:
    """
    Retrieve the groups from DDB
    :return: List of groups
    """
    groups: List[Dict[str, Any]] = table_utils.list_table(GROUPS_TABLE_NAME)
    return groups


def create_group(group: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new RES group
    :param group: group to create
    :return: created group
    """
    group_name = group.get("group_name")
    if not group_name:
        raise Exception("group name is required")

    try:
        if get_group(group_name):
            raise Exception(f"group: {group_name} already exists")
    except exceptions.GroupNotFound:
        pass

    if not group.get("ds_name"):
        raise Exception("group ds_name is required")

    logger.info(f"Creating group {group_name}")

    current_time_ms = time_utils.current_time_ms()
    group_to_create = {
        **group,
        "enabled": True,
        "created_on": current_time_ms,
        "updated_on": current_time_ms,
    }
    created_group: Dict[str, Any] = table_utils.create_item(
        GROUPS_TABLE_NAME, group_to_create, ["group_name"]
    )

    logger.info(f"Created group {group_name} successfully")

    return created_group


def delete_group(group: Dict[str, Any], force: bool = False) -> None:
    """
    delete a group
    :param group: group to delete
    :param force: force delete a group even if group has existing members
    """
    if not group.get("group_name"):
        raise Exception("group name is required")
    group_name = group["group_name"]

    try:
        group = get_group(group_name)
    except exceptions.GroupNotFound:
        return

    logger.info(f"Deleting group {group_name}")

    # Delete User Group associations
    users = _get_users_in_group(group_name)
    if users:
        if force:
            _remove_users_from_group(users, group, force)
        else:
            raise Exception(
                "Users associated to group. Group must be empty before it can be deleted.",
            )

    actor_key = f"{group_name}:{constants.ROLE_ASSIGNMENT_ACTOR_GROUP_TYPE}"
    _delete_project_associations_by_actor_key(actor_key, force)

    table_utils.delete_item(GROUPS_TABLE_NAME, {"group_name": group_name})

    logger.info(f"Deleted group {group_name} successfully")


def _delete_project_associations_by_actor_key(
    actor_key: str, force: bool = False
) -> None:
    assignments = role_assignments.list_role_assignments(actor_key=actor_key)

    def _assignment_filter(assignment: Dict[str, Any]) -> bool:
        return assignment.get("resource_type") == constants.PROJECT_ROLE_ASSIGNMENT_TYPE

    project_assignments = [
        assignment for assignment in assignments if _assignment_filter(assignment)
    ]

    # Delete Project associations
    if project_assignments:
        if force:
            for project_assignment in project_assignments:
                role_assignments.delete_role_assignment(project_assignment)
        else:
            raise Exception(
                "Projects associated to group or user. Group or user must not be mapped to any project before it can be deleted.",
            )


def get_group(group_name: str) -> Dict[str, Any]:
    """
    Retrieve the RES group from DDB
    :param group_name: name of the group
    :return: RES group
    """
    if not group_name:
        raise Exception("group name is required")

    group: Optional[Dict[str, Any]] = table_utils.get_item(
        GROUPS_TABLE_NAME,
        key={"group_name": group_name},
    )

    if not group:
        raise exceptions.GroupNotFound(
            f"Group not found: {group_name}",
        )

    return group


def list_users() -> List[Dict[str, Any]]:
    """
    Retrieve the users from DDB
    :return: list of users
    """
    users: List[Dict[str, Any]] = table_utils.list_table(USERS_TABLE_NAME)
    return users


def create_user(user: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create an RES user
    :param user: user to create
    :return: created user
    """
    username = user.get("username")
    if not username or len(username.strip()) == 0:
        raise Exception("username is required")
    if not re.match(constants.USERNAME_REGEX, username):
        raise Exception(constants.USERNAME_ERROR_MESSAGE)
    auth_utils.check_allowed_username(username)

    logger.info(f"Creating user {username}")

    username = auth_utils.sanitize_username(username)
    try:
        if get_user(username):
            raise Exception(
                f"username: {username} already exists.",
            )
    except exceptions.UserNotFound:
        pass
    user["username"] = username
    user["email"] = auth_utils.sanitize_email(user.get("email", ""))

    login_shell = user.get("login_shell")
    if not login_shell or len(login_shell.strip()) == 0:
        user["login_shell"] = auth_utils.DEFAULT_LOGIN_SHELL

    home_dir = user.get("home_dir")
    if not home_dir or len(home_dir.strip()) == 0:
        user["home_dir"] = os.path.join(auth_utils.USER_HOME_DIR_BASE, username)

    user["uid"], user["gid"] = _get_uid_and_gid_for_username(username)
    if not user.get("uid") or not user.get("gid"):
        raise Exception(
            f"Unable to retrieve UID and GID for user {username}",
        )

    user["sudo"] = user.get("sudo", False)
    user["is_active"] = user.get("is_active", False)
    user["additional_groups"] = user.get("additional_groups", [])
    user["enabled"] = True

    current_time_ms = time_utils.current_time_ms()
    user_to_create = {
        **user,
        "created_on": current_time_ms,
        "updated_on": current_time_ms,
        "synced_on": current_time_ms,
    }

    created_user: Dict[str, Any] = table_utils.create_item(
        USERS_TABLE_NAME,
        user_to_create,
        ["username"],
    )
    if user["additional_groups"]:
        add_user_to_groups_by_names(created_user, user["additional_groups"])

    logger.info(f"Created user {username} successfully")

    return created_user


def _get_uid_and_gid_for_username(username: str) -> tuple[Optional[int], Optional[int]]:
    """
    Get the UID and GID for a given user
    :param username: name of the user
    :return: UID and GID
    """
    try:
        user_info = pwd.getpwnam(username)

        uid = user_info.pw_uid
        gid = user_info.pw_gid

        return uid, gid
    except KeyError:
        logger.warning(f"User: {username} not yet available")
        return None, None


def update_user(user: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update the user in DDB
    :param user: the user to update
    :return: the updated user
    """
    username = auth_utils.sanitize_username(user["username"])
    existing_user = get_user(username)
    user["username"] = username

    if not existing_user.get("enabled"):
        raise Exception(
            "User is disabled and cannot be modified.",
        )

    if user.get("email"):
        new_email = auth_utils.sanitize_email(user["email"])
        if existing_user.get("email") != new_email:
            user["email"] = new_email

    user["updated_on"] = time_utils.current_time_ms()
    user.pop("created_on", None)

    updated_user: Dict[str, Any] = table_utils.update_item(
        USERS_TABLE_NAME, {"username": username}, user
    )

    return updated_user


def delete_user(user: Dict[str, Any], force: bool = False) -> None:
    """
    Delete the given user
    :param user: the user to delete
    :param force: force removal
    """
    if not user.get("username"):
        raise Exception("Username is empty")

    username = auth_utils.sanitize_username(user["username"])
    user = get_user(username=username)

    logger.info(f"Deleting user {username}")

    groups = user.get("additional_groups", [])
    if groups:
        logger.info(f"clean-up group memberships for user {username}")
        remove_user_from_groups_by_names(user=user, group_names=groups, force=force)

    actor_key = f"{username}:{constants.ROLE_ASSIGNMENT_ACTOR_USER_TYPE}"
    _delete_project_associations_by_actor_key(actor_key, force)

    table_utils.delete_item(
        USERS_TABLE_NAME,
        key={"username": username},
    )

    logger.info(f"Deleted user {username} successfully")


def remove_user_from_groups_by_names(
    user: Dict[str, Any],
    group_names: List[str],
    sudoers_group_name: Optional[str] = None,
    force: bool = False,
) -> None:
    """
    remove a user from multiple groups.
    useful for operations such as delete user.
    :param user: user to remove
    :param group_names: group names to remove user from
    :param sudoers_group_name: sudoers group name
    :param force: force removal
    """
    if not user:
        raise Exception("user is required")
    if not group_names:
        raise Exception("group_names is required")

    username = user.get("username", "")

    # dedupe and sanitize
    groups_to_remove = list(set(group_names))
    if not user.get("enabled") and not force:
        raise Exception(f"user is disabled: {username}")

    additional_groups = user.get("additional_groups", [])
    remove_user_admin_access = False
    for group_name in groups_to_remove:
        logger.info(f"removing user {username} from group {group_name}")

        try:
            group = get_group(group_name)
        except exceptions.GroupNotFound:
            if group_name in additional_groups:
                additional_groups.remove(group_name)

            if group_name == sudoers_group_name:
                remove_user_admin_access = True

            continue

        if not group.get("enabled") and not force:
            logger.warning(
                f"Cannot remove user {username} from a disabled group {group_name}"
            )
            continue

        if group_name in additional_groups:
            additional_groups.remove(group_name)

        if group.get("role") == constants.ADMIN_ROLE:
            remove_user_admin_access = True

        delete_membership({"group_name": group_name, "username": username})

    if remove_user_admin_access:
        logger.info(f"Designating user {username} as non-admin")

        user["sudo"] = False
        user["role"] = constants.USER_ROLE

    user["synced_on"] = time_utils.current_time_ms()
    user["additional_groups"] = list(additional_groups)
    update_user(user)


def add_user_to_groups_by_names(
    user: Dict[str, Any], group_names: List[str], bypass_active_user_check: bool = False
) -> None:
    """
    add user to groups
    :param user: user to add
    :param group_names: List of groups to add the user to
    :param bypass_active_user_check: For an inactive user, the user relation with groups and projects are not updated. The group_name is only added to the user's additional_groups attribute.
    The bypass_active_user_check flag can be used to bypass this check. This is helpful to add users to RES specific admin and user groups, were the user's relations to these groups must be updated
    even if the user is inactive
    """
    if not user:
        raise Exception("user is required")

    if not group_names:
        raise Exception("group_names is required")

    username = user.get("username", "")
    if not user.get("enabled"):
        raise Exception(
            f"user is disabled: {username}",
        )

    additional_groups = set(user.get("additional_groups", []))
    for group_name in group_names:
        logger.info(f"Adding user {username} to group {group_name}")

        group = get_group(group_name)
        if not group.get("enabled"):
            raise Exception(
                f"cannot add user {username} to a disabled user group {group_name}",
            )

        additional_groups.add(group_name)

        if group.get("role") == constants.ADMIN_ROLE:
            logger.info(f"Designating user {username} as admin")

            user["sudo"] = True
            user["role"] = constants.ADMIN_ROLE

        if bypass_active_user_check or user.get("is_active"):
            create_membership({"group_name": group_name, "username": username})

    user["synced_on"] = time_utils.current_time_ms()
    user["additional_groups"] = list(additional_groups)
    update_user(user)


def get_user(username: str) -> Dict[str, Any]:
    """
    Retrieve the user from DDB
    :param username: name of the user
    :return: the user
    """
    user: Dict[str, Any] = table_utils.get_item(
        USERS_TABLE_NAME, key={"username": username}
    )
    if not user:
        raise exceptions.UserNotFound(
            f"User not found: {username}",
        )
    return user


def create_membership(membership: Dict[str, str]) -> None:
    """
    Create the user membership in a group
    :param membership: membership to create
    """
    if not membership.get("group_name"):
        raise Exception("group_name is required")
    if not membership.get("username"):
        raise Exception("username is required")

    table_utils.create_item(
        GROUP_MEMBERS_TABLE_NAME,
        item=membership,
    )


def delete_membership(membership: Dict[str, str]) -> None:
    """
    Delete the user membership in a group
    :param membership: membership to delete
    """
    if not membership.get("group_name"):
        raise Exception("group_name is required")
    if not membership.get("username"):
        raise Exception("username is required")

    table_utils.delete_item(
        GROUP_MEMBERS_TABLE_NAME,
        key=membership,
    )


def _get_users_in_group(group_name: str) -> List[Dict[str, Any]]:
    """
    Gets a list of usernames in a group
    :param group_name: name of the group
    :return: list of usernames
    """
    if not group_name:
        raise Exception("group name is required")

    users: List[Dict[str, Any]] = table_utils.query(
        GROUP_MEMBERS_TABLE_NAME, {"group_name": group_name}
    )
    return users


def _remove_users_from_group(
    users: List[Dict[str, Any]], group: Dict[str, Any], force: bool = False
) -> None:
    """
    remove multiple users from a group
    useful for bulk operations from front end
    :param usernames: list of usernames
    :param group: group to remove users from
    :param force: force delete even if group is disabled. if user is not found, skip user.
    """
    if not users:
        raise Exception("users is required")

    if not group:
        raise Exception("group is required")

    if not group.get("enabled") and not force:
        raise Exception(
            "cannot remove users from a disabled user group",
        )

    is_admin = group.get("role") == constants.ADMIN_ROLE

    for user in users:
        username = user.get("username")
        if not username:
            raise Exception("username is required")

        if not user.get("enabled") and not force:
            raise Exception(
                f"user is disabled: {username}",
            )

        additional_groups = set(user.get("additional_groups", []))
        group_name = group.get("group_name", "")
        if group_name in additional_groups:
            logger.info(f"removing user {username} from group {group_name}")

            user["additional_groups"] = list(additional_groups - {group_name})
            if is_admin:
                logger.info(f"Designating user {username} as non-admin")

                user["sudo"] = False
                user["role"] = constants.USER_ROLE

            user["synced_on"] = time_utils.current_time_ms()
            update_user(user)

        if user.get("is_active"):
            delete_membership({"group_name": group_name, "username": username})
