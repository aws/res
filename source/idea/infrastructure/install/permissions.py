#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import aws_cdk
from aws_cdk import aws_iam as iam
from constructs import Construct, DependencyGroup


class Permissions(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        dependency_group: DependencyGroup,
        environment_name: str,
    ):
        super().__init__(scope, id)
        # TODO: Split role into separate Install/Delete/Update roles to allow for finer grained permissions
        self.pipeline_role = iam.Role(
            self,
            "PipelineRole",
            assumed_by=self.get_principal(),
            role_name=f"Admin-{environment_name}-PipelineRole",
        )

        self.pipeline_role.add_to_policy(statement=self.get_cloudformation_access())
        self.pipeline_role.add_to_policy(statement=self.get_directoryservice_access())
        self.pipeline_role.add_to_policy(statement=self.get_dynamodb_access())
        self.pipeline_role.add_to_policy(statement=self.get_ecr_access())
        self.pipeline_role.add_to_policy(
            statement=self.get_ecr_authorizationtoken_access()
        )
        self.pipeline_role.add_to_policy(statement=self.get_ec2_access())
        self.pipeline_role.add_to_policy(statement=self.get_ec2_describe_access())
        self.pipeline_role.add_to_policy(statement=self.get_efs_access())
        self.pipeline_role.add_to_policy(statement=self.get_elb_access())
        self.pipeline_role.add_to_policy(statement=self.get_elb_readonly_access())
        self.pipeline_role.add_to_policy(statement=self.get_es_access())
        self.pipeline_role.add_to_policy(statement=self.get_cloudtrail_access())
        self.pipeline_role.add_to_policy(statement=self.get_fsx_access())
        self.pipeline_role.add_to_policy(statement=self.get_iam_access())
        self.pipeline_role.add_to_policy(statement=self.get_kms_access())
        self.pipeline_role.add_to_policy(statement=self.get_lambda_access())
        self.pipeline_role.add_to_policy(statement=self.get_cloudwatch_logs_access())
        self.pipeline_role.add_to_policy(statement=self.get_cloudwatch_access())
        self.pipeline_role.add_to_policy(statement=self.get_route53_access())
        self.pipeline_role.add_to_policy(statement=self.get_s3_access())
        self.pipeline_role.add_to_policy(statement=self.get_secretsmanager_access())
        self.pipeline_role.add_to_policy(statement=self.get_ssm_access())
        self.pipeline_role.add_to_policy(statement=self.get_sns_access())
        self.pipeline_role.add_to_policy(statement=self.get_sqs_access())
        self.pipeline_role.add_to_policy(statement=self.get_sts_access())
        self.pipeline_role.add_to_policy(statement=self.get_tag_access())
        self.pipeline_role.add_to_policy(statement=self.get_cognito_idp_access())
        self.pipeline_role.add_to_policy(statement=self.get_cognito_idp_list_access())

        dependency_group.add(self.pipeline_role)

    def get_principal(self) -> iam.ServicePrincipal:
        return iam.ServicePrincipal(
            "ecs-tasks.amazonaws.com",
            conditions={
                "ArnLike": {
                    "aws:SourceArn": f"arn:{aws_cdk.Aws.PARTITION}:ecs:{aws_cdk.Aws.REGION}:{aws_cdk.Aws.ACCOUNT_ID}:*"
                },
                "StringEquals": {"aws:SourceAccount": aws_cdk.Aws.ACCOUNT_ID},
            },
        )

    def get_cloudformation_access(self) -> iam.PolicyStatement:
        return iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            resources=[
                f"arn:{aws_cdk.Aws.PARTITION}:cloudformation:{aws_cdk.Aws.REGION}:{aws_cdk.Aws.ACCOUNT_ID}:stack/res-*"
            ],
            actions=[
                "cloudformation:CreateChangeSet",
                "cloudformation:CreateStack",
                "cloudformation:DeleteChangeSet",
                "cloudformation:DeleteStack",
                "cloudformation:DescribeChangeSet",
                "cloudformation:DescribeStackEvents",
                "cloudformation:DescribeStacks",
                "cloudformation:ExecuteChangeSet",
                "cloudformation:GetTemplate",
                "cloudformation:UpdateTerminationProtection",
            ],
        )

    def get_directoryservice_access(self) -> iam.PolicyStatement:
        return iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            resources=[
                f"arn:{aws_cdk.Aws.PARTITION}:ds:{aws_cdk.Aws.REGION}:{aws_cdk.Aws.ACCOUNT_ID}:*"
            ],
            actions=["ds:CreateMicrosoftAD", "ds:DescribeDirectories"],
        )

    def get_dynamodb_access(self) -> iam.PolicyStatement:
        return iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            resources=[
                f"arn:{aws_cdk.Aws.PARTITION}:dynamodb:{aws_cdk.Aws.REGION}:{aws_cdk.Aws.ACCOUNT_ID}:*"
            ],
            actions=["dynamodb:*"],
        )

    def get_ecr_access(self) -> iam.PolicyStatement:
        return iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            resources=[
                f"arn:{aws_cdk.Aws.PARTITION}:ecr:{aws_cdk.Aws.REGION}:{aws_cdk.Aws.ACCOUNT_ID}:*"
            ],
            actions=["ecr:*"],
        )

    def get_ecr_authorizationtoken_access(self) -> iam.PolicyStatement:
        return iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            resources=["*"],
            actions=["ecr:GetAuthorizationToken"],
        )

    def get_ec2_access(self) -> iam.PolicyStatement:
        return iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            resources=[
                f"arn:{aws_cdk.Aws.PARTITION}:ec2:{aws_cdk.Aws.REGION}:{aws_cdk.Aws.ACCOUNT_ID}:*"
            ],
            actions=["ec2:*"],
        )

    def get_ec2_describe_access(self) -> iam.PolicyStatement:
        return iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            resources=["*"],
            actions=[
                "ec2:DescribeTags",
                "ec2:DescribeInstances",
                "ec2:DescribeRegions",
            ],
        )

    def get_efs_access(self) -> iam.PolicyStatement:
        return iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            resources=[
                f"arn:{aws_cdk.Aws.PARTITION}:elasticfilesystem:{aws_cdk.Aws.REGION}:{aws_cdk.Aws.ACCOUNT_ID}:*"
            ],
            actions=[
                "elasticfilesystem:CreateFileSystem",
                "elasticfilesystem:CreateMountTarget",
                "elasticfilesystem:DescribeFileSystems",
                "elasticfilesystem:DescribeMountTargets",
                "elasticfilesystem:PutFileSystemPolicy",
                "elasticfilesystem:PutLifecycleConfiguration",
            ],
        )

    def get_elb_access(self) -> iam.PolicyStatement:
        return iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            resources=[
                f"arn:{aws_cdk.Aws.PARTITION}:elasticloadbalancing:{aws_cdk.Aws.REGION}:{aws_cdk.Aws.ACCOUNT_ID}:*"
            ],
            actions=["elasticloadbalancing:*"],
        )

    def get_elb_readonly_access(self) -> iam.PolicyStatement:
        return iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            resources=["*"],
            actions=["elasticloadbalancing:Describe*"],
        )

    def get_es_access(self) -> iam.PolicyStatement:
        return iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            resources=[
                f"arn:{aws_cdk.Aws.PARTITION}:es:{aws_cdk.Aws.REGION}:{aws_cdk.Aws.ACCOUNT_ID}:*"
            ],
            actions=[
                "es:AddTags",
                "es:CreateElasticsearchDomain",
                "es:DescribeElasticsearchDomain",
                "es:ListDomainNames",
            ],
        )

    def get_cloudtrail_access(self) -> iam.PolicyStatement:
        return iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            resources=[
                f"arn:{aws_cdk.Aws.PARTITION}:events:{aws_cdk.Aws.REGION}:{aws_cdk.Aws.ACCOUNT_ID}:*"
            ],
            actions=["events:*"],
        )

    def get_fsx_access(self) -> iam.PolicyStatement:
        return iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            resources=[
                f"arn:{aws_cdk.Aws.PARTITION}:fsx:{aws_cdk.Aws.REGION}:{aws_cdk.Aws.ACCOUNT_ID}:*"
            ],
            actions=[
                "fsx:CreateFileSystem",
                "fsx:DescribeFileSystems",
                "fsx:TagResource",
            ],
        )

    def get_iam_access(self) -> iam.PolicyStatement:
        return iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            resources=[f"arn:{aws_cdk.Aws.PARTITION}:iam::{aws_cdk.Aws.ACCOUNT_ID}:*"],
            actions=[
                "iam:AddRoleToInstanceProfile",
                "iam:AttachRolePolicy",
                "iam:CreateInstanceProfile",
                "iam:CreateRole",
                "iam:DeleteRolePolicy",
                "iam:DetachRolePolicy",
                "iam:GetRole",
                "iam:GetRolePolicy",
                "iam:ListRoles",
                "iam:PassRole",
                "iam:PutRolePolicy",
                "iam:TagRole",
                "iam:DeleteRole",
            ],
        )

    def get_kms_access(self) -> iam.PolicyStatement:
        return iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            resources=[
                f"arn:{aws_cdk.Aws.PARTITION}:kms:{aws_cdk.Aws.REGION}:{aws_cdk.Aws.ACCOUNT_ID}:*"
            ],
            actions=[
                "kms:CreateGrant",
                "kms:Decrypt",
                "kms:DescribeKey",
                "kms:GenerateDataKey",
                "kms:RetireGrant",
            ],
        )

    def get_lambda_access(self) -> iam.PolicyStatement:
        return iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            resources=[
                f"arn:{aws_cdk.Aws.PARTITION}:lambda:{aws_cdk.Aws.REGION}:{aws_cdk.Aws.ACCOUNT_ID}:*"
            ],
            actions=[
                "lambda:AddPermission",
                "lambda:CreateFunction",
                "lambda:GetFunction",
                "lambda:InvokeFunction",
            ],
        )

    def get_cloudwatch_logs_access(self) -> iam.PolicyStatement:
        return iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            resources=[
                f"arn:{aws_cdk.Aws.PARTITION}:logs:{aws_cdk.Aws.REGION}:{aws_cdk.Aws.ACCOUNT_ID}:*"
            ],
            actions=[
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:DescribeLogGroups",
                "logs:PutRetentionPolicy",
            ],
        )

    def get_cloudwatch_access(self) -> iam.PolicyStatement:
        return iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            resources=[
                f"arn:{aws_cdk.Aws.PARTITION}:cloudwatch:{aws_cdk.Aws.REGION}:{aws_cdk.Aws.ACCOUNT_ID}:*"
            ],
            actions=["cloudwatch:*"],
        )

    def get_route53_access(self) -> iam.PolicyStatement:
        return iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            resources=[f"arn:{aws_cdk.Aws.PARTITION}:route53:::*"],
            actions=["route53:*"],
        )

    def get_s3_access(self) -> iam.PolicyStatement:
        return iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            resources=[f"arn:{aws_cdk.Aws.PARTITION}:s3:::*"],
            actions=[
                "s3:*",
            ],
        )

    def get_secretsmanager_access(self) -> iam.PolicyStatement:
        return iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            resources=[
                f"arn:{aws_cdk.Aws.PARTITION}:secretsmanager:{aws_cdk.Aws.REGION}:{aws_cdk.Aws.ACCOUNT_ID}:*"
            ],
            actions=["secretsmanager:CreateSecret", "secretsmanager:TagResource"],
        )

    def get_sns_access(self) -> iam.PolicyStatement:
        return iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            resources=[
                f"arn:{aws_cdk.Aws.PARTITION}:sns:{aws_cdk.Aws.REGION}:{aws_cdk.Aws.ACCOUNT_ID}:*"
            ],
            actions=[
                "sns:CreateTopic",
                "sns:GetTopicAttributes",
                "sns:ListSubscriptionsByTopic",
                "sns:SetTopicAttributes",
                "sns:Subscribe",
                "sns:TagResource",
            ],
        )

    def get_sqs_access(self) -> iam.PolicyStatement:
        return iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            resources=[
                f"arn:{aws_cdk.Aws.PARTITION}:sqs:{aws_cdk.Aws.REGION}:{aws_cdk.Aws.ACCOUNT_ID}:*"
            ],
            actions=["sqs:*"],
        )

    def get_ssm_access(self) -> iam.PolicyStatement:
        return iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            resources=[
                f"arn:{aws_cdk.Aws.PARTITION}:ssm:{aws_cdk.Aws.REGION}:{aws_cdk.Aws.ACCOUNT_ID}:*",
                f"arn:{aws_cdk.Aws.PARTITION}:ec2:{aws_cdk.Aws.REGION}:{aws_cdk.Aws.ACCOUNT_ID}:*",
                f"arn:{aws_cdk.Aws.PARTITION}:ssm:{aws_cdk.Aws.REGION}::document/AWS-RunShellScript",
            ],
            actions=[
                "ssm:*",
            ],
        )

    def get_sts_access(self) -> iam.PolicyStatement:
        return iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            resources=[
                f"arn:{aws_cdk.Aws.PARTITION}:sts::{aws_cdk.Aws.ACCOUNT_ID}:*",
                f"arn:{aws_cdk.Aws.PARTITION}:iam::{aws_cdk.Aws.ACCOUNT_ID}:role/*",
            ],
            actions=["sts:*"],
        )

    def get_tag_access(self) -> iam.PolicyStatement:
        return iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            resources=["*"],
            actions=["tag:GetResources"],
        )

    def get_cognito_idp_access(self) -> iam.PolicyStatement:
        return iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            resources=[
                f"arn:{aws_cdk.Aws.PARTITION}:cognito-idp:{aws_cdk.Aws.REGION}:{aws_cdk.Aws.ACCOUNT_ID}:*"
            ],
            actions=["cognito-idp:*"],
        )

    def get_cognito_idp_list_access(self) -> iam.PolicyStatement:
        return iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            resources=["*"],
            actions=["cognito-idp:ListUserPools"],
        )
