#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import List

import aws_cdk
from aws_cdk import aws_iam as iam

from idea.infrastructure.install.constants import INSTALLER_ECR_REPO_NAME_SUFFIX


class UpdatePermissions:
    def __init__(
        self,
        environment_name: str,
    ):
        self.environment_name = environment_name

    def get_permissions(self) -> List[iam.PolicyStatement]:
        statements = []
        statements.extend(self.get_dynamodb_access())
        statements.extend(self.get_ecr_access())
        statements.extend(self.get_elb_access())
        statements.extend(self.get_sts_access())

        return statements

    def get_dynamodb_access(self) -> List[iam.PolicyStatement]:
        return [
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                resources=[
                    f"arn:{aws_cdk.Aws.PARTITION}:dynamodb:{aws_cdk.Aws.REGION}:{aws_cdk.Aws.ACCOUNT_ID}:table/{self.environment_name}.*"
                ],
                actions=[
                    "dynamodb:DescribeTable",
                ],
            ),
        ]

    def get_ecr_access(self) -> List[iam.PolicyStatement]:
        return [
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                resources=[
                    f"arn:{aws_cdk.Aws.PARTITION}:ecr:{aws_cdk.Aws.REGION}:{aws_cdk.Aws.ACCOUNT_ID}:repository/{self.environment_name}{INSTALLER_ECR_REPO_NAME_SUFFIX}"
                ],
                actions=[
                    "ecr:BatchGetImage",
                    "ecr:GetDownloadUrlForLayer",
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                resources=[
                    f"arn:{aws_cdk.Aws.PARTITION}:ecr:{aws_cdk.Aws.REGION}:{aws_cdk.Aws.ACCOUNT_ID}:repository/*"
                ],
                actions=[
                    "ecr:DeleteRepository",
                ],
                conditions={
                    "StringEquals": {
                        "aws:ResourceTag/res:EnvironmentName": self.environment_name
                    },
                },
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                resources=["*"],
                actions=[
                    "ecr:GetAuthorizationToken",
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                resources=[
                    f"arn:{aws_cdk.Aws.PARTITION}:ecr:{aws_cdk.Aws.REGION}:*:repository/aws-guardduty-agent-fargate"
                ],
                actions=[
                    "ecr:BatchCheckLayerAvailability",
                    "ecr:GetDownloadUrlForLayer",
                    "ecr:BatchGetImage",
                ],
            ),
        ]

    def get_elb_access(self) -> List[iam.PolicyStatement]:
        return [
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                resources=["*"],
                actions=["elasticloadbalancing:DescribeListeners"],
            ),
        ]

    def get_sts_access(self) -> List[iam.PolicyStatement]:
        return [
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                resources=[
                    f"arn:{aws_cdk.Aws.PARTITION}:iam::{aws_cdk.Aws.ACCOUNT_ID}:role/cdk-*-role-{aws_cdk.Aws.ACCOUNT_ID}-{aws_cdk.Aws.REGION}",
                ],
                actions=[
                    "sts:AssumeRole",
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                resources=[
                    "*",
                ],
                actions=[
                    "sts:GetCallerIdentity",
                ],
            ),
        ]
