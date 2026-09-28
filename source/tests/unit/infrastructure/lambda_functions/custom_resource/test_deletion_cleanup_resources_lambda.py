#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import time
from unittest import TestCase
from unittest.mock import MagicMock

import boto3
import botocore.exceptions
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
            "_delete_fleets",
            MagicMock(return_value=None),
        )
        self.monkeypatch.setattr(
            handler,
            "_delete_leftover_launch_templates",
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

    def test_delete_fleets_with_fleet_ids(self):
        mock_ec2_client = MagicMock()
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = iter(
            [
                {
                    "Fleets": [
                        {"FleetId": "fleet-1", "FleetState": "active"},
                        {"FleetId": "fleet-2", "FleetState": "active"},
                    ]
                }
            ]
        )
        mock_ec2_client.get_paginator.return_value = mock_paginator
        mock_ec2_client.delete_fleets.return_value = {
            "SuccessfulFleetDeletions": [
                {"FleetId": "fleet-1"},
                {"FleetId": "fleet-2"},
            ],
            "UnsuccessfulFleetDeletions": [],
        }
        mock_aws_provider = MagicMock()
        mock_aws_provider.ec2.return_value = mock_ec2_client

        self.monkeypatch.setattr(
            handler, "AwsClientProvider", MagicMock(return_value=mock_aws_provider)
        )

        handler._delete_fleets()
        mock_ec2_client.delete_fleets.assert_called_once_with(
            FleetIds=["fleet-1", "fleet-2"], TerminateInstances=True
        )

    def test_delete_fleets_skips_already_terminated(self):
        mock_ec2_client = MagicMock()
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = iter(
            [
                {
                    "Fleets": [
                        {"FleetId": "fleet-1", "FleetState": "active"},
                        {"FleetId": "fleet-2", "FleetState": "deleted_terminating"},
                        {"FleetId": "fleet-3", "FleetState": "deleted_running"},
                        {"FleetId": "fleet-4", "FleetState": "deleted"},
                    ]
                }
            ]
        )
        mock_ec2_client.get_paginator.return_value = mock_paginator
        mock_ec2_client.delete_fleets.return_value = {
            "SuccessfulFleetDeletions": [{"FleetId": "fleet-1"}],
            "UnsuccessfulFleetDeletions": [],
        }
        mock_aws_provider = MagicMock()
        mock_aws_provider.ec2.return_value = mock_ec2_client

        self.monkeypatch.setattr(
            handler, "AwsClientProvider", MagicMock(return_value=mock_aws_provider)
        )

        handler._delete_fleets()
        mock_ec2_client.delete_fleets.assert_called_once_with(
            FleetIds=["fleet-1"], TerminateInstances=True
        )

    def test_delete_fleets_no_fleets_found(self):
        mock_ec2_client = MagicMock()
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = iter([{"Fleets": []}])
        mock_ec2_client.get_paginator.return_value = mock_paginator
        mock_aws_provider = MagicMock()
        mock_aws_provider.ec2.return_value = mock_ec2_client

        self.monkeypatch.setattr(
            handler, "AwsClientProvider", MagicMock(return_value=mock_aws_provider)
        )

        handler._delete_fleets()
        mock_ec2_client.delete_fleets.assert_not_called()

    def test_delete_fleets_raises_on_real_failure(self):
        mock_ec2_client = MagicMock()
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = iter(
            [{"Fleets": [{"FleetId": "fleet-1", "FleetState": "active"}]}]
        )
        mock_ec2_client.get_paginator.return_value = mock_paginator
        mock_ec2_client.delete_fleets.return_value = {
            "SuccessfulFleetDeletions": [],
            "UnsuccessfulFleetDeletions": [
                {"FleetId": "fleet-1", "Error": {"Code": "UnauthorizedOperation"}}
            ],
        }
        mock_aws_provider = MagicMock()
        mock_aws_provider.ec2.return_value = mock_ec2_client

        self.monkeypatch.setattr(
            handler, "AwsClientProvider", MagicMock(return_value=mock_aws_provider)
        )

        with pytest.raises(Exception, match="Failed to delete fleets"):
            handler._delete_fleets()

    def test_delete_fleets_tolerates_already_deleted(self):
        mock_ec2_client = MagicMock()
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = iter(
            [{"Fleets": [{"FleetId": "fleet-1", "FleetState": "active"}]}]
        )
        mock_ec2_client.get_paginator.return_value = mock_paginator
        mock_ec2_client.delete_fleets.return_value = {
            "SuccessfulFleetDeletions": [],
            "UnsuccessfulFleetDeletions": [
                {"FleetId": "fleet-1", "Error": {"Code": "fleetIdDoesNotExist"}}
            ],
        }
        mock_aws_provider = MagicMock()
        mock_aws_provider.ec2.return_value = mock_ec2_client

        self.monkeypatch.setattr(
            handler, "AwsClientProvider", MagicMock(return_value=mock_aws_provider)
        )

        handler._delete_fleets()

    def test_delete_fleets_batches_over_25(self):
        mock_ec2_client = MagicMock()
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = iter(
            [
                {
                    "Fleets": [
                        {"FleetId": f"fleet-{i}", "FleetState": "active"}
                        for i in range(30)
                    ]
                }
            ]
        )
        mock_ec2_client.get_paginator.return_value = mock_paginator
        mock_ec2_client.delete_fleets.return_value = {
            "SuccessfulFleetDeletions": [],
            "UnsuccessfulFleetDeletions": [],
        }
        mock_aws_provider = MagicMock()
        mock_aws_provider.ec2.return_value = mock_ec2_client

        self.monkeypatch.setattr(
            handler, "AwsClientProvider", MagicMock(return_value=mock_aws_provider)
        )

        handler._delete_fleets()
        assert mock_ec2_client.delete_fleets.call_count == 2
        first_call = mock_ec2_client.delete_fleets.call_args_list[0]
        second_call = mock_ec2_client.delete_fleets.call_args_list[1]
        assert len(first_call.kwargs["FleetIds"]) == 25
        assert len(second_call.kwargs["FleetIds"]) == 5

    def test_delete_leftover_launch_templates(self):
        mock_ec2_client = MagicMock()
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = iter(
            [
                {
                    "LaunchTemplates": [
                        {"LaunchTemplateId": "lt-111"},
                        {"LaunchTemplateId": "lt-222"},
                    ]
                }
            ]
        )
        mock_ec2_client.get_paginator.return_value = mock_paginator
        mock_ec2_client.delete_launch_template.return_value = {}
        mock_aws_provider = MagicMock()
        mock_aws_provider.ec2.return_value = mock_ec2_client

        self.monkeypatch.setattr(
            handler, "AwsClientProvider", MagicMock(return_value=mock_aws_provider)
        )

        handler._delete_leftover_launch_templates()
        assert mock_ec2_client.delete_launch_template.call_count == 2
        mock_ec2_client.delete_launch_template.assert_any_call(
            LaunchTemplateId="lt-111"
        )
        mock_ec2_client.delete_launch_template.assert_any_call(
            LaunchTemplateId="lt-222"
        )

    def test_delete_leftover_launch_templates_none_found(self):
        mock_ec2_client = MagicMock()
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = iter([{"LaunchTemplates": []}])
        mock_ec2_client.get_paginator.return_value = mock_paginator
        mock_aws_provider = MagicMock()
        mock_aws_provider.ec2.return_value = mock_ec2_client

        self.monkeypatch.setattr(
            handler, "AwsClientProvider", MagicMock(return_value=mock_aws_provider)
        )

        handler._delete_leftover_launch_templates()
        mock_ec2_client.delete_launch_template.assert_not_called()

    def test_delete_leftover_launch_templates_raises_on_failure(self):
        mock_ec2_client = MagicMock()
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = iter(
            [
                {
                    "LaunchTemplates": [
                        {"LaunchTemplateId": "lt-111"},
                        {"LaunchTemplateId": "lt-222"},
                    ]
                }
            ]
        )
        mock_ec2_client.get_paginator.return_value = mock_paginator
        mock_ec2_client.delete_launch_template.side_effect = [
            {},
            botocore.exceptions.ClientError(
                {
                    "Error": {
                        "Code": "UnauthorizedOperation",
                        "Message": "Access denied",
                    }
                },
                "DeleteLaunchTemplate",
            ),
        ]
        mock_aws_provider = MagicMock()
        mock_aws_provider.ec2.return_value = mock_ec2_client

        self.monkeypatch.setattr(
            handler, "AwsClientProvider", MagicMock(return_value=mock_aws_provider)
        )

        with pytest.raises(Exception, match="Failed to delete launch template lt-222"):
            handler._delete_leftover_launch_templates()

    def test_delete_leftover_launch_templates_tolerates_already_deleted(self):
        mock_ec2_client = MagicMock()
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = iter(
            [
                {
                    "LaunchTemplates": [
                        {"LaunchTemplateId": "lt-111"},
                        {"LaunchTemplateId": "lt-222"},
                    ]
                }
            ]
        )
        mock_ec2_client.get_paginator.return_value = mock_paginator
        mock_ec2_client.delete_launch_template.side_effect = [
            {},
            botocore.exceptions.ClientError(
                {
                    "Error": {
                        "Code": "InvalidLaunchTemplateId.NotFound",
                        "Message": "Launch template not found",
                    }
                },
                "DeleteLaunchTemplate",
            ),
        ]
        mock_aws_provider = MagicMock()
        mock_aws_provider.ec2.return_value = mock_ec2_client

        self.monkeypatch.setattr(
            handler, "AwsClientProvider", MagicMock(return_value=mock_aws_provider)
        )

        handler._delete_leftover_launch_templates()
        assert mock_ec2_client.delete_launch_template.call_count == 2
