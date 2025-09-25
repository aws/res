#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import List

import aws_cdk as cdk
from aws_cdk import aws_iam as iam

from idea.infrastructure.install.constructs.iam import Policy
from idea.infrastructure.install.infra_utils.arn_builder import ArnBuilder
from idea.infrastructure.install.policies.lambda_basic_execution_policy import (
    LambdaBasicExecutionPolicy,
)


class ConfigureSSOLambdaPolicy(Policy):
    @staticmethod
    def create_policy_statements(arn_builder: ArnBuilder) -> List[iam.PolicyStatement]:
        policy_statements = [
            # Cognito permissions
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "cognito-idp:UpdateUserPoolClient",
                    "cognito-idp:CreateUserPoolClient",
                    "cognito-idp:GetIdentityProviderByIdentifier",
                    "cognito-idp:UpdateIdentityProvider",
                    "cognito-idp:CreateIdentityProvider",
                    "cognito-idp:DeleteIdentityProvider",
                ],
                resources=[arn_builder.user_pool_arn],  # type: ignore
            ),
            # DynamoDB permissions
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "dynamodb:GetItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:PutItem",
                    "dynamodb:DescribeTable",
                ],
                resources=[arn_builder.get_ddb_table_arn("cluster-settings")],
            ),
        ]
        policy_statements.extend(
            LambdaBasicExecutionPolicy.create_policy_statements(arn_builder)
        )

        policy_statements.append(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "secretsmanager:DescribeSecret",
                    "secretsmanager:CreateSecret",
                    "secretsmanager:UpdateSecret",
                    "secretsmanager:TagResource",
                ],
                resources=[
                    f"arn:{cdk.Aws.PARTITION}:secretsmanager:*:*:secret:{arn_builder.cluster_name}-sso-client-secret*"
                ],
            )
        )

        return policy_statements
