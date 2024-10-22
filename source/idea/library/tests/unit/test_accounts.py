#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


from typing import Dict, Optional

import pytest
import res as res
import res.constants as constants
import res.exceptions as exceptions
from res.resources import accounts, role_assignments


class AccountsTestContext:
    crud_user: Optional[Dict]
    crud_group: Optional[Dict]
    crud_group_1: Optional[Dict]


def test_accounts_create_user_missing_username_should_fail():
    """
    create user with missing username
    """
    with pytest.raises(Exception) as exc_info:
        accounts.create_user(user={"username": ""})
    assert "username is required" in exc_info.value.args[0]


def test_accounts_create_user_invalid_username_should_fail():
    """
    create user with invalid username
    """
    create_user_invalid_username(r"Invalid Username")
    create_user_invalid_username(r"-InvalidUsername")
    # Username with dollar sign at the end will be treated as service account by system.
    # https://learn.microsoft.com/en-us/troubleshoot/windows-server/active-directory/compatibility-user-accounts-end-dollar-sign
    create_user_invalid_username(r"InvalidUsername$")
    # Special unicode characters are not allowed due to security concerns (similar to SQL injection or JS injection)
    create_user_invalid_username(r"\u2460\u2461\u2462\u2463")


def create_user_invalid_username(username: str):
    with pytest.raises(Exception) as exc_info:
        accounts.create_user(user={"username": username})
    assert constants.USERNAME_ERROR_MESSAGE in exc_info.value.args[0]


def test_accounts_create_user_system_account_username_should_fail(context):
    """
    create user with username as system accounts
    """
    with pytest.raises(Exception) as exc_info:
        accounts.create_user(user={"username": "root"})
    assert "invalid username:" in exc_info.value.args[0]


def test_accounts_create_user_missing_email_should_fail(context):
    """
    create user with missing email
    """
    with pytest.raises(Exception) as exc_info:
        accounts.create_user(user={"username": "mockuser1"})
    assert "email is required" in exc_info.value.args[0]


def test_accounts_create_user_invalid_email_should_fail(context):
    """
    create user with invalid email
    """
    with pytest.raises(Exception) as exc_info:
        accounts.create_user(user={"username": "mockuser1", "email": "invalid-email"})
    assert "invalid email:" in exc_info.value.args[0]


def test_accounts_create_user_with_verified_email_missing_uid_should_fail(context):
    """
    create valid account with email verified and no uid
    """
    with pytest.raises(Exception) as exc_info:
        accounts.create_user(
            user={"username": "mockuser1", "email": "mockuser1@example.com"},
        )
    assert "Unable to retrieve UID and GID for user mockuser1" in exc_info.value.args[0]


def test_accounts_create_user_with_verified_email_missing_gid_should_fail(context):
    """
    Create valid account with email verified and no gid
    """

    with pytest.raises(Exception) as exc_info:
        accounts.create_user(
            user={"username": "mockuser1", "email": "mockuser1@example.com"},
        )
    assert "Unable to retrieve UID and GID for user mockuser1" in exc_info.value.args[0]


def test_accounts_crud_create_user(context, monkeypatch):
    """
    create user
    """
    monkeypatch.setattr(
        accounts, "_get_uid_and_gid_for_username", lambda x: (1000, 1000)
    )

    created_user = accounts.create_user(
        user={
            "username": "accounts_user1",
            "email": "accounts_user1@example.com",
            "uid": 1000,
            "gid": 1000,
            "login_shell": "/bin/bash",
            "home_dir": "home/account_user1",
            "additional_groups": [],
            "enabled": True,
        },
    )

    assert created_user["username"] is not None
    assert created_user["email"] is not None

    user = accounts.get_user(username=created_user["username"])

    assert user is not None
    assert user.get("username") is not None
    assert user.get("email") is not None
    assert not user.get("additional_groups")
    assert user.get("enabled") is True
    assert user.get("uid") is not None and user.get("uid") == created_user.get("uid")
    assert user.get("gid") is not None and user.get("uid") == created_user.get("gid")
    assert user.get("sudo") is not None or user.get("sudo") is False
    assert user.get("home_dir") is not None and user.get(
        "home_dir"
    ) == created_user.get("home_dir")
    assert user.get("login_shell") is not None and user.get(
        "login_shell"
    ) == created_user.get("login_shell")
    assert user.get("password") is None
    assert user.get("created_on") is not None
    assert user.get("updated_on") is not None

    AccountsTestContext.crud_user = user


def test_accounts_crud_create_user_with_capital_letters_hyphen_and_period_in_sam_account_name(
    context,
    monkeypatch,
):
    """
    create user
    """
    monkeypatch.setattr(
        accounts, "_get_uid_and_gid_for_username", lambda x: (1000, 1000)
    )

    created_user = accounts.create_user(
        user={
            "username": "accounts_USER3.-",
            "email": "accounts_user3@example.com",
            "uid": 1000,
            "gid": 1000,
            "login_shell": "/bin/bash",
            "home_dir": "home/account_user3.-",
            "additional_groups": [],
        },
    )

    assert created_user.get("username") is not None
    assert created_user.get("email") is not None

    user = accounts.get_user(username=created_user.get("username"))

    assert user is not None
    assert user.get("username") is not None
    assert user.get("email") is not None
    assert user.get("home_dir") is not None and user.get(
        "home_dir"
    ) == created_user.get("home_dir")


def test_accounts_crud_get_user(context):
    """
    get user
    """
    assert AccountsTestContext.crud_user is not None
    crud_user = AccountsTestContext.crud_user

    user = accounts.get_user(username=crud_user.get("username"))

    assert user is not None
    assert user.get("username") == crud_user.get("username")
    assert user.get("uid") == crud_user.get("uid")
    assert user.get("gid") == crud_user.get("gid")


def test_accounts_crud_update_user(context):
    """
    update user
    """
    assert AccountsTestContext.crud_user is not None
    crud_user = AccountsTestContext.crud_user

    update_user = {
        "username": crud_user.get("username"),
        "email": "accounts_user1_modified@example.com",
        "uid": 6000,
        "gid": 6000,
        "login_shell": "/bin/csh",
    }
    accounts.update_user(user=update_user)

    user = accounts.get_user(username=crud_user.get("username"))
    assert user.get("username") == update_user.get("username")
    assert user.get("email") == update_user.get("email")
    assert user.get("uid") == update_user.get("uid")
    assert user.get("gid") == update_user.get("gid")
    assert user.get("login_shell") == update_user.get("login_shell")


def test_accounts_crud_list_users(context):
    """
    list users
    """
    assert AccountsTestContext.crud_user is not None
    crud_user = AccountsTestContext.crud_user

    result = accounts.list_users()
    assert result is not None

    found = None
    for user in result:
        if user.get("username") == crud_user.get("username"):
            found = user
            break
    assert found is not None


def test_accounts_create_group_with_invalid_name_or_type_should_fail(context):
    """
    external group with invalid name or type
    """
    with pytest.raises(Exception) as exc_info:
        accounts.create_group(
            {
                "title": "Dummy Group",
                "name": None,
                "ds_name": None,
            }
        )
    assert f"group name is required" in exc_info.value.args[0]


def test_accounts_create_group_with_existing_group_name_should_fail(monkeypatch):
    """
    existing group
    """
    monkeypatch.setattr(accounts, "get_group", lambda x: "xyz")
    with pytest.raises(Exception) as exc_info:
        accounts.create_group(
            {
                "title": "Dummy Group",
                "group_name": "xyz",
                "ds_name": "xyz",
            }
        )
    assert f"group: xyz already exists" in exc_info.value.args[0]


def test_accounts_create_group_without_ds_name_in_external_ad_should_fail(context):
    """
    group without ds_name
    """
    with pytest.raises(Exception) as exc_info:
        accounts.create_group(
            {
                "title": "Dummy Group",
                "group_name": "pqr",
            }
        )
    assert f"group ds_name is required" in exc_info.value.args[0]


def test_accounts_get_group_with_empty_group_name_should_fail():
    """
    get group with empty name
    """
    with pytest.raises(Exception) as exc_info:
        accounts.get_group("")
    assert f"group name is required" in exc_info.value.args[0]


def test_accounts_delete_group_should_raise_exception_for_empty_group():
    """
    delete empty group-name
    """
    with pytest.raises(Exception) as exc_info:
        accounts.delete_group({})
    assert "group name is required" in exc_info.value.args[0]


def test_accounts_delete_group_should_raise_exception_for_users_in_group(monkeypatch):
    """
    delete groups with users in
    """
    monkeypatch.setattr(accounts, "get_group", lambda x: {"group_name": "xyz"})
    monkeypatch.setattr(
        accounts, "_get_users_in_group", lambda x: [{"username": "xyz"}]
    )
    with pytest.raises(Exception) as exc_info:
        accounts.delete_group({"group_name": "xyz"})
    assert (
        "Users associated to group. Group must be empty before it can be deleted."
        in exc_info.value.args[0]
    )


def test_accounts_add_user_to_groups_by_names_raise_exception_for_empty_usernames_or_group_name():
    """
    Add user in group with empty username
    """
    with pytest.raises(Exception) as exc_info:
        accounts.add_user_to_groups_by_names(
            user={},
            group_names=["xyz"],
        )
    assert "user is required" in exc_info.value.args[0]

    with pytest.raises(Exception) as exc_info:
        accounts.add_user_to_groups_by_names(
            user={"username": "xyz"},
            group_names=[],
        )
    assert "group_names is required" in exc_info.value.args[0]


def test_accounts_add_user_to_groups_by_names_raise_exception_for_group_not_enabled(
    monkeypatch,
):
    """
    add users to a disabled group
    """
    response = {"enabled": False}
    monkeypatch.setattr(accounts, "get_group", lambda x: response)
    with pytest.raises(Exception) as exc_info:
        accounts.add_user_to_groups_by_names(
            user={"username": "xyz", "enabled": True},
            group_names=["xyz"],
        )
    assert "cannot add user xyz to a disabled user group xyz" in exc_info.value.args[0]


def test_accounts_add_user_to_groups_by_names_raise_exception_for_user_is_none(
    context, monkeypatch
):
    """
    add user to group with username none
    """
    response = {"enabled": True}
    monkeypatch.setattr(accounts, "get_group", lambda x: response)
    with pytest.raises(exceptions.UserNotFound) as exc_info:
        accounts.add_user_to_groups_by_names(
            user={"username": "x4", "enabled": True},
            group_names=["xyz"],
        )
    assert "User not found: x4" in exc_info.value.args[0]


def test_accounts_add_user_to_groups_by_names_raise_exception_for_user_is_disabled(
    monkeypatch,
):
    """
    add disabled users to group
    """
    monkeypatch.setattr(
        accounts,
        "get_group",
        lambda x: {"enabled": True, "group_type": "pqr"},
    )
    monkeypatch.setattr(accounts, "get_user", lambda x: {"enabled": False})
    with pytest.raises(Exception) as exc_info:
        accounts.add_user_to_groups_by_names(
            user={"username": "x4", "enabled": False},
            group_names=["xyz"],
        )
    assert "user is disabled: x4" in exc_info.value.args[0]


def test_accountsremove_user_from_groups_raise_exception_for_empty_usernames_or_group_name():
    """
    remove users with empty either of user or group names
    """
    with pytest.raises(Exception) as exc_info:
        accounts.remove_user_from_groups_by_names(
            user={},
            group_names=["xyz"],
        )
    assert "user is required" in exc_info.value.args[0]

    with pytest.raises(Exception) as exc_info:
        accounts.remove_user_from_groups_by_names(
            user={"username": "xyz", "enabled": True},
            group_names=[],
        )
    assert "group_names is required" in exc_info.value.args[0]


def test_accountsremove_user_from_groups_raise_exception_when_user_not_enabled(
    monkeypatch,
):
    """
    remove a disabled user
    """
    monkeypatch.setattr(accounts, "get_user", lambda x: {"enabled": False})
    with pytest.raises(Exception) as exc_info:
        accounts.remove_user_from_groups_by_names(
            user={"username": "xyz"},
            group_names=["xyz"],
        )
    assert "user is disabled: xyz" in exc_info.value.args[0]


def test_accounts_remove_users_from_group_raise_exception_for_empty_users_or_group_name():
    """
    remove users with empty either of user or group names
    """
    with pytest.raises(Exception) as exc_info:
        accounts._remove_users_from_group(
            users=[],
            group={"group_name": "xyz", "enabled": True},
        )
    assert "users is required" in exc_info.value.args[0]

    with pytest.raises(Exception) as exc_info:
        accounts._remove_users_from_group(
            users=[{"username": "xyz"}],
            group={},
        )
    assert "group is required" in exc_info.value.args[0]


def test_accounts_remove_users_from_group_create_the_list_raise_exception_when_user_not_enabled(
    monkeypatch,
):
    """
    remove a disabled user
    """
    monkeypatch.setattr(accounts, "get_user", lambda x: {"enabled": False})
    with pytest.raises(Exception) as exc_info:
        accounts._remove_users_from_group(
            users=[{"username": "xyz"}],
            group={"group_name": "xyz", "enabled": True},
        )
    assert "user is disabled: xyz" in exc_info.value.args[0]


def test_accounts_remove_users_from_group_create_the_list_raise_exception_when_group_not_enabled(
    monkeypatch,
):
    """
    remove a disabled user
    """
    monkeypatch.setattr(accounts, "get_user", lambda x: {"enabled": True})
    with pytest.raises(Exception) as exc_info:
        accounts._remove_users_from_group(
            users=[{"username": "xyz"}],
            group={"group_name": "xyz", "enabled": False},
        )
    assert "cannot remove users from a disabled user group" in exc_info.value.args[0]


def test_accounts_crud_create_group(
    context,
):
    """
    external group
    """
    group = accounts.create_group(
        {
            "title": "Dummy Group",
            "group_name": "dummy-group",
            "ds_name": "dummy-group",
            "gid": None,
        }
    )
    assert group is not None

    assert group.get("group_name") == "dummy-group"

    AccountsTestContext.crud_group = group


def test_accounts_crud_list_group(context):
    """
    list groups
    """
    assert AccountsTestContext.crud_group is not None
    crud_group = AccountsTestContext.crud_group

    groups = accounts.list_groups()

    assert len(groups) == 1
    assert groups[0]["group_name"] == crud_group["group_name"]


def test_accounts_crud_add_user_to_groups_by_names_success(context):
    """
    add users to admin group
    """
    assert AccountsTestContext.crud_user is not None
    crud_user = AccountsTestContext.crud_user
    assert AccountsTestContext.crud_group is not None
    crud_group = AccountsTestContext.crud_group

    accounts.add_user_to_groups_by_names(
        user=crud_user,
        group_names=[crud_group["group_name"]],
        bypass_active_user_check=True,
    )

    users = accounts._get_users_in_group(group_name=crud_group["group_name"])
    assert len(users) == 1
    assert crud_user["username"] == users[0]["username"]


def test_accounts_crud_remove_user_from_groups_success(context):
    """
    remove user from groups workflow
    """
    assert AccountsTestContext.crud_user is not None
    crud_user = AccountsTestContext.crud_user
    assert AccountsTestContext.crud_group is not None
    crud_group = AccountsTestContext.crud_group

    crud_group_1 = accounts.create_group(
        {
            "title": "Dummy Group 1",
            "group_name": "dummy-group-1",
            "ds_name": "dummy-group-1",
            "gid": None,
        }
    )
    AccountsTestContext.crud_group_1 = crud_group_1

    accounts.add_user_to_groups_by_names(
        user=crud_user,
        group_names=[crud_group_1["group_name"]],
        bypass_active_user_check=True,
    )

    accounts.remove_user_from_groups_by_names(
        user=crud_user,
        group_names=[crud_group["group_name"], crud_group_1["group_name"]],
    )

    users = accounts._get_users_in_group(group_name=crud_group["group_name"])
    assert len(users) == 0
    users = accounts._get_users_in_group(group_name=crud_group_1["group_name"])
    assert len(users) == 0


def test_accounts_crud_delete_user(context):
    """
    delete user
    """
    assert AccountsTestContext.crud_user is not None
    crud_user = AccountsTestContext.crud_user
    assert AccountsTestContext.crud_group is not None
    crud_group = AccountsTestContext.crud_group
    assert AccountsTestContext.crud_group_1 is not None
    crud_group_1 = AccountsTestContext.crud_group_1

    accounts.add_user_to_groups_by_names(
        user=crud_user,
        group_names=[crud_group["group_name"], crud_group_1["group_name"]],
        bypass_active_user_check=True,
    )

    accounts.delete_user(crud_user)

    users = accounts._get_users_in_group(group_name=crud_group["group_name"])
    assert len(users) == 0
    users = accounts._get_users_in_group(group_name=crud_group_1["group_name"])
    assert len(users) == 0

    with pytest.raises(exceptions.UserNotFound) as exc_info:
        accounts.get_user(crud_user["username"])
    assert f'User not found: {crud_user["username"]}' in exc_info.value.args[0]


def test_accounts_crud_delete_group(context, monkeypatch):
    assert AccountsTestContext.crud_group is not None
    crud_group = AccountsTestContext.crud_group

    def _list_role_assignments(actor_key: str):
        if (
            actor_key
            == f'{crud_group["group_name"]}:{constants.ROLE_ASSIGNMENT_ACTOR_GROUP_TYPE}'
        ):
            return [
                {
                    "actor_key": f'{crud_group["group_name"]}:{constants.ROLE_ASSIGNMENT_ACTOR_GROUP_TYPE}',
                    "resource_key": f"project:{constants.PROJECT_ROLE_ASSIGNMENT_TYPE}",
                    "resource_id": "project",
                    "resource_type": constants.PROJECT_ROLE_ASSIGNMENT_TYPE,
                }
            ]
        else:
            assert False, "list_role_assignments is not invoked"

    monkeypatch.setattr(
        role_assignments, "list_role_assignments", _list_role_assignments
    )

    delete_role_assignments_invoked = False

    def _delete_role_assignment(assignment: Dict[str, str]):
        if (
            assignment["actor_key"]
            == f'{crud_group["group_name"]}:{constants.ROLE_ASSIGNMENT_ACTOR_GROUP_TYPE}'
            and assignment["resource_key"]
            == f"project:{constants.PROJECT_ROLE_ASSIGNMENT_TYPE}"
        ):
            nonlocal delete_role_assignments_invoked
            delete_role_assignments_invoked = True

    monkeypatch.setattr(
        role_assignments, "delete_role_assignment", _delete_role_assignment
    )

    accounts.delete_group(crud_group, True)
    with pytest.raises(exceptions.GroupNotFound) as exc_info:
        accounts.get_group(crud_group["group_name"])
    assert f"Group not found:" in exc_info.value.args[0]

    assert delete_role_assignments_invoked
