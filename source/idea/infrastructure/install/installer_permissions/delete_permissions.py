#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import List

import aws_cdk
from aws_cdk import aws_iam as iam

from idea.infrastructure.install.constants import INSTALLER_ECR_REPO_NAME_SUFFIX


class DeletePermissions:
    def __init__(
        self,
        environment_name: str,
    ):
        self.environment_name = environment_name

    def get_permissions(self) -> List[iam.PolicyStatement]:
        statements = []
        statements.extend(self.get_cloudformation_access())
        statements.extend(self.get_dynamodb_access())
        statements.extend(self.get_ecr_access())
        statements.extend(self.get_ec2_access())
        statements.extend(self.get_lambda_access())
        statements.extend(self.get_elb_access())
        statements.extend(self.get_iam_access())
        statements.extend(self.get_cloudwatch_alarms_access())
        statements.extend(self.get_s3_access())
        statements.extend(self.get_ssm_access())

        return statements

    def get_cloudformation_access(self) -> List[iam.PolicyStatement]:
        return [
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                resources=[
                    f"arn:{aws_cdk.Aws.PARTITION}:cloudformation:{aws_cdk.Aws.REGION}:{aws_cdk.Aws.ACCOUNT_ID}:stack/{self.environment_name}-*/*"
                ],
                actions=[
                    "cloudformation:DeleteStack",
                    "cloudformation:UpdateTerminationProtection",
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
                    "cloudformation:DescribeStacks",
                    "cloudformation:ListStacks",
                ],
            ),
        ]

    def get_dynamodb_access(self) -> List[iam.PolicyStatement]:
        return [
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                resources=[
                    f"arn:{aws_cdk.Aws.PARTITION}:dynamodb:{aws_cdk.Aws.REGION}:{aws_cdk.Aws.ACCOUNT_ID}:table/{self.environment_name}.*"
                ],
                actions=[
                    "dynamodb:DeleteTable",
                    "dynamodb:DescribeTable",
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                resources=[
                    f"arn:{aws_cdk.Aws.PARTITION}:dynamodb:{aws_cdk.Aws.REGION}:{aws_cdk.Aws.ACCOUNT_ID}:table/*"
                ],
                actions=[
                    "dynamodb:ListTables",
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

    def get_ec2_access(self) -> List[iam.PolicyStatement]:
        return [
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                resources=[
                    f"arn:{aws_cdk.Aws.PARTITION}:ec2:{aws_cdk.Aws.REGION}:{aws_cdk.Aws.ACCOUNT_ID}:instance/*",
                ],
                actions=[
                    "ec2:DescribeInstanceAttribute",
                    "ec2:TerminateInstances",
                ],
                conditions={
                    "StringEquals": {
                        "aws:ResourceTag/res:EnvironmentName": self.environment_name
                    },
                },
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                resources=[
                    "*",
                ],
                actions=[
                    "ec2:DescribeInstances",
                ],
            ),
        ]

    def get_lambda_access(self) -> List[iam.PolicyStatement]:
        return [
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                resources=[
                    f"arn:{aws_cdk.Aws.PARTITION}:lambda:{aws_cdk.Aws.REGION}:{aws_cdk.Aws.ACCOUNT_ID}:function:*",
                ],
                actions=[
                    "lambda:UpdateFunctionConfiguration",
                ],
                conditions={
                    "StringEquals": {
                        "aws:ResourceTag/res:EnvironmentName": self.environment_name
                    },
                },
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                resources=[
                    "*",
                ],
                actions=[
                    "lambda:ListFunctions",
                    "lambda:ListTags",
                ],
            ),
        ]

    def get_elb_access(self) -> List[iam.PolicyStatement]:
        return [
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                resources=["*"],
                actions=["elasticloadbalancing:DescribeTargetGroups"],
            ),
        ]

    def get_iam_access(self) -> List[iam.PolicyStatement]:
        return [
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                resources=[
                    f"arn:{aws_cdk.Aws.PARTITION}:iam::{aws_cdk.Aws.ACCOUNT_ID}:role/cdk-*-role-{aws_cdk.Aws.ACCOUNT_ID}-{aws_cdk.Aws.REGION}"
                ],
                actions=[
                    "iam:DeleteRole",
                    "iam:DeleteRolePolicy",
                    "iam:DetachRolePolicy",
                    "iam:GetRole",
                    "iam:ListAttachedRolePolicies",
                    "iam:ListRolePolicies",
                ],
                conditions={
                    "StringEquals": {
                        "aws:ResourceTag/res:EnvironmentName": self.environment_name
                    },
                },
            )
        ]

    def get_cloudwatch_alarms_access(self) -> List[iam.PolicyStatement]:
        return [
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                resources=[
                    f"arn:{aws_cdk.Aws.PARTITION}:cloudwatch:{aws_cdk.Aws.REGION}:{aws_cdk.Aws.ACCOUNT_ID}:alarm:TargetTracking-table/*"
                ],
                actions=[
                    "cloudwatch:DeleteAlarms",
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                resources=["*"],
                actions=[
                    "cloudwatch:DescribeAlarms",
                ],
            ),
        ]

    def get_s3_access(self) -> List[iam.PolicyStatement]:
        return [
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                resources=[
                    f"arn:{aws_cdk.Aws.PARTITION}:s3:::{self.environment_name}-cluster-{aws_cdk.Aws.REGION}-{aws_cdk.Aws.ACCOUNT_ID}",
                    f"arn:{aws_cdk.Aws.PARTITION}:s3:::log-{self.environment_name}-cluster-{aws_cdk.Aws.REGION}-{aws_cdk.Aws.ACCOUNT_ID}",
                ],
                actions=[
                    "s3:DeleteBucket",
                    "s3:DeleteBucketPolicy",
                    "s3:GetBucketPolicy",
                    "s3:ListBucketVersions",
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                resources=[
                    f"arn:{aws_cdk.Aws.PARTITION}:s3:::{self.environment_name}-cluster-{aws_cdk.Aws.REGION}-{aws_cdk.Aws.ACCOUNT_ID}/*",
                    f"arn:{aws_cdk.Aws.PARTITION}:s3:::log-{self.environment_name}-cluster-{aws_cdk.Aws.REGION}-{aws_cdk.Aws.ACCOUNT_ID}/*",
                ],
                actions=[
                    "s3:DeleteObjectVersion",
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                resources=["*"],
                actions=[
                    "s3:ListAllMyBuckets",
                ],
            ),
        ]

    def get_ssm_access(self) -> List[iam.PolicyStatement]:
        return [
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                resources=[
                    f"arn:{aws_cdk.Aws.PARTITION}:ssm:{aws_cdk.Aws.REGION}:{aws_cdk.Aws.ACCOUNT_ID}:parameter/cdk-bootstrap/*/version",
                ],
                actions=[
                    "ssm:DeleteParameter",
                ],
                conditions={
                    "StringEquals": {
                        "aws:ResourceTag/res:EnvironmentName": self.environment_name
                    },
                },
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                resources=[
                    "*",
                ],
                actions=[
                    "ssm:ListCommandInvocations",
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                resources=[
                    f"arn:{aws_cdk.Aws.PARTITION}:ssm:{aws_cdk.Aws.REGION}::document/AWS-RunShellScript",
                ],
                actions=[
                    "ssm:SendCommand",
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                resources=[
                    f"arn:{aws_cdk.Aws.PARTITION}:ec2:{aws_cdk.Aws.REGION}:{aws_cdk.Aws.ACCOUNT_ID}:instance/*",
                ],
                actions=[
                    "ssm:SendCommand",
                ],
                conditions={
                    "StringEquals": {
                        "aws:ResourceTag/res:EnvironmentName": self.environment_name
                    },
                },
            ),
        ]
