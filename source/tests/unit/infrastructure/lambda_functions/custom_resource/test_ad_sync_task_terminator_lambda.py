#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from unittest import TestCase
from unittest.mock import MagicMock

import pytest
from moto import mock_aws

from idea.infrastructure.resources.lambda_functions.custom_resource.ad_sync_task_terminator_lambda import (
    handler,
)

DUMMY_URL = "dummy_url"


@pytest.fixture(scope="class")
def monkeypatch_for_class(request):
    request.cls.monkeypatch = pytest.MonkeyPatch()


@mock_aws
@pytest.mark.usefixtures("monkeypatch_for_class")
class TestADSyncTaskTerminatorLambda(TestCase):
    def mock_dependencies(self, mock_cfn_response_send, mock_terminate_ad_sync):
        self.monkeypatch.setattr(handler, "_send_response", mock_cfn_response_send)
        self.monkeypatch.setattr(handler, "_terminate_ad_sync", mock_terminate_ad_sync)

    def test_handler_send_cfn_response(self):
        event = {"RequestType": "Delete", "ResponseURL": DUMMY_URL}
        mock_cfn_response_send = MagicMock()
        mock_terminate_ad_sync = MagicMock()
        mock_cfn_response_send.return_value = None
        mock_terminate_ad_sync.return_value = None

        self.mock_dependencies(mock_cfn_response_send, mock_terminate_ad_sync)

        handler.handler(event, {})
        response = handler.CustomResourceResponse(
            Status="SUCCESS",
            Reason="SUCCESS",
            PhysicalResourceId="",
            StackId="",
            RequestId="",
            LogicalResourceId="",
        )

        mock_terminate_ad_sync.assert_called_once()
        mock_cfn_response_send.assert_called_once_with(url=DUMMY_URL, response=response)
