#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import List

from aws_cdk import aws_iam as iam

from idea.infrastructure.install.constructs.iam import Policy
from idea.infrastructure.install.infra_utils.arn_builder import ArnBuilder
from idea.infrastructure.install.policies.lambda_basic_execution_policy import (
    LambdaBasicExecutionPolicy,
)


class TagResourcesPolicy(Policy):
    @staticmethod
    def create_policy_statements(arn_builder: ArnBuilder) -> List[iam.PolicyStatement]:
        policy_statements = [
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "dynamodb:GetItem",
                ],
                resources=[arn_builder.get_ddb_table_arn("cluster-settings")],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "iam:ListPolicies",
                    "iam:ListInstanceProfiles",
                    "dynamodb:ListTables",
                    "ec2:DescribeSecurityGroups",
                    "ec2:DescribeNetworkInterfaces",
                    "ec2:DescribeInstances",
                    "cloudformation:ListStacks",
                    "cloudformation:DescribeStacks",
                    "elasticloadbalancing:DescribeLoadBalancers",
                    "elasticloadbalancing:DescribeListeners",
                ],
                resources=["*"],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["iam:TagPolicy", "iam:UntagPolicy"],
                resources=[
                    arn_builder.get_policy_arn(f"{arn_builder.cluster_name}-*"),
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "iam:TagInstanceProfile",
                    "iam:UntagInstanceProfile",
                ],
                resources=[
                    arn_builder.get_instance_profile_arn("*"),
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "iam:TagRole",
                    "iam:UntagRole",
                ],
                resources=[
                    arn_builder.get_iam_role_arn(f"{arn_builder.cluster_name}-*"),
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "elasticloadbalancing:AddTags",
                    "elasticloadbalancing:RemoveTags",
                ],
                resources=[
                    arn_builder.get_arn(
                        "elasticloadbalancing",
                        f"listener/*/{arn_builder.cluster_name}-*/*/*",
                    ),
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "events:ListRules",
                    "events:TagResource",
                    "events:UntagResource",
                ],
                resources=[arn_builder.get_eventbridge_rule_arn()],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "lambda:GetEventSourceMapping",
                    "lambda:ListTags",
                    "lambda:TagResource",
                    "lambda:UntagResource",
                ],
                resources=[
                    arn_builder.get_arn("lambda", "event-source-mapping:*"),
                    arn_builder.get_arn(
                        "lambda", f"function:{arn_builder.cluster_name}-*"
                    ),
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "secretsmanager:TagResource",
                    "secretsmanager:UntagResource",
                ],
                resources=[
                    arn_builder.get_secretmanager_secret_arn(
                        f"{arn_builder.cluster_name}-sso-client-secret"
                    )
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "dynamodb:TagResource",
                    "dynamodb:UntagResource",
                ],
                resources=[arn_builder.get_ddb_table_arn(f"vdc.dcv-broker.*")],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "ec2:CreateTags",
                    "ec2:DeleteTags",
                ],
                resources=[
                    arn_builder.get_arn(
                        "ec2",
                        f"instance/*",
                    ),
                    arn_builder.get_arn(
                        "ec2",
                        f"volume/*",
                    ),
                    arn_builder.get_arn(
                        "ec2",
                        f"network-interface/*",
                    ),
                    arn_builder.get_arn(
                        "ec2",
                        f"launch-template/*",
                    ),
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "cloudformation:ListStackResources",
                ],
                resources=[arn_builder.get_arn("cloudformation", "stack/*/*")],
            ),
        ]
        policy_statements.extend(
            LambdaBasicExecutionPolicy.create_policy_statements(arn_builder)
        )

        return policy_statements
