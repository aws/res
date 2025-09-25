#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import List

from aws_cdk import aws_iam as iam

from idea.infrastructure.install.constructs.iam import Policy
from idea.infrastructure.install.infra_utils.arn_builder import ArnBuilder
from idea.infrastructure.install.policies.lambda_basic_execution_policy import (
    LambdaBasicExecutionPolicy,
)


class CleanupEC2InstancePolicy(Policy):
    @staticmethod
    def create_policy_statements(arn_builder: ArnBuilder) -> List[iam.PolicyStatement]:
        tag_condition = {
            "StringEquals": {
                "aws:ResourceTag/res:EnvironmentName": arn_builder.cluster_name,
            },
        }
        policy_statements = [
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "ec2:DescribeInstances",
                    "lambda:ListFunctions",
                    "lambda:ListTags",
                ],
                resources=["*"],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "ec2:DescribeInstanceAttribute",
                    "ec2:ModifyInstanceAttribute",
                    "ec2:TerminateInstances",
                ],
                resources=[
                    arn_builder.get_arn(
                        service="ec2",
                        resource="instance/*",
                    )
                ],
                conditions=tag_condition,
            ),
        ]
        policy_statements.extend(
            LambdaBasicExecutionPolicy.create_policy_statements(arn_builder)
        )

        return policy_statements
