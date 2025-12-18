#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import List

from aws_cdk import aws_iam as iam

from idea.infrastructure.install.constructs.iam import Policy
from idea.infrastructure.install.infra_utils.arn_builder import ArnBuilder


class BackendLambdaPolicy(Policy):
    @staticmethod
    def create_policy_statements(arn_builder: ArnBuilder) -> List[iam.PolicyStatement]:
        policy_statements = [
            iam.PolicyStatement(
                actions=[
                    "dynamodb:GetItem",
                    "dynamodb:PutItem",
                    "dynamodb:BatchGetItem",
                    "dynamodb:DeleteItem",
                    "dynamodb:Scan",
                    "dynamodb:Query",
                    "dynamodb:UpdateItem",
                ],
                resources=[
                    arn_builder.get_ddb_table_arn("*"),
                ],
            ),
            iam.PolicyStatement(
                actions=["cognito-idp:DescribeUserPoolClient"],
                resources=[
                    arn_builder.user_pool_arn,  # type: ignore
                ],
            ),
            iam.PolicyStatement(
                actions=[
                    "ec2:TerminateInstances",
                    "ec2:RunInstances",
                    "ec2:CreateTags",
                    "ec2:MonitorInstances",
                ],
                resources=[
                    arn_builder.get_arn("ec2", "*/*"),
                    arn_builder.get_arn("ec2", "image/*", account_id=""),
                ],
            ),
            iam.PolicyStatement(
                actions=[
                    "ec2:DescribeInstances",
                    "ec2:DescribeInstanceStatus",
                    "ec2:DescribeInstanceTypes",
                    "ec2:DescribeImages",
                ],
                resources=["*"],
            ),
            iam.PolicyStatement(
                actions=[
                    "ssm:SendCommand",
                    "ssm:GetCommandInvocation",
                ],
                resources=[
                    arn_builder.get_arn("ec2", "instance/*"),
                    arn_builder.get_arn(
                        "ssm", "document/AWS-RunShellScript", account_id=""
                    ),
                ],
            ),
            iam.PolicyStatement(
                actions=["route53:ChangeResourceRecordSets", "route53:GetHostedZone"],
                resources=[
                    arn_builder.get_arn(
                        "route53", "hostedzone/*", account_id="", region=""
                    ),
                ],
            ),
            iam.PolicyStatement(
                actions=["iam:PassRole"],
                resources=[
                    arn_builder.get_iam_role_arn(
                        f"{arn_builder.cluster_name}-bastion-host-role"
                    ),
                    arn_builder.get_iam_role_arn(
                        f"{arn_builder.cluster_name}-ad-sync-task-role"
                    ),
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
                        ),
                    }
                },
            ),
            iam.PolicyStatement(
                actions=["ec2:DescribeSecurityGroups"],
                resources=["*"],
            ),
            iam.PolicyStatement(
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
                actions=["ssm:GetParameter"],
                resources=[
                    arn_builder.get_arn("ssm", "parameter/aws/service/*", account_id="*", region="*"),
                ],
            ),
            iam.PolicyStatement(
                actions=["ssm:GetParameter"],
                resources=["*"],
                conditions={
                    "StringEquals": {
                        "ssm:ResourceTag/res:EnvironmentName": arn_builder.cluster_name,
                        "ssm:ResourceTag/res:ModuleName": "virtual-desktop-controller",
                    }
                },
            ),
        ]

        return policy_statements
