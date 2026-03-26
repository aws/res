#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import List

from aws_cdk import aws_iam as iam

from idea.infrastructure.install.constructs.iam import Policy
from idea.infrastructure.install.infra_utils.arn_builder import ArnBuilder
from idea.infrastructure.install.policies.lambda_basic_execution_policy import (
    LambdaBasicExecutionPolicy,
)


class CleanupResources(Policy):
    @staticmethod
    def create_policy_statements(arn_builder: ArnBuilder) -> List[iam.PolicyStatement]:
        tag_condition = {
            "StringEquals": {
                "aws:ResourceTag/res:EnvironmentName": arn_builder.cluster_name,
            },
        }
        policy_statements = [
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "ec2:DescribeInstances",
                    "lambda:ListFunctions",
                    "lambda:ListTags",
                ],
                resources=["*"],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "ec2:DescribeInstanceAttribute",
                    "ec2:ModifyInstanceAttribute",
                    "ec2:TerminateInstances",
                ],
                resources=[
                    arn_builder.get_arn(
                        service="ec2",
                        resource="instance/*",
                    )
                ],
                conditions=tag_condition,
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "iam:DeleteInstanceProfile",
                    "iam:RemoveRoleFromInstanceProfile",
                ],
                resources=[
                    arn_builder.get_instance_profile_arn("vdi-*"),
                    arn_builder.get_vdi_iam_instance_profile_arn("*"),
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "iam:DeleteRole",
                    "iam:DetachRolePolicy",
                ],
                resources=[
                    arn_builder.get_vdi_iam_role_arn("*"),
                ],
            ),
            iam.PolicyStatement(
                actions=[
                    "iam:ListAttachedRolePolicies",
                ],
                resources=[
                    arn_builder.get_vdi_iam_role_arn("*"),
                    arn_builder.get_iam_role_arn_no_custom_path(
                        f"{arn_builder.cluster_name}-vdi-*"
                    ),
                ],
                effect=iam.Effect.ALLOW,
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "dynamodb:Scan",
                ],
                resources=[
                    arn_builder.get_ddb_table_arn("projects"),
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "dynamodb:GetItem",
                ],
                resources=[
                    arn_builder.get_ddb_table_arn("cluster-settings"),
                ],
            ),
        ]
        policy_statements.extend(
            LambdaBasicExecutionPolicy.create_policy_statements(arn_builder)
        )

        return policy_statements
