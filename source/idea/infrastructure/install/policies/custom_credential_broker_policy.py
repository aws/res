#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import List

from aws_cdk import aws_iam as iam

from idea.infrastructure.install.constructs.iam import ManagedPolicy
from idea.infrastructure.install.infra_utils.arn_builder import ArnBuilder
from idea.infrastructure.install.policies.lambda_basic_execution_policy import (
    LambdaBasicExecutionPolicy,
)


class CustomCredentialBrokerPolicy(ManagedPolicy):
    @staticmethod
    def create_policy_statements(arn_builder: ArnBuilder) -> List[iam.PolicyStatement]:
        policy_statements = [
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "sts:AssumeRole",
                ],
                resources=[
                    arn_builder.get_iam_arn("s3-mount-bucket-read-only"),
                    arn_builder.get_iam_arn("s3-mount-bucket-read-write"),
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "dynamodb:GetItem",
                    "dynamodb:BatchGetItem",
                ],
                resources=arn_builder.cluster_config_ddb_arn,  # type: ignore
                conditions={
                    "ForAllValues:StringLike": {
                        "dynamodb:LeadingKeys": [
                            "shared-storage.*",
                        ]
                    }
                },
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "dynamodb:BatchGetItem",
                    "dynamodb:GetItem",
                    "dynamodb:Query",
                    "dynamodb:Scan",
                ],
                resources=[
                    arn_builder.get_ddb_table_arn("vdc.controller.user-sessions"),
                    arn_builder.get_ddb_table_arn(
                        "vdc.controller.user-sessions/index/*"
                    ),
                ],
            ),
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
                    "ec2:CreateTags",
                    "ec2:CreateNetworkInterface",
                ],
                resources=[
                    arn_builder.get_arn("ec2", "subnet/*"),
                    arn_builder.get_arn("ec2", "network-interface/*"),
                    arn_builder.get_arn("ec2", "security-group/*"),
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "sts:AssumeRole",
                ],
                resources=["*"],
                conditions={
                    "StringEquals": {
                        "iam:ResourceTag/res:Resource": "s3-bucket-iam-role",
                    }
                },
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "ec2:AssignPrivateIpAddresses",
                    "ec2:UnassignPrivateIpAddresses",
                ],
                resources=["*"],
                conditions={
                    "ForAnyValue:StringLikeIfExists": {
                        "ec2:SubnetID": [
                            arn_builder.get_arn("ec2", "subnet/*"),
                        ]
                    }
                },
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "sts:AssumeRole",
                ],
                resources=[
                    arn_builder.get_iam_arn("vdc-host-role"),
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "secretsmanager:GetSecretValue",
                ],
                resources=[
                    arn_builder.get_secretmanager_secret_arn(""),
                ],
                conditions={
                    "StringEquals": {
                        "secretsmanager:SecretId": "*custom-credential-broker-secret*",
                    }
                },
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "dynamodb:GetItem",
                    "dynamodb:Query",
                    "dynamodb:Scan",
                    "dynamodb:BatchGetItem",
                    "dynamodb:DescribeTable",
                ],
                resources=[
                    arn_builder.get_ddb_table_arn("cluster-settings"),
                ],
                conditions={
                    "ForAllValues:StringEquals": {
                        "dynamodb:LeadingKeys": [
                            "vdc.custom_credential_broker_secret_name"
                        ]
                    }
                },
            ),
        ]
        policy_statements.extend(
            LambdaBasicExecutionPolicy.create_policy_statements(arn_builder)
        )

        return policy_statements
