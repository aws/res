#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import List

from aws_cdk import aws_iam as iam

from idea.infrastructure.install.constructs.iam import Policy
from idea.infrastructure.install.infra_utils.arn_builder import ArnBuilder
from idea.infrastructure.install.policies.lambda_basic_execution_policy import (
    LambdaBasicExecutionPolicy,
)


class Ec2StateEventTransformerPolicy(Policy):
    @staticmethod
    def create_policy_statements(arn_builder: ArnBuilder) -> List[iam.PolicyStatement]:
        policy_statements = [
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["ec2:DescribeInstances"],
                resources=["*"],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["sns:Publish"],
                resources=[arn_builder.get_sns_arn("*ec2-state-change*")],
            ),
        ]
        policy_statements.extend(
            LambdaBasicExecutionPolicy.create_policy_statements(arn_builder)
        )

        if arn_builder.cluster_settings.kms_sns_key_id:
            kms_statement = iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["kms:GenerateDataKey", "kms:Decrypt"],
                resources=[arn_builder.kms_sns_key_arn],  # type: ignore
            )
            policy_statements.append(kms_statement)

        return policy_statements
