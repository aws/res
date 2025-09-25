#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import List

import aws_cdk as cdk
import res.constants as constants  # type: ignore
from aws_cdk import aws_iam as iam

from idea.infrastructure.install.constructs.iam import Policy
from idea.infrastructure.install.infra_utils.arn_builder import ArnBuilder
from idea.infrastructure.install.policies import (
    ActiveDirectoryPolicy,
    CustomKmsKeyPolicy,
)


class VirtualDesktopDcvPolicy(Policy):
    @staticmethod
    def create_policy_statements(arn_builder: ArnBuilder) -> List[iam.PolicyStatement]:
        policy_statements = [
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                    "logs:PutRetentionPolicy",
                ],
                resources=["*"],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["s3:GetObject", "s3:ListBucket"],
                resources=arn_builder.s3_global_arns,  # type: ignore
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["s3:GetObject"],
                resources=["*"],
                conditions={
                    "StringEquals": {
                        "s3:ExistingObjectTag/res:EnvironmentName": arn_builder.cluster_name
                    }
                },
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["s3:GetObject", "s3:ListBucket"],
                resources=arn_builder.s3_bucket_arns,  # type: ignore
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["s3:GetObject", "s3:ListBucket"],
                resources=arn_builder.dcv_license_s3_bucket_arns,  # type: ignore
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["sqs:SendMessage"],
                resources=[
                    arn_builder.get_sqs_arn("vdc-events.fifo"),
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["ec2:CreateTags"],
                resources=[
                    arn_builder.get_arn("ec2", "volume/*", region="*"),
                    arn_builder.get_arn("ec2", "network-interface/*", region="*"),
                    arn_builder.get_arn("ec2", "instance/*", region="*"),
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "ec2:DescribeVolumes",
                    "ec2:DescribeNetworkInterfaces",
                    "fsx:DescribeFileSystems",
                    "tag:GetResources",
                    "tag:GetTagValues",
                    "tag:GetTagKeys",
                ],
                resources=["*"],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "kinesis:ListShards",
                    "kinesis:GetRecords",
                    "kinesis:GetShardIterator",
                ],
                resources=[arn_builder.get_ddb_table_stream_arn("cluster-settings")],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "dynamodb:GetItem",
                    "dynamodb:Scan",
                    "dynamodb:DescribeTable",
                ],
                resources=[
                    arn_builder.get_ddb_table_arn("cluster-settings"),
                    arn_builder.get_ddb_table_arn("cluster-settings/stream/*"),
                    arn_builder.get_ddb_table_arn("modules"),
                    arn_builder.get_ddb_table_arn("accounts.users"),
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "execute-api:Invoke",
                ],
                resources=[
                    arn_builder.custom_credential_broker_api_gateway_execute_get_api_arn,  # type: ignore
                    arn_builder.vdi_helper_api_gateway_execute_api_arn,  # type: ignore
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "s3:GetObject",
                ],
                resources=arn_builder.s3_public_host_modules,  # type: ignore
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "cognito-idp:AdminInitiateAuth",
                    "cognito-idp:AdminGetUser",
                    "cognito-idp:ListGroups",
                    "cognito-idp:AdminListGroupsForUser",
                    "cognito-idp:ListUsers",
                ],
                resources=[arn_builder.user_pool_arn],  # type: ignore
            ),
        ]
        policy_statements.extend(
            ActiveDirectoryPolicy.create_policy_statements(arn_builder)
        )
        policy_statements.extend(
            CustomKmsKeyPolicy.create_policy_statements(arn_builder)
        )

        return policy_statements
