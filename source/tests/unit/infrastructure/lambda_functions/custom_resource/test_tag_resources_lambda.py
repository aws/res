#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
from unittest import TestCase
from unittest.mock import MagicMock

import boto3
import pytest
from moto import mock_aws
from res.constants import (
    AWS_TAG_CFN_STACK_NAME,
    ENVIRONMENT_NAME_KEY,
    ENVIRONMENT_NAME_TAG_KEY,
    EVENTBRIDGE_RULE_RESOURCE_TYPE,
    INSTANCE_PROFILE_RESOURCE_TYPE,
    LOAD_BALANCER_RESOURCE_TYPE,
    MANAGED_POLICY_RESOURCE_TYPE,
    OLD_CUSTOM_TAG_KEYS,
    PARENT_STACK_NAME_KEY,
)
from res.resources import cluster_settings

from idea.infrastructure.resources.lambda_functions.custom_resource.tag_resources_lambda import (
    tag_resources_handler,
)

TEST_ENV_NAME = "res-test"
DUMMY_URL = "dummy_url"
DUMMY_ARN_1 = "dummy_arn1"
DUMMY_ARN_2 = "dummy_arn2"
DUMMY_TAG_KEY = "dummy_tag_key"
DUMMY_TAG_VALUE = "dummy_tag_value"
DUMMY_PREFIX = "prefix-"
DUMMY_CUSTOM_TAG_ITEM = f"Key={DUMMY_TAG_KEY},Value={DUMMY_TAG_VALUE}"
DUMMY_CUSTOM_TAG_LIST = [{"Key": DUMMY_TAG_KEY, "Value": DUMMY_TAG_VALUE}]


@pytest.fixture(scope="class")
def monkeypatch_for_class(request):
    request.cls.monkeypatch = pytest.MonkeyPatch()


@mock_aws
@pytest.mark.usefixtures("monkeypatch_for_class")
class TestTagResourcesLambda(TestCase):
    def setUp(self) -> None:
        os.environ[ENVIRONMENT_NAME_KEY] = TEST_ENV_NAME
        os.environ[PARENT_STACK_NAME_KEY] = TEST_ENV_NAME

    def tearDown(self):
        self.monkeypatch.undo()

    def test_handler_send_cfn_response(self):
        event = {
            "RequestType": "Create",
            "ResponseURL": DUMMY_URL,
            "ResourceProperties": {OLD_CUSTOM_TAG_KEYS: DUMMY_TAG_KEY},
        }
        mock_cfn_response_send = MagicMock()
        mock_cfn_response_send.return_value = None

        mock_cfn_client = MagicMock()
        mock_list_paginator = MagicMock()
        mock_list_paginate = iter(
            [
                {
                    "StackSummaries": [
                        {
                            "StackName": DUMMY_ARN_1,
                        },
                    ]
                }
            ]
        )
        mock_list_resources_paginator = MagicMock()
        mock_list_resources_paginate = iter(
            [
                {
                    "StackResourceSummaries": [
                        {
                            "ResourceType": MANAGED_POLICY_RESOURCE_TYPE,
                            "PhysicalResourceId": DUMMY_ARN_1,
                        },
                        {
                            "ResourceType": INSTANCE_PROFILE_RESOURCE_TYPE,
                            "PhysicalResourceId": DUMMY_ARN_2,
                        },
                        {
                            "ResourceType": LOAD_BALANCER_RESOURCE_TYPE,
                            "PhysicalResourceId": DUMMY_ARN_1,
                        },
                        {
                            "ResourceType": EVENTBRIDGE_RULE_RESOURCE_TYPE,
                            "PhysicalResourceId": DUMMY_ARN_2,
                        },
                    ]
                }
            ]
        )

        mock_list_resources_paginator.paginate.return_value = (
            mock_list_resources_paginate
        )
        mock_list_paginator.paginate.return_value = mock_list_paginate
        mock_cfn_client.get_paginator.side_effect = {
            "list_stacks": mock_list_paginator,
            "list_stack_resources": mock_list_resources_paginator,
        }.get
        mock_cfn_client.describe_stacks.return_value = {
            "Stacks": [
                {
                    "Tags": [
                        {
                            "Key": ENVIRONMENT_NAME_TAG_KEY,
                            "Value": TEST_ENV_NAME,
                        }
                    ]
                }
            ]
        }
        self.monkeypatch.setattr(
            boto3, "client", MagicMock(return_value=mock_cfn_client)
        )

        self.monkeypatch.setattr(
            cluster_settings,
            "get_setting",
            MagicMock(
                side_effect=lambda key: {
                    "global-settings.custom_tags": [DUMMY_CUSTOM_TAG_ITEM],
                    "cluster.iam.iam_resource_prefix": DUMMY_PREFIX,
                }.get(key, "")
            ),
        )

        self.monkeypatch.setattr(
            tag_resources_handler,
            "_tag_managed_policies",
            MagicMock(return_value=None),
        )
        self.monkeypatch.setattr(
            tag_resources_handler,
            "_tag_instance_profile",
            MagicMock(return_value=None),
        )
        self.monkeypatch.setattr(
            tag_resources_handler,
            "_tag_load_balancer_listeners",
            MagicMock(return_value=None),
        )
        self.monkeypatch.setattr(
            tag_resources_handler,
            "_tag_eventbridge_rules",
            MagicMock(return_value=None),
        )
        self.monkeypatch.setattr(
            tag_resources_handler,
            "_tag_network_interface",
            MagicMock(return_value=None),
        )
        self.monkeypatch.setattr(
            tag_resources_handler,
            "_tag_launch_templates",
            MagicMock(return_value=None),
        )
        self.monkeypatch.setattr(
            tag_resources_handler, "send_response", mock_cfn_response_send
        )

        tag_resources_handler.handler(event, {})
        response = tag_resources_handler.CustomResourceResponse(
            Status="SUCCESS",
            Reason="SUCCESS",
            PhysicalResourceId="",
            StackId="",
            RequestId="",
            LogicalResourceId="",
            Data={},
        )
        mock_cfn_response_send.assert_called_once_with(url=DUMMY_URL, response=response)
        assert cluster_settings.get_setting.call_count == 2
        mock_cfn_client.describe_stacks.assert_called_once_with(StackName=DUMMY_ARN_1)
        tag_resources_handler._tag_managed_policies.assert_called_once_with(
            DUMMY_CUSTOM_TAG_LIST, [DUMMY_TAG_KEY], [DUMMY_ARN_1]
        )
        tag_resources_handler._tag_instance_profile.assert_called_once_with(
            DUMMY_CUSTOM_TAG_LIST, [DUMMY_TAG_KEY], [DUMMY_ARN_2]
        )
        tag_resources_handler._tag_load_balancer_listeners.assert_called_once_with(
            DUMMY_CUSTOM_TAG_LIST, [DUMMY_TAG_KEY], [DUMMY_ARN_1]
        )
        tag_resources_handler._tag_eventbridge_rules.assert_called_once_with(
            DUMMY_CUSTOM_TAG_LIST, [DUMMY_TAG_KEY], [DUMMY_ARN_2]
        )

    def test_tag_managed_policies(self):
        mock_iam_client = MagicMock()
        mock_paginator = MagicMock()
        mock_paginate = iter(
            [
                {
                    "Policies": [
                        {
                            "Arn": DUMMY_ARN_1,
                        },
                        {
                            "Arn": DUMMY_ARN_2,
                        },
                    ]
                }
            ]
        )
        mock_paginator.paginate.return_value = mock_paginate
        mock_iam_client.get_paginator.return_value = mock_paginator
        self.monkeypatch.setattr(
            boto3, "client", MagicMock(return_value=mock_iam_client)
        )

        tag_resources_handler._tag_managed_policies(
            DUMMY_CUSTOM_TAG_LIST, [DUMMY_TAG_KEY], [DUMMY_ARN_1]
        )
        mock_iam_client.untag_policy.assert_called_once_with(
            PolicyArn=DUMMY_ARN_1, TagKeys=[DUMMY_TAG_KEY]
        )
        mock_iam_client.tag_policy.assert_called_once_with(
            PolicyArn=DUMMY_ARN_1, Tags=DUMMY_CUSTOM_TAG_LIST
        )

    def test_tag_load_balancer_listeners(self):
        mock_elb_client = MagicMock()
        mock_listener_paginator = MagicMock()
        mock_listener_paginate = iter(
            [
                {
                    "Listeners": [
                        {
                            "ListenerArn": DUMMY_ARN_1,
                        },
                    ]
                }
            ]
        )
        mock_listener_paginator.paginate.return_value = mock_listener_paginate

        mock_elb_client.get_paginator.return_value = mock_listener_paginator
        self.monkeypatch.setattr(
            boto3, "client", MagicMock(return_value=mock_elb_client)
        )

        tag_resources_handler._tag_load_balancer_listeners(
            DUMMY_CUSTOM_TAG_LIST, [DUMMY_TAG_KEY], [DUMMY_ARN_1]
        )

        mock_listener_paginator.paginate.assert_called_once_with(
            LoadBalancerArn=DUMMY_ARN_1
        )
        assert mock_elb_client.remove_tags.call_count == 1
        assert mock_elb_client.add_tags.call_count == 1

    def test_tag_network_interface(self):
        mock_ec2_client = MagicMock()

        mock_sg_paginator = MagicMock()
        mock_sg_paginate = iter(
            [
                {
                    "SecurityGroups": [
                        {
                            "GroupName": f"{TEST_ENV_NAME}-sg1",
                            "GroupId": DUMMY_ARN_1,
                            "Tags": [
                                {
                                    "Key": AWS_TAG_CFN_STACK_NAME,
                                    "Value": TEST_ENV_NAME,
                                }
                            ],
                        },
                        {
                            "GroupName": f"{TEST_ENV_NAME}_sg2",
                            "GroupId": DUMMY_ARN_1,
                            "Tags": [
                                {
                                    "Key": ENVIRONMENT_NAME_TAG_KEY,
                                    "Value": TEST_ENV_NAME,
                                }
                            ],
                        },
                        {
                            "GroupName": "not-prefix-sg",
                            "GroupId": DUMMY_ARN_1,
                            "Tags": [
                                {
                                    "Key": ENVIRONMENT_NAME_TAG_KEY,
                                    "Value": TEST_ENV_NAME,
                                }
                            ],
                        },
                        {
                            "GroupName": "invalid-sg",
                            "GroupId": DUMMY_ARN_1,
                            "Tags": [],
                        },
                    ]
                }
            ]
        )
        mock_sg_paginator.paginate.return_value = mock_sg_paginate

        mock_eni_paginator = MagicMock()
        mock_eni_paginate = iter(
            [
                {
                    "NetworkInterfaces": [
                        {"NetworkInterfaceId": DUMMY_ARN_1},
                        {"NetworkInterfaceId": DUMMY_ARN_2},
                    ]
                }
            ]
        )
        mock_eni_paginator.paginate.return_value = mock_eni_paginate

        mock_ec2_client.get_paginator.side_effect = [
            mock_sg_paginator,
            mock_eni_paginator,
        ]
        self.monkeypatch.setattr(
            boto3, "client", MagicMock(return_value=mock_ec2_client)
        )

        tag_resources_handler._tag_network_interface(
            DUMMY_CUSTOM_TAG_LIST, [DUMMY_TAG_KEY], TEST_ENV_NAME, TEST_ENV_NAME
        )

        mock_eni_paginator.paginate.assert_called_once_with(
            Filters=[
                {
                    "Name": "group-id",
                    "Values": [DUMMY_ARN_1] * 3,
                }
            ]
        )

        mock_ec2_client.delete_tags.assert_called_once_with(
            Resources=[DUMMY_ARN_1, DUMMY_ARN_2],
            Tags=[
                {
                    "Key": DUMMY_TAG_KEY,
                }
            ],
        )
        mock_ec2_client.create_tags.assert_called_once_with(
            Resources=[DUMMY_ARN_1, DUMMY_ARN_2], Tags=DUMMY_CUSTOM_TAG_LIST
        )

    def test_update_tags_dcv_ddb(self):
        mock_ddb_client = MagicMock()
        mock_paginator = MagicMock()
        mock_paginate = iter(
            [
                {
                    "TableNames": [
                        f"{TEST_ENV_NAME}.vdc.dcv-broker.{DUMMY_ARN_1}",
                        "invalid-table-name",
                    ]
                }
            ]
        )
        mock_paginator.paginate.return_value = mock_paginate
        mock_ddb_client.get_paginator.return_value = mock_paginator
        self.monkeypatch.setattr(
            boto3, "client", MagicMock(return_value=mock_ddb_client)
        )

        tag_resources_handler._update_tags_dcv_ddb(
            DUMMY_CUSTOM_TAG_LIST, [], TEST_ENV_NAME
        )

        assert mock_ddb_client.untag_resource.call_count == 0
        assert mock_ddb_client.tag_resource.call_count == 1

    def test_update_tags_existing_hosts(self):
        mock_ec2_client = MagicMock()
        mock_iam_client = MagicMock()

        # Create separate paginator mocks
        mock_vdi_paginator = MagicMock()
        mock_vdi_paginator.paginate.return_value = iter(
            [
                {
                    "Reservations": [
                        {
                            "Instances": [
                                {
                                    "InstanceId": DUMMY_ARN_1,
                                    "BlockDeviceMappings": [
                                        {"Ebs": {"VolumeId": DUMMY_ARN_1}}
                                    ],
                                    "NetworkInterfaces": [
                                        {"NetworkInterfaceId": DUMMY_ARN_1}
                                    ],
                                    "Tags": [
                                        {"Key": "res:Project", "Value": DUMMY_TAG_VALUE}
                                    ],
                                }
                            ]
                        }
                    ]
                }
            ]
        )

        mock_infra_paginator = MagicMock()
        mock_infra_paginator.paginate.return_value = iter(
            [
                {
                    "Reservations": [
                        {
                            "Instances": [
                                {
                                    "InstanceId": DUMMY_ARN_2,
                                    "BlockDeviceMappings": [
                                        {"Ebs": {"VolumeId": DUMMY_ARN_2}}
                                    ],
                                    "NetworkInterfaces": [
                                        {"NetworkInterfaceId": DUMMY_ARN_2}
                                    ],
                                }
                            ]
                        }
                    ]
                }
            ]
        )

        # get_paginator returns the paginator, then .paginate() is called on it
        mock_ec2_client.get_paginator.side_effect = [
            mock_vdi_paginator,
            mock_infra_paginator,
        ]

        self.monkeypatch.setattr(
            boto3,
            "client",
            MagicMock(
                side_effect=lambda service: (
                    mock_ec2_client if service == "ec2" else mock_iam_client
                )
            ),
        )
        self.monkeypatch.setattr(
            cluster_settings, "get_setting", lambda x: DUMMY_PREFIX
        )

        tag_resources_handler._update_tags_existing_hosts(
            DUMMY_CUSTOM_TAG_LIST, [DUMMY_TAG_KEY], TEST_ENV_NAME, DUMMY_PREFIX
        )

        mock_ec2_client.delete_tags.assert_called_once_with(
            Resources=[DUMMY_ARN_1, DUMMY_ARN_2] * 3,
            Tags=[
                {
                    "Key": DUMMY_TAG_KEY,
                }
            ],
        )
        mock_ec2_client.create_tags.assert_called_once_with(
            Resources=[DUMMY_ARN_1, DUMMY_ARN_2] * 3, Tags=DUMMY_CUSTOM_TAG_LIST
        )

        mock_iam_client.untag_role.assert_called_once_with(
            RoleName=f"{DUMMY_PREFIX}{TEST_ENV_NAME}-vdi-{DUMMY_TAG_VALUE}",
            TagKeys=[DUMMY_TAG_KEY],
        )
        mock_iam_client.tag_role.assert_called_once_with(
            RoleName=f"{DUMMY_PREFIX}{TEST_ENV_NAME}-vdi-{DUMMY_TAG_VALUE}",
            Tags=DUMMY_CUSTOM_TAG_LIST,
        )
