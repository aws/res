import os
from datetime import datetime
from typing import Any
from unittest.mock import MagicMock

import boto3
import pytest

from idea.infrastructure.install import cognito_sync_handler
from idea.infrastructure.install.cognito_sync_handler import CognitoGroup, CognitoUser
from ideadatamodel import SocaAnyPayload, constants  # type: ignore

userPoolId = "fakeUserPool"


@pytest.fixture
def mock_env_vars() -> None:
    os.environ["CUSTOM_UID_ATTRIBUTE"] = f"custom:{constants.COGNITO_UID_ATTRIBUTE}"
    os.environ["COGNITO_MIN_ID_INCLUSIVE"] = str(constants.COGNITO_MIN_ID_INCLUSIVE)
    os.environ["CLUSTER_NAME"] = "res-new"
    os.environ["GROUP_TYPE_PROJECT"] = constants.GROUP_TYPE_PROJECT
    os.environ["COGNITO_SUDOER_GROUP_NAME"] = "res"
    os.environ["ADMIN_ROLE"] = constants.ADMIN_ROLE
    os.environ["USER_ROLE"] = constants.USER_ROLE
    os.environ["GROUP_TYPE_INTERNAL"] = constants.GROUP_TYPE_INTERNAL
    os.environ["COGNITO_USER_IDP_TYPE"] = constants.COGNITO_USER_IDP_TYPE
    os.environ["SSO_USER_IDP_TYPE"] = constants.SSO_USER_IDP_TYPE
    os.environ["COGNITO_USER_POOL_ID"] = userPoolId
    os.environ["CLUSTER_ADMIN_NAME"] = "clusteradmin"


exampleDateOne: datetime = datetime(2023, 5, 15, 12, 30, 0)
exampleDateTwo: datetime = datetime(2023, 6, 15, 12, 30, 0)
groupA = {
    "GroupName": "groupa",
    "UserPoolId": userPoolId,
    "Description": "example description for groupa",
    "LastModifiedDate": exampleDateTwo,
    "CreationDate": exampleDateOne,
}
cognito_group: list[CognitoGroup] = [
    {
        "created_time": groupA["CreationDate"],  # type: ignore
        "description": str(groupA["Description"]),
        "group_name": str(groupA["GroupName"]),
        "updated_time": groupA["LastModifiedDate"],  # type: ignore
    }
]
group_name_to_username = {"groupa": ["user1"]}

native_cognito_users: list[CognitoUser] = [
    {
        "username": "user1",
        "email": "user1@example.com",
        "created_on": exampleDateOne,
        "enabled": True,
        "updated_on": exampleDateTwo,
        "uid": 1234,
    }
]


@pytest.fixture
def cognito_client(request: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    def side_effects(*args: Any) -> SocaAnyPayload:
        if args[0] == "list_groups":
            paginator = SocaAnyPayload()
            paginator.paginate = MagicMock(return_value=[{"Groups": [groupA]}])
        elif args[0] == "list_users_in_group":
            paginator = SocaAnyPayload()
            paginator.paginate = MagicMock(
                return_value=[{"Users": [{"Username": "user1"}]}]
            )
        elif args[0] == "list_users":
            paginator = SocaAnyPayload()
            paginator.paginate = MagicMock(
                return_value=[
                    {
                        "Users": [
                            {
                                "Username": "user1",
                                "Enabled": True,
                                "UserCreateDate": exampleDateOne,
                                "UserLastModifiedDate": exampleDateTwo,
                                "UserStatus": "CONFIRMED",
                                "Attributes": [
                                    {
                                        "Name": f"custom:{constants.COGNITO_UID_ATTRIBUTE}",
                                        "Value": "1234",
                                    },
                                    {"Name": "email", "Value": "user1@example.com"},
                                ],
                            }
                        ]
                    }
                ]
            )

        return paginator

    cognito_client = SocaAnyPayload()
    cognito_client.get_paginator = MagicMock(side_effect=side_effects)

    def mock_client(_: str) -> Any:
        return cognito_client

    monkeypatch.setattr(boto3, "client", mock_client)


@pytest.fixture
def ddb_client_accounts_groups(request: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    paginator = SocaAnyPayload()
    paginator.paginate = MagicMock(
        return_value=[
            {
                "Items": [
                    {
                        "identity_source": {"S": "Native user"},
                        "group_name": {"S": "groupa"},
                    }
                ]
            }
        ]
    )

    ddb_client = SocaAnyPayload()
    ddb_client.get_paginator = MagicMock(return_value=paginator)

    def mock_client(_: str) -> Any:
        return ddb_client

    monkeypatch.setattr(boto3, "client", mock_client)


@pytest.fixture
def ddb_client_accounts_group_members(
    request: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    paginator = SocaAnyPayload()
    paginator.paginate = MagicMock(
        return_value=[
            {"Items": [{"group_name": {"S": "groupa"}, "username": {"S": "user1"}}]}
        ]
    )

    ddb_client = SocaAnyPayload()
    ddb_client.get_paginator = MagicMock(return_value=paginator)

    def mock_client(_: str) -> Any:
        return ddb_client

    monkeypatch.setattr(boto3, "client", mock_client)


@pytest.fixture
def ddb_resource(request: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    batch = SocaAnyPayload
    batch.put_item = MagicMock(return_value=())

    batch_writer = SocaAnyPayload
    batch_writer = MagicMock(return_value=[batch])

    table = SocaAnyPayload()
    table.batch_writer = MagicMock(return_value=batch_writer)

    ddb_resource = SocaAnyPayload()
    ddb_resource.Table = MagicMock(return_value=table)

    def mock_resource(_: str) -> Any:
        return ddb_resource

    monkeypatch.setattr(boto3, "resource", mock_resource)


@pytest.fixture
def ddb_client_accounts_users(request: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    paginator = SocaAnyPayload()
    paginator.paginate = MagicMock(
        return_value=[
            {
                "Items": [
                    {
                        "identity_source": {"S": "Native user"},
                        "username": {"S": "user1"},
                    }
                ]
            }
        ]
    )

    ddb_client = SocaAnyPayload()
    ddb_client.get_paginator = MagicMock(return_value=paginator)

    def mock_client(_: str) -> Any:
        return ddb_client

    monkeypatch.setattr(boto3, "client", mock_client)


def test_get_all_cognito_groups(cognito_client: Any, mock_env_vars: Any) -> None:
    cognito_groups = cognito_sync_handler.get_all_cognito_groups()
    assert cognito_groups == cognito_group


def test_update_group(
    ddb_client_accounts_groups: Any,
    ddb_resource: Any,
    mock_env_vars: Any,
) -> None:
    cognito_sync_handler.update_group(cognito_group)


def test_group_name_to_usernames(cognito_client: Any, mock_env_vars: Any) -> None:
    actual_value = cognito_sync_handler.get_group_member_association_from_cognito(
        cognito_group
    )
    assert actual_value == group_name_to_username


def test_update_group_member_association_in_ddb(
    ddb_client_accounts_group_members: Any, ddb_resource: Any
) -> None:
    cognito_sync_handler.update_group_member_association_in_ddb(group_name_to_username)


def test_get_all_native_cognito_users(cognito_client: Any, mock_env_vars: Any) -> None:
    actual_value = cognito_sync_handler.get_all_native_cognito_users()
    assert actual_value == native_cognito_users


def test_update_users_in_ddb(
    ddb_client_accounts_users: Any, ddb_resource: Any, mock_env_vars: Any
) -> None:
    cognito_sync_handler.update_users_in_ddb(
        native_cognito_users, group_name_to_username
    )


def test_get_gid() -> None:
    uid = cognito_sync_handler.get_gid("a")
    assert uid == 2000200001

    uid = cognito_sync_handler.get_gid("zzzzzz")
    assert uid == 2387620488


def test_get_gid_invalid_group_names(mock_env_vars: Any) -> None:
    with pytest.raises(Exception) as exc_info:
        cognito_sync_handler.get_gid("groupnametoolong")

    assert str(exc_info.value) == "Group name must be 6 letters or less"

    with pytest.raises(Exception) as exc_info:
        cognito_sync_handler.get_gid("A")

    assert (
        str(exc_info.value) == "Group name must consist of lowercase alphabetic letters"
    )
