#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import List

from aws_cdk import aws_iam as iam
from res.constants import MODULE_NAME_VDC  # type: ignore

from idea.infrastructure.install.constructs.iam import ManagedPolicy
from idea.infrastructure.install.infra_utils.arn_builder import ArnBuilder
from idea.infrastructure.install.policies.lambda_basic_execution_policy import (
    LambdaBasicExecutionPolicy,
)


class VdiHelperPolicy(ManagedPolicy):
    @staticmethod
    def create_policy_statements(arn_builder: ArnBuilder) -> List[iam.PolicyStatement]:
        policy_statements = [
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "ec2:DescribeSubnets",
                    "ec2:DescribeNetworkInterfaces",
                    "ec2:DeleteNetworkInterface",
                    "ec2:DescribeInstances",
                ],
                resources=["*"],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "ec2:CreateNetworkInterface",
                ],
                resources=[
                    arn_builder.get_arn(
                        service="ec2",
                        resource="subnet/*",
                    ),
                    arn_builder.get_arn(
                        service="ec2",
                        resource="network-interface/*",
                    ),
                    arn_builder.get_arn(
                        service="ec2",
                        resource="security-group/*",
                    ),
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["ec2:TerminateInstances", "ec2:StopInstances"],
                resources=["*"],
                conditions={
                    "StringEquals": {
                        "aws:ResourceTag/res:EnvironmentName": arn_builder.cluster_name,
                        "aws:ResourceTag/res:ModuleName": MODULE_NAME_VDC,
                        "aws:ResourceTag/res:NodeType": "virtual-desktop-dcv-host",
                    }
                },
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["sqs:SendMessage"],
                resources=[
                    arn_builder.get_sqs_arn("vdc-events.fifo"),
                    arn_builder.get_sqs_arn("ad-automation.fifo"),
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["secretsmanager:GetSecretValue"],
                resources=["*"],
                conditions={
                    "StringEquals": {
                        "secretsmanager:ResourceTag/res:EnvironmentName": arn_builder.cluster_name,
                        "secretsmanager:ResourceTag/res:ModuleName": "virtual-desktop-controller",
                    }
                },
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["dynamodb:GetItem"],
                resources=[
                    arn_builder.get_ddb_table_arn("cluster-settings"),
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "dynamodb:GetItem",
                    "dynamodb:Query",
                    "dynamodb:DeleteItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:PutItem",
                ],
                resources=[
                    arn_builder.get_ddb_table_arn("vdc.controller.user-sessions"),
                    arn_builder.get_ddb_table_arn(
                        "vdc.controller.user-sessions/index/*"
                    ),
                    arn_builder.get_ddb_table_arn("vdc.controller.session-permissions"),
                    arn_builder.get_ddb_table_arn("vdc.controller.schedules"),
                ],
            ),
        ]

        policy_statements.extend(
            LambdaBasicExecutionPolicy.create_policy_statements(arn_builder)
        )

        return policy_statements
