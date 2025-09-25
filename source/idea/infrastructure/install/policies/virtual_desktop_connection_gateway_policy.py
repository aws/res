#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import List, Union

import aws_cdk as cdk
import constructs
import res.constants as constants  # type: ignore
from aws_cdk import CfnCondition, Fn
from aws_cdk import aws_iam as iam

from idea.batteries_included.parameters.parameters import BIParameters
from idea.infrastructure.install.constructs.iam import Policy
from idea.infrastructure.install.infra_utils.arn_builder import ArnBuilder
from idea.infrastructure.install.parameters.customdomain import CustomDomainKey
from idea.infrastructure.install.parameters.parameters import RESParameters
from idea.infrastructure.install.policies import CustomKmsKeyPolicy


class VirtualDesktopConnectionGatewayPolicy(Policy):
    @staticmethod
    def create_policy_statements(
        arn_builder: ArnBuilder,
    ) -> List[iam.PolicyStatement]:

        vdi_domain_cert_provided = CfnCondition(
            arn_builder.cluster_settings.scope,
            f"vdi-domain-cert-provided",
            expression=Fn.condition_not(
                Fn.condition_equals(
                    arn_builder.parameters.get_str(
                        CustomDomainKey.CERTIFICATE_SECRET_ARN_FOR_VDI
                    ),
                    "",
                ),
            ),
        )

        vdi_domain_private_key_provided = CfnCondition(
            arn_builder.cluster_settings.scope,
            f"vdi-domain-private-key-provided",
            expression=Fn.condition_not(
                Fn.condition_equals(
                    arn_builder.parameters.get_str(
                        CustomDomainKey.PRIVATE_KEY_SECRET_ARN_FOR_VDI
                    ),
                    "",
                ),
            ),
        )

        policy_statements = [
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "ec2:DescribeVolumes",
                    "ec2:DescribeNetworkInterfaces",
                    "ec2:DescribeImageAttribute",
                    "ec2:DescribeImages",
                    "ec2:CreateImage",
                    "ec2:CreateTags",
                    "ec2:RegisterImage",
                    "ec2:RunInstances",
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
                actions=["iam:PassRole"],
                resources=[arn_builder.get_iam_arn("vdc-gateway-role")],
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
                actions=["dynamodb:GetItem", "dynamodb:Scan", "dynamodb:DescribeTable"],
                resources=arn_builder.cluster_config_ddb_arn,  # type: ignore
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["dynamodb:DescribeTable"],
                resources=[arn_builder.get_ddb_table_arn("modules")],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
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
                effect=iam.Effect.ALLOW,
                actions=["logs:PutRetentionPolicy"],
                resources=["*"],
            ),
            iam.PolicyStatement(
                actions=["secretsmanager:GetSecretValue"],
                resources=["*"],
                effect=iam.Effect.ALLOW,
                sid="GetDomainCertificate",
                conditions={
                    "ArnEquals": {
                        "secretsmanager:SecretId": Fn.condition_if(
                            vdi_domain_cert_provided.logical_id,
                            arn_builder.parameters.get_str(
                                CustomDomainKey.CERTIFICATE_SECRET_ARN_FOR_VDI
                            ),
                            arn_builder.get_arn("secretsmanager", "secret:"),
                        )
                    },
                },
            ),
            iam.PolicyStatement(
                actions=["secretsmanager:GetSecretValue"],
                resources=["*"],
                effect=iam.Effect.ALLOW,
                sid="GetDomainPrivateKey",
                conditions={
                    "ArnEquals": {
                        "secretsmanager:SecretId": Fn.condition_if(
                            vdi_domain_private_key_provided.logical_id,
                            arn_builder.parameters.get_str(
                                CustomDomainKey.PRIVATE_KEY_SECRET_ARN_FOR_VDI
                            ),
                            arn_builder.get_arn("secretsmanager", "secret:"),
                        )
                    },
                },
            ),
        ]

        policy_statements.extend(
            CustomKmsKeyPolicy.create_policy_statements(arn_builder)
        )

        return policy_statements
