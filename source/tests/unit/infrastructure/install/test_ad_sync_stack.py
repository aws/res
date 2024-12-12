#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from aws_cdk.assertions import Template

from idea.infrastructure.install.constants import (
    RES_COMMON_LAMBDA_RUNTIME,
    RES_ECR_REPO_NAME_SUFFIX,
)
from idea.infrastructure.install.parameters.common import CommonKey
from idea.infrastructure.install.stacks.ad_sync_stack import ADSyncStack
from ideadatamodel import constants  # type: ignore
from tests.unit.infrastructure.install import util


def test_stack_description(ad_sync_template: Template) -> None:
    ad_sync_template.template_matches(
        {"Description": "Nested Stack for supporting AD Sync"}
    )


def test_ad_sync_security_group_creation(
    ad_sync_stack: ADSyncStack, ad_sync_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        ad_sync_stack.nested_stack,
        ad_sync_template,
        resources=["ADSyncSecurityGroup"],
        cfn_type="AWS::EC2::SecurityGroup",
        props={
            "Properties": {
                "GroupDescription": "Security group for AD Sync task",
                "SecurityGroupEgress": [
                    {
                        "CidrIp": "0.0.0.0/0",
                        "Description": "Allow all outbound traffic by default",
                        "IpProtocol": "-1",
                    }
                ],
            }
        },
    )


def test_ad_sync_lock_table_creation(
    ad_sync_stack: ADSyncStack,
    ad_sync_template: Template,
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        ad_sync_stack.nested_stack,
        ad_sync_template,
        resources=["ad-sync-distributed-lock-table"],
        cfn_type="AWS::DynamoDB::Table",
        props={
            "UpdateReplacePolicy": "Delete",
            "DeletionPolicy": "Delete",
            "Properties": {
                "TableName": {
                    "Fn::Join": [
                        "",
                        [
                            ad_sync_stack.nested_stack.resolve(
                                ad_sync_stack.cluster_name
                            ),
                            ".ad-sync.distributed-lock",
                        ],
                    ]
                },
                "KeySchema": [
                    {"AttributeName": "lock_key", "KeyType": "HASH"},
                    {"AttributeName": "sort_key", "KeyType": "RANGE"},
                ],
            },
        },
    )


def test_scheduled_ad_sync_lambda_role_creation(
    ad_sync_stack: ADSyncStack,
    ad_sync_template: Template,
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        ad_sync_stack.nested_stack,
        ad_sync_template,
        resources=["scheduled-ad-sync-role"],
        cfn_type="AWS::IAM::Role",
        props={
            "Properties": {
                "AssumeRolePolicyDocument": {
                    "Statement": [
                        {
                            "Action": "sts:AssumeRole",
                            "Effect": "Allow",
                            "Principal": {"Service": "lambda.amazonaws.com"},
                        }
                    ],
                },
                "PermissionsBoundary": {
                    "Fn::If": [
                        "PermissionBoundaryProvided",
                        ad_sync_stack.nested_stack.resolve(
                            ad_sync_stack.parameters.get_str(
                                CommonKey.IAM_PERMISSION_BOUNDARY
                            )
                        ),
                        {"Ref": "AWS::NoValue"},
                    ]
                },
                "RoleName": {
                    "Fn::Join": [
                        "",
                        [
                            ad_sync_stack.nested_stack.resolve(
                                ad_sync_stack.cluster_name
                            ),
                            "-scheduled-ad-sync-role",
                        ],
                    ]
                },
                "Tags": [
                    {
                        "Key": constants.IDEA_TAG_NAME,
                        "Value": {
                            "Fn::Join": [
                                "",
                                [
                                    ad_sync_stack.nested_stack.resolve(
                                        ad_sync_stack.cluster_name
                                    ),
                                    "-ad-sync",
                                ],
                            ]
                        },
                    },
                    {
                        "Key": constants.IDEA_TAG_ENVIRONMENT_NAME,
                        "Value": ad_sync_stack.nested_stack.resolve(
                            ad_sync_stack.cluster_name
                        ),
                    },
                ],
            }
        },
    )


def test_scheduled_ad_sync_lambda_role_policy_creation(
    ad_sync_stack: ADSyncStack,
    ad_sync_template: Template,
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        ad_sync_stack.nested_stack,
        ad_sync_template,
        resources=["scheduled-ad-sync-policy"],
        cfn_type="AWS::IAM::Policy",
        props={
            "Properties": {
                "PolicyDocument": {
                    "Statement": [
                        {
                            "Action": "logs:CreateLogGroup",
                            "Effect": "Allow",
                            "Resource": "*",
                            "Sid": "CloudWatchLogsPermissions",
                        },
                        {
                            "Action": [
                                "logs:CreateLogStream",
                                "logs:PutLogEvents",
                                "logs:DeleteLogStream",
                            ],
                            "Effect": "Allow",
                            "Resource": "*",
                            "Sid": "CloudWatchLogStreamPermissions",
                        },
                        {
                            "Action": [
                                "dynamodb:GetItem",
                                "dynamodb:Scan",
                            ],
                            "Effect": "Allow",
                            "Resource": {
                                "Fn::Join": [
                                    "",
                                    [
                                        "arn:",
                                        {"Ref": "AWS::Partition"},
                                        ":dynamodb:",
                                        {"Ref": "AWS::Region"},
                                        ":",
                                        {"Ref": "AWS::AccountId"},
                                        ":table/",
                                        ad_sync_stack.nested_stack.resolve(
                                            ad_sync_stack.cluster_name
                                        ),
                                        ".cluster-settings",
                                    ],
                                ]
                            },
                            "Sid": "ClusterSettingsTablePermissions",
                        },
                        {
                            "Action": [
                                "dynamodb:GetItem",
                                "dynamodb:PutItem",
                                "dynamodb:DeleteItem",
                            ],
                            "Effect": "Allow",
                            "Resource": {
                                "Fn::Join": [
                                    "",
                                    [
                                        "arn:",
                                        {"Ref": "AWS::Partition"},
                                        ":dynamodb:",
                                        {"Ref": "AWS::Region"},
                                        ":",
                                        {"Ref": "AWS::AccountId"},
                                        ":table/",
                                        ad_sync_stack.nested_stack.resolve(
                                            ad_sync_stack.cluster_name
                                        ),
                                        ".ad-sync.distributed-lock",
                                    ],
                                ]
                            },
                            "Sid": "ADSyncLockTablePermissions",
                        },
                        {
                            "Action": [
                                "ecs:RunTask",
                                "ecs:StopTask",
                                "ecs:ListTasks",
                            ],
                            "Condition": {
                                "ArnEquals": {
                                    "ecs:cluster": {
                                        "Fn::GetAtt": ["ADSyncCluster1AEA8808", "Arn"]
                                    }
                                }
                            },
                            "Effect": "Allow",
                            "Resource": "*",
                        },
                        {
                            "Action": "iam:PassRole",
                            "Effect": "Allow",
                            "Resource": {
                                "Fn::Join": [
                                    "",
                                    [
                                        "arn:",
                                        {"Ref": "AWS::Partition"},
                                        ":iam::",
                                        {"Ref": "AWS::AccountId"},
                                        ":role/",
                                        ad_sync_stack.nested_stack.resolve(
                                            ad_sync_stack.cluster_name
                                        ),
                                        "-ad-sync-task-role",
                                    ],
                                ]
                            },
                        },
                        {
                            "Action": "ec2:DescribeSecurityGroups",
                            "Effect": "Allow",
                            "Resource": "*",
                        },
                    ],
                },
                "PolicyName": {
                    "Fn::Join": [
                        "",
                        [
                            ad_sync_stack.nested_stack.resolve(
                                ad_sync_stack.cluster_name
                            ),
                            "-scheduled-ad-sync-policy",
                        ],
                    ]
                },
                "Roles": [
                    {
                        "Ref": util.get_logical_id(
                            ad_sync_stack.nested_stack, ["scheduled-ad-sync-role"]
                        )
                    }
                ],
            }
        },
    )


def test_scheduled_ad_sync_lambda_creation(
    ad_sync_stack: ADSyncStack,
    ad_sync_template: Template,
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        ad_sync_stack.nested_stack,
        ad_sync_template,
        resources=["scheduled-ad-sync"],
        cfn_type="AWS::Lambda::Function",
        props={
            "Properties": {
                "FunctionName": {
                    "Fn::Join": [
                        "",
                        [
                            ad_sync_stack.nested_stack.resolve(
                                ad_sync_stack.cluster_name
                            ),
                            "-scheduled-ad-sync",
                        ],
                    ]
                },
                "Handler": "scheduled_ad_sync_handler.handler",
                "Role": {
                    "Fn::GetAtt": [
                        util.get_logical_id(
                            ad_sync_stack.nested_stack, ["scheduled-ad-sync-role"]
                        ),
                        "Arn",
                    ]
                },
                "Runtime": RES_COMMON_LAMBDA_RUNTIME.to_string(),
                "Tags": [
                    {
                        "Key": constants.IDEA_TAG_NAME,
                        "Value": {
                            "Fn::Join": [
                                "",
                                [
                                    ad_sync_stack.nested_stack.resolve(
                                        ad_sync_stack.cluster_name
                                    ),
                                    "-ad-sync",
                                ],
                            ]
                        },
                    },
                    {
                        "Key": constants.IDEA_TAG_ENVIRONMENT_NAME,
                        "Value": ad_sync_stack.nested_stack.resolve(
                            ad_sync_stack.cluster_name
                        ),
                    },
                ],
            }
        },
    )


def test_ad_sync_scheduled_rule_creation(
    ad_sync_stack: ADSyncStack,
    ad_sync_template: Template,
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        ad_sync_stack.nested_stack,
        ad_sync_template,
        resources=["ad-sync-schedule-rule"],
        cfn_type="AWS::Events::Rule",
        props={
            "Properties": {
                "Name": {
                    "Fn::Join": [
                        "",
                        [
                            ad_sync_stack.nested_stack.resolve(
                                ad_sync_stack.cluster_name
                            ),
                            "-ad-sync-schedule-rule",
                        ],
                    ]
                },
                "ScheduleExpression": "cron(0 0/1 * * ? *)",
                "State": "ENABLED",
                "Targets": [
                    {
                        "Arn": {
                            "Fn::GetAtt": [
                                util.get_logical_id(
                                    ad_sync_stack.nested_stack, ["scheduled-ad-sync"]
                                ),
                                "Arn",
                            ]
                        },
                        "Id": "Target0",
                    }
                ],
            }
        },
    )


def test_ad_sync_task_role(
    ad_sync_stack: ADSyncStack,
    ad_sync_template: Template,
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        ad_sync_stack.nested_stack,
        ad_sync_template,
        resources=["ad-sync-task-role"],
        cfn_type="AWS::IAM::Role",
        props={
            "Properties": {
                "AssumeRolePolicyDocument": {
                    "Statement": [
                        {
                            "Action": "sts:AssumeRole",
                            "Effect": "Allow",
                            "Principal": {"Service": "ecs-tasks.amazonaws.com"},
                        }
                    ],
                },
                "PermissionsBoundary": {
                    "Fn::If": [
                        "PermissionBoundaryProvided",
                        ad_sync_stack.nested_stack.resolve(
                            ad_sync_stack.parameters.get_str(
                                CommonKey.IAM_PERMISSION_BOUNDARY
                            )
                        ),
                        {"Ref": "AWS::NoValue"},
                    ]
                },
                "RoleName": {
                    "Fn::Join": [
                        "",
                        [
                            ad_sync_stack.nested_stack.resolve(
                                ad_sync_stack.cluster_name
                            ),
                            "-ad-sync-task-role",
                        ],
                    ]
                },
                "Tags": [
                    {
                        "Key": constants.IDEA_TAG_NAME,
                        "Value": {
                            "Fn::Join": [
                                "",
                                [
                                    ad_sync_stack.nested_stack.resolve(
                                        ad_sync_stack.cluster_name
                                    ),
                                    "-ad-sync",
                                ],
                            ]
                        },
                    },
                    {
                        "Key": constants.IDEA_TAG_ENVIRONMENT_NAME,
                        "Value": ad_sync_stack.nested_stack.resolve(
                            ad_sync_stack.cluster_name
                        ),
                    },
                ],
            }
        },
    )


def test_ad_sync_task_policy_creation(
    ad_sync_stack: ADSyncStack,
    ad_sync_template: Template,
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        ad_sync_stack.nested_stack,
        ad_sync_template,
        resources=["ad-sync-task-policy"],
        cfn_type="AWS::IAM::Policy",
        props={
            "Properties": {
                "PolicyDocument": {
                    "Statement": [
                        {
                            "Action": "logs:CreateLogGroup",
                            "Effect": "Allow",
                            "Resource": "*",
                            "Sid": "CloudWatchLogsPermissions",
                        },
                        {
                            "Action": [
                                "logs:CreateLogStream",
                                "logs:PutLogEvents",
                                "logs:DeleteLogStream",
                            ],
                            "Effect": "Allow",
                            "Resource": "*",
                            "Sid": "CloudWatchLogStreamPermissions",
                        },
                        {
                            "Action": "secretsmanager:GetSecretValue",
                            "Effect": "Allow",
                            "Resource": "*",
                            "Sid": "SecretsManagerPermissions",
                        },
                        {
                            "Action": [
                                "dynamodb:GetItem",
                                "dynamodb:Query",
                                "dynamodb:Scan",
                                "dynamodb:UpdateItem",
                                "dynamodb:PutItem",
                                "dynamodb:DeleteItem",
                            ],
                            "Effect": "Allow",
                            "Resource": [
                                {
                                    "Fn::Join": [
                                        "",
                                        [
                                            "arn:",
                                            {"Ref": "AWS::Partition"},
                                            ":dynamodb:",
                                            {"Ref": "AWS::Region"},
                                            ":",
                                            {"Ref": "AWS::AccountId"},
                                            ":table/",
                                            ad_sync_stack.nested_stack.resolve(
                                                ad_sync_stack.cluster_name
                                            ),
                                            ".cluster-settings",
                                        ],
                                    ]
                                },
                                {
                                    "Fn::Join": [
                                        "",
                                        [
                                            "arn:",
                                            {"Ref": "AWS::Partition"},
                                            ":dynamodb:",
                                            {"Ref": "AWS::Region"},
                                            ":",
                                            {"Ref": "AWS::AccountId"},
                                            ":table/",
                                            ad_sync_stack.nested_stack.resolve(
                                                ad_sync_stack.cluster_name
                                            ),
                                            ".accounts.users",
                                        ],
                                    ]
                                },
                                {
                                    "Fn::Join": [
                                        "",
                                        [
                                            "arn:",
                                            {"Ref": "AWS::Partition"},
                                            ":dynamodb:",
                                            {"Ref": "AWS::Region"},
                                            ":",
                                            {"Ref": "AWS::AccountId"},
                                            ":table/",
                                            ad_sync_stack.nested_stack.resolve(
                                                ad_sync_stack.cluster_name
                                            ),
                                            ".accounts.users/index/*",
                                        ],
                                    ]
                                },
                                {
                                    "Fn::Join": [
                                        "",
                                        [
                                            "arn:",
                                            {"Ref": "AWS::Partition"},
                                            ":dynamodb:",
                                            {"Ref": "AWS::Region"},
                                            ":",
                                            {"Ref": "AWS::AccountId"},
                                            ":table/",
                                            ad_sync_stack.nested_stack.resolve(
                                                ad_sync_stack.cluster_name
                                            ),
                                            ".accounts.groups",
                                        ],
                                    ]
                                },
                                {
                                    "Fn::Join": [
                                        "",
                                        [
                                            "arn:",
                                            {"Ref": "AWS::Partition"},
                                            ":dynamodb:",
                                            {"Ref": "AWS::Region"},
                                            ":",
                                            {"Ref": "AWS::AccountId"},
                                            ":table/",
                                            ad_sync_stack.nested_stack.resolve(
                                                ad_sync_stack.cluster_name
                                            ),
                                            ".accounts.group-members",
                                        ],
                                    ]
                                },
                                {
                                    "Fn::Join": [
                                        "",
                                        [
                                            "arn:",
                                            {"Ref": "AWS::Partition"},
                                            ":dynamodb:",
                                            {"Ref": "AWS::Region"},
                                            ":",
                                            {"Ref": "AWS::AccountId"},
                                            ":table/",
                                            ad_sync_stack.nested_stack.resolve(
                                                ad_sync_stack.cluster_name
                                            ),
                                            ".projects",
                                        ],
                                    ]
                                },
                                {
                                    "Fn::Join": [
                                        "",
                                        [
                                            "arn:",
                                            {"Ref": "AWS::Partition"},
                                            ":dynamodb:",
                                            {"Ref": "AWS::Region"},
                                            ":",
                                            {"Ref": "AWS::AccountId"},
                                            ":table/",
                                            ad_sync_stack.nested_stack.resolve(
                                                ad_sync_stack.cluster_name
                                            ),
                                            ".projects/index/*",
                                        ],
                                    ]
                                },
                                {
                                    "Fn::Join": [
                                        "",
                                        [
                                            "arn:",
                                            {"Ref": "AWS::Partition"},
                                            ":dynamodb:",
                                            {"Ref": "AWS::Region"},
                                            ":",
                                            {"Ref": "AWS::AccountId"},
                                            ":table/",
                                            ad_sync_stack.nested_stack.resolve(
                                                ad_sync_stack.cluster_name
                                            ),
                                            ".authz.role-assignments",
                                        ],
                                    ]
                                },
                                {
                                    "Fn::Join": [
                                        "",
                                        [
                                            "arn:",
                                            {"Ref": "AWS::Partition"},
                                            ":dynamodb:",
                                            {"Ref": "AWS::Region"},
                                            ":",
                                            {"Ref": "AWS::AccountId"},
                                            ":table/",
                                            ad_sync_stack.nested_stack.resolve(
                                                ad_sync_stack.cluster_name
                                            ),
                                            ".authz.role-assignments/index/*",
                                        ],
                                    ]
                                },
                            ],
                        },
                        {
                            "Action": [
                                "ecr:BatchGetImage",
                                "ecr:DescribeRepositories",
                                "ecr:GetDownloadUrlForLayer",
                                "ecr:GetLifecyclePolicy",
                                "ecr:GetRepositoryPolicy",
                                "ecr:ListTagsForResource",
                            ],
                            "Effect": "Allow",
                            "Resource": {
                                "Fn::Join": [
                                    "",
                                    [
                                        "arn:",
                                        {"Ref": "AWS::Partition"},
                                        ":ecr:",
                                        {"Ref": "AWS::Region"},
                                        ":",
                                        {"Ref": "AWS::AccountId"},
                                        ":repository/",
                                        ad_sync_stack.nested_stack.resolve(
                                            ad_sync_stack.cluster_name
                                        ),
                                        RES_ECR_REPO_NAME_SUFFIX,
                                    ],
                                ]
                            },
                            "Sid": "ECRPermissions",
                        },
                        {
                            "Action": "ecr:GetAuthorizationToken",
                            "Effect": "Allow",
                            "Resource": "*",
                            "Sid": "ECRAuthorizationPermissions",
                        },
                    ],
                },
                "PolicyName": {
                    "Fn::Join": [
                        "",
                        [
                            ad_sync_stack.nested_stack.resolve(
                                ad_sync_stack.cluster_name
                            ),
                            "-ad-sync-task-policy",
                        ],
                    ]
                },
                "Roles": [
                    {
                        "Ref": util.get_logical_id(
                            ad_sync_stack.nested_stack, ["ad-sync-task-role"]
                        )
                    }
                ],
            }
        },
    )


def test_ad_sync_task_definition_creation(
    ad_sync_stack: ADSyncStack,
    ad_sync_template: Template,
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        ad_sync_stack.nested_stack,
        ad_sync_template,
        resources=["ad-sync-task-definition"],
        cfn_type="AWS::ECS::TaskDefinition",
        props={
            "Properties": {
                "ContainerDefinitions": [
                    {
                        "Command": [
                            "/bin/sh",
                            "-c",
                            "/bin/sh -ex <<'EOC'\nsource venv/bin/activate\nres-ad-sync\nEOC\n",
                        ],
                        "Environment": [
                            {
                                "Name": "environment_name",
                                "Value": ad_sync_stack.nested_stack.resolve(
                                    ad_sync_stack.cluster_name
                                ),
                            },
                            {
                                "Name": "AWS_DEFAULT_REGION",
                                "Value": {"Ref": "AWS::Region"},
                            },
                        ],
                        "Essential": True,
                        "Image": "fake-registry-name",
                        "LogConfiguration": {
                            "LogDriver": "awslogs",
                            "Options": {
                                "awslogs-group": {
                                    "Ref": util.get_logical_id(
                                        ad_sync_stack.nested_stack,
                                        ["ad-sync-task-log-group"],
                                    )
                                },
                                "awslogs-stream-prefix": "ecs",
                            },
                        },
                        "Name": "ad-sync-task-container",
                    }
                ],
                "Cpu": "512",
                "ExecutionRoleArn": {
                    "Fn::GetAtt": [
                        util.get_logical_id(
                            ad_sync_stack.nested_stack, ["ad-sync-task-role"]
                        ),
                        "Arn",
                    ]
                },
                "Family": {
                    "Fn::Join": [
                        "",
                        [
                            ad_sync_stack.nested_stack.resolve(
                                ad_sync_stack.cluster_name
                            ),
                            "-ad-sync-task-definition",
                        ],
                    ]
                },
                "Memory": "1024",
                "NetworkMode": "awsvpc",
                "RequiresCompatibilities": ["FARGATE"],
                "Tags": [
                    {
                        "Key": constants.IDEA_TAG_NAME,
                        "Value": {
                            "Fn::Join": [
                                "",
                                [
                                    ad_sync_stack.nested_stack.resolve(
                                        ad_sync_stack.cluster_name
                                    ),
                                    "-ad-sync",
                                ],
                            ]
                        },
                    },
                    {
                        "Key": constants.IDEA_TAG_ENVIRONMENT_NAME,
                        "Value": ad_sync_stack.nested_stack.resolve(
                            ad_sync_stack.cluster_name
                        ),
                    },
                ],
                "TaskRoleArn": {
                    "Fn::GetAtt": [
                        util.get_logical_id(
                            ad_sync_stack.nested_stack, ["ad-sync-task-role"]
                        ),
                        "Arn",
                    ]
                },
            }
        },
    )


def test_ad_sync_task_log_group_creation(
    ad_sync_stack: ADSyncStack,
    ad_sync_template: Template,
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        ad_sync_stack.nested_stack,
        ad_sync_template,
        resources=["ad-sync-task-log-group"],
        cfn_type="AWS::Logs::LogGroup",
        props={
            "Properties": {
                "LogGroupName": {
                    "Fn::Join": [
                        "",
                        [
                            ad_sync_stack.nested_stack.resolve(
                                ad_sync_stack.cluster_name
                            ),
                            "/ad-sync",
                        ],
                    ]
                },
            }
        },
    )


def test_terminate_ad_sync_ecs_task_role_creation(
    ad_sync_stack: ADSyncStack,
    ad_sync_template: Template,
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        ad_sync_stack.nested_stack,
        ad_sync_template,
        resources=["terminate-ad-sync-ecs-task-role"],
        cfn_type="AWS::IAM::Role",
        props={
            "Properties": {
                "AssumeRolePolicyDocument": {
                    "Statement": [
                        {
                            "Action": "sts:AssumeRole",
                            "Effect": "Allow",
                            "Principal": {"Service": "lambda.amazonaws.com"},
                        }
                    ],
                },
                "PermissionsBoundary": {
                    "Fn::If": [
                        "PermissionBoundaryProvided",
                        ad_sync_stack.nested_stack.resolve(
                            ad_sync_stack.parameters.get_str(
                                CommonKey.IAM_PERMISSION_BOUNDARY
                            )
                        ),
                        {"Ref": "AWS::NoValue"},
                    ]
                },
                "RoleName": {
                    "Fn::Join": [
                        "",
                        [
                            ad_sync_stack.nested_stack.resolve(
                                ad_sync_stack.cluster_name
                            ),
                            "-terminate-ad-sync-ecs-task-role",
                        ],
                    ]
                },
                "Tags": [
                    {
                        "Key": constants.IDEA_TAG_NAME,
                        "Value": {
                            "Fn::Join": [
                                "",
                                [
                                    ad_sync_stack.nested_stack.resolve(
                                        ad_sync_stack.cluster_name
                                    ),
                                    "-ad-sync",
                                ],
                            ]
                        },
                    },
                    {
                        "Key": constants.IDEA_TAG_ENVIRONMENT_NAME,
                        "Value": ad_sync_stack.nested_stack.resolve(
                            ad_sync_stack.cluster_name
                        ),
                    },
                ],
            }
        },
    )


def test_terminate_ad_sync_ecs_task_role_policy_creation(
    ad_sync_stack: ADSyncStack,
    ad_sync_template: Template,
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        ad_sync_stack.nested_stack,
        ad_sync_template,
        resources=["terminate-ad-sync-ecs-task-policy"],
        cfn_type="AWS::IAM::Policy",
        props={
            "Properties": {
                "PolicyDocument": {
                    "Statement": [
                        {
                            "Action": "logs:CreateLogGroup",
                            "Effect": "Allow",
                            "Resource": "*",
                            "Sid": "CloudWatchLogsPermissions",
                        },
                        {
                            "Action": [
                                "logs:CreateLogStream",
                                "logs:PutLogEvents",
                                "logs:DeleteLogStream",
                            ],
                            "Effect": "Allow",
                            "Resource": "*",
                            "Sid": "CloudWatchLogStreamPermissions",
                        },
                        {
                            "Action": [
                                "dynamodb:GetItem",
                                "dynamodb:PutItem",
                                "dynamodb:DeleteItem",
                            ],
                            "Effect": "Allow",
                            "Resource": {
                                "Fn::Join": [
                                    "",
                                    [
                                        "arn:",
                                        {"Ref": "AWS::Partition"},
                                        ":dynamodb:",
                                        {"Ref": "AWS::Region"},
                                        ":",
                                        {"Ref": "AWS::AccountId"},
                                        ":table/",
                                        ad_sync_stack.nested_stack.resolve(
                                            ad_sync_stack.cluster_name
                                        ),
                                        ".ad-sync.distributed-lock",
                                    ],
                                ]
                            },
                            "Sid": "ADSyncLockTablePermissions",
                        },
                        {
                            "Action": [
                                "ecs:StopTask",
                                "ecs:ListTasks",
                                "ecs:DescribeTasks",
                            ],
                            "Condition": {
                                "ArnEquals": {
                                    "ecs:cluster": {
                                        "Fn::GetAtt": ["ADSyncCluster1AEA8808", "Arn"]
                                    }
                                }
                            },
                            "Effect": "Allow",
                            "Resource": "*",
                        },
                        {
                            "Action": "iam:PassRole",
                            "Effect": "Allow",
                            "Resource": {
                                "Fn::Join": [
                                    "",
                                    [
                                        "arn:",
                                        {"Ref": "AWS::Partition"},
                                        ":iam::",
                                        {"Ref": "AWS::AccountId"},
                                        ":role/",
                                        ad_sync_stack.nested_stack.resolve(
                                            ad_sync_stack.cluster_name
                                        ),
                                        "-ad-sync-task-role",
                                    ],
                                ]
                            },
                        },
                    ],
                },
                "PolicyName": {
                    "Fn::Join": [
                        "",
                        [
                            ad_sync_stack.nested_stack.resolve(
                                ad_sync_stack.cluster_name
                            ),
                            "-terminate-ad-sync-ecs-task-policy",
                        ],
                    ]
                },
                "Roles": [
                    {
                        "Ref": util.get_logical_id(
                            ad_sync_stack.nested_stack,
                            ["terminate-ad-sync-ecs-task-role"],
                        )
                    }
                ],
            }
        },
    )


def test_terminate_ad_sync_ecs_task_lambda_creation(
    ad_sync_stack: ADSyncStack,
    ad_sync_template: Template,
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        ad_sync_stack.nested_stack,
        ad_sync_template,
        resources=["terminate-ad-sync-ecs-task"],
        cfn_type="AWS::Lambda::Function",
        props={
            "Properties": {
                "FunctionName": {
                    "Fn::Join": [
                        "",
                        [
                            ad_sync_stack.nested_stack.resolve(
                                ad_sync_stack.cluster_name
                            ),
                            "-terminate-ad-sync-ecs-task",
                        ],
                    ]
                },
                "Handler": "handler.handler",
                "Role": {
                    "Fn::GetAtt": [
                        util.get_logical_id(
                            ad_sync_stack.nested_stack,
                            ["terminate-ad-sync-ecs-task-role"],
                        ),
                        "Arn",
                    ]
                },
                "Runtime": RES_COMMON_LAMBDA_RUNTIME.to_string(),
                "Tags": [
                    {
                        "Key": constants.IDEA_TAG_NAME,
                        "Value": {
                            "Fn::Join": [
                                "",
                                [
                                    ad_sync_stack.nested_stack.resolve(
                                        ad_sync_stack.cluster_name
                                    ),
                                    "-ad-sync",
                                ],
                            ]
                        },
                    },
                    {
                        "Key": constants.IDEA_TAG_ENVIRONMENT_NAME,
                        "Value": ad_sync_stack.nested_stack.resolve(
                            ad_sync_stack.cluster_name
                        ),
                    },
                ],
            }
        },
    )


def test_terminate_ad_sync_ecs_task_custom_resource_creation(
    ad_sync_stack: ADSyncStack,
    ad_sync_template: Template,
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        ad_sync_stack.nested_stack,
        ad_sync_template,
        resources=["terminate-ad-sync-ecs-task-custom-resource"],
        cfn_type="Custom::TerminateADSyncECSTask",
        props={
            "Properties": {
                "ServiceToken": {
                    "Fn::GetAtt": [
                        util.get_logical_id(
                            ad_sync_stack.nested_stack, ["terminate-ad-sync-ecs-task"]
                        ),
                        "Arn",
                    ]
                },
            }
        },
    )
