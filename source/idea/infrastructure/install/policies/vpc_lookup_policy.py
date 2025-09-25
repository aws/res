#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import List

from aws_cdk import aws_iam as iam

from idea.infrastructure.install.constructs.iam import Policy
from idea.infrastructure.install.infra_utils.arn_builder import ArnBuilder
from idea.infrastructure.install.policies.lambda_basic_execution_policy import (
    LambdaBasicExecutionPolicy,
)


class VpcLookupPolicy(Policy):
    @staticmethod
    def create_policy_statements(arn_builder: ArnBuilder) -> List[iam.PolicyStatement]:
        policy_statements = [
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["ec2:DescribeVpcs"],
                resources=["*"],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["ec2:DescribeSubnets"],
                resources=["*"],
            ),
        ]
        policy_statements.extend(
            LambdaBasicExecutionPolicy.create_policy_statements(arn_builder)
        )

        return policy_statements
