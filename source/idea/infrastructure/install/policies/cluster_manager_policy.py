#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import List

import aws_cdk as cdk
from aws_cdk import CfnCondition, Fn
from aws_cdk import aws_iam as iam

from idea.infrastructure.install.constructs.iam import Policy
from idea.infrastructure.install.infra_utils.arn_builder import ArnBuilder
from idea.infrastructure.install.parameters.directoryservice import DirectoryServiceKey
from idea.infrastructure.install.policies.custom_kms_key_policy import (
    CustomKmsKeyPolicy,
)


class ClusterManagerPolicy(Policy):
    @staticmethod
    def create_policy_statements(arn_builder: ArnBuilder) -> List[iam.PolicyStatement]:

        domain_tls_cert_provided = CfnCondition(
            arn_builder.cluster_settings.scope,
            f"domain-tls-cert-provided",
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
            f"service-account-credentials-secret-provided",
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
            # SQS SendMessage to VDC controller
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["sqs:SendMessage"],
                resources=[arn_builder.get_sqs_arn("vdc-controller")],
            ),
            # EC2, Budgets, EFS, FSx permissions
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "ec2:DescribeVolumes",
                    "ec2:DescribeNetworkInterfaces",
                    "ec2:DescribeInstances",
                    "ec2:DescribeInstanceTypes",
                    "budgets:ViewBudget",
                    "elasticfilesystem:DescribeFileSystems",
                    "fsx:DescribeFileSystems",
                    "fsx:DescribeVolumes",
                    "fsx:DescribeStorageVirtualMachines",
                    "elasticfilesystem:DescribeMountTargets",
                    "ec2:DescribeSubnets",
                    "ec2:CreateNetworkInterface",
                    "ec2:CreateTags",
                    "iam:CreateServiceLinkedRole",
                    "iam:ListPolicies",
                    "ec2:DescribeSecurityGroups",
                ],
                resources=["*"],
            ),
            # EC2 CreateTags for volumes and network interfaces
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["ec2:CreateTags"],
                resources=[
                    arn_builder.get_arn("ec2", "network-interface/*"),
                    arn_builder.get_arn("ec2", "volume/*"),
                ],
            ),
            # SES permissions
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["ses:SendEmail"],
                resources=[arn_builder.get_arn("ses", "identity/*")],
            ),
            # S3 permissions
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "s3:GetObject",
                    "s3:ListBucket",
                    "s3:PutObject",
                    "s3:GetBucketAcl",
                ],
                resources=arn_builder.s3_bucket_arns,  # type: ignore
            ),
            # S3 Host modules
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["s3:GetObject"],
                resources=arn_builder.s3_public_host_modules,  # type: ignore
            ),
            # DynamoDB permissions - extended
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "dynamodb:GetItem",
                    "dynamodb:BatchGetItem",
                    "dynamodb:Query",
                    "dynamodb:Scan",
                    "dynamodb:DescribeTable",
                    "dynamodb:DescribeStream",
                    "dynamodb:GetRecords",
                    "dynamodb:GetShardIterator",
                    "dynamodb:ListStreams",
                    "dynamodb:UpdateItem",
                    "dynamodb:PutItem",
                    "dynamodb:DeleteItem",
                    "dynamodb:TagResource",
                    "dynamodb:CreateTable",
                    "dynamodb:TransactWriteItems",
                ],
                resources=[
                    arn_builder.get_ddb_table_arn("cluster-settings"),
                    arn_builder.get_ddb_table_arn("cluster-settings/stream/*"),
                    arn_builder.get_ddb_table_arn("modules"),
                    arn_builder.get_ddb_table_arn("email-templates"),
                    arn_builder.get_ddb_table_arn("accounts.users"),
                    arn_builder.get_ddb_table_arn("accounts.users/index/*"),
                    arn_builder.get_ddb_table_arn("accounts.groups"),
                    arn_builder.get_ddb_table_arn("accounts.group-members"),
                    arn_builder.get_ddb_table_arn("accounts.sso-state"),
                    arn_builder.get_ddb_table_arn("accounts.group-members/stream/*"),
                    arn_builder.get_ddb_table_arn("projects"),
                    arn_builder.get_ddb_table_arn("projects/index/*"),
                    arn_builder.get_ddb_table_arn("projects.user-projects"),
                    arn_builder.get_ddb_table_arn("projects.project-groups"),
                    arn_builder.get_ddb_table_arn("ad-automation"),
                    arn_builder.get_ddb_table_arn("cluster-manager.distributed-lock"),
                    arn_builder.get_ddb_table_arn("snapshots"),
                    arn_builder.get_ddb_table_arn("apply-snapshot"),
                    arn_builder.get_ddb_table_arn("authz.roles"),
                    arn_builder.get_ddb_table_arn("authz.role-assignments"),
                    arn_builder.get_ddb_table_arn("authz.role-assignments/index/*"),
                    arn_builder.get_ddb_table_arn("ad-sync.distributed-lock"),
                    arn_builder.get_ddb_table_arn("ad-sync.status"),
                    arn_builder.get_ddb_table_arn("ad-sync.status/index/*"),
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "dynamodb:ImportTable",
                    "dynamodb:DescribeImport",
                    "dynamodb:DeleteTable",
                    "dynamodb:Scan",
                ],
                resources=[arn_builder.get_ddb_table_arn("temp-*")],
            ),
            # DynamoDB export permissions
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "dynamodb:ExportTableToPointInTime",
                    "dynamodb:UpdateContinuousBackups",
                ],
                resources=[arn_builder.get_ddb_table_arn(f"*")],
            ),
            # DynamoDB describe export permissions
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["dynamodb:DescribeExport"],
                resources=[arn_builder.get_ddb_table_export_arn],  # type: ignore
            ),
            # Kinesis permissions for DDB streams
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "kinesis:CreateStream",
                    "kinesis:ListShards",
                    "kinesis:GetRecords",
                    "kinesis:GetShardIterator",
                ],
                resources=[arn_builder.get_ddb_table_stream_arn("cluster-settings")],
            ),
            # Secrets Manager permissions - extended
            iam.PolicyStatement(
                conditions={
                    "StringEquals": {
                        "secretsmanager:ResourceTag/res:EnvironmentName": arn_builder.cluster_name,
                        "secretsmanager:ResourceTag/res:ModuleName": [
                            "cluster-manager",
                            "directoryservice",
                        ],
                    }
                },
                actions=[
                    "secretsmanager:GetSecretValue",
                    "secretsmanager:PutSecretValue",
                ],
                resources=["*"],
                effect=iam.Effect.ALLOW,
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "secretsmanager:CreateSecret",
                    "secretsmanager:DescribeSecret",
                    "secretsmanager:TagResource",
                    "secretsmanager:PutSecretValue",
                ],
                resources=[
                    arn_builder.get_secretmanager_secret_arn(
                        f"{arn_builder.cluster_name}-directoryservice-ServiceAccountUserDN"
                    )
                ],
            ),
            iam.PolicyStatement(
                actions=["secretsmanager:GetSecretValue"],
                resources=["*"],
                effect=iam.Effect.ALLOW,
                sid="GetDomainTLSCertCM",
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
                sid="GetServiceAccountCredentialCM",
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
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "secretsmanager:CreateSecret",
                    "secretsmanager:DescribeSecret",
                    "secretsmanager:TagResource",
                    "secretsmanager:PutSecretValue",
                ],
                resources=[
                    arn_builder.get_secretmanager_secret_arn(
                        f"{arn_builder.cluster_name}-sso-client-secret"
                    )
                ],
            ),
            # Cognito permissions
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["cognito-idp:*"],
                resources=[arn_builder.user_pool_arn],  # type: ignore
            ),
            # SQS queue permissions
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "sqs:ChangeMessageVisibility",
                    "sqs:Delete*",
                    "sqs:Get*",
                    "sqs:List*",
                    "sqs:ReceiveMessage",
                ],
                resources=[
                    arn_builder.get_sqs_arn("cluster-manager-notifications.fifo"),
                    arn_builder.get_sqs_arn("ad-automation.fifo"),
                ],
            ),
            # Logs permissions
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["logs:PutRetentionPolicy"],
                resources=["*"],
            ),
            # Kinesis data stream permissions
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["kinesis:PutRecord", "kinesis:PutRecords"],
                resources=[arn_builder.get_kinesis_arn],  # type: ignore
            ),
            # IAM permissions for VDI roles
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "iam:CreateRole",
                    "iam:DeleteRole",
                    "iam:CreateInstanceProfile",
                    "iam:DeleteInstanceProfile",
                    "iam:AddRoleToInstanceProfile",
                    "iam:PassRole",
                    "iam:AttachRolePolicy",
                    "iam:DetachRolePolicy",
                    "iam:GetRole",
                    "iam:TagRole",
                    "iam:TagInstanceProfile",
                    "iam:DeleteInstanceProfile",
                    "iam:RemoveRoleFromInstanceProfile",
                ],
                resources=[
                    arn_builder.get_vdi_iam_role_arn("*"),
                    arn_builder.get_vdi_iam_instance_profile_arn("*"),
                ],
            ),
            # Load Balancer permissions
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "elasticloadbalancing:DescribeTargetGroups",
                    "elasticloadbalancing:DescribeListeners",
                    "elasticloadbalancing:DeleteTargetGroup",
                    "elasticloadbalancing:CreateListener",
                    "elasticloadbalancing:DeleteListener",
                    "elasticloadbalancing:CreateTargetGroup",
                    "elasticloadbalancing:RegisterTargets",
                    "elasticloadbalancing:AddTags",
                ],
                resources=["*"],
            ),
            iam.PolicyStatement(
                actions=[
                    "iam:AttachRolePolicy",
                    "iam:DetachRolePolicy",
                    "iam:GetRole",
                ],
                resources=[arn_builder.get_vdi_iam_role_arn("*")],
                effect=iam.Effect.ALLOW,
            ),
            iam.PolicyStatement(
                actions=[
                    "iam:ListAttachedRolePolicies",
                ],
                resources=[
                    arn_builder.get_vdi_iam_role_arn("*"),
                    arn_builder.get_iam_role_arn_no_custom_path(
                        f"{arn_builder.cluster_name}-vdi-*"
                    ),
                ],
                effect=iam.Effect.ALLOW,
            ),
            iam.PolicyStatement(
                conditions={
                    "StringEquals": {
                        "aws:ResourceTag/res:Resource": "s3-bucket-iam-role"
                    }
                },
                actions=["iam:GetRole"],
                resources=["*"],
                effect=iam.Effect.ALLOW,
            ),
            iam.PolicyStatement(
                conditions={
                    "ArnEquals": {
                        "iam:PolicyARN": [
                            arn_builder.get_policy_arn(
                                f"{arn_builder.cluster_name}-amazon-ssm-managed-instance-core"
                            ),
                            arn_builder.get_policy_arn(
                                f"{arn_builder.cluster_name}-cloud-watch-agent-server-policy"
                            ),
                            arn_builder.get_policy_arn(
                                f"{arn_builder.cluster_name}-vdi-host-scoped-down-managed-policy"
                            ),
                        ]
                    }
                },
                actions=["iam:AttachRolePolicy", "iam:DetachRolePolicy"],
                resources=[
                    arn_builder.get_iam_role_arn(
                        f"{arn_builder.cluster_name}-{cdk.Aws.REGION}/vdi/{arn_builder.cluster_name}-vdi-*"
                    )
                ],
                effect=iam.Effect.ALLOW,
            ),
            iam.PolicyStatement(
                conditions={
                    "StringEquals": {"aws:ResourceTag/res:Resource": "vdi-host-policy"}
                },
                actions=["iam:GetPolicy"],
                resources=["*"],
                effect=iam.Effect.ALLOW,
            ),
            iam.PolicyStatement(
                actions=[
                    "elasticloadbalancing:DescribeTargetGroups",
                    "elasticloadbalancing:DescribeListeners",
                ],
                resources=["*"],
                effect=iam.Effect.ALLOW,
            ),
            iam.PolicyStatement(
                actions=[
                    "elasticloadbalancing:DeleteTargetGroup",
                    "elasticloadbalancing:CreateListener",
                    "elasticloadbalancing:DeleteListener",
                    "elasticloadbalancing:CreateTargetGroup",
                    "elasticloadbalancing:RegisterTargets",
                    "elasticloadbalancing:AddTags",
                ],
                resources=[
                    arn_builder.get_elastic_load_balancer_arn(
                        f"targetgroup/{arn_builder.cluster_name}*/*"
                    ),
                    arn_builder.get_elastic_load_balancer_arn(
                        f"listener/net/{arn_builder.cluster_name}*/*/*"
                    ),
                    arn_builder.get_elastic_load_balancer_arn(
                        f"loadbalancer/net/{arn_builder.cluster_name}*/*"
                    ),
                ],
                effect=iam.Effect.ALLOW,
            ),
            # EC2 Security Group permissions
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "ec2:AuthorizeSecurityGroupEgress",
                    "ec2:RevokeSecurityGroupEgress",
                ],
                resources=[
                    arn_builder.get_security_group_arn,
                    arn_builder.get_security_group_rule_arn,
                ],
            ),
            # Lambda invoke permissions
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["lambda:InvokeFunction"],
                resources=[
                    arn_builder.get_lambda_function_arn(
                        f"{arn_builder.cluster_name}-configure_sso"
                    )
                ],
            ),
            # ECS permissions
            iam.PolicyStatement(
                conditions={
                    "ArnEquals": {
                        "ecs:cluster": arn_builder.get_ecs_cluster_arn(
                            f"{arn_builder.cluster_name}-*"
                        )
                    }
                },
                effect=iam.Effect.ALLOW,
                actions=["ecs:RunTask", "ecs:StopTask", "ecs:ListTasks"],
                resources=["*"],
            ),
            iam.PolicyStatement(
                actions=["ec2:DescribeSecurityGroups"],
                resources=["*"],
                effect=iam.Effect.ALLOW,
            ),
            iam.PolicyStatement(
                actions=["iam:PassRole"],
                resources=[arn_builder.get_iam_arn(f"ad-sync-task-role")],
                effect=iam.Effect.ALLOW,
            ),
        ]

        policy_statements.extend(
            CustomKmsKeyPolicy.create_policy_statements(arn_builder)
        )

        return policy_statements
