#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

"""
Test Cases for AccountsService
"""

from typing import Optional

import pytest
from ideaclustermanager import AppContext
from ideaclustermanager.app.accounts.account_tasks import (
    CreateUserHomeDirectoryTask,
    SyncGroupInDirectoryServiceTask,
    SyncUserInDirectoryServiceTask,
)
from ideaclustermanager.app.accounts.auth_utils import AuthUtils
from ideaclustermanager.app.accounts.user_home_directory import UserHomeDirectory
from ideasdk.utils import Utils
from ideatestutils import IdeaTestProps

from ideadatamodel import (
    Group,
    ListUsersRequest,
    User,
    constants,
    errorcodes,
    exceptions,
)
from ideadatamodel.auth import (
    AuthResult,
    InitiateAuthRequest,
    InitiateAuthResult,
    RespondToAuthChallengeRequest,
    RespondToAuthChallengeResult,
)

test_props = IdeaTestProps()


class AccountsTestContext:
    crud_user: Optional[User]


def test_accounts_create_user_missing_username_should_fail(context: AppContext):
    """
    create user with missing username
    """
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.create_user(user=User(username=""))
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert "username is required" in exc_info.value.message


def test_accounts_create_user_invalid_username_should_fail(context: AppContext):
    """
    create user with invalid username
    """
    create_user_invalid_username(context, r"Invalid Username")
    create_user_invalid_username(context, r"-InvalidUsername")
    # Username with dollar sign at the end will be treated as service account by system.
    # https://learn.microsoft.com/en-us/troubleshoot/windows-server/active-directory/compatibility-user-accounts-end-dollar-sign
    create_user_invalid_username(context, r"InvalidUsername$")
    # Special unicode characters are not allowed due to security concerns (similar to SQL injection or JS injection)
    create_user_invalid_username(context, r"\u2460\u2461\u2462\u2463")


def create_user_invalid_username(context: AppContext, username: str):
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.create_user(user=User(username=username))
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert constants.USERNAME_ERROR_MESSAGE in exc_info.value.message


def test_accounts_create_user_who_does_not_exist_in_AD_should_fail(context: AppContext):
    """
    create user who does not exist in AD
    """
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.create_user(
            user=User(
                username=test_props.get_non_existent_username(),
            )
        )
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert (
        "User nonexistent does not exist in AD, please add user in AD and retry"
        in exc_info.value.message
    )


def test_accounts_create_user_system_account_username_should_fail(context: AppContext):
    """
    create user with username as system accounts
    """
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.create_user(user=User(username="root"))
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert "invalid username:" in exc_info.value.message


def test_accounts_create_user_missing_email_should_fail(context: AppContext):
    """
    create user with missing email
    """
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.create_user(user=User(username="mockuser1"))
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert "email is required" in exc_info.value.message


def test_accounts_create_user_invalid_email_should_fail(context: AppContext):
    """
    create user with invalid email
    """
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.create_user(
            user=User(username="mockuser1", email="invalid-email")
        )
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert "invalid email:" in exc_info.value.message


def test_accounts_create_user_with_verified_email_missing_uid_should_fail(
    context: AppContext,
):
    """
    create valid account with email verified and no uid
    """
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.create_user(
            user=User(username="mockuser1", email="mockuser1@example.com"),
            email_verified=True,
        )
    assert exc_info.value.error_code == errorcodes.UID_AND_GID_NOT_FOUND
    assert (
        "Unable to retrieve UID and GID for User: mockuser1" in exc_info.value.message
    )


def test_accounts_create_user_with_verified_email_missing_gid_should_fail(
    context: AppContext,
):
    """
    Create valid account with email verified and no gid
    """

    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.create_user(
            user=User(username="mockuser1", email="mockuser1@example.com", uid=1234),
            email_verified=True,
        )
    assert exc_info.value.error_code == errorcodes.UID_AND_GID_NOT_FOUND
    assert (
        "Unable to retrieve UID and GID for User: mockuser1" in exc_info.value.message
    )


def test_accounts_crud_create_user(context: AppContext, monkeypatch):
    """
    create user
    """
    monkeypatch.setattr(
        context.accounts.sssd, "get_uid_and_gid_for_user", lambda x: (1000, 1000)
    )

    created_user = context.accounts.create_user(
        user=User(
            username="accounts_user1",
            email="accounts_user1@example.com",
            password="MockPassword_123!%",
            uid=1000,
            gid=1000,
            login_shell="/bin/bash",
            home_dir="home/account_user1",
            additional_groups=[],
        ),
        email_verified=True,
    )

    assert created_user.username is not None
    assert created_user.email is not None

    user = context.accounts.get_user(username=created_user.username)

    assert user is not None
    assert user.username is not None
    assert user.email is not None
    assert user.additional_groups is None
    assert user.enabled is not None
    assert user.enabled is True
    assert user.uid is not None and user.uid == created_user.uid
    assert user.gid is not None and user.uid == created_user.gid
    assert user.sudo is not None or user.sudo is False
    assert user.home_dir is not None and user.home_dir == created_user.home_dir
    assert user.login_shell is not None and user.login_shell == created_user.login_shell
    assert user.password is None
    assert user.created_on is not None
    assert user.updated_on is not None

    AccountsTestContext.crud_user = user


def test_accounts_crud_create_user_ad_uid_and_gid(context: AppContext, monkeypatch):
    """
    create user with AD provided uid and gid
    """
    monkeypatch.setattr(context.accounts.sssd, "ldap_id_mapping", lambda x: "False")
    monkeypatch.setattr(
        context.accounts.sssd, "get_uid_and_gid_for_user", lambda x: (100, 100)
    )
    created_user = context.accounts.create_user(
        user=User(
            username="accounts_user2",
            email="accounts_user2@example.com",
            password="MockPassword_123!%",
            uid=100,
            gid=100,
            login_shell="/bin/bash",
            home_dir="home/account_user2",
            additional_groups=[],
        ),
        email_verified=True,
    )

    assert created_user.username is not None
    assert created_user.email is not None

    user = context.accounts.get_user(username=created_user.username)

    assert user.uid == 100
    assert user.gid == 100


def test_accounts_crud_create_user_with_capital_letters_hyphen_and_period_in_sam_account_name(
    context: AppContext, monkeypatch
):
    """
    create user
    """
    monkeypatch.setattr(
        context.accounts.sssd, "get_uid_and_gid_for_user", lambda x: (1000, 1000)
    )

    created_user = context.accounts.create_user(
        user=User(
            username="accounts_USER3.-",
            email="accounts_user3@example.com",
            password="MockPassword_123!%",
            uid=1000,
            gid=1000,
            login_shell="/bin/bash",
            home_dir="home/account_user3.-",
            additional_groups=[],
        ),
        email_verified=True,
    )

    assert created_user.username is not None
    assert created_user.email is not None

    user = context.accounts.get_user(username=created_user.username)

    assert user is not None
    assert user.username is not None
    assert user.email is not None
    assert user.home_dir is not None and user.home_dir == created_user.home_dir


def test_accounts_crud_get_user(context: AppContext):
    """
    get user
    """
    assert AccountsTestContext.crud_user is not None
    crud_user = AccountsTestContext.crud_user

    user = context.accounts.get_user(username=crud_user.username)

    assert user is not None
    assert user.username == crud_user.username
    assert user.uid == crud_user.uid
    assert user.gid == crud_user.gid


def test_accounts_crud_get_user_by_email(context: AppContext):
    """
    get user by email
    """
    assert AccountsTestContext.crud_user is not None
    crud_user = AccountsTestContext.crud_user

    user = context.accounts.get_user_by_email(email=crud_user.email)

    assert user is not None
    assert user.username == crud_user.username
    assert user.email == crud_user.email


def test_accounts_crud_get_user_by_email(context: AppContext):
    """
    get user by email
    """
    assert AccountsTestContext.crud_user is not None
    crud_user = AccountsTestContext.crud_user

    user = context.accounts.get_user_by_email(email=crud_user.email)

    assert user is not None
    assert user.username == crud_user.username
    assert user.email == crud_user.email


def test_accounts_crud_modify_user(context: AppContext):
    """
    modify user
    """
    assert AccountsTestContext.crud_user is not None
    crud_user = AccountsTestContext.crud_user

    modify_user = User(
        username=crud_user.username,
        email="accounts_user1_modified@example.com",
        uid=6000,
        gid=6000,
        login_shell="/bin/csh",
    )
    context.accounts.modify_user(user=modify_user, email_verified=True)

    user = context.accounts.get_user(username=crud_user.username)
    assert user.username == modify_user.username
    assert user.email == modify_user.email
    assert user.uid == modify_user.uid
    assert user.gid == modify_user.gid
    assert user.login_shell == modify_user.login_shell


def test_accounts_crud_disable_user(context: AppContext):
    """
    disable user
    """
    assert AccountsTestContext.crud_user is not None
    crud_user = AccountsTestContext.crud_user

    context.accounts.disable_user(crud_user.username)
    user = context.accounts.get_user(username=crud_user.username)
    assert user.enabled is False


def test_accounts_crud_enable_user(context: AppContext):
    """
    enable user
    """
    assert AccountsTestContext.crud_user is not None
    crud_user = AccountsTestContext.crud_user

    context.accounts.enable_user(crud_user.username)
    user = context.accounts.get_user(username=crud_user.username)
    assert user.enabled is True


def test_accounts_crud_list_users(context: AppContext):
    """
    list users
    """
    assert AccountsTestContext.crud_user is not None
    crud_user = AccountsTestContext.crud_user

    result = context.accounts.list_users(ListUsersRequest())
    assert result.listing is not None

    found = None
    for user in result.listing:
        if user.username == crud_user.username:
            found = user
            break
    assert found is not None


def test_accounts_create_user_home_directory(context: AppContext, monkeypatch):
    """
    user home directory
    """
    crud_user = AccountsTestContext.crud_user
    username = crud_user.username
    monkeypatch.setattr(context.accounts, "get_user", lambda x: crud_user)
    task = CreateUserHomeDirectoryTask(context=context)
    monkeypatch.setattr(UserHomeDirectory, "initialize", lambda x: True)
    try:
        task.invoke(
            payload={
                "username": username,
            }
        )
    except Exception as e:
        print("failed in create home directory task: {e}")


def test_sync_user_in_directory_service_task(context, monkeypatch):
    """
    sync users in directory service, read_only
    """
    monkeypatch.setattr(context.ldap_client, "is_readonly", lambda: True)
    crud_user = AccountsTestContext.crud_user
    username = crud_user.username
    payload = {"username": username, "enabled": "true"}
    monkeypatch.setattr(context.accounts.user_dao, "get_user", lambda x: payload)
    monkeypatch.setattr(Utils, "get_value_as_bool", lambda x, y, z: False)
    task = SyncUserInDirectoryServiceTask(context=context)
    try:
        task.invoke(payload=payload)
    except Exception as e:
        print("failed in sync user directory service task: {e}")


def test_sync_group_in_directory_service_task(context, monkeypatch):
    """
    sync groups in directory service, read_only
    """
    monkeypatch.setattr(context.ldap_client, "is_readonly", lambda: True)
    payload = {"group_name": "xyz", "enabled": "true"}
    monkeypatch.setattr(context.accounts.group_dao, "get_group", lambda x: payload)
    task = SyncGroupInDirectoryServiceTask(context=context)
    try:
        task.invoke(payload=payload)
    except Exception as e:
        print("failed in sync group directory service task: {e}")


def test_accounts_crud_delete_user(context: AppContext):
    """
    delete user
    """
    assert AccountsTestContext.crud_user is not None
    crud_user = AccountsTestContext.crud_user

    context.accounts.delete_user(username=crud_user.username)
    result = context.accounts.user_dao.get_user(crud_user.username)
    assert result is None


def test_accounts_create_internal_group(context: AppContext):
    """
    internal group
    """
    group = context.accounts.create_group(
        Group(
            title="Dummy Internal Group",
            name="dummy-internal-group",
            ds_name="dummy-internal-group",
            gid=None,
            group_type=constants.GROUP_TYPE_PROJECT,
            type=constants.GROUP_TYPE_INTERNAL,
        )
    )
    assert group is not None

    assert group.gid is None
    assert group.name == "dummy-internal-group"
    assert group.type == constants.GROUP_TYPE_INTERNAL


def test_accounts_create_internal_group_ad_gid(context: AppContext, monkeypatch):
    """
    internal group with AD provided gid
    """
    monkeypatch.setattr(context.accounts.sssd, "ldap_id_mapping", lambda: "False")
    group = context.accounts.create_group(
        Group(
            title="Dummy Internal Group2",
            name="dummy-internal-group-2",
            ds_name="dummy-internal-group-2",
            gid=100,
            group_type=constants.GROUP_TYPE_PROJECT,
            type=constants.GROUP_TYPE_INTERNAL,
        )
    )
    returned_group = context.accounts.get_group(group.name)

    assert returned_group is not None

    assert returned_group.gid == 100
    assert returned_group.name == "dummy-internal-group-2"
    assert returned_group.type == constants.GROUP_TYPE_INTERNAL


def test_accounts_create_group_with_no_type_param_must_attemp_an_external_group_creation(
    context: AppContext,
):
    """
    external group
    """
    group = context.accounts.create_group(
        Group(
            title="Dummy Group",
            name="dummy-group",
            ds_name="dummy-group",
            gid=None,
            group_type=constants.GROUP_TYPE_PROJECT,
        )
    )
    assert group is not None

    assert group.name == "dummy-group"
    assert group.type == constants.GROUP_TYPE_EXTERNAL


def test_accounts_create_group_with_invalid_type_should_fail(context: AppContext):
    """
    external group with invalid type
    """
    with pytest.raises(exceptions.SocaException) as exc_info:
        group = context.accounts.create_group(
            Group(
                title="Dummy Group",
                name="dummy-group",
                ds_name="dummy-group",
                gid=None,
                group_type=constants.GROUP_TYPE_PROJECT,
                type="abc",
            )
        )
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert (
        f"invalid group type: abc. must be one of: {[constants.GROUP_TYPE_EXTERNAL, constants.GROUP_TYPE_INTERNAL]}"
        in exc_info.value.message
    )


def test_accounts_create_group_with_invalid_name_or_type_should_fail(
    context: AppContext,
):
    """
    external group with invalid name or type
    """
    with pytest.raises(exceptions.SocaException) as exc_info:
        group = context.accounts.create_group(
            Group(
                title="Dummy Group",
                name=None,
                ds_name=None,
            )
        )
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert f"group.name is required" in exc_info.value.message

    with pytest.raises(exceptions.SocaException) as exc_info:
        group = context.accounts.create_group(
            Group(
                title="Dummy Group",
                name="xyz",
                ds_name="xyz",
                group_type=None,
                type=None,
            )
        )
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert f"group.group_type is required" in exc_info.value.message

    with pytest.raises(exceptions.SocaException) as exc_info:
        group = context.accounts.create_group(
            Group(
                title="Dummy Group",
                name="xyz",
                ds_name="xyz",
                group_type="xyz",
                type="xyz",
            )
        )
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS


def test_accounts_create_group_with_existing_group_name_should_fail(
    context: AppContext, monkeypatch
):
    """
    existing group
    """
    monkeypatch.setattr(context.accounts.group_dao, "get_group", lambda x: "xyz")
    with pytest.raises(exceptions.SocaException) as exc_info:
        group = context.accounts.create_group(
            Group(
                title="Dummy Group",
                name="xyz",
                ds_name="xyz",
                group_type="user",
                type="external",
            )
        )
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert f"group: xyz already exists" in exc_info.value.message


def test_accounts_create_group_without_ds_name_in_external_ad_should_fail(
    context: AppContext, monkeypatch
):
    """
    group without ds_name
    """
    monkeypatch.setattr(context.ldap_client, "is_readonly", lambda: True)
    with pytest.raises(exceptions.SocaException) as exc_info:
        group = context.accounts.create_group(
            Group(
                title="Dummy Group",
                name="pqr",
                ds_name=None,
                group_type="user",
                type="external",
            )
        )
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert (
        f"group.ds_name is required when using Read-Only Directory Service: activedirectory"
        in exc_info.value.message
    )


def test_accounts_create_group_in_ad_none_should_fail(context: AppContext, monkeypatch):
    """
    create group with no name
    """
    monkeypatch.setattr(context.ldap_client, "is_readonly", lambda: True)
    monkeypatch.setattr(context.ldap_client, "get_group", lambda x: None)
    with pytest.raises(exceptions.SocaException) as exc_info:
        group = context.accounts.create_group(
            Group(
                title="Dummy Group",
                name="pqr",
                ds_name="pqr",
                group_type="user",
                type="external",
            )
        )
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert (
        f"group with name pqr is not found in Read-Only Directory Service: activedirectory"
        in exc_info.value.message
    )


def test_accounts_create_group_in_ad_gid_none_should_fail_ad_gid(
    context: AppContext, monkeypatch
):
    """
    group with gid none
    """
    monkeypatch.setattr(context.ldap_client, "is_readonly", lambda: True)
    monkeypatch.setattr(context.accounts.sssd, "get_gid_for_group", lambda x: None)

    response = {"gid": None, "name": "pqr"}
    monkeypatch.setattr(context.ldap_client, "get_group", lambda x: response)
    monkeypatch.setattr(context.accounts.sssd, "ldap_id_mapping", lambda: "False")
    with pytest.raises(exceptions.SocaException) as exc_info:
        group = context.accounts.create_group(
            Group(
                title="Dummy Group",
                name="pqr",
                ds_name="pqr",
                group_type="user",
                type="external",
            )
        )
    assert exc_info.value.error_code == errorcodes.GID_NOT_FOUND
    assert f"Unable to retrieve GID for Group: pqr" in exc_info.value.message


def test_accounts_create_group_in_ad_with_valid_but_name_none_should_fail(
    context: AppContext, monkeypatch
):
    """
    with gid but name none
    """
    monkeypatch.setattr(context.ldap_client, "is_readonly", lambda: True)
    response = {"gid": 123, "name": None}
    monkeypatch.setattr(context.ldap_client, "get_group", lambda x: response)
    with pytest.raises(exceptions.SocaException) as exc_info:
        group = context.accounts.create_group(
            Group(
                title="Dummy Group",
                name="pqr",
                ds_name="pqr",
                group_type="user",
                type="external",
            )
        )
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert (
        f"Group name matching the provided name pqr is not found in Directory Service: activedirectory"
        in exc_info.value.message
    )


def test_accounts_create_group_but_name_in_ad_is_different_should_fail(
    context: AppContext, monkeypatch
):
    """
    group name and ds_name mismatch
    """
    monkeypatch.setattr(context.ldap_client, "is_readonly", lambda: True)
    response = {"gid": 123, "name": "pqrs"}
    monkeypatch.setattr(context.ldap_client, "get_group", lambda x: response)
    with pytest.raises(exceptions.SocaException) as exc_info:
        group = context.accounts.create_group(
            Group(
                title="Dummy Group",
                name="pqr",
                ds_name="pqr",
                group_type="user",
                type="external",
            )
        )
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert (
        f"group.ds_name pqr does not match the value pqrs read from Directory Service: activedirectory"
        in exc_info.value.message
    )


def test_accounts_get_group_with_empty_group_name_should_fail(
    context: AppContext, monkeypatch
):
    """
    get group with empty name
    """
    monkeypatch.setattr(Utils, "is_empty", lambda x: True)
    with pytest.raises(exceptions.SocaException) as exc_info:
        group = context.accounts.get_group(
            Group(
                title="Dummy Group",
                name="",
                ds_name="",
                group_type="user",
                type="external",
            )
        )
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert f"group_name is required" in exc_info.value.message


def test_accounts_get_group_with_group_none_should_fail(
    context: AppContext, monkeypatch
):
    """
    get group with name none
    """
    monkeypatch.setattr(context.accounts.group_dao, "get_group", lambda x: None)
    with pytest.raises(exceptions.SocaException) as exc_info:
        group = context.accounts.get_group(
            Group(
                title="Dummy Group",
                name="xyz",
                ds_name="xyz",
                group_type="user",
                type="external",
            )
        )
    assert exc_info.value.error_code == errorcodes.AUTH_GROUP_NOT_FOUND
    assert f"Group not found: title='Dummy Group'" in exc_info.value.message


def test_accounts_modify_group_with_empty_group_name_should_fail(
    context: AppContext, monkeypatch
):
    """
    modify group with empty name
    """
    monkeypatch.setattr(Utils, "is_empty", lambda x: True)
    with pytest.raises(exceptions.SocaException) as exc_info:
        group = context.accounts.modify_group(
            Group(
                title="Dummy Group",
                name="",
                ds_name="",
                group_type="user",
                type="external",
            )
        )
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert f"group_name is required" in exc_info.value.message


def test_accounts_modify_group_with_db_group_none_should_fail(
    context: AppContext, monkeypatch
):
    """
    modify group with none name
    """
    monkeypatch.setattr(context.accounts.group_dao, "get_group", lambda x: None)
    with pytest.raises(exceptions.SocaException) as exc_info:
        group = context.accounts.modify_group(
            Group(
                title="Dummy Group",
                name="xyz",
                ds_name="xyz",
                group_type="user",
                type="external",
            )
        )
    assert exc_info.value.error_code == errorcodes.AUTH_GROUP_NOT_FOUND
    assert f"group not found for group name: xyz" in exc_info.value.message


def test_accounts_modify_group_with_db_group_disabled_should_fail(
    context: AppContext, monkeypatch
):
    """
    modify a disabled group
    """
    response = {"enabled": None}
    monkeypatch.setattr(context.accounts.group_dao, "get_group", lambda x: response)
    with pytest.raises(exceptions.SocaException) as exc_info:
        group = context.accounts.modify_group(
            Group(
                title="Dummy Group",
                name="xyz",
                ds_name="xyz",
                group_type="user",
                type="external",
            )
        )
    assert exc_info.value.error_code == errorcodes.AUTH_GROUP_IS_DISABLED
    assert f"cannot modify a disabled group" in exc_info.value.message


def test_accounts_modify_group_should_succeed(context: AppContext, monkeypatch):
    """
    modify group
    """
    response = {"enabled": True, "group_name": "xyz", "title": "Dummy Group"}
    monkeypatch.setattr(context.accounts.group_dao, "get_group", lambda x: response)
    monkeypatch.setattr(context.accounts.group_dao, "update_group", lambda x: response)
    try:
        group = context.accounts.modify_group(
            Group(
                title="Dummy Group",
                name="xyz",
                ds_name="xyz",
                group_type="user",
                type="external",
            )
        )
    except Exception as e:
        print("failed in updating group: {e}")
    response = {"converted_group": "updated_from_group"}
    monkeypatch.setattr(
        context.accounts.group_dao, "convert_from_db", lambda x: response
    )
    try:
        group = context.accounts.modify_group(
            Group(
                title="Dummy Group",
                name="xyz",
                ds_name="xyz",
                group_type="user",
                type="external",
            )
        )
    except Exception as e:
        print("failed in convert from db group: {e}")


def test_accounts_delete_group_should_raise_exception_for_empty_group(
    context: AppContext, monkeypatch
):
    """
    delete empty group-name
    """
    monkeypatch.setattr(Utils, "is_empty", lambda x: True)
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.delete_group(
            Group(
                title="",
                name="",
                ds_name="",
                group_type="user",
                type="external",
            )
        )
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert "group_name is required" in exc_info.value.message


def test_accounts_delete_group_should_raise_exception_for_none_group(
    context: AppContext, monkeypatch
):
    """
    delete group with name none
    """
    monkeypatch.setattr(context.accounts.group_dao, "get_group", lambda x: None)
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.delete_group(
            group_name="xyz",
        )
    assert exc_info.value.error_code == errorcodes.AUTH_GROUP_NOT_FOUND
    assert "group: xyz not found." in exc_info.value.message


def test_accounts_delete_group_should_raise_exception_for_users_in_group(
    context: AppContext, monkeypatch
):
    """
    delete groups with users in
    """
    monkeypatch.setattr(context.accounts.group_dao, "get_group", lambda x: "xyz")
    monkeypatch.setattr(
        context.accounts.group_members_dao, "has_users_in_group", lambda x: True
    )
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.delete_group(
            group_name="xyz",
        )
    assert exc_info.value.error_code == errorcodes.AUTH_INVALID_OPERATION
    assert (
        "Users associated to group. Group must be empty before it can be deleted."
        in exc_info.value.message
    )


def test_accounts_enable_group_raise_exception_for_empty_group_name(
    context: AppContext, monkeypatch
):
    """
    Enable a group with name empty
    """
    monkeypatch.setattr(Utils, "is_empty", lambda x: True)
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.enable_group(
            group_name="",
        )
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert "group_name is required" in exc_info.value.message


def test_accounts_enable_group_raise_exception_for_none_group(
    context: AppContext, monkeypatch
):
    """
    Enable a group with name none
    """
    monkeypatch.setattr(context.accounts.group_dao, "get_group", lambda x: None)
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.enable_group(
            group_name="xyz",
        )
    assert exc_info.value.error_code == errorcodes.AUTH_GROUP_NOT_FOUND
    assert "group: xyz not found" in exc_info.value.message


def test_accounts_enable_group_update_for_valid_group(context: AppContext, monkeypatch):
    """
    Update a valid group
    """
    monkeypatch.setattr(context.accounts.group_dao, "get_group", lambda x: "xyz")
    try:
        context.accounts.enable_group(
            group_name="xyz",
        )
    except Exception as e:
        print("failed to update group: {e}")


def test_accounts_disable_group_raise_exception_for_empty_group_name(
    context: AppContext, monkeypatch
):
    """
    disable a group with empty name
    """
    monkeypatch.setattr(Utils, "is_empty", lambda x: True)
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.disable_group(
            group_name="",
        )
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert "group_name is required" in exc_info.value.message


def test_accounts_disable_group_raise_exception_for_none_group(
    context: AppContext, monkeypatch
):
    """
    disable a group with none name
    """
    monkeypatch.setattr(context.accounts.group_dao, "get_group", lambda x: None)
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.disable_group(
            group_name="xyz",
        )
    assert exc_info.value.error_code == errorcodes.AUTH_GROUP_NOT_FOUND
    assert "group: xyz not found" in exc_info.value.message


def test_accounts_disable_group_update_for_valid_group(
    context: AppContext, monkeypatch
):
    """
    disbale a vaild group
    """
    monkeypatch.setattr(context.accounts.group_dao, "get_group", lambda x: "xyz")
    try:
        context.accounts.disable_group(
            group_name="xyz",
        )
    except Exception as e:
        print("failed to update group: {e}")


def test_accounts_return_list_group_request(context: AppContext, monkeypatch):
    """
    list groups
    """
    monkeypatch.setattr(context.accounts.group_dao, "list_groups", lambda x: [])
    try:
        context.accounts.list_groups(
            request="xyz",
        )
    except Exception as e:
        print("failed to respond to list group: {e}")


def test_accounts_return_list_users_in_group_request(context: AppContext, monkeypatch):
    """
    list users in group
    """
    monkeypatch.setattr(
        context.accounts.group_members_dao, "list_users_in_group", lambda x: []
    )
    try:
        context.accounts.list_users_in_group(
            request="xyz",
        )
    except Exception as e:
        print("failed to respond to list users in group: {e}")


def test_accounts_add_user_to_group_raise_exception_for_empty_usernames_or_group_name(
    context: AppContext, monkeypatch
):
    """
    Add user in group with empty username
    """
    monkeypatch.setattr(Utils, "is_empty", lambda x: not (x))
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.add_users_to_group(
            usernames=[],
            group_name="xyz",
        )
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert "usernames is required" in exc_info.value.message

    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.add_users_to_group(
            usernames=["xyz"],
            group_name="",
        )
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert "group_name is required" in exc_info.value.message


def test_accounts_add_user_to_group_raise_exception_for_group_not_enabled(
    context: AppContext, monkeypatch
):
    """
    add users to a disabled group
    """
    response = {"enabled": False}
    monkeypatch.setattr(context.accounts.group_dao, "get_group", lambda x: response)
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.add_users_to_group(
            usernames=["xyz"],
            group_name="xyz",
        )
    assert exc_info.value.error_code == errorcodes.AUTH_GROUP_IS_DISABLED
    assert "cannot add users to a disabled user group" in exc_info.value.message


def test_accounts_add_user_to_group_raise_exception_for_user_is_none(
    context: AppContext, monkeypatch
):
    """
    add user to group with username none
    """
    monkeypatch.setattr(context.accounts.user_dao, "get_user", lambda x: None)
    response = {"enabled": True}
    monkeypatch.setattr(context.accounts.group_dao, "get_group", lambda x: response)
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.add_users_to_group(
            usernames=["x4"],
            group_name="xyz",
        )
    assert exc_info.value.error_code == errorcodes.AUTH_USER_NOT_FOUND
    assert "user not found: x4" in exc_info.value.message


def test_accounts_add_user_to_group_raise_exception_for_user_is_disabled(
    context: AppContext, monkeypatch
):
    """
    add disabled users to group
    """
    monkeypatch.setattr(
        context.accounts.group_dao,
        "get_group",
        lambda x: {"enabled": True, "group_type": "pqr"},
    )
    monkeypatch.setattr(
        context.accounts.user_dao, "get_user", lambda x: {"enabled": False}
    )
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.add_users_to_group(
            usernames=["x4"],
            group_name="xyz",
        )
    assert exc_info.value.error_code == errorcodes.AUTH_USER_IS_DISABLED
    assert "user is disabled: x4" in exc_info.value.message


def test_accounts_add_user_to_admin_group_coverage(context: AppContext, monkeypatch):
    """
    add users to admin group
    """
    monkeypatch.setattr(
        context.accounts.group_dao,
        "get_group",
        lambda x: {"enabled": True, "group_type": "pqr"},
    )
    monkeypatch.setattr(
        context.accounts.user_dao, "get_user", lambda x: {"enabled": False}
    )
    monkeypatch.setattr(constants, "GROUP_TYPE_USER", lambda x: "123")
    monkeypatch.setattr(constants, "GROUP_TYPE_PROJECT", lambda x: "456")
    try:
        context.accounts.add_users_to_group(
            usernames=["x4"],
            group_name="xyz",
            bypass_active_user_check=True,
        )
    except Exception as e:
        print("failed to add admin users group: {e}")


def test_accounts_remove_user_from_group_raise_exception_for_empty_usernames_or_group_name(
    context: AppContext, monkeypatch
):
    """
    remove users with empty either of user or group names
    """
    monkeypatch.setattr(Utils, "is_empty", lambda x: not (x))
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.remove_user_from_groups(
            username="",
            group_names=["xyz"],
        )
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert "usernames is required" in exc_info.value.message

    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.remove_user_from_groups(
            username="xyz",
            group_names=[],
        )
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert "group_names is required" in exc_info.value.message


def test_accounts_remove_user_from_group_create_the_list(
    context: AppContext, monkeypatch
):
    """
    remove users from group workflow
    """
    try:
        context.accounts.remove_user_from_groups(
            username="pqr",
            group_names=["xyz", "xyz"],
        )
    except Exception as e:
        print("failed to remove user from groups group_names: {e}")


def test_accounts_remove_user_from_group_create_the_list_raise_exception_when_user_not_enabled(
    context: AppContext, monkeypatch
):
    """
    remove a disabled user
    """
    monkeypatch.setattr(
        context.accounts.user_dao, "get_user", lambda x: {"enabled": False}
    )
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.remove_user_from_groups(
            username="xyz",
            group_names=["xyz"],
        )
    assert exc_info.value.error_code == errorcodes.AUTH_USER_IS_DISABLED
    assert "user is disabled: xyz" in exc_info.value.message


def test_accounts_remove_user_from_groups_from_user_create_the_list(
    context: AppContext, monkeypatch
):
    """
    normal workflow of removing users from group
    """
    monkeypatch.setattr(
        context.accounts.user_dao,
        "get_user",
        lambda x: {"enabled": True, "additional_groups": ["g1", "g2", "g3"]},
    )
    try:
        context.accounts.remove_user_from_groups(
            username="pqr",
            group_names=["xyz", "xyz"],
        )
    except Exception as e:
        print("failed to remove user from groups group_names: {e}")


def test_accounts_remove_users_from_group_raise_exception_for_empty_username_or_group(
    context: AppContext, monkeypatch
):
    """
    removing user from group with either user / group empty
    """
    monkeypatch.setattr(Utils, "is_empty", lambda x: not (x))
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.remove_users_from_group(
            usernames=[],
            group_name="xyz",
        )
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert "usernames is required" in exc_info.value.message

    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.remove_users_from_group(
            usernames=["xyz"],
            group_name="",
        )
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert "group_name is required" in exc_info.value.message


def test_accounts_add_admin_user_raise_exception_for_empty_username(
    context: AppContext, monkeypatch
):
    """
    add admin user with empty username
    """
    monkeypatch.setattr(Utils, "is_empty", lambda x: not (x))
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.add_admin_user(
            username="",
        )
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert "username is required" in exc_info.value.message


def test_accounts_add_admin_user_raise_exception_for_none_user(
    context: AppContext, monkeypatch
):
    """
    add admin user with user name none
    """
    monkeypatch.setattr(
        context.accounts.user_dao,
        "get_user",
        lambda x: None,
    )
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.add_admin_user(
            username="xyz",
        )
    assert exc_info.value.error_code == errorcodes.AUTH_USER_NOT_FOUND
    assert "User not found: xyz" in exc_info.value.message


def test_accounts_add_admin_user_return_if_admin_role_found(
    context: AppContext, monkeypatch
):
    """
    add admin user normal workflow
    """
    monkeypatch.setattr(
        context.accounts.user_dao, "get_user", lambda x: {"role": "admin"}
    )
    try:
        context.accounts.add_admin_user(
            username="pqr",
        )
    except Exception as e:
        print("failed to add admin user {e}")


def test_accounts_add_admin_user_update_succeed(context: AppContext, monkeypatch):
    """
    update an admin user
    """
    monkeypatch.setattr(
        context.accounts.user_dao,
        "get_user",
        lambda x: {"username": "xx", "sudo": True},
    )
    monkeypatch.setattr(context.accounts.user_dao, "update_user", lambda x: True)
    try:
        context.accounts.add_admin_user(
            username="xx",
        )
    except Exception as e:
        print("failed to add admin user {e}")


def test_accounts_remove_admin_user_raise_exception_for_empty_username(
    context: AppContext, monkeypatch
):
    """
    remove admin user with empty username
    """
    monkeypatch.setattr(Utils, "is_empty", lambda x: not (x))
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.remove_admin_user(
            username="",
        )
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert "username is required" in exc_info.value.message


def test_accounts_remove_admin_user_raise_exception_if_cluster_admin(
    context: AppContext, monkeypatch
):
    """
    remove cluseradmin user
    """
    monkeypatch.setattr(context.accounts, "is_cluster_administrator", lambda x: True)
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.remove_admin_user(
            username="xxx",
        )
    assert exc_info.value.error_code == errorcodes.AUTH_INVALID_OPERATION
    assert (
        "Admin rights cannot be revoked from RES Environment Administrator: xxx."
        in exc_info.value.message
    )


def test_accounts_remove_admin_user_raise_exception_for_none_user(
    context: AppContext, monkeypatch
):
    """
    remove admin user when username none
    """
    monkeypatch.setattr(
        context.accounts.user_dao,
        "get_user",
        lambda x: None,
    )
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.remove_admin_user(
            username="xyz",
        )
    assert exc_info.value.error_code == errorcodes.AUTH_USER_NOT_FOUND
    assert "User not found: xyz" in exc_info.value.message


def test_accounts_remove_admin_user_return_if_user_role_found(
    context: AppContext, monkeypatch
):
    """
    remove admin user normal worlflow
    """
    monkeypatch.setattr(
        context.accounts.user_dao, "get_user", lambda x: {"role": "user"}
    )
    try:
        context.accounts.remove_admin_user(
            username="pqr",
        )
    except Exception as e:
        print("failed to remove admin user {e}")


def test_accounts_remove_admin_user_update_succeed(context: AppContext, monkeypatch):
    monkeypatch.setattr(
        context.accounts.user_dao, "get_user", lambda x: {"username": "xx"}
    )
    """
    remove admin user with update user valid
    """
    monkeypatch.setattr(context.accounts.user_dao, "update_user", lambda x: True)
    try:
        context.accounts.remove_admin_user(
            username="xx",
        )
    except Exception as e:
        print("failed to add admin user {e}")


def test_accounts_get_user_raise_exception_for_none_user(
    context: AppContext, monkeypatch
):
    """
    get_user with none as username
    """
    monkeypatch.setattr(context.accounts.user_dao, "get_user", lambda x: None)
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.get_user(
            username="xyz",
        )
    assert exc_info.value.error_code == errorcodes.AUTH_USER_NOT_FOUND
    assert "User not found: xyz" in exc_info.value.message


def test_accounts_enable_user_raise_exception_for_empty_username(
    context: AppContext, monkeypatch
):
    """
    enable user with empty username
    """
    monkeypatch.setattr(Utils, "is_empty", lambda x: not (x))
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.enable_user(
            username="",
        )
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert "username is required" in exc_info.value.message


def test_accounts_enable_user_raise_exception_for_none_username(
    context: AppContext, monkeypatch
):
    """
    enable user with none username
    """
    monkeypatch.setattr(context.accounts.user_dao, "get_user", lambda x: None)
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.enable_user(
            username="xyz",
        )
    assert exc_info.value.error_code == errorcodes.AUTH_USER_NOT_FOUND
    assert "User not found: xyz" in exc_info.value.message


def test_accounts_enable_user_return_normally_for_enabled_user(
    context: AppContext, monkeypatch
):
    """
    enable user noromal workflow
    """
    monkeypatch.setattr(
        context.accounts.user_dao, "get_user", lambda x: {"enabled": True}
    )
    monkeypatch.setattr(Utils, "get_value_as_bool", lambda x, y, z: True)
    try:
        context.accounts.enable_user(
            username="xyz",
        )
    except Exception as e:
        print("failed to enable user {e}")


def test_accounts_disable_user_raise_exception_for_empty_username(
    context: AppContext, monkeypatch
):
    """
    disable user with empty username
    """
    monkeypatch.setattr(Utils, "is_empty", lambda x: not (x))
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.disable_user(
            username="",
        )
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert "username is required" in exc_info.value.message


def test_accounts_disable_user_raise_exception_for_cluster_admin(
    context: AppContext, monkeypatch
):
    """
    disable clusteradmin user
    """
    monkeypatch.setattr(context.accounts, "is_cluster_administrator", lambda x: True)
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.disable_user(
            username="xyz",
        )
    assert exc_info.value.error_code == errorcodes.AUTH_INVALID_OPERATION
    assert "Cluster Administrator cannot be disabled." in exc_info.value.message


def test_accounts_disable_user_raise_exception_for_existing_none_user(
    context: AppContext, monkeypatch
):
    """
    disable a user with none username
    """
    monkeypatch.setattr(context.accounts.user_dao, "get_user", lambda x: None)
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.disable_user(
            username="xyz",
        )
    assert exc_info.value.error_code == errorcodes.AUTH_USER_NOT_FOUND
    assert "User not found: xyz" in exc_info.value.message


def test_accounts_disable_user_return_normally_for_disabled_user(
    context: AppContext, monkeypatch
):
    """
    disable user normal workflow
    """
    monkeypatch.setattr(
        context.accounts.user_dao, "get_user", lambda x: {"enabled": True}
    )
    monkeypatch.setattr(Utils, "get_value_as_bool", lambda x, y, z: False)
    try:
        context.accounts.disable_user(
            username="xyz",
        )
    except Exception as e:
        print("failed to disable user {e}")


def test_accounts_delete_user_raise_exception_for_cluster_admin(
    context: AppContext, monkeypatch
):
    """
    delete clusteradmin user
    """
    monkeypatch.setattr(context.accounts, "is_cluster_administrator", lambda x: True)
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.delete_user(
            username="xyz",
        )
    assert exc_info.value.error_code == errorcodes.AUTH_INVALID_OPERATION
    assert "Cluster Administrator cannot be deleted." in exc_info.value.message


def test_accounts_delete_user_remove_user_from_groups(context: AppContext, monkeypatch):
    """
    delete user normal workflow
    """
    monkeypatch.setattr(Utils, "is_not_empty", lambda x: True)
    monkeypatch.setattr(Utils, "get_value_as_list", lambda x, y, z: ["g1"])
    try:
        context.accounts.delete_user(
            username="xyz",
        )
    except Exception as e:
        print("failed to log none user {e}")


def test_accounts_reset_password_raise_exception_for_empty_username(
    context: AppContext, monkeypatch
):
    """
    reset password for empty username
    """
    monkeypatch.setattr(AuthUtils, "sanitize_username", lambda x: x)
    monkeypatch.setattr(Utils, "is_empty", lambda x: True)
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.reset_password(
            username="xyz",
        )
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert "username is required" in exc_info.value.message


def test_accounts_reset_password_normal_workflow_for_valid_username(
    context: AppContext, monkeypatch
):
    """
    reset password normal workflow
    """
    monkeypatch.setattr(AuthUtils, "sanitize_username", lambda x: x)
    monkeypatch.setattr(
        context.accounts.user_pool, "admin_reset_password", lambda x: True
    )
    try:
        context.accounts.reset_password(
            username="xyz",
        )
    except Exception as e:
        print("failed to reset password {e}")


def test_accounts_change_password_normal_workflow_for_valid_username(
    context: AppContext, monkeypatch
):
    """
    change password normal workflow
    """
    monkeypatch.setattr(
        context.accounts.user_pool, "change_password", lambda x, y, z, a: True
    )
    try:
        context.accounts.change_password(
            username="xyz",
            access_token="pqr",
            old_password="abc123",
            new_password="123abc",
        )
    except Exception as e:
        print("failed to change password {e}")


def test_accounts_initiate_auth_empty_auth_flow_raise_exception(
    context: AppContext, monkeypatch
):
    """
    initiate auth with empty auth
    """
    monkeypatch.setattr(Utils, "is_empty", lambda x: True)
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.initiate_auth(
            request=InitiateAuthRequest(),
        )
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert "auth_flow is required" in exc_info.value.message


def test_accounts_initiate_auth_user_password_auth_flow(
    context: AppContext, monkeypatch
):
    """
    initiate auth normal workflow
    """
    username = "clusteradmin"
    decoded_token = {
        "username": username,
    }
    mock_auth_result = InitiateAuthResult(
        auth=AuthResult(access_token=""),
    )

    monkeypatch.setattr(
        context.user_pool, "initiate_username_password_auth", lambda a: mock_auth_result
    )
    monkeypatch.setattr(
        context.token_service, "decode_token", lambda token: decoded_token
    )
    result = context.accounts.initiate_auth(
        request=InitiateAuthRequest(
            auth_flow="USER_PASSWORD_AUTH",
            cognito_username=username,
            password="abc123",
        ),
    )
    assert result.role == "admin"
    assert result.db_username == "clusteradmin"


def test_accounts_initiate_auth_user_password_auth_flow_fail(context: AppContext):
    username = "clusteradmin"
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.initiate_auth(
            request=InitiateAuthRequest(
                auth_flow="USER_PASSWORD_AUTH",
                cognito_username="random",
                password="abc123",
            ),
        )
    assert exc_info.value.error_code == errorcodes.UNAUTHORIZED_ACCESS
    assert "Unauthorized Access" in exc_info.value.message

    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.initiate_auth(
            request=InitiateAuthRequest(
                auth_flow="USER_PASSWORD_AUTH",
                cognito_username=username,
                password="",
            ),
        )
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert "Invalid parameters: password is required" in exc_info.value.message


def test_accounts_initiate_auth_refresh_token_auth_flow(
    context: AppContext, monkeypatch
):
    """
    initiate auth with refresh token normal workflow
    """
    try:
        context.accounts.initiate_auth(
            request=InitiateAuthRequest(
                auth_flow="REFRESH_TOKEN_AUTH",
                cognito_username="clusteradmin",
                refresh_token="abc123",
            ),
        )
    except Exception as e:
        print("failed to refresh_token_auth in initiate_auth {e}")
    monkeypatch.setattr(Utils, "is_empty", lambda x: bool(x == "clusteradmin"))
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.initiate_auth(
            request=InitiateAuthRequest(
                auth_flow="REFRESH_TOKEN_AUTH",
                cognito_username="clusteradmin",
                refresh_token="abc123",
            ),
        )
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert "username is required" in exc_info.value.message
    monkeypatch.setattr(Utils, "is_empty", lambda x: bool(x == "abc123"))
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.initiate_auth(
            request=InitiateAuthRequest(
                auth_flow="REFRESH_TOKEN_AUTH",
                cognito_username="clusteradmin",
                refresh_token="abc123",
            ),
        )
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert "refresh_token is required" in exc_info.value.message


def test_accounts_initiate_sso_auth_flow(context: AppContext, monkeypatch):
    """
    initiate auth with SSO workflow
    """
    try:
        context.accounts.initiate_auth(
            request=InitiateAuthRequest(
                auth_flow="SSO_AUTH",
                cognito_username="xyz",
                authorization_code="abc123",
            ),
        )
    except Exception as e:
        print("failed sso_auth in initiate_auth {e}")
    monkeypatch.setattr(context.accounts, "is_sso_enabled", lambda: False)
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.initiate_auth(
            request=InitiateAuthRequest(
                auth_flow="SSO_AUTH",
                cognito_username="xyz",
                authorization_code="def123",
            ),
        )
    assert exc_info.value.error_code == errorcodes.UNAUTHORIZED_ACCESS
    assert "Unauthorized Access" in exc_info.value.message
    monkeypatch.setattr(context.accounts, "is_sso_enabled", lambda: True)
    monkeypatch.setattr(Utils, "is_empty", lambda x: bool(x == "def123"))
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.initiate_auth(
            request=InitiateAuthRequest(
                auth_flow="SSO_AUTH",
                cognito_username="xyz",
                authorization_code="def123",
            ),
        )
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert "authorization_code is required" in exc_info.value.message
    monkeypatch.setattr(Utils, "is_empty", lambda x: False)
    monkeypatch.setattr(context.accounts.sso_state_dao, "get_sso_state", lambda x: None)
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.initiate_auth(
            request=InitiateAuthRequest(
                auth_flow="SSO_AUTH",
                cognito_username="xyz",
                authorization_code="def123",
            ),
        )
    assert exc_info.value.error_code == errorcodes.UNAUTHORIZED_ACCESS
    monkeypatch.setattr(context.accounts.sso_state_dao, "get_sso_state", lambda x: x)
    try:
        context.accounts.initiate_auth(
            request=InitiateAuthRequest(
                auth_flow="SSO_AUTH",
                cognito_username="xyz",
                authorization_code="def123",
            ),
        )
    except:
        print("failed sso_auth in initiate_auth {e}")


def test_accounts_initiate_sso_refresh_auth_flow(context: AppContext, monkeypatch):
    """
    with SSO refresh token workflow
    """
    monkeypatch.setattr(context.accounts, "is_sso_enabled", lambda: False)
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.initiate_auth(
            request=InitiateAuthRequest(
                auth_flow="SSO_REFRESH_TOKEN_AUTH",
                cognito_username="xyz1",
                authorization_code="abc456",
            ),
        )
    assert exc_info.value.error_code == errorcodes.UNAUTHORIZED_ACCESS
    monkeypatch.setattr(context.accounts, "is_sso_enabled", lambda: True)
    monkeypatch.setattr(Utils, "is_empty", lambda x: bool(x == "xyz1"))
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.initiate_auth(
            request=InitiateAuthRequest(
                auth_flow="SSO_REFRESH_TOKEN_AUTH",
                cognito_username="xyz1",
                refresh_token="abc456",
            ),
        )
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert "username is required" in exc_info.value.message
    monkeypatch.setattr(Utils, "is_empty", lambda x: bool(x == "abc456"))
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.initiate_auth(
            request=InitiateAuthRequest(
                auth_flow="SSO_REFRESH_TOKEN_AUTH",
                cognito_username="xyz1",
                refresh_token="abc456",
            ),
        )
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert "refresh_token is required" in exc_info.value.message
    monkeypatch.setattr(Utils, "is_empty", lambda x: False)
    try:
        context.accounts.initiate_auth(
            request=InitiateAuthRequest(
                auth_flow="SSO_REFRESH_TOKEN_AUTH",
                cognito_username="xyz1",
                refresh_token="abc456",
            ),
        )
    except:
        print("failed sso_refresh_token_auth in initiate_auth {e}")


def test_accounts_respond_to_auth_challenge(context: AppContext, monkeypatch):
    """
    auth challenge workflow
    """
    monkeypatch.setattr(Utils, "is_empty", lambda x: bool(x == "xyz1"))
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.respond_to_auth_challenge(
            request=RespondToAuthChallengeRequest(
                username="xyz1",
            ),
        )
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert "username is required" in exc_info.value.message
    monkeypatch.setattr(Utils, "is_empty", lambda x: bool(x == "pqr"))
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.respond_to_auth_challenge(
            request=RespondToAuthChallengeRequest(
                username="xyz1",
                challenge_name="pqr",
            ),
        )
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert "challenge_name is required" in exc_info.value.message
    monkeypatch.setattr(Utils, "is_empty", lambda x: bool(x == "pqrs"))
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.respond_to_auth_challenge(
            request=RespondToAuthChallengeRequest(
                username="xyz1",
                challenge_name="pqr",
            ),
        )
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert "challenge_name: pqr is not supported." in exc_info.value.message
    monkeypatch.setattr(Utils, "is_empty", lambda x: bool(x == "ses101"))
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.respond_to_auth_challenge(
            request=RespondToAuthChallengeRequest(
                username="xyz1",
                challenge_name="NEW_PASSWORD_REQUIRED",
                session="ses101",
            ),
        )
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert "session is required." in exc_info.value.message
    monkeypatch.setattr(Utils, "is_empty", lambda x: bool(x == "pwd101"))
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.respond_to_auth_challenge(
            request=RespondToAuthChallengeRequest(
                username="xyz1",
                challenge_name="NEW_PASSWORD_REQUIRED",
                session="ses101",
                new_password="pwd101",
            ),
        )
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert "new_password is required." in exc_info.value.message
    monkeypatch.setattr(Utils, "is_empty", lambda x: False)
    try:
        context.accounts.respond_to_auth_challenge(
            request=RespondToAuthChallengeRequest(
                username="xyz1",
                challenge_name="NEW_PASSWORD_REQUIRED",
                session="ses101",
                new_password="pwd101",
            ),
        )
    except:
        print("failed respond_to_auth_challenge in initiate_auth {e}")
