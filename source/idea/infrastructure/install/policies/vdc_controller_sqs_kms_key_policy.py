#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import List

from aws_cdk import aws_iam as iam

from idea.infrastructure.install.constructs.iam import Policy
from idea.infrastructure.install.infra_utils.arn_builder import ArnBuilder


class VdcControllerSqsKmsKeyPolicy(Policy):
    @staticmethod
    def create_policy_statements(arn_builder: ArnBuilder) -> List[iam.PolicyStatement]:
        policy_statements = [
            iam.PolicyStatement(
                actions=["kms:*"],
                principals=[iam.AccountRootPrincipal()],
                resources=["*"],
            ),
            iam.PolicyStatement(
                actions=[
                    "kms:GenerateDataKey",
                    "kms:Decrypt",
                    "kms:ReEncrypt*",
                    "kms:DescribeKey",
                    "kms:Encrypt",
                ],
                principals=[
                    iam.ServicePrincipal("sns.amazonaws.com"),
                    iam.ServicePrincipal("sqs.amazonaws.com"),
                ],
                resources=["*"],
            ),
        ]

        return policy_statements
