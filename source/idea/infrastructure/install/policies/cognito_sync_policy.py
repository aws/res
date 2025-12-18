#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import List

from aws_cdk import aws_iam as iam

from idea.infrastructure.install.constructs.iam import Policy
from idea.infrastructure.install.infra_utils.arn_builder import ArnBuilder


class CognitoSyncPolicy(Policy):
    @staticmethod
    def create_policy_statements(arn_builder: ArnBuilder) -> List[iam.PolicyStatement]:
        policy_statements = [
            iam.PolicyStatement(
                actions=[
                    "dynamodb:PutItem",
                    "dynamodb:DeleteItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:BatchWriteItem",
                    "dynamodb:Scan",
                ],
                resources=[
                    arn_builder.get_ddb_table_arn("accounts.users"),
                    arn_builder.get_ddb_table_arn("accounts.groups"),
                    arn_builder.get_ddb_table_arn("accounts.group-members"),
                ],
            ),
            iam.PolicyStatement(
                actions=[
                    "cognito-idp:ListGroups",
                    "cognito-idp:ListUsers",
                    "cognito-idp:ListUsersInGroup",
                    "cognito-idp:AdminDisableUser",
                ],
                resources=[arn_builder.user_pool_arn],  # type: ignore
            ),
        ]

        return policy_statements
