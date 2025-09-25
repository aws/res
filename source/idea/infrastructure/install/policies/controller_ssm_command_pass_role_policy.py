#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import List

from aws_cdk import aws_iam as iam

from idea.infrastructure.install.constructs.iam import Policy
from idea.infrastructure.install.infra_utils.arn_builder import ArnBuilder


class ControllerSSMCommandPassRolePolicy(Policy):
    @staticmethod
    def create_policy_statements(arn_builder: ArnBuilder) -> List[iam.PolicyStatement]:
        policy_statements = [
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "sns:Publish",
                ],
                resources=[arn_builder.get_sns_arn("vdc-ssm-commands-sns-topic")],
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
                    "logs:PutRetentionPolicy",
                ],
                resources=["*"],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                ],
                resources=[arn_builder.get_log_group_arn("vdc/dcv-session/*")],
            ),
        ]

        if arn_builder.cluster_settings.kms_secretsmanager_key_id:
            kms_statement = iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["kms:GenerateDataKey", "kms:Decrypt"],
                resources=[arn_builder.kms_secretsmanager_key_arn],  # type: ignore
            )
            policy_statements.append(kms_statement)

        return policy_statements
