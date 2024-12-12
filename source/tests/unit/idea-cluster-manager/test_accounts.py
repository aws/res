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
from ideaclustermanager.app.accounts.auth_utils import AuthUtils
from ideasdk.utils import Utils
from ideatestutils import IdeaTestProps
from res.resources import accounts

from ideadatamodel import (
    ConfirmSignUpRequest,
    Group,
    ListUsersRequest,
    ListUsersResult,
    ResendConfirmationCodeRequest,
    SignUpUserRequest,
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
)

test_props = IdeaTestProps()


class AccountsTestContext:
    crud_user: Optional[User]


def test_accounts_get_group(context: AppContext, monkeypatch):
    """
    get group
    """
    existing_group = {
        "title": "Dummy Group",
        "group_name": "xyz",
        "ds_name": "xyz",
        "enabled": False,
    }
    monkeypatch.setattr(
        accounts,
        "get_group",
        lambda group_name: (
            existing_group if group_name == existing_group["group_name"] else None
        ),
    )

    group = context.accounts.get_group(group_name=existing_group["group_name"])

    assert group is not None
    assert group.name == existing_group["group_name"]
    assert group.ds_name == existing_group["group_name"]
    assert group.title == existing_group["title"]
    assert group.enabled == existing_group["enabled"]


def test_accounts_modify_group(context: AppContext, monkeypatch):
    """
    modify user
    """
    updated_group = {
        "title": "Updated Group",
        "group_name": "xyz",
        "ds_name": "xyz",
        "enabled": True,
    }
    monkeypatch.setattr(
        accounts,
        "update_group",
        lambda group_to_update: (
            updated_group
            if group_to_update["group_name"] == updated_group["group_name"]
            else None
        ),
    )

    group = Group(
        name=updated_group["group_name"],
    )
    modified_group = context.accounts.modify_group(group)
    assert modified_group.title == updated_group["title"]
    assert modified_group.name == updated_group["group_name"]
    assert modified_group.ds_name == updated_group["ds_name"]
    assert modified_group.enabled == updated_group["enabled"]


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


def test_accounts_remove_admin_user_raise_exception_if_cluster_admin(
    context: AppContext, monkeypatch
):
    """
    remove cluseradmin user
    """
    monkeypatch.setattr(context.accounts, "is_cluster_administrator", lambda x: True)
    with pytest.raises(Exception) as exc_info:
        context.accounts.remove_admin_user(
            username="xxx",
        )
    assert exc_info.value.error_code == errorcodes.AUTH_INVALID_OPERATION
    assert (
        "Admin rights cannot be revoked from RES Environment Administrator: xxx."
        in exc_info.value.message
    )


def test_accounts_remove_admin_user_update_succeed(context: AppContext, monkeypatch):
    monkeypatch.setattr(accounts, "get_user", lambda x: {"username": "xx"})
    """
    remove admin user with update user valid
    """
    monkeypatch.setattr(accounts, "update_user", lambda x: True)
    try:
        context.accounts.remove_admin_user(
            username="xx",
        )
    except Exception as e:
        print("failed to add admin user {e}")


def test_accounts_get_user(context: AppContext, monkeypatch):
    """
    get user
    """
    existing_user = {
        "username": "accounts_user1",
        "email": "accounts_user1@example.com",
        "password": "MockPassword_123!%",
        "uid": 1000,
        "gid": 1000,
        "login_shell": "/bin/bash",
        "home_dir": "home/account_user1",
        "additional_groups": [],
    }
    monkeypatch.setattr(
        accounts,
        "get_user",
        lambda username: (
            existing_user if username == existing_user["username"] else None
        ),
    )

    user = context.accounts.get_user(username=existing_user["username"])

    assert user is not None
    assert user.username == existing_user["username"]
    assert user.uid == existing_user["uid"]
    assert user.gid == existing_user["gid"]


def test_accounts_get_user_by_email(context: AppContext, monkeypatch):
    """
    get user by email
    """
    existing_user = {
        "username": "accounts_user1",
        "email": "accounts_user1@example.com",
        "password": "MockPassword_123!%",
        "uid": 1000,
        "gid": 1000,
        "login_shell": "/bin/bash",
        "home_dir": "home/account_user1",
        "additional_groups": [],
    }
    monkeypatch.setattr(
        context.accounts.user_dao,
        "get_user_by_email",
        lambda email: [existing_user] if email == existing_user["email"] else [],
    )

    user = context.accounts.get_user_by_email(email=existing_user["email"])

    assert user is not None
    assert user.username == existing_user["username"]
    assert user.email == existing_user["email"]


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


def test_accounts_disable_user_return_normally_for_disabled_user(
    context: AppContext, monkeypatch
):
    """
    disable user normal workflow
    """
    monkeypatch.setattr(accounts, "get_user", lambda x: {"enabled": True})
    try:
        context.accounts.disable_user(
            username="xyz",
        )
    except Exception as e:
        print("failed to disable user {e}")


def test_accounts_modify_user(context: AppContext, monkeypatch):
    """
    modify user
    """
    updated_user = {
        "username": "accounts_user1",
        "email": "accounts_user1_modified@example.com",
        "password": "MockPassword_123!%",
        "uid": 1000,
        "gid": 1000,
        "login_shell": "/bin/bash",
        "home_dir": "home/account_user1",
        "additional_groups": [],
    }
    monkeypatch.setattr(
        accounts,
        "update_user",
        lambda user_to_update: (
            updated_user
            if user_to_update["username"] == updated_user["username"]
            else None
        ),
    )

    user = User(
        username=updated_user["username"],
    )
    modified_user = context.accounts.modify_user(user)
    assert modified_user.username == updated_user["username"]
    assert modified_user.email == updated_user["email"]
    assert modified_user.uid == updated_user["uid"]
    assert modified_user.gid == updated_user["gid"]
    assert modified_user.login_shell == updated_user["login_shell"]


def test_accounts_return_list_users_request(context: AppContext, monkeypatch):
    """
    list users
    """
    existing_user = User(
        username="accounts_user1",
        email="accounts_user1@example.com",
        password="MockPassword_123!%",
        uid=1000,
        gid=1000,
        login_shell="/bin/bash",
        home_dir="home/account_user1",
        additional_groups=[],
    )
    monkeypatch.setattr(
        context.accounts.user_dao,
        "list_users",
        lambda x: ListUsersResult(listing=[existing_user]),
    )

    result = context.accounts.list_users(ListUsersRequest())
    assert result.listing is not None

    found = None
    for user in result.listing:
        if user.username == existing_user.username:
            found = user
            break
    assert found is not None


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

    set_enable_native_user_login_to_true(context, monkeypatch)

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


def test_accounts_initiate_auth_user_password_auth_flow_fail(
    context: AppContext, monkeypatch
):
    # When identity-provider.cognito.enable_native_user_login is turned off, users who are not `clusteradmin` should not be able to authenticate
    monkeypatch.setattr(context._config, "get_bool", lambda key, required: False)
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
                cognito_username="clusteradmin",
                password="",
            ),
        )
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert "Invalid parameters: password is required" in exc_info.value.message


def set_enable_native_user_login_to_true(context: AppContext, monkeypatch):
    # Set identity-provider.cognito.enable_native_user_login to true
    monkeypatch.setattr(context._config, "get_bool", lambda key, required: True)


def test_accounts_initiate_auth_refresh_token_auth_flow(
    context: AppContext, monkeypatch
):
    """
    initiate auth with refresh token normal workflow
    """
    try:
        set_enable_native_user_login_to_true(context, monkeypatch)
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
    set_enable_native_user_login_to_true(context, monkeypatch)
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
    set_enable_native_user_login_to_true(context, monkeypatch)
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
    set_enable_native_user_login_to_true(context, monkeypatch)
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
    set_enable_native_user_login_to_true(context, monkeypatch)
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
    set_enable_native_user_login_to_true(context, monkeypatch)
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
    set_enable_native_user_login_to_true(context, monkeypatch)
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
    set_enable_native_user_login_to_true(context, monkeypatch)
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
    set_enable_native_user_login_to_true(context, monkeypatch)
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
    set_enable_native_user_login_to_true(context, monkeypatch)
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
    set_enable_native_user_login_to_true(context, monkeypatch)
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
    set_enable_native_user_login_to_true(context, monkeypatch)
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


@pytest.mark.parametrize(
    "invalid_email",
    [
        "invalidemail!+$=%^&()@example.com",  # disallowed special characters
        "-invalidemail@example.com",  # cannot start with -
        "_invalidemail@example.com",  # cannot start with _
        "@example.com",  # longer than 0 characters
        "Invalid@example.com",  # no capital letters
        "aaaabbbbccccddddeeeeffffgggghhhhi@example.com",  # longer than 32 characters
        "12345@example.com",  # cannot start with numbers
    ],
)
def test_accounts_sign_up_user_invalid_email(
    context: AppContext, monkeypatch, invalid_email
):
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.sign_up_user(
            SignUpUserRequest(email=invalid_email, password="validPassword!234")
        )
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert constants.COGNITO_USERNAME_ERROR_MESSAGE in exc_info.value.message


def test_accounts_sign_up_user_invalid_password(context: AppContext, monkeypatch):
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.sign_up_user(
            SignUpUserRequest(email="validemail@example.com", password="fakePassword")
        )
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert "Password should include at least 1 number" in exc_info.value.message


def test_accounts_sign_up_user_duplicate(context: AppContext, monkeypatch):
    monkeypatch.setattr(accounts, "get_user", lambda x: {"enabled": True})
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.sign_up_user(
            SignUpUserRequest(email="validemail@example.com", password="fakePassword1.")
        )
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert "User already exists: validemail" in exc_info.value.message


@pytest.mark.parametrize(
    "valid_email",
    [
        "validemail123@example.com",  # can contain lowercase letters and numbers
        "valid-_email@example.com",  # - and _ allowed
        "aaaabbbbccccddddeeeeffffgggghhhh@example.com",  # 32 max length
        "a@example.com",  # 1 min length
    ],
)
def test_accounts_sign_up_user_succeed(context: AppContext, monkeypatch, valid_email):
    monkeypatch.setattr(
        context.accounts.user_pool, "sign_up_user", lambda username, email, password: ""
    )
    # Expect no error to be thrown. There is nothing to assert since return value is void
    context.accounts.sign_up_user(
        SignUpUserRequest(email=valid_email, password="validPassword!234")
    )


def raise_general_exception(message: str):
    raise exceptions.general_exception(message)


def test_accounts_confirm_sign_up_invalid_confirmation_code(
    context: AppContext, monkeypatch
):
    error_message = "Invalid confirmation code"
    monkeypatch.setattr(
        context.accounts.user_pool,
        "confirm_sign_up",
        lambda username, confirmation_code: raise_general_exception(error_message),
    )

    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.confirm_sign_up(
            ConfirmSignUpRequest(
                email="validemail@example.com", confirmation_code="1234"
            )
        )
    assert exc_info.value.error_code == errorcodes.GENERAL_ERROR
    assert error_message in exc_info.value.message


def test_accounts_confirm_sign_up_invalid_user(context: AppContext, monkeypatch):
    error_message = "User not found"
    monkeypatch.setattr(
        context.accounts.user_pool,
        "confirm_sign_up",
        lambda username, confirmation_code: raise_general_exception(error_message),
    )

    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.confirm_sign_up(
            ConfirmSignUpRequest(
                email="validemail@example.com", confirmation_code="1234"
            )
        )
    assert exc_info.value.error_code == errorcodes.GENERAL_ERROR
    assert error_message in exc_info.value.message


def test_accounts_confirm_sign_up_succeed(context: AppContext, monkeypatch):
    monkeypatch.setattr(
        context.accounts.user_pool,
        "confirm_sign_up",
        lambda username, confirmation_code: "",
    )

    # Expect no error to be thrown. There is nothing to assert since return value is void
    context.accounts.confirm_sign_up(
        ConfirmSignUpRequest(email="validemail@example.com", confirmation_code="1234")
    )


def test_accounts_resend_confirmation_code_invalid_user(
    context: AppContext, monkeypatch
):
    error_message = "User not found"
    monkeypatch.setattr(
        context.accounts.user_pool,
        "resend_confirmation_code",
        lambda username: raise_general_exception(error_message),
    )

    with pytest.raises(exceptions.SocaException) as exc_info:
        context.accounts.resend_confirmation_code(
            ResendConfirmationCodeRequest(username="testuser")
        )
    assert exc_info.value.error_code == errorcodes.GENERAL_ERROR
    assert error_message in exc_info.value.message


def test_accounts_resend_confirmation_code_success(context: AppContext, monkeypatch):
    monkeypatch.setattr(
        context.accounts.user_pool,
        "resend_confirmation_code",
        lambda username: "",
    )

    # Expect no error to be thrown. There is nothing to assert since return value is void
    context.accounts.resend_confirmation_code(
        ResendConfirmationCodeRequest(username="testuser")
    )
