#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import List

from aws_cdk import aws_iam as iam

from idea.infrastructure.install.constructs.iam import ManagedPolicy
from idea.infrastructure.install.infra_utils.arn_builder import ArnBuilder


class CustomKmsKeyPolicy(ManagedPolicy):
    @staticmethod
    def create_policy_statements(arn_builder: ArnBuilder) -> List[iam.PolicyStatement]:
        policy_statements = []
        # Statement for customer-managed KMS key
        if arn_builder.cluster_settings.kms_key_type == "customer-managed":
            policy_statements.append(
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["kms:Encrypt", "kms:Decrypt", "kms:GenerateDataKey"],
                    resources=arn_builder.kms_key_arns,  # type: ignore
                )
            )

        # Statement for DynamoDB KMS key
        ddb_key_id = arn_builder.cluster_settings.kms_dynamodb_key_id
        if ddb_key_id:
            policy_statements.append(
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["kms:DescribeKey", "kms:CreateGrant"],
                    resources=[arn_builder.kms_dynamodb_key_arn],  # type: ignore
                )
            )

        # Statement with condition for environment name
        policy_statements.append(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["kms:Encrypt", "kms:Decrypt", "kms:GenerateDataKey"],
                resources=["*"],
                conditions={
                    "StringEquals": {
                        "aws:ResourceTag/res:EnvironmentName": arn_builder.cluster_name
                    }
                },
            )
        )

        return policy_statements
