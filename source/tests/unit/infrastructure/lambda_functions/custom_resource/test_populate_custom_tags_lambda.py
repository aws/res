#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
from unittest import TestCase
from unittest.mock import MagicMock

import boto3
import pytest
from moto import mock_aws
from res.constants import ENVIRONMENT_NAME_KEY
from res.resources import cluster_settings

from idea.infrastructure.resources.lambda_functions.custom_resource.populate_custom_tags_lambda import (
    populate_custom_tags_handler,
)

TEST_ENV_NAME = "res-test"
DUMMY_URL = "dummy_url"
DUMMY_STACK_ID = "dummy_stack_id"
DUMMY_TAG_KEY = "dummy_tag_key"
DUMMY_TAG_VALUE = "dummy_tag_value"


@pytest.fixture(scope="class")
def monkeypatch_for_class(request):
    request.cls.monkeypatch = pytest.MonkeyPatch()


@mock_aws
@pytest.mark.usefixtures("monkeypatch_for_class")
class TestPopulateCustomTagsLambda(TestCase):
    def setUp(self) -> None:
        os.environ[ENVIRONMENT_NAME_KEY] = TEST_ENV_NAME

    def test_handler_send_cfn_response(self):
        event = {
            "RequestType": "Create",
            "ResponseURL": DUMMY_URL,
            "StackId": DUMMY_STACK_ID,
        }
        mock_cfn_response_send = MagicMock()
        mock_cfn_response_send.return_value = None

        self.monkeypatch.setattr(
            cluster_settings, "update_setting", MagicMock(return_value=None)
        )

        mock_cfn_client = MagicMock()
        self.monkeypatch.setattr(
            boto3, "client", MagicMock(return_value=mock_cfn_client)
        )
        mock_cfn_client.describe_stacks.return_value = {
            "Stacks": [
                {
                    "StackId": DUMMY_STACK_ID,
                    "Tags": [{"Key": DUMMY_TAG_KEY, "Value": DUMMY_TAG_VALUE}],
                }
            ]
        }

        self.monkeypatch.setattr(
            populate_custom_tags_handler, "send_response", mock_cfn_response_send
        )

        populate_custom_tags_handler.handler(event, {})
        response = populate_custom_tags_handler.CustomResourceResponse(
            Status="SUCCESS",
            Reason="SUCCESS",
            PhysicalResourceId="",
            StackId=DUMMY_STACK_ID,
            RequestId="",
            LogicalResourceId="",
            Data={},
        )
        mock_cfn_response_send.assert_called_once_with(url=DUMMY_URL, response=response)
        mock_cfn_client.describe_stacks.assert_called_once_with(
            StackName=DUMMY_STACK_ID
        )
        cluster_settings.update_setting.assert_called_once_with(
            "global-settings.custom_tags",
            [f"Key={DUMMY_TAG_KEY},Value={DUMMY_TAG_VALUE}"],
        )
