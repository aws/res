#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import List

from aws_cdk import aws_iam as iam

from idea.infrastructure.install.constructs.iam import Policy
from idea.infrastructure.install.infra_utils.arn_builder import ArnBuilder


class CognitoTriggerWorkflowCreatePostAuthPolicy(Policy):
    @staticmethod
    def create_policy_statements(arn_builder: ArnBuilder) -> List[iam.PolicyStatement]:
        policy_statements = [
            iam.PolicyStatement(
                actions=[
                    "dynamodb:GetItem",
                    "dynamodb:UpdateItem",
                ],
                resources=[
                    arn_builder.get_ddb_table_arn("accounts.users"),
                ],
            ),
            iam.PolicyStatement(
                actions=[
                    "cognito-idp:ListUsers",
                ],
                resources=[arn_builder.user_pool_arn],  # type: ignore
            ),
            iam.PolicyStatement(
                actions=[
                    "sqs:SendMessage",
                ],
                resources=[
                    arn_builder.get_sqs_arn("cognito-post-auth-dlq.fifo"),
                    arn_builder.get_sqs_arn("cognito-post-auth.fifo"),
                ],
            ),
        ]

        return policy_statements
