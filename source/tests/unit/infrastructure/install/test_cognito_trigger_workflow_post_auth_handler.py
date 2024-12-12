import os
from typing import Any
from unittest.mock import MagicMock

import boto3
import pytest

from idea.infrastructure.install import cognito_trigger_workflow_post_auth_handler
from ideadatamodel import SocaAnyPayload, constants  # type: ignore


@pytest.fixture
def env_vars() -> None:
    os.environ["COGNITO_USER_IDP_TYPE"] = constants.COGNITO_USER_IDP_TYPE
    os.environ["CLUSTER_NAME"] = "res-new"
    os.environ["QUEUE_URL"] = "fakeSQSQueueURL"


@pytest.fixture
def sqs_client(monkeypatch: pytest.MonkeyPatch) -> None:

    client = SocaAnyPayload()
    client.send_message = MagicMock(return_value={})

    def mock_client(_: str) -> Any:
        return client

    monkeypatch.setattr(boto3, "client", mock_client)


@pytest.fixture
def ddb_resource(request: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    table = SocaAnyPayload()
    table.get_item = MagicMock(
        return_value={
            "Item": {
                "username": "fakeUser",
                "identity_source": constants.COGNITO_USER_IDP_TYPE,
            },
        }
    )
    table.update_item = MagicMock(return_value={})

    ddb_resource = SocaAnyPayload()
    ddb_resource.Table = MagicMock(return_value=table)

    def mock_resource(_: str) -> Any:
        return ddb_resource

    monkeypatch.setattr(boto3, "resource", mock_resource)


def test_user_has_uid_in_ddb(
    monkeypatch: pytest.MonkeyPatch,
    env_vars: Any,
    ddb_resource: Any,
) -> None:
    response = cognito_trigger_workflow_post_auth_handler.user_has_uid_in_ddb(
        "fakeUserPoolId"
    )
    assert not response


def test_handle_event(
    monkeypatch: pytest.MonkeyPatch,
    env_vars: Any,
    sqs_client: Any,
    ddb_resource: Any,
) -> None:

    event = {
        "userPoolId": "fakeUserPoolId",
        "userName": "fakeUser",
        "request": {"userAttributes": {"cognito:user_status": "CONFIRMED"}},
    }
    response = cognito_trigger_workflow_post_auth_handler.handle_event(event, None)
    assert response == event
