#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import List

from aws_cdk import aws_iam as iam
from res.constants import AD_SYNC_LOCK_TABLE, AD_SYNC_STATUS_TABLE  # type: ignore

from idea.infrastructure.install.constructs.iam import Policy
from idea.infrastructure.install.infra_utils.arn_builder import ArnBuilder


class ScheduledADSyncPolicy(Policy):
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
                actions=[
                    "dynamodb:GetItem",
                    "dynamodb:Scan",
                ],
                sid="ClusterSettingsTablePermissions",
                resources=[
                    arn_builder.get_ddb_table_arn("cluster-settings"),
                ],
            ),
            iam.PolicyStatement(
                actions=[
                    "dynamodb:GetItem",
                    "dynamodb:PutItem",
                    "dynamodb:DeleteItem",
                ],
                sid="ADSyncLockTablePermissions",
                resources=[
                    arn_builder.get_ddb_table_arn(AD_SYNC_LOCK_TABLE),
                ],
            ),
            iam.PolicyStatement(
                actions=[
                    "dynamodb:Query",
                    "dynamodb:Scan",
                    "dynamodb:UpdateItem",
                    "dynamodb:PutItem",
                ],
                sid="ADSyncStatusTablePermissions",
                resources=[
                    arn_builder.get_ddb_table_arn(AD_SYNC_STATUS_TABLE),
                ],
            ),
            iam.PolicyStatement(
                actions=[
                    "ecs:RunTask",
                    "ecs:StopTask",
                    "ecs:ListTasks",
                ],
                resources=["*"],
                conditions={
                    "ArnEquals": {
                        "ecs:cluster": arn_builder.get_arn(
                            "ecs", f"cluster/{arn_builder.cluster_name}-ad-sync-cluster"
                        )
                    }
                },
            ),
            iam.PolicyStatement(
                actions=["iam:PassRole"],
                resources=[
                    arn_builder.get_iam_role_arn(
                        f"{arn_builder.cluster_name}-ad-sync-task-role"
                    ),
                ],
            ),
            iam.PolicyStatement(
                actions=["ec2:DescribeSecurityGroups"],
                resources=["*"],
            ),
        ]

        return policy_statements
