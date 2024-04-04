#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
import importlib.metadata
from typing import Any, Dict, Optional

import pytest
from aws_cdk.assertions import Match, Template

import idea
from idea.infrastructure.install.parameters.common import CommonKey
from idea.infrastructure.install.stack import InstallStack
from ideadatamodel import constants  # type: ignore
from tests.unit.infrastructure.install import util


@pytest.fixture
def sse_specification(dynamodb_kms_key_alias: Optional[str]) -> Dict[str, Any]:
    if dynamodb_kms_key_alias is None:
        return {}
    return {
        "SSESpecification": {
            "SSEEnabled": True,
            "SSEType": "KMS",
            "KMSMasterKeyId": Match.any_value(),
        }
    }


def test_stack_description(stack: InstallStack, template: Template) -> None:
    template.template_matches(
        {"Description": f"RES_{importlib.metadata.version(idea.__package__)}"}
    )


def test_settings_table_creation(
    stack: InstallStack, template: Template, sse_specification: Dict[str, Any]
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        stack,
        template,
        resources=["Settings"],
        cfn_type="AWS::DynamoDB::Table",
        props={
            "Properties": {
                "KeySchema": [{"AttributeName": "key", "KeyType": "HASH"}],
                "AttributeDefinitions": [
                    {"AttributeName": "key", "AttributeType": "S"}
                ],
                "KinesisStreamSpecification": {"StreamArn": Match.any_value()},
                "Tags": [
                    {
                        "Key": constants.IDEA_TAG_ENVIRONMENT_NAME,
                        "Value": {
                            "Ref": CommonKey.CLUSTER_NAME,
                        },
                    }
                ],
                **sse_specification,
            },
        },
    )


def test_settings_table_kinesis_stream_creation(
    stack: InstallStack, template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        stack,
        template,
        resources=["SettingsKinesisStream"],
        cfn_type="AWS::Kinesis::Stream",
        props={
            "Properties": {
                "StreamModeDetails": {"StreamMode": "ON_DEMAND"},
                "Tags": [
                    {
                        "Key": constants.IDEA_TAG_ENVIRONMENT_NAME,
                        "Value": {
                            "Ref": CommonKey.CLUSTER_NAME,
                        },
                    }
                ],
                "StreamEncryption": {
                    "EncryptionType": "KMS",
                    "KeyId": "alias/aws/kinesis",
                },
            },
        },
    )


def test_modules_table_creation(
    stack: InstallStack, template: Template, sse_specification: Dict[str, Any]
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        stack,
        template,
        resources=["Modules"],
        cfn_type="AWS::DynamoDB::Table",
        props={
            "Properties": {
                "KeySchema": [{"AttributeName": "module_id", "KeyType": "HASH"}],
                "AttributeDefinitions": [
                    {"AttributeName": "module_id", "AttributeType": "S"}
                ],
                "Tags": [
                    {
                        "Key": constants.IDEA_TAG_BACKUP_PLAN,
                        "Value": {
                            "Fn::Join": [
                                "",
                                [
                                    {
                                        "Ref": CommonKey.CLUSTER_NAME,
                                    },
                                    f"-{constants.MODULE_CLUSTER}",
                                ],
                            ]
                        },
                    },
                    {
                        "Key": constants.IDEA_TAG_ENVIRONMENT_NAME,
                        "Value": {
                            "Ref": CommonKey.CLUSTER_NAME,
                        },
                    },
                ],
                **sse_specification,
            },
        },
    )
