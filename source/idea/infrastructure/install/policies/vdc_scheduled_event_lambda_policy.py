#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import List

from aws_cdk import aws_iam as iam

from idea.infrastructure.install.constructs.iam import ManagedPolicy
from idea.infrastructure.install.infra_utils.arn_builder import ArnBuilder
from idea.infrastructure.install.policies.lambda_basic_execution_policy import (
    LambdaBasicExecutionPolicy,
)


class VdcScheduledEventLambdaPolicy(ManagedPolicy):
    @staticmethod
    def create_policy_statements(arn_builder: ArnBuilder) -> List[iam.PolicyStatement]:
        policy_statements: List[iam.PolicyStatement] = [
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "dynamodb:Query",
                    "dynamodb:GetItem",
                ],
                resources=[
                    arn_builder.get_ddb_table_arn("vdc.controller.schedules"),
                    arn_builder.get_ddb_table_arn("vdc.controller.user-sessions"),
                    arn_builder.get_ddb_table_arn("cluster-settings"),
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["dynamodb:Scan"],
                resources=[
                    arn_builder.get_ddb_table_arn("vdc.controller.session-permissions"),
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["dynamodb:PutItem"],
                resources=[
                    arn_builder.get_ddb_table_arn("vdc.controller.ssm-commands"),
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["ssm:SendCommand"],
                resources=[
                    arn_builder.get_arn(
                        service="ec2",
                        resource="instance/*",
                    ),
                ],
                conditions={
                    "StringEquals": {
                        "aws:ResourceTag/res:EnvironmentName": arn_builder.cluster_name,
                    }
                },
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["ssm:SendCommand"],
                resources=[
                    arn_builder.get_arn(
                        service="ssm",
                        resource="document/AWS-RunShellScript",
                        account_id="",
                    ),
                    arn_builder.get_arn(
                        service="ssm",
                        resource="document/AWS-RunPowerShellScript",
                        account_id="",
                    ),
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["iam:PassRole"],
                resources=[
                    arn_builder.get_iam_role_arn(
                        f"{arn_builder.cluster_name}-vdc-ssm-commands-sns-topic-role"
                    ),
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["secretsmanager:GetSecretValue"],
                resources=[
                    arn_builder.get_arn(
                        service="secretsmanager",
                        resource=f"secret:{arn_builder.cluster_name}-vdc-client-id-*",
                    ),
                    arn_builder.get_arn(
                        service="secretsmanager",
                        resource=f"secret:{arn_builder.cluster_name}-vdc-client-secret-*",
                    ),
                ],
            ),
        ]

        if arn_builder.cluster_settings.kms_secretsmanager_key_id:
            policy_statements.append(
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["kms:Decrypt"],
                    resources=[arn_builder.kms_secretsmanager_key_arn],  # type: ignore
                )
            )

        policy_statements.extend(
            LambdaBasicExecutionPolicy.create_policy_statements(arn_builder)
        )

        return policy_statements
