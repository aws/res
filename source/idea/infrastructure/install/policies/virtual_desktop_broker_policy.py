#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import List

import aws_cdk as cdk
import res.constants as constants  # type: ignore
from aws_cdk import aws_iam as iam

from idea.infrastructure.install.constructs.iam import Policy
from idea.infrastructure.install.infra_utils.arn_builder import ArnBuilder
from idea.infrastructure.install.policies import CustomKmsKeyPolicy


class VirtualDesktopBrokerPolicy(Policy):
    @staticmethod
    def create_policy_statements(arn_builder: ArnBuilder) -> List[iam.PolicyStatement]:
        policy_statements = [
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["sqs:SendMessage"],
                resources=[arn_builder.get_sqs_arn("vdc-events.fifo")],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "s3:GetObject",
                    "s3:ListBucket",
                    "s3:PutObject",
                    "s3:GetBucketAcl",
                ],
                resources=arn_builder.s3_bucket_arns,  # type: ignore
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "dynamodb:BatchGet*",
                    "dynamodb:DescribeStream",
                    "dynamodb:DescribeTable",
                    "dynamodb:Get*",
                    "dynamodb:Query",
                    "dynamodb:Scan",
                    "dynamodb:BatchWrite*",
                    "dynamodb:CreateTable",
                    "dynamodb:Delete*",
                    "dynamodb:Update*",
                    "dynamodb:PutItem",
                ],
                resources=[arn_builder.get_ddb_table_arn("vdc.*")],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "dynamodb:GetItem",
                    "dynamodb:Scan",
                    "dynamodb:DescribeTable",
                ],
                resources=arn_builder.cluster_config_ddb_arn,  # type: ignore
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["dynamodb:DescribeTable"],
                resources=[arn_builder.get_ddb_table_arn("modules")],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "sns:*",
                    "events:PutTargets",
                    "events:PutRule",
                    "events:PutEvents",
                    "events:DeleteRule",
                    "events:RemoveTargets",
                    "ec2:DescribeVolumes",
                    "ec2:DescribeNetworkInterfaces",
                    "ec2:DescribeImageAttribute",
                    "ec2:DescribeImages",
                    "ec2:DescribeInstances",
                    "ec2:ModifyInstanceAttribute",
                    "ec2:CreateImage",
                    "ec2:RebootInstances",
                    "ec2:CreateTags",
                    "ec2:RegisterImage",
                    "ec2:RunInstances",
                    "fsx:DescribeFileSystems",
                    "tag:GetResources",
                    "tag:GetTagValues",
                    "tag:GetTagKeys",
                    "ssm:ListDocuments",
                    "ssm:ListDocumentVersions",
                    "ssm:DescribeDocument",
                    "ssm:GetDocument",
                    "ssm:DescribeInstanceInformation",
                    "ssm:DescribeDocumentParameters",
                    "ssm:DescribeInstanceProperties",
                    "ssm:ListCommands",
                    "ssm:SendCommand",
                    "ssm:GetCommandInvocation",
                    "ssm:DescribeAutomationExecutions",
                    "elasticloadbalancing:DescribeTargetHealth",
                ],
                resources=["*"],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "ec2:StartInstances",
                    "ec2:TerminateInstances",
                    "ec2:StopInstances",
                    "ec2:DeregisterImage",
                ],
                resources=["*"],
                conditions={
                    "StringEquals": {
                        "aws:ResourceTag/res:EnvironmentName": arn_builder.cluster_name,
                        "aws:ResourceTag/res:ModuleName": "virtual-desktop-controller",
                    }
                },
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "logs:PutRetentionPolicy",
                ],
                resources=["*"],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "iam:PassRole",
                ],
                resources=[arn_builder.get_iam_arn("vdc-broker-role")],
            ),
        ]
        policy_statements.extend(
            CustomKmsKeyPolicy.create_policy_statements(arn_builder)
        )

        return policy_statements
