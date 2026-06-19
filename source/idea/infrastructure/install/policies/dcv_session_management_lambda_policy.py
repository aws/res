#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import List

from aws_cdk import aws_iam as iam

from idea.infrastructure.install.constructs.iam import Policy
from idea.infrastructure.install.infra_utils.arn_builder import ArnBuilder


class DcvSessionManagementLambdaPolicy(Policy):
    @staticmethod
    def create_policy_statements(
        arn_builder: ArnBuilder,
    ) -> List[iam.PolicyStatement]:
        policy_statements = [
            iam.PolicyStatement(
                actions=[
                    "dynamodb:Scan",
                ],
                resources=[
                    arn_builder.get_ddb_table_arn("vdc.controller.user-sessions")
                ],
            ),
            iam.PolicyStatement(
                actions=[
                    "dynamodb:GetItem",
                ],
                resources=[
                    arn_builder.get_ddb_table_arn("cluster-settings"),
                    arn_builder.get_ddb_table_arn("vdc.controller.session-permissions"),
                    arn_builder.get_ddb_table_arn("vdc.controller.user-sessions"),
                    arn_builder.get_ddb_table_arn("vdc.controller.dcv-connection-tokens"),
                ],
            ),
            iam.PolicyStatement(
                actions=[
                    "dynamodb:PutItem",
                ],
                resources=[
                    arn_builder.get_ddb_table_arn("vdc.controller.dcv-connection-tokens"),
                ],
            ),
            iam.PolicyStatement(
                actions=["ssm:SendCommand"],
                resources=[
                    arn_builder.get_arn("ec2", "instance/*"),
                    arn_builder.get_arn(
                        "ssm", "document/AWS-RunShellScript", account_id=""
                    ),
                    arn_builder.get_arn(
                        "ssm", "document/AWS-RunPowerShellScript", account_id=""
                    ),
                ],
            ),
            iam.PolicyStatement(
                actions=["ssm:GetCommandInvocation"],
                resources=["*"],
            ),
            iam.PolicyStatement(
                actions=[
                    "s3:GetObject",
                ],
                resources=arn_builder.ssm_command_output_bucket_arn,  # type: ignore
            ),
        ]
        return policy_statements
