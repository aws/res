#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
from unittest import TestCase
from unittest.mock import ANY, MagicMock

import boto3
import pytest
from moto import mock_aws
from requests import patch
from res.constants import ENVIRONMENT_NAME_KEY
from res.resources import email_templates, permission_profiles, software_stacks

from idea.infrastructure.resources.lambda_functions.custom_resource.ddb_default_values_populator_lambda import (
    handler,
)

TEST_ENV_NAME = "res-test"
DUMMY_URL = "dummy_url"
DUMMY_PERMISSION_PROFILE = {"profile_id": "dummy_id", "title": "dummy title"}
DUMMY_SOFTWARE_STACK = {
    "base_os": "dummy_base_os",
    "stack_id": "dummy_id",
    "ami_id": "dummy_ami_id",
}
DUMMY_EMAIL_TEMPLATE = {
    email_templates.EMAIL_TEMPLATE_DB_NAME_KEY: "dummy_name",
    email_templates.EMAIL_TEMPLATE_DB_TEMPLATE_TYPE_KEY: "dummy_type",
}


@pytest.fixture(scope="class")
def monkeypatch_for_class(request):
    request.cls.monkeypatch = pytest.MonkeyPatch()


@mock_aws
@pytest.mark.usefixtures("monkeypatch_for_class")
class TestDDBDeaultValuesPoplulatorLambda(TestCase):
    def setUp(self) -> None:
        os.environ[ENVIRONMENT_NAME_KEY] = TEST_ENV_NAME
        os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
        self.dynamodb_client = boto3.client("dynamodb")

    def test_handler_send_cfn_response(self):
        event = {"RequestType": "Create", "ResponseURL": DUMMY_URL}
        mock_cfn_response_send = MagicMock()
        mock_cfn_response_send.return_value = None
        self.monkeypatch.setattr(handler, "_send_response", mock_cfn_response_send)
        self.monkeypatch.setattr(
            permission_profiles,
            "is_permission_profiles_table_empty",
            MagicMock(return_value=True),
        )
        self.monkeypatch.setattr(
            handler,
            "_load_base_permission_profiles",
            MagicMock(return_value=[DUMMY_PERMISSION_PROFILE]),
        )
        self.monkeypatch.setattr(
            permission_profiles,
            "create_permission_profile",
            MagicMock(return_value=None),
        )

        self.monkeypatch.setattr(
            software_stacks,
            "is_software_stacks_table_empty",
            MagicMock(return_value=True),
        )
        self.monkeypatch.setattr(
            handler,
            "_load_base_software_stacks",
            MagicMock(return_value=[DUMMY_SOFTWARE_STACK]),
        )
        self.monkeypatch.setattr(
            software_stacks,
            "create_software_stack",
            MagicMock(return_value=None),
        )
        mock_initialize_settings = MagicMock()
        mock_initialize_settings.return_value = None
        self.monkeypatch.setattr(
            handler, "_initialize_modules_cluster_settings", mock_initialize_settings
        )

        mock_initialize_dynamic_settings = MagicMock()
        mock_initialize_settings.return_value = None
        self.monkeypatch.setattr(
            handler, "_initialize_dynamic_settings", mock_initialize_dynamic_settings
        )
        self.monkeypatch.setattr(
            email_templates,
            "is_email_templates_table_empty",
            MagicMock(return_value=True),
        )
        self.monkeypatch.setattr(
            handler,
            "_load_base_email_templates",
            MagicMock(return_value=[DUMMY_EMAIL_TEMPLATE]),
        )
        self.monkeypatch.setattr(
            email_templates, "create_email_template", MagicMock(return_value=None)
        )

        handler.handler(event, {})
        response = handler.CustomResourceResponse(
            Status="SUCCESS",
            Reason="SUCCESS",
            PhysicalResourceId="",
            StackId="",
            RequestId="",
            LogicalResourceId="",
            Data={"elb_principal_type": ANY, "elb_principal_value": ANY},
        )
        permission_profiles.create_permission_profile.assert_called_once_with(
            DUMMY_PERMISSION_PROFILE
        )
        software_stacks.create_software_stack.assert_called_once_with(
            DUMMY_SOFTWARE_STACK
        )
        email_templates.create_email_template.assert_called_once_with(
            DUMMY_EMAIL_TEMPLATE
        )
        mock_cfn_response_send.assert_called_once_with(url=DUMMY_URL, response=response)
