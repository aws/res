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
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["s3:GetObject"],
                resources=["*"],
                conditions={
                    "StringEquals": {
                        "s3:ExistingObjectTag/res:EnvironmentName": arn_builder.cluster_name
                    }
                },
            ),
            # S3 permissions for bucket ARNs
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["s3:GetObject", "s3:ListBucket"],
                resources=arn_builder.s3_bucket_arns,  # type: ignore
            ),
            # DCV license S3 bucket permissions
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["s3:GetObject", "s3:ListBucket"],
                resources=arn_builder.dcv_license_s3_bucket_arns,  # type: ignore
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
            # Execute API ObjectStorageTempCredentials permissions
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["execute-api:Invoke"],
                resources=[arn_builder.custom_credential_broker_api_gateway_execute_post_api_arn],  # type: ignore
            ),
            # Cognito permissions
            # TODO: This should be removed after fixing the issue that VDI cognito modules setup not using bootstrap profile issue.
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "cognito-idp:AdminInitiateAuth",
                    "cognito-idp:AdminGetUser",
                    "cognito-idp:ListGroups",
                    "cognito-idp:AdminListGroupsForUser",
                    "cognito-idp:ListUsers",
                ],
                resources=[arn_builder.user_pool_arn],  # type: ignore
            ),
        ]
        policy_statements.extend(
            CustomKmsKeyPolicy.create_policy_statements(arn_builder)
        )

        return policy_statements
