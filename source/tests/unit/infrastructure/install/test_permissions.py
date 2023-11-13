#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from typing import Any

import pytest
from aws_cdk.assertions import Template

from idea.infrastructure.install.parameters.common import CommonKey
from idea.infrastructure.install.stack import InstallStack
from tests.unit.infrastructure.install import util


@pytest.fixture
def assume_role_policy_document() -> dict[str, Any]:
    return {
        "Statement": [
            {
                "Action": "sts:AssumeRole",
                "Condition": {
                    "ArnLike": {
                        "aws:SourceArn": {
                            "Fn::Join": [
                                "",
                                [
                                    "arn:",
                                    {"Ref": "AWS::Partition"},
                                    ":ecs:",
                                    {"Ref": "AWS::Region"},
                                    ":",
                                    {"Ref": "AWS::AccountId"},
                                    ":*",
                                ],
                            ]
                        }
                    },
                    "StringEquals": {"aws:SourceAccount": {"Ref": "AWS::AccountId"}},
                },
                "Effect": "Allow",
                "Principal": {"Service": "ecs-tasks.amazonaws.com"},
            }
        ]
    }


@pytest.mark.parametrize("role", ("InstallRole", "UpdateRole", "DeleteRole"))
def test_role_creation(
    stack: InstallStack,
    template: Template,
    assume_role_policy_document: dict[str, Any],
    role: str,
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        stack,
        template,
        resources=["Installer", "Tasks", "Permissions", role],
        cfn_type="AWS::IAM::Role",
        props={
            "Properties": {
                "AssumeRolePolicyDocument": assume_role_policy_document,
                "RoleName": {
                    "Fn::Join": [
                        "",
                        ["Admin-", {"Ref": CommonKey.CLUSTER_NAME}, f"-{role}"],
                    ]
                },
            },
        },
    )
    util.assert_resource_name_has_correct_type_and_props(
        stack,
        template,
        resources=["Installer", "Tasks", "Permissions", role, "DefaultPolicy"],
        cfn_type="AWS::IAM::Policy",
        props={
            "Properties": {
                "Roles": [
                    {
                        "Ref": util.get_logical_id(
                            stack, ["Installer", "Tasks", "Permissions", role]
                        )
                    }
                ]
            }
        },
    )
