#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
from unittest import TestCase
from unittest.mock import MagicMock

import boto3
import pytest
from moto import mock_aws
from requests import patch

from idea.infrastructure.resources.lambda_functions.custom_resource.parameter_list_to_string_transform_lambda import (
    handler,
)

TEST_ENV_NAME = "res-test"
DUMMY_URL = "dummy_url"
DUMMY_SUBNETS = "dummy_subnets"


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
        self.monkeypatch.setattr(handler, "_send_response", mock_cfn_response_send)
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
            },
        )
        mock_cfn_response_send.assert_called_once_with(url=DUMMY_URL, response=response)
