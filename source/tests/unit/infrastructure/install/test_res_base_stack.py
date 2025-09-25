# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from typing import Any, Dict, List

import pytest
from aws_cdk.assertions import Match, Template

from idea.infrastructure.install.constants import RES_COMMON_LAMBDA_RUNTIME
from idea.infrastructure.install.parameters.common import CommonKey
from idea.infrastructure.install.stacks.res_base_stack import ResBaseStack
from tests.unit.infrastructure.install import util


@pytest.fixture
def cluster_manager_tags(res_base_stack: ResBaseStack) -> List[Dict[str, Any]]:
    return [
        {
            "Key": "res:BackupPlan",
            "Value": {
                "Fn::Join": [
                    "",
                    [
                        res_base_stack.nested_stack.resolve(
                            res_base_stack.cluster_name
                        ),
                        "-cluster",
                    ],
                ]
            },
        },
        {
            "Key": "res:EnvironmentName",
            "Value": res_base_stack.nested_stack.resolve(res_base_stack.cluster_name),
        },
        {"Key": "res:ModuleId", "Value": "cluster-manager"},
        {"Key": "res:ModuleName", "Value": "cluster-manager"},
    ]


@pytest.fixture
def vdc_tags(res_base_stack: ResBaseStack) -> List[Dict[str, Any]]:
    return [
        {
            "Key": "res:BackupPlan",
            "Value": {
                "Fn::Join": [
                    "",
                    [
                        res_base_stack.nested_stack.resolve(
                            res_base_stack.cluster_name
                        ),
                        "-cluster",
                    ],
                ]
            },
        },
        {
            "Key": "res:EnvironmentName",
            "Value": res_base_stack.nested_stack.resolve(res_base_stack.cluster_name),
        },
        {"Key": "res:ModuleId", "Value": "vdc"},
        {"Key": "res:ModuleName", "Value": "virtual-desktop-controller"},
    ]


DB_CFN_TYPE = "AWS::DynamoDB::Table"
KINESIS_CFN_TYPE = "AWS::Kinesis::Stream"
LAMBDA_FUNCTION_CFN_TYPE = "AWS::Lambda::Function"
LAMBDA_EVENT_MAPPING_CFN_TYPE = "AWS::Lambda::EventSourceMapping"
IAM_ROLE_CFN_TYPE = "AWS::IAM::Role"
IAM_ROLE_POLICY_CFN_TYPE = "AWS::IAM::Policy"


def test_stack_description(res_base_template: Template) -> None:
    res_base_template.template_matches({"Description": "Nested RES Base Stack"})


def test_project_table_creation(
    res_base_stack: ResBaseStack,
    res_base_template: Template,
    cluster_manager_tags: List[Dict[str, Any]],
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        res_base_stack.nested_stack,
        res_base_template,
        resources=["projects-table"],
        cfn_type=DB_CFN_TYPE,
        props={
            "Properties": {
                "KeySchema": [{"AttributeName": "project_id", "KeyType": "HASH"}],
                "AttributeDefinitions": [
                    {"AttributeName": "project_id", "AttributeType": "S"},
                    {"AttributeName": "name", "AttributeType": "S"},
                ],
                "BillingMode": "PAY_PER_REQUEST",
                "Tags": cluster_manager_tags,
                "GlobalSecondaryIndexes": [
                    {
                        "IndexName": "project-name-index",
                        "KeySchema": [{"AttributeName": "name", "KeyType": "HASH"}],
                        "Projection": {"ProjectionType": "ALL"},
                    }
                ],
            },
        },
    )


def test_user_table_creation(
    res_base_stack: ResBaseStack,
    res_base_template: Template,
    cluster_manager_tags: List[Dict[str, Any]],
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        res_base_stack.nested_stack,
        res_base_template,
        resources=["accounts-users-table"],
        cfn_type=DB_CFN_TYPE,
        props={
            "Properties": {
                "KeySchema": [{"AttributeName": "username", "KeyType": "HASH"}],
                "AttributeDefinitions": [
                    {"AttributeName": "username", "AttributeType": "S"},
                    {"AttributeName": "role", "AttributeType": "S"},
                    {"AttributeName": "email", "AttributeType": "S"},
                ],
                "Tags": cluster_manager_tags,
                "GlobalSecondaryIndexes": [
                    {
                        "IndexName": "role-index",
                        "KeySchema": [{"AttributeName": "role", "KeyType": "HASH"}],
                        "Projection": {
                            "ProjectionType": "INCLUDE",
                            "NonKeyAttributes": ["additional_groups", "username"],
                        },
                    },
                    {
                        "IndexName": "email-index",
                        "KeySchema": [{"AttributeName": "email", "KeyType": "HASH"}],
                        "Projection": {
                            "ProjectionType": "INCLUDE",
                            "NonKeyAttributes": [
                                "role",
                                "username",
                                "is_active",
                                "enabled",
                                "identity_source",
                            ],
                        },
                    },
                ],
            },
        },
    )


def test_group_table_creation(
    res_base_stack: ResBaseStack,
    res_base_template: Template,
    cluster_manager_tags: List[Dict[str, Any]],
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        res_base_stack.nested_stack,
        res_base_template,
        resources=["accounts-groups-table"],
        cfn_type=DB_CFN_TYPE,
        props={
            "Properties": {
                "KeySchema": [{"AttributeName": "group_name", "KeyType": "HASH"}],
                "AttributeDefinitions": [
                    {"AttributeName": "group_name", "AttributeType": "S"}
                ],
                "Tags": cluster_manager_tags,
            },
        },
    )


def test_group_member_table_creation(
    res_base_stack: ResBaseStack,
    res_base_template: Template,
    cluster_manager_tags: List[Dict[str, Any]],
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        res_base_stack.nested_stack,
        res_base_template,
        resources=["accounts-group-members-table"],
        cfn_type=DB_CFN_TYPE,
        props={
            "Properties": {
                "KeySchema": [
                    {"AttributeName": "group_name", "KeyType": "HASH"},
                    {"AttributeName": "username", "KeyType": "RANGE"},
                ],
                "AttributeDefinitions": [
                    {"AttributeName": "group_name", "AttributeType": "S"},
                    {"AttributeName": "username", "AttributeType": "S"},
                ],
                "Tags": cluster_manager_tags,
            },
        },
    )


def test_sso_state_table_creation(
    res_base_stack: ResBaseStack,
    res_base_template: Template,
    cluster_manager_tags: List[Dict[str, Any]],
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        res_base_stack.nested_stack,
        res_base_template,
        resources=["accounts-sso-state-table"],
        cfn_type=DB_CFN_TYPE,
        props={
            "Properties": {
                "KeySchema": [{"AttributeName": "state", "KeyType": "HASH"}],
                "AttributeDefinitions": [
                    {"AttributeName": "state", "AttributeType": "S"}
                ],
                "Tags": cluster_manager_tags,
                "TimeToLiveSpecification": {"AttributeName": "ttl", "Enabled": True},
            },
        },
    )


def test_role_assignment_table_creation(
    res_base_stack: ResBaseStack,
    res_base_template: Template,
    cluster_manager_tags: List[Dict[str, Any]],
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        res_base_stack.nested_stack,
        res_base_template,
        resources=["authz-role-assignments-table"],
        cfn_type=DB_CFN_TYPE,
        props={
            "Properties": {
                "KeySchema": [
                    {"AttributeName": "actor_key", "KeyType": "HASH"},
                    {"AttributeName": "resource_key", "KeyType": "RANGE"},
                ],
                "AttributeDefinitions": [
                    {"AttributeName": "actor_key", "AttributeType": "S"},
                    {"AttributeName": "resource_key", "AttributeType": "S"},
                ],
                "Tags": cluster_manager_tags,
                "GlobalSecondaryIndexes": [
                    {
                        "IndexName": "resource-key-index",
                        "KeySchema": [
                            {"AttributeName": "resource_key", "KeyType": "HASH"},
                            {"AttributeName": "actor_key", "KeyType": "RANGE"},
                        ],
                        "Projection": {"ProjectionType": "ALL"},
                    }
                ],
            },
        },
    )


def test_roles_table_creation(
    res_base_stack: ResBaseStack,
    res_base_template: Template,
    cluster_manager_tags: List[Dict[str, Any]],
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        res_base_stack.nested_stack,
        res_base_template,
        resources=["authz-roles-table"],
        cfn_type=DB_CFN_TYPE,
        props={
            "Properties": {
                "KeySchema": [
                    {"AttributeName": "role_id", "KeyType": "HASH"},
                ],
                "AttributeDefinitions": [
                    {"AttributeName": "role_id", "AttributeType": "S"},
                ],
                "Tags": cluster_manager_tags,
            },
        },
    )


def test_ad_automation_table_creation(
    res_base_stack: ResBaseStack,
    res_base_template: Template,
    cluster_manager_tags: List[Dict[str, Any]],
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        res_base_stack.nested_stack,
        res_base_template,
        resources=["ad-automation-table"],
        cfn_type=DB_CFN_TYPE,
        props={
            "Properties": {
                "KeySchema": [
                    {"AttributeName": "instance_id", "KeyType": "HASH"},
                ],
                "AttributeDefinitions": [
                    {"AttributeName": "instance_id", "AttributeType": "S"},
                ],
                "Tags": cluster_manager_tags,
            },
        },
    )


def test_snapshot_table_creation(
    res_base_stack: ResBaseStack,
    res_base_template: Template,
    cluster_manager_tags: List[Dict[str, Any]],
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        res_base_stack.nested_stack,
        res_base_template,
        resources=["snapshots-table"],
        cfn_type=DB_CFN_TYPE,
        props={
            "Properties": {
                "KeySchema": [
                    {"AttributeName": "s3_bucket_name", "KeyType": "HASH"},
                    {"AttributeName": "snapshot_path", "KeyType": "RANGE"},
                ],
                "AttributeDefinitions": [
                    {"AttributeName": "s3_bucket_name", "AttributeType": "S"},
                    {"AttributeName": "snapshot_path", "AttributeType": "S"},
                ],
                "Tags": cluster_manager_tags,
            },
        },
    )


def test_apply_snapshot_table_creation(
    res_base_stack: ResBaseStack,
    res_base_template: Template,
    cluster_manager_tags: List[Dict[str, Any]],
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        res_base_stack.nested_stack,
        res_base_template,
        resources=["apply-snapshot-table"],
        cfn_type=DB_CFN_TYPE,
        props={
            "Properties": {
                "KeySchema": [
                    {"AttributeName": "apply_snapshot_identifier", "KeyType": "HASH"}
                ],
                "AttributeDefinitions": [
                    {"AttributeName": "apply_snapshot_identifier", "AttributeType": "S"}
                ],
                "Tags": cluster_manager_tags,
            },
        },
    )


def test_distributed_local_table_creation(
    res_base_stack: ResBaseStack,
    res_base_template: Template,
    cluster_manager_tags: List[Dict[str, Any]],
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        res_base_stack.nested_stack,
        res_base_template,
        resources=["cluster-manager-distributed-lock-table"],
        cfn_type=DB_CFN_TYPE,
        props={
            "Properties": {
                "KeySchema": [
                    {"AttributeName": "lock_key", "KeyType": "HASH"},
                    {"AttributeName": "sort_key", "KeyType": "RANGE"},
                ],
                "AttributeDefinitions": [
                    {"AttributeName": "lock_key", "AttributeType": "S"},
                    {"AttributeName": "sort_key", "AttributeType": "S"},
                ],
                "Tags": cluster_manager_tags,
                "TimeToLiveSpecification": {
                    "AttributeName": "expiry_time",
                    "Enabled": True,
                },
            },
        },
    )


def test_email_template_table_creation(
    res_base_stack: ResBaseStack,
    res_base_template: Template,
    cluster_manager_tags: List[Dict[str, Any]],
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        res_base_stack.nested_stack,
        res_base_template,
        resources=["email-templates-table"],
        cfn_type=DB_CFN_TYPE,
        props={
            "Properties": {
                "KeySchema": [{"AttributeName": "name", "KeyType": "HASH"}],
                "AttributeDefinitions": [
                    {"AttributeName": "name", "AttributeType": "S"}
                ],
                "Tags": cluster_manager_tags,
            },
        },
    )


def test_vdc_permission_profile_table_creation(
    res_base_stack: ResBaseStack,
    res_base_template: Template,
    vdc_tags: List[Dict[str, Any]],
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        res_base_stack.nested_stack,
        res_base_template,
        resources=["vdc-controller-permission-profiles-table"],
        cfn_type=DB_CFN_TYPE,
        props={
            "Properties": {
                "KeySchema": [{"AttributeName": "profile_id", "KeyType": "HASH"}],
                "AttributeDefinitions": [
                    {"AttributeName": "profile_id", "AttributeType": "S"}
                ],
                "Tags": vdc_tags,
            },
        },
    )


def test_vdc_schedule_table_creation(
    res_base_stack: ResBaseStack,
    res_base_template: Template,
    vdc_tags: List[Dict[str, Any]],
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        res_base_stack.nested_stack,
        res_base_template,
        resources=["vdc-controller-schedules-table"],
        cfn_type=DB_CFN_TYPE,
        props={
            "Properties": {
                "KeySchema": [
                    {
                        "AttributeName": "day_of_week",
                        "KeyType": "HASH",
                    },
                    {
                        "AttributeName": "schedule_id",
                        "KeyType": "RANGE",
                    },
                ],
                "AttributeDefinitions": [
                    {
                        "AttributeName": "day_of_week",
                        "AttributeType": "S",
                    },
                    {
                        "AttributeName": "schedule_id",
                        "AttributeType": "S",
                    },
                ],
                "Tags": vdc_tags,
            },
        },
    )


def test_vdc_ssm_command_table_creation(
    res_base_stack: ResBaseStack,
    res_base_template: Template,
    vdc_tags: List[Dict[str, Any]],
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        res_base_stack.nested_stack,
        res_base_template,
        resources=["vdc-controller-ssm-commands-table"],
        cfn_type=DB_CFN_TYPE,
        props={
            "Properties": {
                "KeySchema": [
                    {
                        "AttributeName": "command_id",
                        "KeyType": "HASH",
                    },
                ],
                "AttributeDefinitions": [
                    {"AttributeName": "command_id", "AttributeType": "S"}
                ],
                "Tags": vdc_tags,
            },
        },
    )


def test_vdc_software_stack_table_creation(
    res_base_stack: ResBaseStack,
    res_base_template: Template,
    vdc_tags: List[Dict[str, Any]],
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        res_base_stack.nested_stack,
        res_base_template,
        resources=["vdc-controller-software-stacks-table"],
        cfn_type=DB_CFN_TYPE,
        props={
            "Properties": {
                "KeySchema": [
                    {
                        "AttributeName": "base_os",
                        "KeyType": "HASH",
                    },
                    {
                        "AttributeName": "stack_id",
                        "KeyType": "RANGE",
                    },
                ],
                "AttributeDefinitions": [
                    {"AttributeName": "base_os", "AttributeType": "S"},
                    {"AttributeName": "stack_id", "AttributeType": "S"},
                ],
                "Tags": vdc_tags,
            },
        },
    )


def test_vdc_session_table_creation(
    res_base_stack: ResBaseStack,
    res_base_template: Template,
    vdc_tags: List[Dict[str, Any]],
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        res_base_stack.nested_stack,
        res_base_template,
        resources=["vdc-controller-user-sessions-table"],
        cfn_type=DB_CFN_TYPE,
        props={
            "Properties": {
                "KeySchema": [
                    {"AttributeName": "owner", "KeyType": "HASH"},
                    {"AttributeName": "idea_session_id", "KeyType": "RANGE"},
                ],
                "AttributeDefinitions": [
                    {"AttributeName": "owner", "AttributeType": "S"},
                    {"AttributeName": "idea_session_id", "AttributeType": "S"},
                ],
                "Tags": vdc_tags,
            },
        },
    )


def test_vdc_session_counter_table_creation(
    res_base_stack: ResBaseStack,
    res_base_template: Template,
    vdc_tags: List[Dict[str, Any]],
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        res_base_stack.nested_stack,
        res_base_template,
        resources=["vdc-controller-user-sessions-counter-table"],
        cfn_type=DB_CFN_TYPE,
        props={
            "Properties": {
                "KeySchema": [
                    {"AttributeName": "idea_session_id", "KeyType": "HASH"},
                    {"AttributeName": "counter_type", "KeyType": "RANGE"},
                ],
                "AttributeDefinitions": [
                    {"AttributeName": "idea_session_id", "AttributeType": "S"},
                    {"AttributeName": "counter_type", "AttributeType": "S"},
                ],
                "Tags": vdc_tags,
            },
        },
    )


def test_vdc_server_table_creation(
    res_base_stack: ResBaseStack,
    res_base_template: Template,
    vdc_tags: List[Dict[str, Any]],
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        res_base_stack.nested_stack,
        res_base_template,
        resources=["vdc-controller-servers-table"],
        cfn_type=DB_CFN_TYPE,
        props={
            "Properties": {
                "KeySchema": [{"AttributeName": "instance_id", "KeyType": "HASH"}],
                "AttributeDefinitions": [
                    {"AttributeName": "instance_id", "AttributeType": "S"},
                ],
                "Tags": vdc_tags,
            },
        },
    )


def test_vdc_session_permission_table_creation(
    res_base_stack: ResBaseStack,
    res_base_template: Template,
    vdc_tags: List[Dict[str, Any]],
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        res_base_stack.nested_stack,
        res_base_template,
        resources=["vdc-controller-session-permissions-table"],
        cfn_type=DB_CFN_TYPE,
        props={
            "Properties": {
                "KeySchema": [
                    {
                        "AttributeName": "idea_session_id",
                        "KeyType": "HASH",
                    },
                    {
                        "AttributeName": "actor_name",
                        "KeyType": "RANGE",
                    },
                ],
                "AttributeDefinitions": [
                    {
                        "AttributeName": "idea_session_id",
                        "AttributeType": "S",
                    },
                    {
                        "AttributeName": "actor_name",
                        "AttributeType": "S",
                    },
                ],
                "Tags": vdc_tags,
            },
        },
    )


def test_vdc_distributed_local_table_creation(
    res_base_stack: ResBaseStack,
    res_base_template: Template,
    vdc_tags: List[Dict[str, Any]],
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        res_base_stack.nested_stack,
        res_base_template,
        resources=["vdc-distributed-lock-table"],
        cfn_type=DB_CFN_TYPE,
        props={
            "Properties": {
                "KeySchema": [
                    {"AttributeName": "lock_key", "KeyType": "HASH"},
                    {"AttributeName": "sort_key", "KeyType": "RANGE"},
                ],
                "AttributeDefinitions": [
                    {"AttributeName": "lock_key", "AttributeType": "S"},
                    {"AttributeName": "sort_key", "AttributeType": "S"},
                ],
                "Tags": vdc_tags,
                "TimeToLiveSpecification": {
                    "AttributeName": "expiry_time",
                    "Enabled": True,
                },
            },
        },
    )


def test_res_base_stack_has_custom_resource(res_base_template: Template) -> None:
    res_base_template.resource_count_is(type="Custom::RESDdbPopulator", count=1)
    res_base_template.resource_count_is(type="Custom::DeleteTargetGroups", count=1)


def test_settings_table_creation(
    res_base_stack: ResBaseStack,
    res_base_template: Template,
    cluster_manager_tags: List[Dict[str, Any]],
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        res_base_stack.nested_stack,
        res_base_template,
        resources=["cluster-settings-table"],
        cfn_type=DB_CFN_TYPE,
        props={
            "Properties": {
                "KeySchema": [{"AttributeName": "key", "KeyType": "HASH"}],
                "AttributeDefinitions": [
                    {"AttributeName": "key", "AttributeType": "S"}
                ],
                "KinesisStreamSpecification": {"StreamArn": Match.any_value()},
                "Tags": cluster_manager_tags,
            },
        },
    )


def test_settings_table_kinesis_stream_creation(
    res_base_stack: ResBaseStack, res_base_template: Template
) -> None:
    cluster_settings = res_base_stack.nested_stack.node.find_child("cluster-settings")
    assert cluster_settings is not None, "Expected to find cluster-settings resource"
    kinesis_stream_node = cluster_settings.node.find_child("KinesisStream")
    assert kinesis_stream_node is not None, "Expected to find KinesisStream resource"
    kinesis_resource = res_base_template.find_resources(
        type=KINESIS_CFN_TYPE,
        props={
            "Properties": {
                "StreamModeDetails": {"StreamMode": "ON_DEMAND"},
                "Tags": [
                    {
                        "Key": "res:EnvironmentName",
                        "Value": res_base_stack.nested_stack.resolve(
                            res_base_stack.cluster_name
                        ),
                    }
                ],
                "StreamEncryption": {
                    "EncryptionType": "KMS",
                    "KeyId": "alias/aws/kinesis",
                },
            },
        },
    )
    assert kinesis_resource


def test_cluster_settings_table_event_handler_creation(
    res_base_stack: ResBaseStack, res_base_template: Template
) -> None:
    cluster_settings = res_base_stack.nested_stack.node.find_child("cluster-settings")
    assert cluster_settings is not None, "Expected to find cluster-settings resource"
    table_event_handler_node = cluster_settings.node.find_child("TableEventHandler")
    assert (
        table_event_handler_node is not None
    ), "Expected to find TableEventHandler resource"
    table_event_handler_resource = res_base_template.find_resources(
        type=LAMBDA_FUNCTION_CFN_TYPE,
        props={
            "Properties": {
                "Environment": {
                    "Variables": {
                        "TABLE_NAME": "cluster-settings",
                        "environment_name": res_base_stack.nested_stack.resolve(
                            res_base_stack.cluster_name
                        ),
                    }
                },
                "Handler": "table_stream_subscription_handler.handle",
                "Role": {
                    "Fn::GetAtt": [
                        util.get_logical_id(
                            res_base_stack.nested_stack,
                            ["ClusterSettingsTableEventHandlerRole"],
                        ),
                        "Arn",
                    ]
                },
                "Runtime": RES_COMMON_LAMBDA_RUNTIME.to_string(),
                "Tags": [
                    {
                        "Key": "res:EnvironmentName",
                        "Value": res_base_stack.nested_stack.resolve(
                            res_base_stack.cluster_name
                        ),
                    }
                ],
            },
        },
    )
    assert table_event_handler_resource


def test_cluster_settings_table_event_handler_role_creation(
    res_base_stack: ResBaseStack, res_base_template: Template
) -> None:
    cluster_settings_table_event_handler_role_node = (
        res_base_stack.nested_stack.node.find_child(
            "ClusterSettingsTableEventHandlerRole"
        )
    )
    assert (
        cluster_settings_table_event_handler_role_node is not None
    ), "Expected to find ClusterSettingsTableEventHandlerRole resource"
    cluster_settings_table_event_handler_role_resource = (
        res_base_template.find_resources(
            type=IAM_ROLE_CFN_TYPE,
            props={
                "Properties": {
                    "Path": res_base_stack.nested_stack.resolve(
                        res_base_stack.parameters.iam_resource_path_string
                    ),
                    "RoleName": {
                        "Fn::Join": [
                            "",
                            [
                                res_base_stack.nested_stack.resolve(
                                    res_base_stack.parameters.iam_resource_prefix_string
                                ),
                                res_base_stack.nested_stack.resolve(
                                    res_base_stack.cluster_name
                                ),
                                "-cluster-settings-table-event-handler-role",
                            ],
                        ]
                    },
                    "Tags": [
                        {
                            "Key": "Name",
                            "Value": {
                                "Fn::Join": [
                                    "",
                                    [
                                        res_base_stack.nested_stack.resolve(
                                            res_base_stack.cluster_name
                                        ),
                                        "-res-base",
                                    ],
                                ]
                            },
                        },
                        {
                            "Key": "res:EnvironmentName",
                            "Value": res_base_stack.nested_stack.resolve(
                                res_base_stack.cluster_name
                            ),
                        },
                    ],
                },
            },
        )
    )
    assert cluster_settings_table_event_handler_role_resource


def test_cluster_settings_table_event_handler_role_policy_creation(
    res_base_stack: ResBaseStack, res_base_template: Template
) -> None:
    cluster_settings_table_event_handler_role_policy = (
        res_base_stack.nested_stack.node.find_child(
            "ClusterSettingsTableEventHandlerRolePolicy"
        )
    )
    assert (
        cluster_settings_table_event_handler_role_policy is not None
    ), "Expected to find ClusterSettingsTableEventHandlerRolePolicy resource"
    cluster_settings_table_event_handler_role_policy_resource = res_base_template.find_resources(
        type=IAM_ROLE_POLICY_CFN_TYPE,
        props={
            "Properties": {
                "PolicyDocument": {
                    "Statement": [
                        {
                            "Action": "logs:CreateLogGroup",
                            "Effect": "Allow",
                            "Resource": "*",
                            "Sid": "CloudWatchLogsPermissions",
                        },
                        {
                            "Action": [
                                "logs:CreateLogStream",
                                "logs:PutLogEvents",
                                "logs:DeleteLogStream",
                            ],
                            "Effect": "Allow",
                            "Resource": "*",
                            "Sid": "CloudWatchLogStreamPermissions",
                        },
                        {
                            "Action": [
                                "dynamodb:GetItem",
                                "dynamodb:PutItem",
                                "dynamodb:DeleteItem",
                            ],
                            "Effect": "Allow",
                            "Resource": {
                                "Fn::Join": [
                                    "",
                                    [
                                        "arn:",
                                        {"Ref": "AWS::Partition"},
                                        ":dynamodb:",
                                        {"Ref": "AWS::Region"},
                                        ":",
                                        {"Ref": "AWS::AccountId"},
                                        ":table/",
                                        res_base_stack.nested_stack.resolve(
                                            res_base_stack.cluster_name
                                        ),
                                        ".ad-sync.distributed-lock",
                                    ],
                                ]
                            },
                            "Sid": "ADSyncLockTablePermissions",
                        },
                        {
                            "Action": [
                                "dynamodb:Query",
                                "dynamodb:Scan",
                                "dynamodb:UpdateItem",
                                "dynamodb:PutItem",
                            ],
                            "Effect": "Allow",
                            "Resource": {
                                "Fn::Join": [
                                    "",
                                    [
                                        "arn:",
                                        {"Ref": "AWS::Partition"},
                                        ":dynamodb:",
                                        {"Ref": "AWS::Region"},
                                        ":",
                                        {"Ref": "AWS::AccountId"},
                                        ":table/",
                                        res_base_stack.nested_stack.resolve(
                                            res_base_stack.cluster_name
                                        ),
                                        ".ad-sync.status",
                                    ],
                                ]
                            },
                            "Sid": "ADSyncStatusTablePermissions",
                        },
                        {
                            "Action": [
                                "ecs:RunTask",
                                "ecs:StopTask",
                                "ecs:ListTasks",
                            ],
                            "Condition": {
                                "ArnEquals": {
                                    "ecs:cluster": {
                                        "Fn::Join": [
                                            "",
                                            [
                                                "arn:",
                                                {"Ref": "AWS::Partition"},
                                                ":ecs:",
                                                {"Ref": "AWS::Region"},
                                                ":",
                                                {"Ref": "AWS::AccountId"},
                                                ":cluster/",
                                                res_base_stack.nested_stack.resolve(
                                                    res_base_stack.cluster_name
                                                ),
                                                "-ad-sync-cluster",
                                            ],
                                        ]
                                    }
                                }
                            },
                            "Effect": "Allow",
                            "Resource": "*",
                        },
                        {
                            "Action": "iam:PassRole",
                            "Effect": "Allow",
                            "Resource": {
                                "Fn::Join": [
                                    "",
                                    [
                                        "arn:",
                                        {"Ref": "AWS::Partition"},
                                        ":iam::",
                                        {"Ref": "AWS::AccountId"},
                                        ":role",
                                        res_base_stack.nested_stack.resolve(
                                            res_base_stack.parameters.iam_resource_path_string
                                        ),
                                        res_base_stack.nested_stack.resolve(
                                            res_base_stack.parameters.iam_resource_prefix_string
                                        ),
                                        res_base_stack.nested_stack.resolve(
                                            res_base_stack.cluster_name
                                        ),
                                        "-ad-sync-task-role",
                                    ],
                                ]
                            },
                        },
                        {
                            "Action": "ec2:DescribeSecurityGroups",
                            "Effect": "Allow",
                            "Resource": "*",
                        },
                    ]
                },
                "PolicyName": {
                    "Fn::Join": [
                        "",
                        [
                            res_base_stack.nested_stack.resolve(
                                res_base_stack.parameters.iam_resource_prefix_string
                            ),
                            res_base_stack.nested_stack.resolve(
                                res_base_stack.cluster_name
                            ),
                            "-cluster-settings-table-event-handler-role-policy",
                        ],
                    ]
                },
                "Roles": [
                    {
                        "Ref": util.get_logical_id(
                            res_base_stack.nested_stack,
                            ["ClusterSettingsTableEventHandlerRole"],
                        )
                    }
                ],
            },
        },
    )
    assert cluster_settings_table_event_handler_role_policy_resource


def test_cluster_settings_table_event_source_mapping_creation(
    res_base_stack: ResBaseStack, res_base_template: Template
) -> None:
    cluster_settings = res_base_stack.nested_stack.node.find_child("cluster-settings")
    assert cluster_settings is not None, "Expected to find cluster-settings resource"
    table_event_source_mapping_node = cluster_settings.node.find_child(
        "TableEventSourceMapping"
    )
    assert (
        table_event_source_mapping_node is not None
    ), "Expected to find TableEventSourceMapping resource"
    table_event_source_mapping_resource = res_base_template.find_resources(
        type=LAMBDA_EVENT_MAPPING_CFN_TYPE,
        props={
            "Properties": {
                "BatchSize": 10,
                "EventSourceArn": {
                    "Fn::GetAtt": [
                        util.get_logical_id(
                            res_base_stack.nested_stack,
                            ["cluster-settings", "KinesisStream"],
                        ),
                        "Arn",
                    ]
                },
                "FunctionName": {
                    "Ref": util.get_logical_id(
                        res_base_stack.nested_stack,
                        ["cluster-settings", "TableEventHandler"],
                    ),
                },
                "MaximumBatchingWindowInSeconds": 1,
                "StartingPosition": "LATEST",
            },
        },
    )
    assert table_event_source_mapping_resource


def test_modules_table_creation(
    res_base_stack: ResBaseStack,
    res_base_template: Template,
    cluster_manager_tags: List[Dict[str, Any]],
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        res_base_stack.nested_stack,
        res_base_template,
        resources=["modules-table"],
        cfn_type=DB_CFN_TYPE,
        props={
            "Properties": {
                "KeySchema": [{"AttributeName": "module_id", "KeyType": "HASH"}],
                "AttributeDefinitions": [
                    {"AttributeName": "module_id", "AttributeType": "S"}
                ],
                "Tags": cluster_manager_tags,
            },
        },
    )


def test_delete_target_groups_role_policy_creation(
    res_base_stack: ResBaseStack,
    res_base_template: Template,
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        res_base_stack.nested_stack,
        res_base_template,
        resources=["delete-target-groups-policy"],
        cfn_type="AWS::IAM::Policy",
        props={
            "Properties": {
                "PolicyDocument": {
                    "Statement": [
                        {
                            "Action": "logs:CreateLogGroup",
                            "Effect": "Allow",
                            "Resource": "*",
                            "Sid": "CloudWatchLogsPermissions",
                        },
                        {
                            "Action": [
                                "logs:CreateLogStream",
                                "logs:PutLogEvents",
                                "logs:DeleteLogStream",
                            ],
                            "Effect": "Allow",
                            "Resource": "*",
                            "Sid": "CloudWatchLogStreamPermissions",
                        },
                        {
                            "Action": [
                                "elasticloadbalancing:DescribeTargetGroups",
                                "elasticloadbalancing:DescribeTags",
                            ],
                            "Effect": "Allow",
                            "Resource": "*",
                        },
                        {
                            "Action": "elasticloadbalancing:DeleteTargetGroup",
                            "Effect": "Allow",
                            "Resource": {
                                "Fn::Join": [
                                    "",
                                    [
                                        "arn:",
                                        {"Ref": "AWS::Partition"},
                                        ":elasticloadbalancing:",
                                        {"Ref": "AWS::Region"},
                                        ":",
                                        {"Ref": "AWS::AccountId"},
                                        ":targetgroup/",
                                        res_base_stack.nested_stack.resolve(
                                            res_base_stack.cluster_name
                                        ),
                                        "-*/*",
                                    ],
                                ]
                            },
                            "Condition": {
                                "StringEquals": {
                                    "aws:ResourceTag/res:EnvironmentName": [
                                        res_base_stack.nested_stack.resolve(
                                            res_base_stack.cluster_name
                                        )
                                    ]
                                }
                            },
                        },
                    ],
                },
                "PolicyName": {
                    "Fn::Join": [
                        "",
                        [
                            res_base_stack.nested_stack.resolve(
                                res_base_stack.parameters.iam_resource_prefix_string
                            ),
                            res_base_stack.nested_stack.resolve(
                                res_base_stack.cluster_name
                            ),
                            "-delete-target-groups-policy",
                        ],
                    ]
                },
                "Roles": [
                    {
                        "Ref": util.get_logical_id(
                            res_base_stack.nested_stack, ["delete-target-groups-role"]
                        )
                    }
                ],
            }
        },
    )


def test_delete_target_groups_lambda_role_creation(
    res_base_stack: ResBaseStack,
    res_base_template: Template,
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        res_base_stack.nested_stack,
        res_base_template,
        resources=["delete-target-groups-role"],
        cfn_type="AWS::IAM::Role",
        props={
            "Properties": {
                "AssumeRolePolicyDocument": {
                    "Statement": [
                        {
                            "Action": "sts:AssumeRole",
                            "Effect": "Allow",
                            "Principal": {"Service": "lambda.amazonaws.com"},
                        }
                    ],
                },
                "PermissionsBoundary": {
                    "Fn::If": [
                        "PermissionBoundaryProvided",
                        res_base_stack.nested_stack.resolve(
                            res_base_stack.parameters.get_str(
                                CommonKey.IAM_PERMISSION_BOUNDARY
                            )
                        ),
                        {"Ref": "AWS::NoValue"},
                    ]
                },
                "Path": res_base_stack.nested_stack.resolve(
                    res_base_stack.parameters.iam_resource_path_string
                ),
                "RoleName": {
                    "Fn::Join": [
                        "",
                        [
                            res_base_stack.nested_stack.resolve(
                                res_base_stack.parameters.iam_resource_prefix_string
                            ),
                            res_base_stack.nested_stack.resolve(
                                res_base_stack.cluster_name
                            ),
                            "-delete-target-groups-role",
                        ],
                    ]
                },
                "Tags": [
                    {
                        "Key": "Name",
                        "Value": {
                            "Fn::Join": [
                                "",
                                [
                                    res_base_stack.nested_stack.resolve(
                                        res_base_stack.cluster_name
                                    ),
                                    "-res-base",
                                ],
                            ]
                        },
                    },
                    {
                        "Key": "res:EnvironmentName",
                        "Value": res_base_stack.nested_stack.resolve(
                            res_base_stack.cluster_name
                        ),
                    },
                ],
            }
        },
    )


def test_delete_target_groups_lambda_creation(
    res_base_stack: ResBaseStack,
    res_base_template: Template,
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        res_base_stack.nested_stack,
        res_base_template,
        resources=["delete-target-groups"],
        cfn_type="AWS::Lambda::Function",
        props={
            "Properties": {
                "FunctionName": {
                    "Fn::Join": [
                        "",
                        [
                            res_base_stack.nested_stack.resolve(
                                res_base_stack.cluster_name
                            ),
                            "-delete-target-groups",
                        ],
                    ]
                },
                "Handler": "handler.handler",
                "Role": {
                    "Fn::GetAtt": [
                        util.get_logical_id(
                            res_base_stack.nested_stack,
                            ["delete-target-groups-role"],
                        ),
                        "Arn",
                    ]
                },
                "Runtime": RES_COMMON_LAMBDA_RUNTIME.to_string(),
                "Tags": [
                    {
                        "Key": "Name",
                        "Value": {
                            "Fn::Join": [
                                "",
                                [
                                    res_base_stack.nested_stack.resolve(
                                        res_base_stack.cluster_name
                                    ),
                                    "-res-base",
                                ],
                            ]
                        },
                    },
                    {
                        "Key": "res:EnvironmentName",
                        "Value": res_base_stack.nested_stack.resolve(
                            res_base_stack.cluster_name
                        ),
                    },
                ],
            }
        },
    )
