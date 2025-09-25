#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import List

from aws_cdk import aws_iam as iam

from idea.infrastructure.install.constructs.iam import ManagedPolicy
from idea.infrastructure.install.infra_utils.arn_builder import ArnBuilder


class CloudWatchAgentServerPolicy(ManagedPolicy):
    @staticmethod
    def create_policy_statements(arn_builder: ArnBuilder) -> List[iam.PolicyStatement]:
        policy_statements = [
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "cloudwatch:PutMetricData",
                    "ec2:DescribeVolumes",
                    "ec2:DescribeTags",
                    "logs:PutLogEvents",
                    "logs:DescribeLogStreams",
                    "logs:DescribeLogGroups",
                    "logs:CreateLogStream",
                    "logs:CreateLogGroup",
                ],
                resources=["*"],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["ssm:GetParameter"],
                resources=[
                    arn_builder.get_arn(
                        service="ssm",
                        resource="parameter/AmazonCloudWatch-*",
                        region="*",
                    )
                ],
            ),
        ]

        return policy_statements
