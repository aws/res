#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
from unittest import TestCase
from unittest.mock import MagicMock

import boto3
import pytest
from moto import mock_aws
from res.constants import ENVIRONMENT_NAME_KEY, ENVIRONMENT_NAME_TAG_KEY

from idea.infrastructure.resources.lambda_functions.custom_resource.delete_target_groups_lambda import (
    handler,
)

TEST_ENV_NAME = "res-test"
DUMMY_URL = "dummy_url"
DUMMY_ARN_1 = "dummy_arn1"
DUMMY_ARN_2 = "dummy_arn2"


@pytest.fixture(scope="class")
def monkeypatch_for_class(request):
    request.cls.monkeypatch = pytest.MonkeyPatch()


@mock_aws
@pytest.mark.usefixtures("monkeypatch_for_class")
class TestDDBDeaultValuesPoplulatorLambda(TestCase):
    def setUp(self) -> None:
        os.environ[ENVIRONMENT_NAME_KEY] = TEST_ENV_NAME
        self.elb_client = boto3.client("elbv2")

    def test_handler_send_cfn_response(self):
        event = {"RequestType": "Delete", "ResponseURL": DUMMY_URL}
        mock_cfn_response_send = MagicMock()
        mock_cfn_response_send.return_value = None
        mock_elb_client = MagicMock()
        mock_paginator = MagicMock()
        mock_paginate = iter(
            [
                {
                    "TargetGroups": [
                        {
                            "TargetGroupName": f"{TEST_ENV_NAME}1",
                            "TargetGroupArn": DUMMY_ARN_1,
                        },
                        {
                            "TargetGroupName": f"{TEST_ENV_NAME}2",
                            "TargetGroupArn": DUMMY_ARN_2,
                        },
                    ]
                }
            ]
        )
        mock_paginator.paginate.return_value = mock_paginate
        mock_elb_client.get_paginator.return_value = mock_paginator
        mock_elb_client.describe_tags.return_value = {
            "TagDescriptions": [
                {
                    "ResourceArn": DUMMY_ARN_1,
                    "Tags": [
                        {
                            "Key": ENVIRONMENT_NAME_TAG_KEY,
                            "Value": TEST_ENV_NAME,
                        }
                    ],
                },
                {
                    "ResourceArn": DUMMY_ARN_2,
                    "Tags": [
                        {
                            "Key": ENVIRONMENT_NAME_TAG_KEY,
                            "Value": "not-matching",
                        }
                    ],
                },
            ]
        }
        self.monkeypatch.setattr(handler, "send_response", mock_cfn_response_send)
        self.monkeypatch.setattr(
            boto3, "client", MagicMock(return_value=mock_elb_client)
        )
        handler.handler(event, {})
        response = handler.CustomResourceResponse(
            Status="SUCCESS",
            Reason="SUCCESS",
            PhysicalResourceId="",
            StackId="",
            RequestId="",
            LogicalResourceId="",
            Data={},
        )

        mock_elb_client.get_paginator.assert_called_once()
        mock_paginator.paginate.assert_called_once()
        mock_elb_client.describe_tags.assert_called_once()
        mock_elb_client.delete_target_group.assert_called_once_with(
            TargetGroupArn=DUMMY_ARN_1
        )
        mock_cfn_response_send.assert_called_once_with(url=DUMMY_URL, response=response)
