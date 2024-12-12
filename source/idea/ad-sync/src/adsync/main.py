#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import logging
import time
from typing import Any, Dict, List, Optional, Set

import res.constants as constants  # type: ignore
import res.exceptions as exceptions  # type: ignore
from res.clients.ldap_client.active_directory_client import (  # type: ignore
    ActiveDirectoryClient,
)
from res.resources import accounts  # type: ignore
from res.utils import aws_utils, ldap_utils, sssd_utils  # type: ignore

logger = logging.getLogger("ad-sync")
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)

DEFAULT_LDAP_GROUP_FILTERSTR = "(objectClass=group)"
DEFAULT_LDAP_USER_FILTERSTR = "(objectClass=user)"


def _fetch_ldap_groups(
    active_directory_client: ActiveDirectoryClient,
) -> List[Dict[str, Any]]:
    """
    Retrieve LDAP groups from AD.
    :param active_directory_client: ActiveDirectoryClient
    :return: List of LDAP groups.
    """
    logger.info("Fetching LDAP groups")

    groups_filter = active_directory_client.options.groups_filter
    if groups_filter:
        _validate_ldap_filter(groups_filter)
        filterstr = f"(&{DEFAULT_LDAP_GROUP_FILTERSTR}{groups_filter})"
    else:
        filterstr = DEFAULT_LDAP_GROUP_FILTERSTR

    search_result = active_directory_client.simple_paginated_search(
        base=active_directory_client.options.groups_ou, filterstr=filterstr
    )

    ldap_result = search_result.get("result", [])

    # Each result tuple is of the form (dn, attrs),
    # where dn is a string containing the DN (distinguished name) of the entry,
    # and attrs is a dictionary containing the attributes associated with the entry.
    ldap_groups: List[Dict[str, Any]] = [
        _convert_ldap_group(group[1]) for group in ldap_result
    ]
    return ldap_groups


def _convert_ldap_group(ldap_group: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Convert the LDAP group attributes into an RES expected dictionary.
    :param ldap_group: LDAP group attributes
    :return: RES expected group dictionary
    """
    if not ldap_group:
        return None

    return {
        "name": ldap_utils.ldap_str(ldap_group.get("cn")),
        "gid": ldap_utils.ldap_str(ldap_group.get("gidNumber")),
        "ds_name": ldap_utils.ldap_str(ldap_group.get("sAMAccountName")),
    }


def _sync_groups(
    active_directory_client: ActiveDirectoryClient, ldap_groups: List[Dict[str, Any]]
) -> Set[str]:
    """
    Sync LDAP groups to RES.
    :param active_directory_client: ActiveDirectoryClient
    :param ldap_groups: List of LDAP groups.
    :return: List of LDAP groups that failed to sync.
    """
    logger.info("Syncing LDAP groups to RES")

    ldap_group_mappings = {group["name"]: group for group in ldap_groups}
    ldap_group_names = set(ldap_group_mappings.keys())

    # only Sync AD Groups
    res_groups = [
        g
        for g in accounts.list_groups()
        if g["identity_source"] == constants.SSO_USER_IDP_TYPE
    ]
    res_group_mappings = {group["group_name"]: group for group in res_groups}
    res_group_names = set(res_group_mappings.keys())

    groups_failed_to_sync: Set[str] = set()
    for group_name in ldap_group_names - res_group_names:
        try:
            group = ldap_group_mappings[group_name]
            accounts.create_group(
                group={
                    "group_name": group["name"],
                    "ds_name": group["ds_name"],
                    "gid": group["gid"],
                    "role": (
                        constants.ADMIN_ROLE
                        if group["name"]
                        == active_directory_client.options.sudoers_group_name
                        else constants.USER_ROLE
                    ),
                    "identity_source": constants.SSO_USER_IDP_TYPE,
                }
            )
        except Exception as e:
            groups_failed_to_sync.add(group_name)
            logger.error(e)

    for group_name in res_group_names - ldap_group_names:
        try:
            accounts.delete_group({"group_name": group_name}, force=True)
        except Exception as e:
            logger.error(e)

    return groups_failed_to_sync


def _sync_users(
    active_directory_client: ActiveDirectoryClient,
    ldap_groups: List[Dict[str, Any]],
    groups_failed_to_sync: Set[str],
) -> None:
    """
    Sync LDAP users to RES. Avoid throwing exception during the AD sync process
    to make sure that all the users can be synced.
    :param active_directory_client: ActiveDirectoryClient
    :param ldap_groups: List of LDAP groups to sync users from.
    :param groups_failed_to_sync: List of groups failed to sync to RES.
    """
    logger.info("Syncing LDAP users to RES")

    users_filter = active_directory_client.options.users_filter
    ldap_user_mappings = _get_ldap_user_mappings(
        active_directory_client, ldap_groups, users_filter
    )
    ldap_usernames = set(ldap_user_mappings.keys())

    # Only retrieve AD users
    res_users = [
        u
        for u in accounts.list_users()
        if u["identity_source"] == constants.SSO_USER_IDP_TYPE
    ]
    res_user_mappings = {user["username"]: user for user in res_users}
    res_usernames = set(res_user_mappings.keys())

    added_users = ldap_usernames - res_usernames
    for username in added_users:
        try:
            user = ldap_user_mappings[username]
            accounts.create_user(
                user={
                    "username": user.get("sam_account_name", ""),
                    "email": user["email"],
                    "uid": user["uid"],
                    "gid": user["gid"],
                    "login_shell": user["login_shell"],
                    "home_dir": user["home_dir"],
                    "additional_groups": user.get("additional_groups", []),
                    "sudo": False,
                    "is_active": False,
                    "role": constants.USER_ROLE,
                    "identity_source": constants.SSO_USER_IDP_TYPE,
                },
                overwrite=True,
            )
        except Exception as e:
            logger.error(e)

    cluster_admin = constants.CLUSTER_ADMIN_USERNAME
    removed_users = res_usernames - ldap_usernames - {cluster_admin}
    for username in removed_users:
        try:
            accounts.delete_user({"username": username})
        except Exception as e:
            logger.error(e)

    all_users = ldap_usernames & res_usernames - {cluster_admin}
    for username in all_users:
        try:
            ldap_user = ldap_user_mappings[username]
            ldap_user_additional_groups = (
                set(ldap_user.get("additional_groups", [])) - groups_failed_to_sync
            )

            res_user = res_user_mappings[username]
            res_user_additional_groups = set(res_user["additional_groups"] or [])

            groups_to_add_to = list(
                ldap_user_additional_groups - res_user_additional_groups
            )
            if groups_to_add_to:
                accounts.add_user_to_groups_by_names(res_user, groups_to_add_to)
            groups_to_remove_from = list(
                res_user_additional_groups - ldap_user_additional_groups
            )
            if groups_to_remove_from:
                accounts.remove_user_from_groups_by_names(
                    res_user,
                    groups_to_remove_from,
                    active_directory_client.options.sudoers_group_name,
                )
        except Exception as e:
            logger.error(e)


def _get_ldap_user_mappings(
    active_directory_client: ActiveDirectoryClient,
    ldap_groups: List[Dict[str, Any]],
    users_filter: Optional[str] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Retrieve the username to user mappings.
    :param active_directory_client: ActiveDirectoryClient
    :param ldap_groups: List of LDAP groups to query for users.
    :param users_filter: Filter to apply when querying users.
    :return: Username to user mappings.
    """
    ldap_user_mappings: Dict[str, Dict[str, Any]] = dict()
    ldap_users_in_ou = _search_users(
        active_directory_client=active_directory_client, users_filter=users_filter
    )
    _consolidate_ldap_user_mappings(
        ldap_users=ldap_users_in_ou,
        ldap_user_mappings=ldap_user_mappings,
    )

    for ldap_group in ldap_groups:
        logger.info(f'Fetching LDAP users from group {ldap_group["name"]}')
        ldap_users_in_group = _fetch_ldap_users_in_group(
            active_directory_client=active_directory_client,
            ldap_group_name=ldap_group["name"],
            users_filter=users_filter,
        )
        _consolidate_ldap_user_mappings(
            ldap_users=ldap_users_in_group,
            ldap_user_mappings=ldap_user_mappings,
            ldap_group_name=ldap_group["name"],
        )

    return ldap_user_mappings


def _search_users(
    active_directory_client: ActiveDirectoryClient,
    ldap_base: Optional[str] = None,
    users_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Search LDAP users using a filter.
    :param active_directory_client: ActiveDirectoryClient
    :param ldap_base: LDAP base
    :param users_filter: LDAP users filter
    :return: List of LDAP users
    """
    logger.info("Fetching LDAP users")

    result = []

    if users_filter:
        _validate_ldap_filter(users_filter)
        filterstr = f"(&{DEFAULT_LDAP_USER_FILTERSTR}{users_filter})"
    else:
        filterstr = DEFAULT_LDAP_USER_FILTERSTR

    if not ldap_base:
        ldap_base = active_directory_client.options.users_ou

    search_result = active_directory_client.simple_paginated_search(
        base=ldap_base, filterstr=filterstr
    )

    ldap_result = search_result.get("result", [])

    for ldap_user in ldap_result:
        # Each result tuple is of the form (dn, attrs),
        # where dn is a string containing the DN (distinguished name) of the entry,
        # and attrs is a dictionary containing the attributes associated with the entry.
        user = _convert_ldap_user(ldap_user[1])
        if not user:
            continue
        result.append(user)

    return result


def _convert_ldap_user(ldap_user: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Convert a LDAP user into a RES dictionary.
    :param ldap_user: LDAP user
    """
    if not ldap_user:
        return None

    username = ldap_utils.ldap_str(ldap_user.get("uid"))
    if not username:
        username = ldap_utils.ldap_str(ldap_user.get("sAMAccountName"))

    result = {
        "cn": ldap_utils.ldap_str(ldap_user.get("cn")),
        "username": username,
        "sam_account_name": ldap_utils.ldap_str(ldap_user.get("sAMAccountName")),
        "email": ldap_utils.ldap_str(ldap_user.get("mail")),
        "uid": ldap_utils.ldap_str(ldap_user.get("uidNumber")),
        "gid": ldap_utils.ldap_str(ldap_user.get("gidNumber")),
        "login_shell": ldap_utils.ldap_str(ldap_user.get("loginShell")),
        "home_dir": ldap_utils.ldap_str(ldap_user.get("homeDirectory")),
    }

    return result


def _consolidate_ldap_user_mappings(
    ldap_users: List[Dict[str, Any]],
    ldap_user_mappings: Dict[str, Dict[str, Any]],
    ldap_group_name: Optional[str] = None,
) -> None:
    """
    Validate the user attribute and create the username to user mappings
    :param ldap_users: List of LDAP users.
    :param ldap_user_mappings: Username to user mappings.
    :param ldap_group_name: additional groups fo the users.
    """
    for ldap_user in filter(lambda user: "sam_account_name" in user, ldap_users):
        sam_account_name = str(ldap_user["sam_account_name"]).lower()
        if sam_account_name not in ldap_user_mappings:
            ldap_user_mappings[sam_account_name] = ldap_user

        if ldap_group_name:
            user = ldap_user_mappings[sam_account_name]
            user["additional_groups"] = list(
                set(user.get("additional_groups", []) + [ldap_group_name])
            )


def _fetch_ldap_users_in_group(
    active_directory_client: ActiveDirectoryClient,
    ldap_group_name: str,
    users_filter: Optional[str],
) -> List[Dict[str, Any]]:
    """
    Retrieve users from an LDAP group.
    :param active_directory_client: ActiveDirectoryClient
    :param ldap_group_name: LDAP group name.
    :param users_filter: Filter to apply when querying users.
    :return: List of users in the LDAP group.
    """
    filterstr = (
        f"(memberOf=cn={ldap_group_name},{active_directory_client.options.groups_ou})"
    )
    if users_filter:
        filterstr = f"(&{filterstr}{users_filter})"

    ldap_users: List[Dict[str, Any]] = _search_users(
        active_directory_client=active_directory_client,
        ldap_base=active_directory_client.options.ldap_base,
        users_filter=filterstr,
    )
    return ldap_users


def _validate_ldap_filter(ldap_filter: Optional[str]) -> None:
    """
    Validate LDAP filter.
    :param ldap_filter: LDAP filter.
    """
    if ldap_filter and not (ldap_filter.startswith("(") and ldap_filter.endswith(")")):
        raise Exception(
            'Invalid LDAP filter: Filter string must start with "(" and end with ")".'
            " Check https://ldap.com/ldap-filters/ for the LDAP filter syntax."
        )


def _start_sssd(active_directory_client: ActiveDirectoryClient) -> None:
    """
    :param active_directory_client: ActiveDirectoryClient
    Write the sssd config file and start the service
    """
    sssd_settings = {
        "domain_name": active_directory_client.options.domain_name,
        "ldap_connection_uri": active_directory_client.options.uri,
        "ldap_base": active_directory_client.options.ldap_base,
        "sssd_ldap_id_mapping": active_directory_client.options.sssd_ldap_id_mapping,
        "service_account_dn": aws_utils.get_secret_string(
            active_directory_client.options.service_account_dn_secret_arn
        ),
        "service_account_credentials": aws_utils.get_secret_string(
            active_directory_client.options.service_account_credentials_secret_arn
        ),
    }
    if active_directory_client.options.tls_certificate_secret_arn:
        sssd_settings["tls_certificate"] = aws_utils.get_secret_string(
            active_directory_client.options.tls_certificate_secret_arn
        )

    sssd_utils.start_sssd(sssd_settings, logger)


def main() -> None:
    """
    start AD sync
    """
    active_directory_client = ActiveDirectoryClient(logger)

    logger.info("Starting SSSD service")
    _start_sssd(active_directory_client)

    logger.info("Starting sync from AD")
    start_time = time.time()

    ldap_groups = _fetch_ldap_groups(active_directory_client)
    groups_failed_to_sync = _sync_groups(active_directory_client, ldap_groups)
    _sync_users(active_directory_client, ldap_groups, groups_failed_to_sync)

    logger.info(f"-------------TIME: {time.time() - start_time}------------")


if __name__ == "__main__":
    main()
