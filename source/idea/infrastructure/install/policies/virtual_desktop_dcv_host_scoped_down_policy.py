#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import List

import aws_cdk as cdk
import res.constants as constants  # type: ignore
from aws_cdk import aws_iam as iam

from idea.infrastructure.install.constructs.iam import ManagedPolicy
from idea.infrastructure.install.infra_utils.arn_builder import ArnBuilder
from idea.infrastructure.install.policies import CustomKmsKeyPolicy


class VirtualDesktopDcvHostScopedDownPolicy(ManagedPolicy):
    @staticmethod
    def create_policy_statements(arn_builder: ArnBuilder) -> List[iam.PolicyStatement]:
        policy_statements = [
            # S3 permissions for global ARNs
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["s3:GetObject", "s3:ListBucket"],
                resources=arn_builder.s3_global_arns,  # type: ignore
            ),
            # S3 permissions for bucket ARNs
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["s3:GetObject", "s3:ListBucket"],
                resources=arn_builder.s3_bucket_arns,  # type: ignore
            ),
            # S3 permission for VDI putting DCV command output
            iam.PolicyStatement(
                actions=[
                    "s3:PutObject",
                ],
                resources=arn_builder.ssm_command_output_bucket_arn,  # type: ignore
            ),
            # Execute API permissions
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["execute-api:Invoke"],
                resources=[
                    arn_builder.custom_credential_broker_api_gateway_execute_get_api_arn,  # type: ignore
                    arn_builder.vdi_helper_api_gateway_execute_api_arn,  # type: ignore
                ],
            ),
            # S3 public host modules permissions
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["s3:GetObject"],
                resources=arn_builder.s3_public_host_modules,  # type: ignore
            ),
            # Cluster settings DDB table permission to get host module URIs
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "dynamodb:GetItem",
                ],
                resources=[
                    arn_builder.get_ddb_table_arn("cluster-settings"),
                ],
                conditions={
                    "ForAllValues:StringLike": {
                        "dynamodb:LeadingKeys": ["cluster-manager.host_modules.*"]
                    }
                },
            ),
        ]
        policy_statements.extend(
            CustomKmsKeyPolicy.create_policy_statements(arn_builder)
        )

        return policy_statements
