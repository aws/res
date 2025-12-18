#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import List

from aws_cdk import aws_iam as iam

from idea.infrastructure.install.constructs.iam import Policy
from idea.infrastructure.install.infra_utils.arn_builder import ArnBuilder


class BastionHostCleanupPolicy(Policy):
    @staticmethod
    def create_policy_statements(arn_builder: ArnBuilder) -> List[iam.PolicyStatement]:
        policy_statements = [
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "ec2:TerminateInstances",
                    "route53:ChangeResourceRecordSets",
                    "route53:ListResourceRecordSets",
                    "dynamodb:GetItem",
                ],
                resources=[
                    arn_builder.get_arn("ec2", "instance/*"),
                    arn_builder.get_arn("route53", "hostedzone/*", "", ""),
                    arn_builder.get_ddb_table_arn("cluster-settings"),
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["ec2:DescribeInstances"],
                resources=["*"],
            ),
        ]

        return policy_statements
