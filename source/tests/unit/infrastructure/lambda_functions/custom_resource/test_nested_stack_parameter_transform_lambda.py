#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
from unittest import TestCase
from unittest.mock import MagicMock

import boto3
import pytest
from moto import mock_aws
from res.resources import cluster_settings

from idea.infrastructure.resources.lambda_functions.custom_resource.parameter_list_to_string_transform_lambda import (
    handler,
)

TEST_ENV_NAME = "res-test"
DUMMY_URL = "dummy_url"
DUMMY_SUBNETS = "dummy_subnets"
DUMMY_TAG_KEY = "dummy_tag_key"
DUMMY_TAG_VALUE = "dummy_tag_value"
DUMMY_CUSTOM_TAG_ITEM = f"Key={DUMMY_TAG_KEY},Value={DUMMY_TAG_VALUE}"


@pytest.fixture(scope="class")
def monkeypatch_for_class(request):
    request.cls.monkeypatch = pytest.MonkeyPatch()


@mock_aws
@pytest.mark.usefixtures("monkeypatch_for_class")
class TestDDBDeaultValuesPoplulatorLambda(TestCase):
    def setUp(self) -> None:
        os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
        os.environ[handler.LB_SUBNETS] = DUMMY_SUBNETS
        os.environ[handler.INFRA_SUBNETS] = DUMMY_SUBNETS
        os.environ[handler.VDI_SUBNETS] = DUMMY_SUBNETS
        self.dynamodb_client = boto3.client("dynamodb")

    def test_handler_send_cfn_response(self):
        event = {"RequestType": "Create", "ResponseURL": DUMMY_URL}
        mock_cfn_response_send = MagicMock()
        mock_cfn_response_send.return_value = None
        self.monkeypatch.setattr(handler, "send_response", mock_cfn_response_send)
        handler.handler(event, {})
        response = handler.CustomResourceResponse(
            Status="SUCCESS",
            Reason="SUCCESS",
            PhysicalResourceId="",
            StackId="",
            RequestId="",
            LogicalResourceId="",
            Data={
                handler.LB_SUBNETS: DUMMY_SUBNETS,
                handler.INFRA_SUBNETS: DUMMY_SUBNETS,
                handler.VDI_SUBNETS: DUMMY_SUBNETS,
                handler.OLD_CUSTOM_TAG_KEYS: "",
            },
        )
        mock_cfn_response_send.assert_called_once_with(url=DUMMY_URL, response=response)

    def test_handler_update_send_cfn_response(self):
        event = {"RequestType": "Update", "ResponseURL": DUMMY_URL}
        mock_cfn_response_send = MagicMock()
        mock_cfn_response_send.return_value = None
        self.monkeypatch.setattr(
            cluster_settings,
            "get_setting",
            MagicMock(return_value=[DUMMY_CUSTOM_TAG_ITEM]),
        )
        self.monkeypatch.setattr(handler, "send_response", mock_cfn_response_send)
        handler.handler(event, {})
        response = handler.CustomResourceResponse(
            Status="SUCCESS",
            Reason="SUCCESS",
            PhysicalResourceId="",
            StackId="",
            RequestId="",
            LogicalResourceId="",
            Data={
                handler.LB_SUBNETS: DUMMY_SUBNETS,
                handler.INFRA_SUBNETS: DUMMY_SUBNETS,
                handler.VDI_SUBNETS: DUMMY_SUBNETS,
                handler.OLD_CUSTOM_TAG_KEYS: DUMMY_TAG_KEY,
            },
        )
        mock_cfn_response_send.assert_called_once_with(url=DUMMY_URL, response=response)
