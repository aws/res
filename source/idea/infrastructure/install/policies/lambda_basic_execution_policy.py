#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import List

from aws_cdk import aws_iam as iam

from idea.infrastructure.install.constructs.iam import Policy
from idea.infrastructure.install.infra_utils.arn_builder import ArnBuilder


class LambdaBasicExecutionPolicy(Policy):
    @staticmethod
    def create_policy_statements(arn_builder: ArnBuilder) -> List[iam.PolicyStatement]:
        policy_statements = [
            iam.PolicyStatement(
                sid="CloudWatchLogsPermissions",
                effect=iam.Effect.ALLOW,
                actions=["logs:CreateLogGroup"],
                resources=[arn_builder.get_lambda_log_group_arn("*")],
            ),
            iam.PolicyStatement(
                sid="CloudWatchLogStreamPermissions",
                effect=iam.Effect.ALLOW,
                actions=[
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                    "logs:DeleteLogStream",
                ],
                resources=[arn_builder.lambda_log_stream_arn],  # type: ignore
            ),
        ]

        return policy_statements
