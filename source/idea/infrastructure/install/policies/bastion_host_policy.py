#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import List

from aws_cdk import aws_iam as iam

from idea.infrastructure.install.constructs.iam import Policy
from idea.infrastructure.install.infra_utils.arn_builder import ArnBuilder
from idea.infrastructure.install.policies.active_directory_policy import (
    ActiveDirectoryPolicy,
)
from idea.infrastructure.install.policies.custom_kms_key_policy import (
    CustomKmsKeyPolicy,
)


class BastionHostPolicy(Policy):
    @staticmethod
    def create_policy_statements(arn_builder: ArnBuilder) -> List[iam.PolicyStatement]:
        policy_statements = [
            iam.PolicyStatement(
                actions=["ec2:DescribeVolumes", "ec2:DescribeNetworkInterfaces"],
                resources=["*"],
                effect=iam.Effect.ALLOW,
            ),
            iam.PolicyStatement(
                actions=["ec2:CreateTags"],
                resources=[
                    arn_builder.get_arn("ec2", "volume/*", region="*"),
                    arn_builder.get_arn("ec2", "network-interface/*", region="*"),
                ],
                effect=iam.Effect.ALLOW,
            ),
            iam.PolicyStatement(
                actions=["s3:GetObject", "s3:ListBucket", "s3:GetBucketAcl"],
                resources=arn_builder.s3_bucket_arns,  # type: ignore
                effect=iam.Effect.ALLOW,
            ),
            iam.PolicyStatement(
                actions=["logs:PutRetentionPolicy"],
                resources=["*"],
                effect=iam.Effect.ALLOW,
            ),
            iam.PolicyStatement(
                actions=[
                    "kinesis:ListShards",
                    "kinesis:GetRecords",
                    "kinesis:GetShardIterator",
                ],
                resources=[
                    arn_builder.get_ddb_table_stream_arn("cluster-settings"),
                    arn_builder.get_ddb_table_stream_arn("accounts.users"),
                ],
                effect=iam.Effect.ALLOW,
            ),
            iam.PolicyStatement(
                actions=["dynamodb:GetItem", "dynamodb:Scan", "dynamodb:DescribeTable"],
                resources=[
                    arn_builder.get_ddb_table_arn("cluster-settings"),
                    arn_builder.get_ddb_table_arn("cluster-settings/stream/*"),
                    arn_builder.get_ddb_table_arn("modules"),
                    arn_builder.get_ddb_table_arn("accounts.users"),
                ],
                effect=iam.Effect.ALLOW,
            ),
            iam.PolicyStatement(
                actions=[
                    "cognito-idp:AdminInitiateAuth",
                    "cognito-idp:AdminGetUser",
                    "cognito-idp:ListGroups",
                    "cognito-idp:AdminListGroupsForUser",
                    "cognito-idp:ListUsers",
                ],
                resources=[
                    arn_builder.user_pool_arn,  # type: ignore
                ],
                effect=iam.Effect.ALLOW,
            ),
            iam.PolicyStatement(
                actions=["s3:GetObject"],
                resources=arn_builder.s3_public_host_modules,  # type: ignore
                effect=iam.Effect.ALLOW,
            ),
        ]

        policy_statements.extend(
            ActiveDirectoryPolicy.create_policy_statements(arn_builder)
        )
        policy_statements.extend(
            CustomKmsKeyPolicy.create_policy_statements(arn_builder)
        )

        return policy_statements
