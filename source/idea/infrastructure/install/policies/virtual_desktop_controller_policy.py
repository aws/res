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


class VirtualDesktopControllerPolicy(Policy):
    @staticmethod
    def create_policy_statements(arn_builder: ArnBuilder) -> List[iam.PolicyStatement]:
        policy_statements = [
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "events:PutTargets",
                    "events:PutRule",
                    "events:PutEvents",
                    "events:DeleteRule",
                    "events:RemoveTargets",
                    "ec2:DescribeVolumes",
                    "ec2:DescribeNetworkInterfaces",
                    "ec2:DescribeImageAttribute",
                    "ec2:DescribeImages",
                    "ec2:ModifyInstanceAttribute",
                    "ec2:CreateImage",
                    "ec2:RebootInstances",
                    "ec2:DescribeInstances",
                    "ec2:DescribeInstanceTypes",
                    "ec2:CreateTags",
                    "ec2:RegisterImage",
                    "ec2:RunInstances",
                    "budgets:ViewBudget",
                    "budgets:DescribeBudget*",
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
                    "dynamodb:ListTables",
                    "application-autoscaling:RegisterScalableTarget",
                    "application-autoscaling:PutScalingPolicy",
                    "application-autoscaling:DescribeScalingPolicies",
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
                    "sqs:DeleteMessage",
                    "sqs:ReceiveMessage",
                    "sqs:SendMessage",
                    "sqs:GetQueueAttributes",
                ],
                resources=[
                    arn_builder.get_sqs_arn("vdc-events.fifo"),
                    arn_builder.get_sqs_arn("vdc-controller"),
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["route53:ChangeResourceRecordSets"],
                resources=[
                    arn_builder.get_route53_hostedzone_arn,  # type: ignore
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "dynamodb:GetItem",
                    "dynamodb:Query",
                    "dynamodb:Scan",
                    "dynamodb:DescribeTable",
                    "dynamodb:DescribeStream",
                    "dynamodb:GetRecords",
                    "dynamodb:GetShardIterator",
                    "dynamodb:ListStreams",
                ],
                resources=arn_builder.cluster_config_ddb_arn,  # type: ignore
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
                    "dynamodb:TagResource",
                ],
                resources=[
                    arn_builder.get_ddb_table_arn("vdc.*"),
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "dynamodb:GetItem",
                ],
                resources=[
                    arn_builder.get_ddb_table_arn("projects"),
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "kinesis:CreateStream",
                    "kinesis:ListShards",
                    "kinesis:GetRecords",
                    "kinesis:GetShardIterator",
                ],
                resources=[
                    arn_builder.get_ddb_table_stream_arn("cluster-settings"),
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "secretsmanager:GetSecretValue",
                ],
                resources=["*"],
                conditions={
                    "StringEquals": {
                        "secretsmanager:ResourceTag/res:EnvironmentName": arn_builder.cluster_name,
                        "secretsmanager:ResourceTag/res:ModuleName": [
                            "virtual-desktop-controller",
                            "directoryservice",
                        ],
                    }
                },
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "sqs:SendMessage",
                ],
                resources=[
                    arn_builder.get_sqs_arn("cluster-manager-notifications.fifo"),
                    arn_builder.get_sqs_arn("ad-automation.fifo"),
                ],
                sid="SendUserNotifications",
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
                    "kinesis:PutRecord",
                    "kinesis:PutRecords",
                ],
                resources=[arn_builder.get_kinesis_arn],  # type: ignore
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "iam:CreateServiceLinkedRole",
                ],
                resources=[
                    arn_builder.get_ddb_application_autoscaling_service_role_arn  # type: ignore
                ],
                conditions={
                    "StringLike": {
                        "iam:AWSServiceName": "dynamodb.application-autoscaling.amazonaws.com",
                    }
                },
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["iam:AttachRolePolicy", "iam:PutRolePolicy"],
                resources=[
                    arn_builder.get_ddb_application_autoscaling_service_role_arn  # type: ignore
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "iam:PassRole",
                ],
                resources=[arn_builder.get_vdi_iam_role_arn("*")],
            ),
        ]
        policy_statements.extend(
            ActiveDirectoryPolicy.create_policy_statements(arn_builder)
        )
        policy_statements.extend(
            CustomKmsKeyPolicy.create_policy_statements(arn_builder)
        )

        return policy_statements
