#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import List

from aws_cdk import aws_iam as iam

from idea.infrastructure.install.constructs.iam import ManagedPolicy
from idea.infrastructure.install.infra_utils.arn_builder import ArnBuilder
from idea.infrastructure.install.policies.lambda_basic_execution_policy import (
    LambdaBasicExecutionPolicy,
)


class VdcEventsQueueLambdaPolicy(ManagedPolicy):
    @staticmethod
    def create_policy_statements(arn_builder: ArnBuilder) -> List[iam.PolicyStatement]:
        policy_statements = [
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "sqs:ReceiveMessage",
                    "sqs:DeleteMessage",
                    "sqs:GetQueueAttributes",
                    "sqs:SendMessage",
                ],
                resources=[
                    arn_builder.get_sqs_arn("vdc-events-v2"),
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["kms:Decrypt", "kms:GenerateDataKey"],
                resources=[
                    arn_builder.get_arn(service="kms", resource="key/*"),
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["ssm:GetCommandInvocation"],
                resources=["*"],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["ssm:SendCommand"],
                resources=[
                    arn_builder.get_arn("ec2", "instance/*"),
                ],
                conditions={
                    "StringEquals": {
                        "aws:ResourceTag/res:EnvironmentName": arn_builder.cluster_name,
                    }
                },
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["ssm:SendCommand"],
                resources=[
                    arn_builder.get_arn(
                        "ssm", "document/AWS-RunShellScript", account_id=""
                    ),
                    arn_builder.get_arn(
                        "ssm", "document/AWS-RunPowerShellScript", account_id=""
                    ),
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["iam:PassRole"],
                resources=[
                    arn_builder.get_iam_role_arn(
                        f"{arn_builder.cluster_name}-vdc-ssm-commands-sns-topic-role"
                    ),
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["ec2:CreateImage", "ec2:DescribeImages"],
                resources=["*"],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["ec2:StopInstances", "ec2:StartInstances"],
                resources=[
                    arn_builder.get_arn("ec2", "instance/*"),
                ],
                conditions={
                    "StringEquals": {
                        "aws:ResourceTag/res:EnvironmentName": arn_builder.cluster_name,
                    }
                },
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "dynamodb:GetItem",
                    "dynamodb:Query",
                    "dynamodb:UpdateItem",
                    "dynamodb:PutItem",
                    "dynamodb:DeleteItem",
                ],
                resources=[
                    arn_builder.get_ddb_table_arn("vdc.controller.user-sessions"),
                    arn_builder.get_ddb_table_arn(
                        "vdc.controller.user-sessions/index/*"
                    ),
                    arn_builder.get_ddb_table_arn("vdc.controller.ssm-commands"),
                    arn_builder.get_ddb_table_arn("vdc.controller.software-stacks"),
                    arn_builder.get_ddb_table_arn("projects"),
                ],
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
                actions=["secretsmanager:GetSecretValue"],
                resources=[
                    arn_builder.get_arn(
                        service="secretsmanager",
                        resource=f"secret:{arn_builder.cluster_name}-vdc-client-id-*",
                    ),
                    arn_builder.get_arn(
                        service="secretsmanager",
                        resource=f"secret:{arn_builder.cluster_name}-vdc-client-secret-*",
                    ),
                ],
            ),
        ]

        policy_statements.extend(
            LambdaBasicExecutionPolicy.create_policy_statements(arn_builder)
        )

        return policy_statements
