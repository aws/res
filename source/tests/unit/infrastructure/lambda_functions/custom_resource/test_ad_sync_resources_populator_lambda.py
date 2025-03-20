#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from unittest import TestCase
from unittest.mock import MagicMock

import pytest
from moto import mock_aws

from idea.infrastructure.resources.lambda_functions.custom_resource.ad_sync_resources_populator_lambda import (
    ad_sync_resources_populator_handler,
)

DUMMY_URL = "dummy_url"


@pytest.fixture(scope="class")
def monkeypatch_for_class(request):
    request.cls.monkeypatch = pytest.MonkeyPatch()


@mock_aws
@pytest.mark.usefixtures("monkeypatch_for_class")
class TestADSyncResourcesPopulatorLambda(TestCase):
    def mock_dependencies(self, mock_cfn_response_send, mock_create_settings):
        self.monkeypatch.setattr(
            ad_sync_resources_populator_handler,
            "_send_response",
            mock_cfn_response_send,
        )
        self.monkeypatch.setattr(
            "res.resources.cluster_settings.create_settings", mock_create_settings
        )

    def test_handler_send_cfn_response(self):
        event = {"RequestType": "Create", "ResponseURL": DUMMY_URL}
        mock_cfn_response_send = MagicMock()
        mock_create_settings = MagicMock()
        mock_cfn_response_send.return_value = None
        mock_create_settings.return_value = ([], [])

        self.mock_dependencies(mock_cfn_response_send, mock_create_settings)

        ad_sync_resources_populator_handler.handler(event, {})
        response = ad_sync_resources_populator_handler.CustomResourceResponse(
            Status="SUCCESS",
            Reason="SUCCESS",
            PhysicalResourceId="",
            StackId="",
            RequestId="",
            LogicalResourceId="",
        )

        mock_create_settings.assert_called_once()
        mock_cfn_response_send.assert_called_once_with(url=DUMMY_URL, response=response)
