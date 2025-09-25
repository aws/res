#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import uuid
from functools import lru_cache
from typing import List

from aws_cdk import CfnCondition, Fn
from aws_cdk import aws_iam as iam

from idea.infrastructure.install.constructs.iam import Policy
from idea.infrastructure.install.infra_utils.arn_builder import ArnBuilder
from idea.infrastructure.install.parameters.directoryservice import DirectoryServiceKey


class ActiveDirectoryPolicy(Policy):
    @staticmethod
    def create_policy_statements(arn_builder: ArnBuilder) -> List[iam.PolicyStatement]:
        unique_id = str(uuid.uuid4())[:8]
        domain_tls_cert_provided = CfnCondition(
            arn_builder.cluster_settings.scope,
            f"domain-tls-cert-provided-{unique_id}",
            expression=Fn.condition_not(
                Fn.condition_equals(
                    arn_builder.parameters.get_str(
                        DirectoryServiceKey.DOMAIN_TLS_CERTIFICATE_SECRET_ARN
                    ),
                    "",
                ),
            ),
        )

        service_account_credentials_secret_provided = CfnCondition(
            arn_builder.cluster_settings.scope,
            f"service-account-credentials-secret-provided-{unique_id}",
            expression=Fn.condition_not(
                Fn.condition_equals(
                    arn_builder.parameters.get_str(
                        DirectoryServiceKey.SERVICE_ACCOUNT_CREDENTIALS_SECRET_ARN
                    ),
                    "",
                ),
            ),
        )

        policy_statements = [
            iam.PolicyStatement(
                sid="ADAutomationSQS",
                actions=["sqs:SendMessage"],
                resources=[arn_builder.get_sqs_arn("ad-automation.fifo")],
                effect=iam.Effect.ALLOW,
            ),
            iam.PolicyStatement(
                sid="ADAutomationDDB",
                actions=["dynamodb:GetItem"],
                resources=[
                    # Replace with actual DynamoDB table ARN
                    arn_builder.get_ddb_table_arn("ad-automation")
                ],
                effect=iam.Effect.ALLOW,
            ),
            iam.PolicyStatement(
                sid="UsersDDB",
                actions=["dynamodb:Query"],
                resources=[
                    arn_builder.get_ddb_table_arn("accounts.users"),
                    arn_builder.get_ddb_table_arn("accounts.users/index/*"),
                ],
                effect=iam.Effect.ALLOW,
            ),
            iam.PolicyStatement(
                actions=["secretsmanager:GetSecretValue"],
                resources=["*"],
                effect=iam.Effect.ALLOW,
                conditions={
                    "StringEquals": {
                        "secretsmanager:ResourceTag/res:EnvironmentName": arn_builder.cluster_name,
                        "secretsmanager:ResourceTag/res:ModuleName": [
                            "directoryservice"
                        ],
                    }
                },
            ),
            iam.PolicyStatement(
                actions=["secretsmanager:GetSecretValue"],
                resources=["*"],
                effect=iam.Effect.ALLOW,
                sid="GetDomainTLSCert",
                conditions={
                    "ArnEquals": {
                        "secretsmanager:SecretId": Fn.condition_if(
                            domain_tls_cert_provided.logical_id,
                            arn_builder.parameters.get_str(
                                DirectoryServiceKey.DOMAIN_TLS_CERTIFICATE_SECRET_ARN
                            ),
                            arn_builder.get_arn("secretsmanager", "secret:"),
                        )
                    },
                },
            ),
            iam.PolicyStatement(
                actions=["secretsmanager:GetSecretValue"],
                resources=["*"],
                effect=iam.Effect.ALLOW,
                sid="GetServiceAccountCredential",
                conditions={
                    "ArnEquals": {
                        "secretsmanager:SecretId": Fn.condition_if(
                            service_account_credentials_secret_provided.logical_id,
                            arn_builder.parameters.get_str(
                                DirectoryServiceKey.SERVICE_ACCOUNT_CREDENTIALS_SECRET_ARN
                            ),
                            arn_builder.get_arn("secretsmanager", "secret:"),
                        )
                    },
                },
            ),
        ]

        return policy_statements
