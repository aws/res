import json
import os
from typing import Any
from unittest.mock import MagicMock

import boto3
import pytest

from idea.infrastructure.install import cognito_trigger_workflow_uid_handler
from ideadatamodel import SocaAnyPayload, constants  # type: ignore


@pytest.fixture
def uid() -> int:
    return 1234


@pytest.fixture
def env_vars() -> None:
    os.environ["CUSTOM_UID_ATTRIBUTE"] = "custom:uid"
    os.environ["COGNITO_MIN_ID_INCLUSIVE"] = "1"
    os.environ["COGNITO_MAX_ID_INCLUSIVE"] = "10"
    os.environ["COGNITO_USER_IDP_TYPE"] = constants.COGNITO_USER_IDP_TYPE
    os.environ["CLUSTER_NAME"] = "res-new"


@pytest.fixture
def cognito_client(monkeypatch: pytest.MonkeyPatch, uid: int) -> None:
    paginator = SocaAnyPayload()
    paginator.paginate = MagicMock(
        return_value=[
            {
                "Users": [
                    {
                        "Username": "fakeUser",
                        "Attributes": [
                            {"Name": "email", "Value": "fakeUser@example.com"},
                            {"Name": "email_verified", "Value": "true"},
                            {"Name": "custom:uid", "Value": str(uid)},
                            {
                                "Name": "sub",
                                "Value": "645864a8-50c1-70da-a6e7-a378f634935e",
                            },
                        ],
                        "Enabled": True,
                        "UserStatus": "CONFIRMED",
                    },
                ]
            }
        ]
    )

    cognito_client = SocaAnyPayload()
    cognito_client.get_paginator = MagicMock(return_value=paginator)

    cognito_client.admin_update_user_attributes = MagicMock(return_value={})

    def mock_client(_: str) -> Any:
        return cognito_client

    monkeypatch.setattr(boto3, "client", mock_client)


@pytest.fixture
def ddb_resource(request: Any, monkeypatch: pytest.MonkeyPatch, uid: int) -> None:
    table = SocaAnyPayload()
    table.get_item = MagicMock(
        return_value={
            "Item": [
                {
                    "username": "fakeUser",
                    "uid": uid,
                    "identity_source": "Native user",
                },
            ]
        }
    )
    table.update_item = MagicMock(return_value={})

    ddb_resource = SocaAnyPayload()
    ddb_resource.Table = MagicMock(return_value=table)

    def mock_resource(_: str) -> Any:
        return ddb_resource

    monkeypatch.setattr(boto3, "resource", mock_resource)


def test_get_uid_of_all_users_in_cognito(
    monkeypatch: pytest.MonkeyPatch,
    cognito_client: Any,
    uid: int,
    env_vars: Any,
) -> None:
    response = cognito_trigger_workflow_uid_handler.get_uid_of_all_users_in_cognito(
        "fakeUserPoolId"
    )
    assert response == {uid}


def test_handle_event(
    monkeypatch: pytest.MonkeyPatch,
    cognito_client: Any,
    ddb_resource: Any,
    uid: int,
    env_vars: Any,
) -> None:
    event = {"Records": [{"body": json.dumps({"username": "fakeUser"})}]}
    response = cognito_trigger_workflow_uid_handler.handle_event(event, None)
    assert response == {"batchItemFailures": []}
