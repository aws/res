#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import List

from aws_cdk import aws_iam as iam

from idea.infrastructure.install.constructs.iam import Policy
from idea.infrastructure.install.infra_utils.arn_builder import ArnBuilder


class S3MountBaseBucketReadOnlyPolicy(Policy):
    @staticmethod
    def create_policy_statements(arn_builder: ArnBuilder) -> List[iam.PolicyStatement]:
        policy_statements = [
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["s3:GetObject", "s3:ListBucket"],
                resources=arn_builder.get_s3_bucket_arns("*"),
                sid="S3ReadOnlyAccess",
            ),
        ]

        return policy_statements
