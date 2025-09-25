#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import List

from aws_cdk import aws_iam as iam

from idea.infrastructure.install import constants
from idea.infrastructure.install.constructs.iam import Policy
from idea.infrastructure.install.infra_utils.arn_builder import ArnBuilder
from idea.infrastructure.install.policies.lambda_basic_execution_policy import (
    LambdaBasicExecutionPolicy,
)


class AddToUserpoolClientScopesPolicy(Policy):
    @staticmethod
    def create_policy_statements(arn_builder: ArnBuilder) -> List[iam.PolicyStatement]:
        policy_statements = [
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "cognito-idp:DescribeUserPoolClient",
                    "cognito-idp:UpdateUserPoolClient",
                ],
                resources=["*"],
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
                        "secretsmanager:ResourceTag/res:ModuleId": constants.MODULE_CLUSTER_MANAGER,
                    }
                },
            ),
        ]
        policy_statements.extend(
            LambdaBasicExecutionPolicy.create_policy_statements(arn_builder)
        )

        if arn_builder.cluster_settings.kms_secretsmanager_key_id:
            kms_statement = iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["kms:GenerateDataKey", "kms:Decrypt"],
                resources=[arn_builder.kms_secretsmanager_key_arn],  # type: ignore
            )
            policy_statements.append(kms_statement)

        return policy_statements
