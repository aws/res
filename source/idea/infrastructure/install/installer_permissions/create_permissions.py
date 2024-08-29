#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import List

import aws_cdk
from aws_cdk import aws_iam as iam

from idea.infrastructure.install.constants import INSTALLER_ECR_REPO_NAME_SUFFIX


class CreatePermissions:
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
        statements.extend(self.get_iam_access())
        statements.extend(self.get_s3_access())
        statements.extend(self.get_ssm_access())
        statements.extend(self.get_sts_access())
        statements.extend(self.get_ec2_access())

        return statements

    def get_cloudformation_access(self) -> List[iam.PolicyStatement]:
        return [
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                resources=[
                    f"arn:{aws_cdk.Aws.PARTITION}:cloudformation:{aws_cdk.Aws.REGION}:{aws_cdk.Aws.ACCOUNT_ID}:stack/{self.environment_name}-*/*"
                ],
                actions=[
                    "cloudformation:CreateChangeSet",
                    "cloudformation:DescribeChangeSet",
                    "cloudformation:DescribeStackEvents",
                    "cloudformation:ExecuteChangeSet",
                    "cloudformation:UpdateTerminationProtection",
                ],
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

    def get_ec2_access(self) -> List[iam.PolicyStatement]:
        return [
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                resources=[
                    "*",
                ],
                actions=[
                    "ec2:DescribeSubnets",
                ],
            )
        ]

    def get_dynamodb_access(self) -> List[iam.PolicyStatement]:
        return [
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                resources=[
                    f"arn:{aws_cdk.Aws.PARTITION}:dynamodb:{aws_cdk.Aws.REGION}:{aws_cdk.Aws.ACCOUNT_ID}:table/{self.environment_name}.*"
                ],
                actions=[
                    "dynamodb:DescribeTable",
                    "dynamodb:GetItem",
                    "dynamodb:Scan",
                    "dynamodb:UpdateItem",
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
                    "ecr:DescribeRepositories",
                    "ecr:GetDownloadUrlForLayer",
                    "ecr:GetLifecyclePolicy",
                    "ecr:GetRepositoryPolicy",
                    "ecr:ListTagsForResource",
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                resources=[
                    f"arn:{aws_cdk.Aws.PARTITION}:ecr:{aws_cdk.Aws.REGION}:{aws_cdk.Aws.ACCOUNT_ID}:repository/cdk-*-container-assets-{aws_cdk.Aws.ACCOUNT_ID}-{aws_cdk.Aws.REGION}"
                ],
                actions=[
                    "ecr:CreateRepository",
                    "ecr:DescribeRepositories",
                    "ecr:SetRepositoryPolicy",
                    "ecr:TagResource",
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

    def get_iam_access(self) -> List[iam.PolicyStatement]:
        return [
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                resources=[
                    f"arn:{aws_cdk.Aws.PARTITION}:iam::{aws_cdk.Aws.ACCOUNT_ID}:role/cdk-*-role-{aws_cdk.Aws.ACCOUNT_ID}-{aws_cdk.Aws.REGION}",
                ],
                actions=[
                    "iam:AttachRolePolicy",
                    "iam:CreateRole",
                    "iam:GetRole",
                    "iam:GetRolePolicy",
                    "iam:ListAttachedRolePolicies",
                    "iam:ListRolePolicies",
                    "iam:PutRolePolicy",
                    "iam:TagRole",
                ],
            )
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
                    "s3:CreateBucket",
                    "s3:GetBucketAcl",
                    "s3:PutBucketAcl",
                    "s3:PutBucketLogging",
                    "s3:GetAccelerateConfiguration",
                    "s3:GetAnalyticsConfiguration",
                    "s3:GetBucketCORS",
                    "s3:GetBucketLogging",
                    "s3:GetBucketNotification",
                    "s3:GetBucketObjectLockConfiguration",
                    "s3:GetBucketOwnershipControls",
                    "s3:GetBucketPolicy",
                    "s3:GetBucketPublicAccessBlock",
                    "s3:GetBucketTagging",
                    "s3:GetBucketVersioning",
                    "s3:GetBucketWebsite",
                    "s3:GetEncryptionConfiguration",
                    "s3:GetIntelligentTieringConfiguration",
                    "s3:GetInventoryConfiguration",
                    "s3:GetLifecycleConfiguration",
                    "s3:GetMetricsConfiguration",
                    "s3:GetReplicationConfiguration",
                    "s3:PutBucketPolicy",
                    "s3:PutBucketPublicAccessBlock",
                    "s3:PutBucketTagging",
                    "s3:PutBucketVersioning",
                    "s3:PutEncryptionConfiguration",
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                resources=[
                    f"arn:{aws_cdk.Aws.PARTITION}:s3:::{self.environment_name}-cluster-{aws_cdk.Aws.REGION}-{aws_cdk.Aws.ACCOUNT_ID}/*",
                    f"arn:{aws_cdk.Aws.PARTITION}:s3:::log-{self.environment_name}-cluster-{aws_cdk.Aws.REGION}-{aws_cdk.Aws.ACCOUNT_ID}/*",
                ],
                actions=[
                    "s3:PutObject",
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
                    "ssm:AddTagsToResource",
                    "ssm:GetParameters",
                    "ssm:PutParameter",
                ],
                conditions={
                    "StringEquals": {
                        "aws:ResourceTag/res:EnvironmentName": self.environment_name
                    },
                },
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
