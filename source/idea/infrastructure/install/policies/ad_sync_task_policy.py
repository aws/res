#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import List

from aws_cdk import aws_iam as iam
from res.constants import AD_SYNC_STATUS_TABLE  # type: ignore

from idea.infrastructure.install.constants import RES_ECR_REPO_NAME_SUFFIX
from idea.infrastructure.install.constructs.iam import Policy
from idea.infrastructure.install.infra_utils.arn_builder import ArnBuilder


class ADSyncTaskPolicy(Policy):
    @staticmethod
    def create_policy_statements(arn_builder: ArnBuilder) -> List[iam.PolicyStatement]:
        policy_statements = [
            iam.PolicyStatement(
                actions=["logs:CreateLogGroup"],
                sid="CloudWatchLogsPermissions",
                resources=["*"],
            ),
            iam.PolicyStatement(
                actions=[
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                    "logs:DeleteLogStream",
                ],
                sid="CloudWatchLogStreamPermissions",
                resources=["*"],
            ),
            iam.PolicyStatement(
                actions=["secretsmanager:GetSecretValue"],
                sid="SecretsManagerPermissions",
                resources=["*"],
            ),
            iam.PolicyStatement(
                actions=[
                    "dynamodb:GetItem",
                    "dynamodb:Query",
                    "dynamodb:Scan",
                    "dynamodb:UpdateItem",
                    "dynamodb:PutItem",
                    "dynamodb:DeleteItem",
                ],
                sid="DynamoDBPermissions",
                resources=[
                    arn_builder.get_ddb_table_arn("cluster-settings"),
                    arn_builder.get_ddb_table_arn("accounts.users"),
                    arn_builder.get_ddb_table_arn("accounts.users/index/*"),
                    arn_builder.get_ddb_table_arn("accounts.groups"),
                    arn_builder.get_ddb_table_arn("accounts.group-members"),
                    arn_builder.get_ddb_table_arn("projects"),
                    arn_builder.get_ddb_table_arn("projects/index/*"),
                    arn_builder.get_ddb_table_arn("authz.role-assignments"),
                    arn_builder.get_ddb_table_arn("authz.role-assignments/index/*"),
                    arn_builder.get_ddb_table_arn(AD_SYNC_STATUS_TABLE),
                    arn_builder.get_ddb_table_arn(f"{AD_SYNC_STATUS_TABLE}/index/*"),
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                resources=[
                    arn_builder.get_arn(
                        "ecr",
                        f"repository/{arn_builder.cluster_name}{RES_ECR_REPO_NAME_SUFFIX}",
                    )
                ],
                actions=[
                    "ecr:BatchGetImage",
                    "ecr:DescribeRepositories",
                    "ecr:GetDownloadUrlForLayer",
                    "ecr:GetLifecyclePolicy",
                    "ecr:GetRepositoryPolicy",
                    "ecr:ListTagsForResource",
                ],
                sid="ECRPermissions",
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                resources=["*"],
                actions=[
                    "ecr:GetAuthorizationToken",
                ],
                sid="ECRAuthorizationPermissions",
            ),
        ]

        return policy_statements
