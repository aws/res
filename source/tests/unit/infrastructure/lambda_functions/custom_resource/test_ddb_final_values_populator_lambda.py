#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
from unittest import TestCase
from unittest.mock import MagicMock, Mock

import boto3
import pytest
from moto import mock_aws
from requests import patch
from res.constants import (  # type: ignore
    ADMIN_ROLE,
    CLUSTER_ADMIN_USERNAME,
    COGNITO_USER_IDP_TYPE,
    DEFAULT_REGION_KEY,
    ENVIRONMENT_NAME_KEY,
)
from res.resources import accounts, cluster_settings
from res.utils import auth_utils

from idea.infrastructure.resources.lambda_functions.custom_resource.ddb_final_values_populator_lambda import (
    handler,
)

TEST_ENV_NAME = "res-test"
DUMMY_URL = "dummy_url"
DUMMY_EMAIL = "dummy_email@example.com"
DUMMY_SETTING = "dummy_setting"
DUMMY_PASSWORD = "dummy_password"
DUMMY_STATUS = "dummy_status"


@pytest.fixture(scope="class")
def monkeypatch_for_class(request):
    request.cls.monkeypatch = pytest.MonkeyPatch()


@mock_aws
@pytest.mark.usefixtures("monkeypatch_for_class")
class TestDDBFinalValuesPoplulatorLambda(TestCase):
    def setUp(self) -> None:
        os.environ[ENVIRONMENT_NAME_KEY] = TEST_ENV_NAME
        os.environ[DEFAULT_REGION_KEY] = "us-east-1"

    def mock_dependencies(self, mock_cfn_response_send, mock_cognito_client):

        self.monkeypatch.setattr(handler, "_send_response", mock_cfn_response_send)

        self.monkeypatch.setattr(
            boto3, "client", MagicMock(return_value=mock_cognito_client)
        )
        self.monkeypatch.setattr(
            cluster_settings, "get_setting", MagicMock(return_value=DUMMY_SETTING)
        )

        self.monkeypatch.setattr(
            auth_utils, "sanitize_email", MagicMock(return_value=DUMMY_EMAIL)
        )

        self.monkeypatch.setattr(
            auth_utils, "generate_password", MagicMock(return_value=DUMMY_PASSWORD)
        )
        self.monkeypatch.setattr(accounts, "get_user", MagicMock(return_value=None))

        self.monkeypatch.setattr(accounts, "create_user", MagicMock(return_value=None))

    def test_handler_send_cfn_response(self):
        event = {"RequestType": "Create", "ResponseURL": DUMMY_URL}
        mock_cfn_response_send = MagicMock()
        mock_cfn_response_send.return_value = None
        mock_cognito_client = MagicMock()
        mock_cognito_client.admin_create_user.return_value = {
            "User": {"UserStatus": "status"}
        }
        self.mock_dependencies(mock_cfn_response_send, mock_cognito_client)
        handler.handler(event, {})
        response = handler.CustomResourceResponse(
            Status="SUCCESS",
            Reason="SUCCESS",
            PhysicalResourceId="",
            StackId="",
            RequestId="",
            LogicalResourceId="",
        )
        mock_cognito_client.admin_create_user.assert_called_once_with(
            **{
                "UserPoolId": DUMMY_SETTING,
                "Username": CLUSTER_ADMIN_USERNAME,
                "TemporaryPassword": DUMMY_PASSWORD,
                "UserAttributes": [
                    {"Name": "email", "Value": DUMMY_EMAIL},
                    {"Name": "email_verified", "Value": str(False)},
                    {"Name": "custom:cluster_name", "Value": TEST_ENV_NAME},
                    {"Name": "custom:aws_region", "Value": "us-east-1"},
                    {
                        "Name": "custom:uid",
                        "Value": str(auth_utils.COGNITO_MIN_ID_INCLUSIVE),
                    },
                ],
                "DesiredDeliveryMediums": ["EMAIL"],
            }
        )
        accounts.create_user.assert_called_once_with(
            {
                "username": CLUSTER_ADMIN_USERNAME,
                "email": DUMMY_EMAIL,
                "uid": auth_utils.COGNITO_MIN_ID_INCLUSIVE,
                "gid": None,
                "additional_groups": [],
                "login_shell": auth_utils.DEFAULT_LOGIN_SHELL,
                "home_dir": os.path.join(
                    auth_utils.USER_HOME_DIR_BASE, CLUSTER_ADMIN_USERNAME
                ),
                "sudo": False,
                "enabled": True,
                "role": ADMIN_ROLE,
                "is_active": True,
                "identity_source": COGNITO_USER_IDP_TYPE,
            }
        )
        mock_cfn_response_send.assert_called_once_with(url=DUMMY_URL, response=response)
