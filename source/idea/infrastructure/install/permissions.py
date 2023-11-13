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

        self.install_role = iam.Role(
            self,
            "InstallRole",
            assumed_by=self.get_principal(),
            role_name=f"Admin-{environment_name}-InstallRole",
        )
        self.install_role.add_to_policy(statement=self.get_install_policy_statement())
        dependency_group.add(self.install_role)

        self.update_role = iam.Role(
            self,
            "UpdateRole",
            assumed_by=self.get_principal(),
            role_name=f"Admin-{environment_name}-UpdateRole",
        )
        self.update_role.add_to_policy(statement=self.get_install_policy_statement())
        dependency_group.add(self.update_role)

        self.delete_role = iam.Role(
            self,
            "DeleteRole",
            assumed_by=self.get_principal(),
            role_name=f"Admin-{environment_name}-DeleteRole",
        )
        self.delete_role.add_to_policy(statement=self.get_install_policy_statement())
        dependency_group.add(self.delete_role)

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

    def get_install_policy_statement(self) -> iam.PolicyStatement:
        return iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            resources=["*"],
            actions=[
                "*",  # TODO: narrow the scope of these permissions
                "backup-storage:MountCapsule",
                "backup:CreateBackupPlan",
                "backup:CreateBackupSelection",
                "backup:CreateBackupVault",
                "backup:DescribeBackupVault",
                "backup:GetBackupPlan",
                "backup:GetBackupSelection",
                "backup:TagResource",
                "cloudformation:CreateChangeSet",
                "cloudformation:CreateStack",
                "cloudformation:DeleteChangeSet",
                "cloudformation:DescribeChangeSet",
                "cloudformation:DescribeStackEvents",
                "cloudformation:DescribeStacks",
                "cloudformation:ExecuteChangeSet",
                "cloudformation:GetTemplate",
                "cloudformation:UpdateTerminationProtection",
                "cloudwatch:PutMetricAlarm",
                "ds:CreateMicrosoftAD",
                "ds:DescribeDirectories",
                "dynamodb:*",
                "ec2:AllocateAddress",
                "ec2:AssociateAddress",
                "ec2:AssociateRouteTable",
                "ec2:AttachInternetGateway",
                "ec2:AuthorizeSecurityGroupEgress",
                "ec2:AuthorizeSecurityGroupIngress",
                "ec2:CreateFlowLogs",
                "ec2:CreateInternetGateway",
                "ec2:CreateNatGateway",
                "ec2:CreateNetworkInterface",
                "ec2:CreateNetworkInterfacePermission",
                "ec2:CreateRoute",
                "ec2:CreateRouteTable",
                "ec2:CreateSecurityGroup",
                "ec2:CreateSubnet",
                "ec2:CreateTags",
                "ec2:CreateVpc",
                "ec2:CreateVpcEndpoint",
                "ec2:DescribeAddresses",
                "ec2:DescribeAvailabilityZones",
                "ec2:DescribeFlowLogs",
                "ec2:DescribeImages",
                "ec2:DescribeInstances",
                "ec2:DescribeInternetGateways",
                "ec2:DescribeKeyPairs",
                "ec2:DescribeNatGateways",
                "ec2:DescribeNetwork*",
                "ec2:DescribeNetworkInterfaces",
                "ec2:DescribeRegions",
                "ec2:DescribeRouteTables",
                "ec2:DescribeSecurityGroups",
                "ec2:DescribeSubnets",
                "ec2:DescribeTags",
                "ec2:DescribeVpcAttribute",
                "ec2:DescribeVpcEndpointServices",
                "ec2:DescribeVpcEndpoints",
                "ec2:DescribeVpcs",
                "ec2:ModifySubnetAttribute",
                "ec2:ModifyVpcAttribute",
                "ec2:RevokeSecurityGroupEgress",
                "ec2:RunInstances",
                "elasticfilesystem:CreateFileSystem",
                "elasticfilesystem:CreateMountTarget",
                "elasticfilesystem:DescribeFileSystems",
                "elasticfilesystem:DescribeMountTargets",
                "elasticfilesystem:PutFileSystemPolicy",
                "elasticfilesystem:PutLifecycleConfiguration",
                "elasticloadbalancing:AddTags",
                "elasticloadbalancing:CreateListener",
                "elasticloadbalancing:CreateLoadBalancer",
                "elasticloadbalancing:CreateRule",
                "elasticloadbalancing:CreateTargetGroup",
                "elasticloadbalancing:DeleteTargetGroup",
                "elasticloadbalancing:DescribeListeners",
                "elasticloadbalancing:DescribeLoadBalancers",
                "elasticloadbalancing:DescribeRules",
                "elasticloadbalancing:DescribeTargetGroups",
                "elasticloadbalancing:DescribeTargetHealth",
                "elasticloadbalancing:ModifyLoadBalancerAttributes",
                "elasticloadbalancing:ModifyRule",
                "elasticloadbalancing:RegisterTargets",
                "es:AddTags",
                "es:CreateElasticsearchDomain",
                "es:DescribeElasticsearchDomain",
                "es:ListDomainNames",
                "events:*",
                "fsx:CreateFileSystem",
                "fsx:DescribeFileSystems",
                "fsx:TagResource",
                "iam:AddRoleToInstanceProfile",
                "iam:AttachRolePolicy",
                "iam:CreateInstanceProfile",
                "iam:CreateRole",
                "iam:GetRole",
                "iam:GetRolePolicy",
                "iam:ListRoles",
                "iam:PassRole",
                "iam:PutRolePolicy",
                "iam:TagRole",
                "kms:CreateGrant",
                "kms:Decrypt",
                "kms:DescribeKey",
                "kms:GenerateDataKey",
                "kms:RetireGrant",
                "lambda:AddPermission",
                "lambda:CreateFunction",
                "lambda:GetFunction",
                "lambda:InvokeFunction",
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:DescribeLogGroups",
                "logs:PutRetentionPolicy",
                "route53:CreateHostedZone",
                "route53:CreateVPCAssociationAuthorization",
                "route53:GetHostedZone",
                "route53resolver:AssociateResolverEndpointIpAddress",
                "route53resolver:AssociateResolverRule",
                "route53resolver:CreateResolverEndpoint",
                "route53resolver:CreateResolverRule",
                "route53resolver:GetResolverEndpoint",
                "route53resolver:GetResolverRule",
                "route53resolver:GetResolverRuleAssociation",
                "route53resolver:PutResolverRulePolicy",
                "route53resolver:TagResource",
                "s3:*Object",
                "s3:GetBucketLocation",
                "s3:ListBucket",
                "secretsmanager:CreateSecret",
                "secretsmanager:TagResource",
                "sns:CreateTopic",
                "sns:GetTopicAttributes",
                "sns:ListSubscriptionsByTopic",
                "sns:SetTopicAttributes",
                "sns:Subscribe",
                "sns:TagResource",
                "sqs:*",
                "sts:DecodeAuthorizationMessage",
            ],
        )
