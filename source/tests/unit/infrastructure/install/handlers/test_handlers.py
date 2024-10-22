#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional
from unittest.mock import Mock

import boto3
import botocore.exceptions
import pytest

from idea.infrastructure.install.handlers import installer_handlers


@pytest.fixture(params=(None, "error"), ids=("success", "error"))
def error(request: pytest.FixtureRequest) -> Optional[str]:
    value = getattr(request, "param")
    if value is None:
        return None
    return str(value)


@pytest.fixture
def sfn_arn() -> str:
    return "mock-arn"


@pytest.fixture
def sfn_client(
    monkeypatch: pytest.MonkeyPatch, sfn_arn: str, error: Optional[str]
) -> Mock:
    client = Mock()
    if error is not None:
        client.start_execution.side_effect = botocore.exceptions.ClientError(
            operation_name=error,
            error_response={},
        )

    def mock_client(_: str) -> Any:
        return client

    monkeypatch.setattr(boto3, "client", mock_client)
    monkeypatch.setenv(installer_handlers.EnvKeys.SFN_ARN, sfn_arn)

    return client


@pytest.fixture
def expected_status(error: Optional[str]) -> str:
    if error is not None:
        return installer_handlers.CustomResourceResponseStatus.FAILED
    return installer_handlers.CustomResourceResponseStatus.SUCCESS


@pytest.fixture
def expected_reason(error: Optional[str]) -> str:
    if error is not None:
        return (
            f"An error occurred (Unknown) when calling the {error} operation: Unknown"
        )
    return installer_handlers.CustomResourceResponseStatus.SUCCESS


@pytest.fixture
def mock_urlopen(monkeypatch: pytest.MonkeyPatch, error: Optional[str]) -> Mock:
    mock_urlopen = Mock()
    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    return mock_urlopen


def test_handle_custom_resource_lifecycle_event(
    mock_urlopen: Mock,
    sfn_client: Mock,
    sfn_arn: str,
    error: Optional[str],
    expected_status: str,
    expected_reason: str,
    callback_url: str,
) -> None:
    event = dict(
        LogicalResourceId="test_logical_resource_id",
        StackId="test_logical_stack_id",
        RequestId="test_logical_request_id",
        ResponseURL=callback_url,
    )

    installer_handlers.handle_custom_resource_lifecycle_event(event, None)

    sfn_client.start_execution.assert_called_once_with(
        stateMachineArn=sfn_arn, input=json.dumps(event)
    )

    assert_made_request_matches(
        mock_urlopen=mock_urlopen,
        expected_url=event["ResponseURL"],
        expected_data=installer_handlers.CustomResourceResponse(
            Status=expected_status,
            Reason=expected_reason,
            PhysicalResourceId=event["LogicalResourceId"],
            StackId=event["StackId"],
            RequestId=event["RequestId"],
            LogicalResourceId=event["LogicalResourceId"],
        ),
    )


def test_handle_custom_resource_delete_lifecycle_event(
    mock_urlopen: Mock,
    sfn_client: Mock,
    sfn_arn: str,
    error: Optional[str],
    expected_status: str,
    expected_reason: str,
    callback_url: str,
) -> None:
    event = dict(
        LogicalResourceId="test_logical_resource_id",
        StackId="test_logical_stack_id",
        RequestId="test_logical_request_id",
        RequestType=installer_handlers.RequestType.DELETE,
        ResponseURL=callback_url,
    )

    installer_handlers.handle_custom_resource_lifecycle_event(event, None)

    sfn_client.start_execution.assert_called_once_with(
        stateMachineArn=sfn_arn, input=json.dumps(event)
    )

    if error is not None:
        assert_made_request_matches(
            mock_urlopen=mock_urlopen,
            expected_url=event["ResponseURL"],
            expected_data=installer_handlers.CustomResourceResponse(
                Status=expected_status,
                Reason=expected_reason,
                PhysicalResourceId=event["LogicalResourceId"],
                StackId=event["StackId"],
                RequestId=event["RequestId"],
                LogicalResourceId=event["LogicalResourceId"],
            ),
        )
    else:
        mock_urlopen.assert_not_called()


@pytest.fixture
def callback_url() -> str:
    return "https://mock-url"


@pytest.fixture
def wait_condition_response_event(
    error: Optional[str], callback_url: str
) -> Dict[str, Any]:
    event: Dict[str, Any] = dict(
        ResourceProperties={installer_handlers.EnvKeys.CALLBACK_URL: callback_url},
    )

    if error is not None:
        event[installer_handlers.EnvKeys.ERROR] = error

    return event


@pytest.fixture
def wait_condition_expected_status(error: Optional[str]) -> str:
    if error is not None:
        return installer_handlers.WaitConditionResponseStatus.FAILURE
    return installer_handlers.WaitConditionResponseStatus.SUCCESS


@pytest.fixture
def wait_condition_expected_reason(error: Optional[str]) -> str:
    if error is not None:
        return json.dumps(error)
    return installer_handlers.WaitConditionResponseStatus.SUCCESS


def test_send_wait_condition_response(
    mock_urlopen: Mock,
    error: Optional[str],
    wait_condition_expected_status: str,
    wait_condition_expected_reason: str,
    wait_condition_response_event: dict[str, Any],
    callback_url: str,
) -> None:
    installer_handlers.send_wait_condition_response(wait_condition_response_event, None)

    assert_made_request_matches(
        mock_urlopen=mock_urlopen,
        expected_url=callback_url,
        expected_data=installer_handlers.WaitConditionResponse(
            Status=wait_condition_expected_status,
            Reason=wait_condition_expected_reason,
            Data="",
            UniqueId="will be replaced",
        ),
        ignore_unique_id=True,
    )


def test_send_wait_condition_delete_response(
    mock_urlopen: Mock,
    error: Optional[str],
    wait_condition_expected_status: str,
    wait_condition_expected_reason: str,
    wait_condition_response_event: dict[str, Any],
    callback_url: str,
    expected_status: str,
) -> None:
    event = dict(
        RequestType=installer_handlers.RequestType.DELETE,
        LogicalResourceId="foo",
        StackId="bar",
        RequestId="foobar",
        ResponseURL=f"{callback_url}/delete",
        **wait_condition_response_event,
    )

    installer_handlers.send_wait_condition_response(event, None)

    assert_made_request_matches(
        mock_urlopen=mock_urlopen,
        expected_url=event["ResponseURL"],
        expected_data=installer_handlers.CustomResourceResponse(
            Status=expected_status,
            Reason=wait_condition_expected_reason,
            PhysicalResourceId=event["LogicalResourceId"],
            StackId=event["StackId"],
            RequestId=event["RequestId"],
            LogicalResourceId=event["LogicalResourceId"],
        ),
    )


def assert_made_request_matches(
    mock_urlopen: Mock,
    expected_url: str,
    expected_data: Any,
    ignore_unique_id: bool = False,
) -> None:
    mock_urlopen.assert_called_once()

    _, args, _ = mock_urlopen.mock_calls[0]
    made_request = args[0]

    assert isinstance(made_request, urllib.request.Request)
    assert made_request.method == "PUT"
    assert made_request.full_url == expected_url

    assert isinstance(made_request.data, bytes)
    made_request_data = json.loads(made_request.data)

    if ignore_unique_id:
        expected_data["UniqueId"] = made_request_data["UniqueId"]

    assert made_request_data == expected_data
