#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
import os
import time
from datetime import datetime
from typing import Any, Dict, Optional, TypedDict

import boto3


class CognitoGroup(TypedDict):
    group_name: str
    description: str
    created_time: datetime
    updated_time: datetime


class CognitoUser(TypedDict):
    username: str
    email: str
    created_on: datetime
    enabled: bool
    updated_on: datetime
    uid: Optional[
        int
    ]  # `uid` is optional because newly added users don't have a `uid` until they login into RES for the first time


def handle_cognito_sync(event: Dict[str, Any], _: Any) -> Any:
    groups = get_all_cognito_groups()
    update_group(groups)

    group_name_to_usernames = get_group_member_association_from_cognito(groups)
    update_group_member_association_in_ddb(group_name_to_usernames)

    native_users = get_all_native_cognito_users()
    update_users_in_ddb(native_users, group_name_to_usernames)

    disable_cognito_user_AD_dups(native_users)

    return {"message": "Cognito sync passed"}


def disable_cognito_user_AD_dups(cognito_users: list[CognitoUser]) -> None:
    cognito_client = boto3.client("cognito-idp")
    cognito_user_names = [user["username"] for user in cognito_users]

    # Get users from DDB
    table_name = f"{os.environ['CLUSTER_NAME']}.accounts.users"
    dynamodb_client = boto3.client("dynamodb")
    paginator = dynamodb_client.get_paginator("scan")

    for page in paginator.paginate(TableName=table_name):
        for item in page["Items"]:
            if (
                item.get("identity_source")
                and item["identity_source"]["S"] == os.environ["SSO_USER_IDP_TYPE"]
                and item["username"]["S"] in cognito_user_names
            ):
                # Disable Cognito users that are duplicate users in AD
                try:
                    print(f"Disabling Cognito native user: {item['username']['S']}")
                    cognito_client.admin_disable_user(
                        UserPoolId=os.environ["COGNITO_USER_POOL_ID"],
                        Username=item["username"]["S"],
                    )
                except Exception as e:
                    print(f"Error disabling user: {str(e)}")


def update_group_member_association_in_ddb(
    cognito_group_to_usernames: dict[str, list[str]]
) -> None:
    # Get users from DDB
    dynamodb_client = boto3.client("dynamodb")
    paginator = dynamodb_client.get_paginator("scan")
    group_to_user_in_ddb = []
    ddb_items_to_delete = []
    table_name = f"{os.environ['CLUSTER_NAME']}.accounts.group-members"
    # If DDB entry exist but that mapping is not in Cognito, add that entry to the list of items to delete
    for page in paginator.paginate(TableName=table_name):
        for item in page["Items"]:
            if item.get("identity_source") == {
                "S": os.environ["COGNITO_USER_IDP_TYPE"]
            }:
                group_name = item["group_name"]["S"]
                username = item["username"]["S"]
                ddb_item = {"group_name": group_name, "username": username}
                group_to_user_in_ddb.append(ddb_item)
                if (
                    group_name not in cognito_group_to_usernames.keys()
                    or username not in cognito_group_to_usernames[group_name]
                ):
                    ddb_items_to_delete.append(ddb_item)

    ddb_items_to_add = []
    for group_name in cognito_group_to_usernames:
        for username in cognito_group_to_usernames[group_name]:
            # If no exact match, then mapping is not in DDB so add it to DDB
            if not any(
                x["group_name"] == group_name and x["username"] == username
                for x in group_to_user_in_ddb
            ):
                ddb_items_to_add.append(
                    {
                        "group_name": group_name,
                        "username": username,
                        "identity_source": os.environ["COGNITO_USER_IDP_TYPE"],
                    }
                )

    dynamodb_resource = boto3.resource("dynamodb")
    table = dynamodb_resource.Table(table_name)
    with table.batch_writer() as batch:
        for item in ddb_items_to_add:
            batch.put_item(Item=item)
            print(f"Adding group mapping {item}")
        for item in ddb_items_to_delete:
            print(f"Deleting group mapping {item}")
            batch.delete_item(
                Key={"group_name": item["group_name"], "username": item["username"]}
            )


def get_group_member_association_from_cognito(
    cognito_groups: list[CognitoGroup],
) -> dict[str, list[str]]:
    cognito_group_names = [group["group_name"] for group in cognito_groups]
    cognito_client = boto3.client("cognito-idp")
    paginator = cognito_client.get_paginator("list_users_in_group")
    group_name_to_users: dict[str, list[str]] = {}
    for group_name in cognito_group_names:
        group_name_to_users[group_name] = []
        for page in paginator.paginate(
            UserPoolId=os.environ["COGNITO_USER_POOL_ID"], GroupName=group_name
        ):
            users = [user["Username"] for user in page["Users"]]
            group_name_to_users[group_name] = group_name_to_users[group_name] + users

    return group_name_to_users


def update_group(cognito_groups: list[CognitoGroup]) -> None:
    table_name = f"{os.environ['CLUSTER_NAME']}.accounts.groups"

    cognito_group_names = [group["group_name"] for group in cognito_groups]

    dynamodb_client = boto3.client("dynamodb")
    paginator = dynamodb_client.get_paginator("scan")
    ddb_items_to_delete = []
    for page in paginator.paginate(TableName=table_name):
        for item in page["Items"]:
            if item["identity_source"]["S"] == os.environ["COGNITO_USER_IDP_TYPE"]:
                ddb_group_name = item["group_name"]["S"]
                if ddb_group_name not in cognito_group_names:
                    # groups that are in DDB but not in Cognito should be deleted
                    ddb_items_to_delete.append(ddb_group_name)

    ddb_items_to_write = []
    for group in cognito_groups:
        group_name = group["group_name"]

        ddb_items_to_write.append(
            {
                "group_name": group_name,
                "created_on": round(
                    group["created_time"].timestamp() * 1000
                ),  # multiply 1000 to get value in microseconds
                "ds_name": group_name,
                "enabled": True,
                "gid": get_gid(group_name),
                "group_type": os.environ["GROUP_TYPE_PROJECT"],
                "role": (
                    os.environ["ADMIN_ROLE"]
                    if group["group_name"] == os.environ["COGNITO_SUDOER_GROUP_NAME"]
                    else os.environ["USER_ROLE"]
                ),  # Can be `user` or `admin` depending on whether group_name equals `COGNITO_SUDOER_GROUP_NAME`
                "title": group_name,
                "updated_on": round(group["updated_time"].timestamp() * 1000),
                "identity_source": os.environ["COGNITO_USER_IDP_TYPE"],
            }
        )

    dynamodb_resource = boto3.resource("dynamodb")
    table = dynamodb_resource.Table(table_name)
    with table.batch_writer() as batch:
        for item in ddb_items_to_write:
            print(f"Adding group {item}")
            batch.put_item(Item=item)
        for item in ddb_items_to_delete:
            print(f"Deleting group {item}")
            batch.delete_item(Key={"group_name": item})


def get_gid(group_name: str) -> int:
    # Convert group_name to a number. Group name max length is 6 letters and must consist of letters from a to z
    if len(group_name) > 6:
        raise Exception("Group name must be 6 letters or less")
    if not group_name.isalpha() or not group_name.islower():
        raise Exception("Group name must consist of lowercase alphabetic letters")
    shift_range = int(os.environ["COGNITO_MIN_ID_INCLUSIVE"])
    encoded_num = 0
    letter_position = 0
    # High level overview of algo: Converting base 27 number to base 10 number and adding shift_range to move the number into the desired GID range. `a` is mapped to 1 and `z` is mapped to 26. `a` cannot be mapped to 0 because then `aa` would map to 0
    # For example if shift_range is 10, then `a` would map to 11 and `zzzzzz`, which is the largest value would map to 321272416
    for char in group_name[::-1]:
        encoded_num += (ord(char) - ord("a") + 1) * pow(27, letter_position)
        letter_position += 1
    # Subtract by 1 since smallest value for encoded_num is 1, and `shift_range` is the minimum valid id
    return encoded_num + (shift_range - 1)


def get_all_cognito_groups() -> list[CognitoGroup]:
    cognito_client = boto3.client("cognito-idp")
    paginator = cognito_client.get_paginator("list_groups")
    user_pool_id = os.environ["COGNITO_USER_POOL_ID"]
    groups: list[CognitoGroup] = []
    for page in paginator.paginate(UserPoolId=user_pool_id):
        for group in page["Groups"]:
            description = group.get("Description", "")
            # Don't get autogenerated group for AD users
            if "Autogenerated group" in description:
                continue
            cognito_group: CognitoGroup = {
                "group_name": group["GroupName"],
                "description": group.get("Description", ""),
                "created_time": group["CreationDate"],
                "updated_time": group["LastModifiedDate"],
            }
            groups.append(cognito_group)
    return groups


def get_all_native_cognito_users() -> list[CognitoUser]:
    cognito_client = boto3.client("cognito-idp")
    paginator = cognito_client.get_paginator("list_users")
    user_pool_id = os.environ["COGNITO_USER_POOL_ID"]
    users: list[CognitoUser] = []
    for page in paginator.paginate(UserPoolId=user_pool_id):
        for user in page["Users"]:
            user_status = user.get("UserStatus", "")
            # Don't get autogenerated group for AD users
            uid_attribute = next(
                (
                    attr
                    for attr in user["Attributes"]
                    if attr["Name"] == os.environ["CUSTOM_UID_ATTRIBUTE"]
                ),
                None,
            )
            uid = None
            if uid_attribute:
                uid = int(uid_attribute["Value"])

            # Skip users who have the status of "EXTERNAL_PROVIDER" because they are AD users
            if "EXTERNAL_PROVIDER" in user_status:
                continue

            email_attribute = next(
                (attr for attr in user["Attributes"] if attr["Name"] == "email"),
                None,
            )
            email = ""
            if email_attribute:
                email = email_attribute["Value"]

            cognito_user: CognitoUser = {
                "username": user["Username"],
                "email": email,
                "created_on": user["UserCreateDate"],
                "enabled": user["Enabled"],
                "updated_on": user["UserLastModifiedDate"],
                "uid": uid,
            }
            users.append(cognito_user)
    return users


def update_users_in_ddb(
    cognito_users: list[CognitoUser], group_name_to_usernames: dict[str, list[str]]
) -> None:
    print(f"cognito_users {cognito_users}")
    table_name = f"{os.environ['CLUSTER_NAME']}.accounts.users"

    dynamodb_client = boto3.client("dynamodb")
    paginator = dynamodb_client.get_paginator("scan")
    ddb_items_to_delete: list[str] = []
    ddb_items_to_skip: list[str] = []
    ddb_admins: list[str] = []
    cognito_users_username = [user["username"] for user in cognito_users]
    print(f"cognito_users_username {cognito_users_username}")

    for page in paginator.paginate(TableName=table_name):
        for item in page["Items"]:
            # Skip Cognito users that are duplicates of SSO users
            if (
                item.get("identity_source")
                and item["identity_source"]["S"] == os.environ["SSO_USER_IDP_TYPE"]
            ):
                ddb_items_to_skip.append(item["username"]["S"])
            # If DDB entry exist but the user is not in Cognito add that entry to the list of items to delete
            if (
                item.get("identity_source")
                and item["identity_source"]["S"] == os.environ["COGNITO_USER_IDP_TYPE"]
                and not item["username"]["S"] in cognito_users_username
            ):
                ddb_items_to_delete.append(item["username"]["S"])
            # If user is already admin we want to preserve the role
            # This can happen if a user is made admin in RES console
            elif item.get("role") and item["role"]["S"] == os.environ["ADMIN_ROLE"]:
                ddb_admins.append(item["username"]["S"])

    username_to_group_names: dict[str, list[str]] = {}
    for group_name in group_name_to_usernames:
        for user in group_name_to_usernames[group_name]:
            if group_name_to_usernames.get(user):
                username_to_group_names[user] = username_to_group_names[user] + [
                    group_name
                ]
            else:
                username_to_group_names[user] = [group_name]

    ddb_items_to_add = []
    # Need to add all users, because user attribute might be updated
    for cognito_user in cognito_users:
        if cognito_user["username"] in ddb_items_to_skip:
            print(f"skipping SSO user {cognito_user['username']}")
            continue
        # Check if any of the user's group is in COGNITO_SUDOER_GROUP_NAME
        sudo = os.environ["COGNITO_SUDOER_GROUP_NAME"] in username_to_group_names.get(
            cognito_user["username"], []
        )
        # Check if user is already admin in DDB
        if cognito_user["username"] in ddb_admins:
            sudo = True
        additional_groups = username_to_group_names.get(cognito_user["username"], [])
        ddb_item = {
            "username": cognito_user["username"],
            "additional_groups": additional_groups,
            "created_on": round(cognito_user["created_on"].timestamp() * 1000),
            "email": cognito_user["email"],
            "enabled": cognito_user["enabled"],
            "gid": (
                get_gid(os.environ["COGNITO_DEFAULT_USER_GROUP"])
                if not additional_groups
                else get_gid(additional_groups[0])
            ),
            "home_dir": f"/home/{cognito_user['username']}",
            "identity_source": os.environ["COGNITO_USER_IDP_TYPE"],
            "is_active": cognito_user["enabled"],
            "login_shell": "/bin/bash",
            "role": (
                os.environ["ADMIN_ROLE"]
                if sudo or cognito_user["username"] == os.environ["CLUSTER_ADMIN_NAME"]
                else os.environ["USER_ROLE"]
            ),
            "sudo": sudo,
            "synced_on": round(time.time() * 1000),
            "updated_on": round(cognito_user["updated_on"].timestamp() * 1000),
        }
        if cognito_user.get("uid", None):
            ddb_item["uid"] = cognito_user["uid"]
        ddb_items_to_add.append(ddb_item)

    dynamodb_resource = boto3.resource("dynamodb")
    table = dynamodb_resource.Table(table_name)
    with table.batch_writer() as batch:
        for item in ddb_items_to_add:
            print(f"Adding user {item}")
            batch.put_item(Item=item)
        for username in ddb_items_to_delete:
            print(f"Deleting user {username}")
            batch.delete_item(Key={"username": username})
