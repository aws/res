#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any
from unittest.mock import Mock

import boto3
import pytest

from idea.infrastructure.install.handlers import ecr_images_handler


@pytest.fixture
def expected_status() -> str:
    return ecr_images_handler.CustomResourceResponseStatus.SUCCESS


@pytest.fixture
def mock_urlopen(monkeypatch: pytest.MonkeyPatch) -> Mock:
    mock_urlopen = Mock()
    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    return mock_urlopen


@pytest.fixture
def callback_url() -> str:
    return "https://mock-url"


class Boto3Client(Mock):
    def get_paginator(self, _: str) -> Mock:
        paginator = Mock()
        paginator.paginate.return_value = [{"imageIds": ["test_id"]}]

        return paginator


@pytest.fixture
def boto3_client(
    monkeypatch: pytest.MonkeyPatch,
) -> Mock:
    client = Boto3Client()
    client.start_build.return_value = {"build": {"id": "test_id"}}
    client.batch_get_builds.return_value = {"builds": [{"buildStatus": "SUCCEEDED"}]}
    client.batch_get_builds.return_value = {"builds": [{"buildStatus": "SUCCEEDED"}]}
    client.batch_delete_image.return_value = None

    def mock_client(_: str) -> Boto3Client:
        return client

    monkeypatch.setattr(boto3, "client", mock_client)

    return client


def test_ecr_images_handler_run_build(
    boto3_client: Mock,
    callback_url: str,
    mock_urlopen: Mock,
    expected_status: str,
) -> None:
    event = dict(
        LogicalResourceId="test_logical_resource_id",
        StackId="test_logical_stack_id",
        RequestId="test_logical_request_id",
        RequestType="Create",
        ResourceProperties={
            "ProjectName": "test_project",
        },
        ResponseURL=callback_url,
    )

    ecr_images_handler.handle_request(event, None)
    boto3_client.start_build.assert_called_once_with(projectName="test_project")
    boto3_client.batch_get_builds.assert_called_once_with(ids=["test_id"])

    assert_made_request_matches(
        mock_urlopen=mock_urlopen,
        expected_url=callback_url,
        expected_data=ecr_images_handler.CustomResourceResponse(
            Status=ecr_images_handler.CustomResourceResponseStatus.SUCCESS,
            Reason=ecr_images_handler.CustomResourceResponseStatus.SUCCESS,
            PhysicalResourceId=event["LogicalResourceId"],  # type: ignore
            StackId=event["StackId"],  # type: ignore
            RequestId=event["RequestId"],  # type: ignore
            LogicalResourceId=event["LogicalResourceId"],  # type: ignore
        ),
    )


def test_ecr_images_handler_delete_image(
    boto3_client: Mock,
    callback_url: str,
    mock_urlopen: Mock,
    expected_status: str,
) -> None:
    event = dict(
        LogicalResourceId="test_logical_resource_id",
        StackId="test_logical_stack_id",
        RequestId="test_logical_request_id",
        RequestType="Delete",
        ResourceProperties={
            "ResEcrRepositoryName": "test_repo",
        },
        ResponseURL=callback_url,
    )

    ecr_images_handler.handle_request(event, None)
    boto3_client.batch_delete_image.assert_called_once_with(
        imageIds=["test_id"], repositoryName="test_repo"
    )

    assert_made_request_matches(
        mock_urlopen=mock_urlopen,
        expected_url=callback_url,
        expected_data=ecr_images_handler.CustomResourceResponse(
            Status=ecr_images_handler.CustomResourceResponseStatus.SUCCESS,
            Reason=ecr_images_handler.CustomResourceResponseStatus.SUCCESS,
            PhysicalResourceId=event["LogicalResourceId"],  # type: ignore
            StackId=event["StackId"],  # type: ignore
            RequestId=event["RequestId"],  # type: ignore
            LogicalResourceId=event["LogicalResourceId"],  # type: ignore
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
