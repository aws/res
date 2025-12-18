#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import List

from aws_cdk import aws_iam as iam

from idea.infrastructure.install.constructs.iam import Policy
from idea.infrastructure.install.infra_utils.arn_builder import ArnBuilder


class ProxyLambdaPolicy(Policy):
    @staticmethod
    def create_policy_statements(arn_builder: ArnBuilder) -> List[iam.PolicyStatement]:
        policy_statements = [
            iam.PolicyStatement(
                actions=["dynamodb:GetItem"],
                resources=[
                    arn_builder.get_ddb_table_arn("accounts.users"),
                    arn_builder.get_ddb_table_arn("cluster-settings"),
                ],
            ),
            iam.PolicyStatement(
                actions=["dynamodb:Scan"],
                resources=[
                    arn_builder.get_ddb_table_arn("accounts.groups"),
                ],
            ),
            iam.PolicyStatement(
                actions=["cognito-idp:DescribeUserPoolClient"],
                resources=[
                    arn_builder.user_pool_arn,  # type: ignore
                ],
            ),
            iam.PolicyStatement(
                actions=["ce:GetCostAndUsage", "ce:GetTags"],
                resources=[
                    arn_builder.get_arn(
                        service="billing", region="", resource="billingview/primary"
                    )
                ],
            ),
        ]

        return policy_statements
