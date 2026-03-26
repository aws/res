#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import time
from unittest import TestCase
from unittest.mock import MagicMock

import boto3
import pytest
from moto import mock_aws
from res.constants import ENVIRONMENT_NAME_TAG_KEY, INSTANCE_NODE_TYPE_TAG_KEY

from idea.infrastructure.resources.lambda_functions.custom_resource.deletion_cleanup_resources_lambda import (
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
class TestDeletionCleanupResourcesLambda(TestCase):
    def setUp(self) -> None:
        os.environ["cognito_user_pool_id"] = DUMMY_ARN_1
        self.monkeypatch.setattr(time, "sleep", lambda _: None)
        self.monkeypatch.setattr(handler, "CLUSTER_NAME", TEST_ENV_NAME)

    def tearDown(self):
        self.monkeypatch.undo()

    def test_deletion_handler_send_cfn_response(self):
        event = {"RequestType": "Delete", "ResponseURL": DUMMY_URL}
        mock_cfn_response_send = MagicMock()
        mock_cfn_response_send.return_value = None

        self.monkeypatch.setattr(
            handler,
            "_terminate_ec2_instances",
            MagicMock(return_value=None),
        )
        self.monkeypatch.setattr(
            handler,
            "_delete_vdi_roles",
            MagicMock(return_value=None),
        )
        self.monkeypatch.setattr(handler, "send_response", mock_cfn_response_send)

        handler.clean_up_resources_handler(event, {})
        response = handler.CustomResourceResponse(
            Status="SUCCESS",
            Reason="SUCCESS",
            PhysicalResourceId="",
            StackId="",
            RequestId="",
            LogicalResourceId="",
        )
        mock_cfn_response_send.assert_called_once_with(url=DUMMY_URL, response=response)

    def test_create_handler_send_cfn_response(self):
        event = {"RequestType": "Create", "ResponseURL": DUMMY_URL}
        mock_cfn_response_send = MagicMock()
        mock_cfn_response_send.return_value = None

        self.monkeypatch.setattr(
            handler,
            "_get_lambdas_and_security_groups_to_detach",
            MagicMock(return_value=([], [])),
        )
        self.monkeypatch.setattr(handler, "send_response", mock_cfn_response_send)

        handler.clean_up_resources_handler(event, {})
        response = handler.CustomResourceResponse(
            Status="SUCCESS",
            Reason="SUCCESS",
            PhysicalResourceId="",
            StackId="",
            RequestId="",
            LogicalResourceId="",
            Data={
                handler.SECURITY_GROUP_IDS: "",
            },
        )
        mock_cfn_response_send.assert_called_once_with(url=DUMMY_URL, response=response)

    def test_detach_vpc_from_lambda(self):
        mock_lambda_client = MagicMock()
        self.monkeypatch.setattr(
            boto3, "client", MagicMock(return_value=mock_lambda_client)
        )
        handler._detach_vpc_from_lambda_functions([DUMMY_ARN_1])
        mock_lambda_client.update_function_configuration.assert_called_once_with(
            FunctionName=DUMMY_ARN_1,
            VpcConfig={
                "SubnetIds": [],
                "SecurityGroupIds": [],
            },
        )

    def test_terminate_ec2_instances(self):
        mock_ec2_client = MagicMock()
        self.monkeypatch.setattr(
            boto3, "client", MagicMock(return_value=mock_ec2_client)
        )
        self.monkeypatch.setattr(
            handler,
            "_find_ec2_instances",
            MagicMock(return_value=([DUMMY_ARN_1, DUMMY_ARN_2], [DUMMY_ARN_1])),
        )
        handler._terminate_ec2_instances()
        assert mock_ec2_client.modify_instance_attribute.call_count == 2
        mock_ec2_client.terminate_instances.assert_called_once_with(
            InstanceIds=[DUMMY_ARN_1]
        )

    def test_find_ec2_instances(self):
        mock_ec2_client = MagicMock()
        mock_paginator = MagicMock()
        mock_paginate = iter(
            [
                {
                    "Reservations": [
                        {
                            "Instances": [
                                {
                                    "InstanceId": DUMMY_ARN_1,
                                    "State": {"Name": "running"},
                                    "Tags": [
                                        {
                                            "Key": ENVIRONMENT_NAME_TAG_KEY,
                                            "Value": TEST_ENV_NAME,
                                        },
                                        {
                                            "Key": INSTANCE_NODE_TYPE_TAG_KEY,
                                            "Value": "host",
                                        },
                                    ],
                                }
                            ],
                        }
                    ]
                }
            ]
        )
        mock_paginator.paginate.return_value = mock_paginate
        mock_ec2_client.get_paginator.return_value = mock_paginator
        mock_ec2_client.describe_instance_attribute.return_value = {
            "DisableApiTermination": {"Value": True}
        }
        self.monkeypatch.setattr(
            boto3, "client", MagicMock(return_value=mock_ec2_client)
        )
        terminate_protected, instance_to_delete = handler._find_ec2_instances()
        mock_ec2_client.describe_instance_attribute.assert_called_once()
        assert len(terminate_protected) == 1
        assert len(instance_to_delete) == 1

    def test_remove_cognito_protection(self):
        mock_cognito_client = MagicMock()
        self.monkeypatch.setattr(
            boto3, "client", MagicMock(return_value=mock_cognito_client)
        )
        handler._remove_cognito_userpool_protection()
        mock_cognito_client.update_user_pool.assert_called_once_with(
            UserPoolId=DUMMY_ARN_1,
            DeletionProtection="INACTIVE",
        )

    def test_get_lambdas_and_security_groups_to_detach(self):

        mock_lambda_client = MagicMock()
        mock_paginator = MagicMock()
        mock_paginate = iter(
            [
                {
                    "Functions": [
                        {
                            "VpcConfig": {
                                "SubnetIds": [DUMMY_ARN_1],
                                "SecurityGroupIds": [DUMMY_ARN_1],
                            },
                            "FunctionArn": DUMMY_ARN_1,
                        },
                        {
                            "FunctionArn": DUMMY_ARN_2,
                        },
                    ]
                }
            ]
        )
        mock_paginator.paginate.return_value = mock_paginate
        mock_lambda_client.get_paginator.return_value = mock_paginator
        mock_lambda_client.list_tags.return_value = {
            "Tags": {ENVIRONMENT_NAME_TAG_KEY: TEST_ENV_NAME}
        }
        self.monkeypatch.setattr(
            boto3, "client", MagicMock(return_value=mock_lambda_client)
        )
        lambdas_to_detach, security_group_list = (
            handler._get_lambdas_and_security_groups_to_detach()
        )
        assert lambdas_to_detach == [DUMMY_ARN_1]
        assert security_group_list == [DUMMY_ARN_1]

    def test_get_network_interface_id(self):
        mock_ec2_client = MagicMock()
        mock_paginator = MagicMock()
        mock_paginate = iter(
            [
                {
                    "NetworkInterfaces": [
                        {
                            "NetworkInterfaceId": DUMMY_ARN_1,
                        },
                    ]
                }
            ]
        )
        mock_paginator.paginate.return_value = mock_paginate
        mock_ec2_client.get_paginator.return_value = mock_paginator
        self.monkeypatch.setattr(
            boto3, "client", MagicMock(return_value=mock_ec2_client)
        )
        network_interfaces = handler._get_network_interface_id([DUMMY_ARN_1])
        mock_paginator.paginate.assert_called_once_with(
            Filters=[
                {
                    "Name": "group-id",
                    "Values": [DUMMY_ARN_1],
                },
                {
                    "Name": "interface-type",
                    "Values": ["lambda", "interface"],
                },
            ]
        )
        assert network_interfaces == [DUMMY_ARN_1]
