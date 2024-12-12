# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from typing import Any, Dict, List

import pytest
from aws_cdk.assertions import Match, Template

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
                    {"AttributeName": "nonce", "KeyType": "RANGE"},
                ],
                "AttributeDefinitions": [
                    {"AttributeName": "instance_id", "AttributeType": "S"},
                    {"AttributeName": "nonce", "AttributeType": "S"},
                ],
                "Tags": cluster_manager_tags,
                "TimeToLiveSpecification": {"AttributeName": "ttl", "Enabled": True},
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
