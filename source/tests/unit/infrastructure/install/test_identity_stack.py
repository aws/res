#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from aws_cdk.assertions import Template
from res.constants import (  # type: ignore
    AD_SYNC_STATUS_SUBMISSION_TIME_KEY,
    AD_SYNC_STATUS_TABLE,
    AD_SYNC_STATUS_TASK_ID_KEY,
)

from idea.infrastructure.install.constants import (
    RES_COMMON_LAMBDA_RUNTIME,
    RES_ECR_REPO_NAME_SUFFIX,
)
from idea.infrastructure.install.parameters.common import CommonKey
from idea.infrastructure.install.stacks.identity_stack import IdentityStack
from ideadatamodel import constants  # type: ignore
from tests.unit.infrastructure.install import util


def test_stack_description(identity_template: Template) -> None:
    identity_template.template_matches(
        {"Description": "Nested Stack for supporting AD Sync"}
    )


def test_ad_sync_security_group_creation(
    identity_stack: IdentityStack, identity_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        identity_stack.nested_stack,
        identity_template,
        resources=["ad-sync-security-group-construct"],
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
    identity_stack: IdentityStack,
    identity_template: Template,
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        identity_stack.nested_stack,
        identity_template,
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
                            identity_stack.nested_stack.resolve(
                                identity_stack.cluster_name
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


def test_ad_sync_status_table_creation(
    identity_stack: IdentityStack,
    identity_template: Template,
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        identity_stack.nested_stack,
        identity_template,
        resources=["ad-sync-status-table"],
        cfn_type="AWS::DynamoDB::Table",
        props={
            "UpdateReplacePolicy": "Delete",
            "DeletionPolicy": "Delete",
            "Properties": {
                "TableName": {
                    "Fn::Join": [
                        "",
                        [
                            identity_stack.nested_stack.resolve(
                                identity_stack.cluster_name
                            ),
                            f".{AD_SYNC_STATUS_TABLE}",
                        ],
                    ]
                },
                "KeySchema": [
                    {"AttributeName": AD_SYNC_STATUS_TASK_ID_KEY, "KeyType": "HASH"},
                    {
                        "AttributeName": AD_SYNC_STATUS_SUBMISSION_TIME_KEY,
                        "KeyType": "RANGE",
                    },
                ],
            },
        },
    )


def test_scheduled_ad_sync_lambda_role_creation(
    identity_stack: IdentityStack,
    identity_template: Template,
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        identity_stack.nested_stack,
        identity_template,
        resources=["scheduled-ad-sync-construct", "ServiceRole"],
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
                        identity_stack.nested_stack.resolve(
                            identity_stack.parameters.get_str(
                                CommonKey.IAM_PERMISSION_BOUNDARY
                            )
                        ),
                        {"Ref": "AWS::NoValue"},
                    ]
                },
                "Path": identity_stack.nested_stack.resolve(
                    identity_stack.parameters.iam_resource_path_string
                ),
                "Tags": [
                    {
                        "Key": constants.IDEA_TAG_NAME,
                        "Value": {
                            "Fn::Join": [
                                "",
                                [
                                    identity_stack.nested_stack.resolve(
                                        identity_stack.cluster_name
                                    ),
                                    "-scheduled-ad-sync",
                                ],
                            ]
                        },
                    },
                    {
                        "Key": constants.IDEA_TAG_ENVIRONMENT_NAME,
                        "Value": identity_stack.nested_stack.resolve(
                            identity_stack.cluster_name
                        ),
                    },
                ],
            }
        },
    )


def test_scheduled_ad_sync_lambda_role_policy_creation(
    identity_stack: IdentityStack,
    identity_template: Template,
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        identity_stack.nested_stack,
        identity_template,
        resources=["scheduled-ad-sync-construct", "ServiceRole", "DefaultPolicy"],
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
                                        identity_stack.nested_stack.resolve(
                                            identity_stack.cluster_name
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
                                        identity_stack.nested_stack.resolve(
                                            identity_stack.cluster_name
                                        ),
                                        ".ad-sync.distributed-lock",
                                    ],
                                ]
                            },
                            "Sid": "ADSyncLockTablePermissions",
                        },
                        {
                            "Action": [
                                "dynamodb:Query",
                                "dynamodb:Scan",
                                "dynamodb:UpdateItem",
                                "dynamodb:PutItem",
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
                                        identity_stack.nested_stack.resolve(
                                            identity_stack.cluster_name
                                        ),
                                        ".ad-sync.status",
                                    ],
                                ]
                            },
                            "Sid": "ADSyncStatusTablePermissions",
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
                                        "Fn::Join": [
                                            "",
                                            [
                                                "arn:",
                                                {"Ref": "AWS::Partition"},
                                                ":ecs:",
                                                {"Ref": "AWS::Region"},
                                                ":",
                                                {"Ref": "AWS::AccountId"},
                                                ":cluster/",
                                                identity_stack.nested_stack.resolve(
                                                    identity_stack.cluster_name
                                                ),
                                                "-ad-sync-cluster",
                                            ],
                                        ]
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
                                        ":role",
                                        identity_stack.nested_stack.resolve(
                                            identity_stack.parameters.iam_resource_path_string
                                        ),
                                        identity_stack.nested_stack.resolve(
                                            identity_stack.parameters.iam_resource_prefix_string
                                        ),
                                        identity_stack.nested_stack.resolve(
                                            identity_stack.cluster_name
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
                "Roles": [
                    {
                        "Ref": util.get_logical_id(
                            identity_stack.nested_stack,
                            ["scheduled-ad-sync-construct", "ServiceRole"],
                        )
                    }
                ],
            }
        },
    )


def test_scheduled_ad_sync_lambda_creation(
    identity_stack: IdentityStack,
    identity_template: Template,
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        identity_stack.nested_stack,
        identity_template,
        resources=["scheduled-ad-sync-construct"],
        cfn_type="AWS::Lambda::Function",
        props={
            "Properties": {
                "FunctionName": {
                    "Fn::Join": [
                        "",
                        [
                            identity_stack.nested_stack.resolve(
                                identity_stack.cluster_name
                            ),
                            "-scheduled-ad-sync",
                        ],
                    ]
                },
                "Handler": "scheduled_ad_sync_handler.handler",
                "Role": {
                    "Fn::GetAtt": [
                        util.get_logical_id(
                            identity_stack.nested_stack,
                            ["scheduled-ad-sync-construct", "ServiceRole"],
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
                                    identity_stack.nested_stack.resolve(
                                        identity_stack.cluster_name
                                    ),
                                    "-scheduled-ad-sync",
                                ],
                            ]
                        },
                    },
                    {
                        "Key": constants.IDEA_TAG_ENVIRONMENT_NAME,
                        "Value": identity_stack.nested_stack.resolve(
                            identity_stack.cluster_name
                        ),
                    },
                ],
            }
        },
    )


def test_ad_sync_scheduled_rule_creation(
    identity_stack: IdentityStack,
    identity_template: Template,
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        identity_stack.nested_stack,
        identity_template,
        resources=["ad-sync-schedule-rule"],
        cfn_type="AWS::Events::Rule",
        props={
            "Properties": {
                "Name": {
                    "Fn::Join": [
                        "",
                        [
                            identity_stack.nested_stack.resolve(
                                identity_stack.cluster_name
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
                                    identity_stack.nested_stack,
                                    ["scheduled-ad-sync-construct"],
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
    identity_stack: IdentityStack,
    identity_template: Template,
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        identity_stack.nested_stack,
        identity_template,
        resources=["ad-sync-task-role-construct"],
        cfn_type="AWS::IAM::Role",
        props={
            "Properties": {
                "AssumeRolePolicyDocument": {
                    "Statement": [
                        {
                            "Action": "sts:AssumeRole",
                            "Effect": "Allow",
                            "Principal": {
                                "Service": {
                                    "Fn::Join": [
                                        "",
                                        ["ecs-tasks.", {"Ref": "AWS::URLSuffix"}],
                                    ]
                                }
                            },
                        }
                    ],
                },
                "PermissionsBoundary": {
                    "Fn::If": [
                        "PermissionBoundaryProvided",
                        identity_stack.nested_stack.resolve(
                            identity_stack.parameters.get_str(
                                CommonKey.IAM_PERMISSION_BOUNDARY
                            )
                        ),
                        {"Ref": "AWS::NoValue"},
                    ]
                },
                "Path": identity_stack.nested_stack.resolve(
                    identity_stack.parameters.iam_resource_path_string
                ),
                "RoleName": {
                    "Fn::Join": [
                        "",
                        [
                            identity_stack.nested_stack.resolve(
                                identity_stack.parameters.iam_resource_prefix_string
                            ),
                            identity_stack.nested_stack.resolve(
                                identity_stack.cluster_name
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
                                    identity_stack.nested_stack.resolve(
                                        identity_stack.cluster_name
                                    ),
                                    "-ad-sync-task-role",
                                ],
                            ]
                        },
                    },
                    {
                        "Key": constants.IDEA_TAG_ENVIRONMENT_NAME,
                        "Value": identity_stack.nested_stack.resolve(
                            identity_stack.cluster_name
                        ),
                    },
                ],
            }
        },
    )


def test_ad_sync_task_policy_creation(
    identity_stack: IdentityStack,
    identity_template: Template,
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        identity_stack.nested_stack,
        identity_template,
        resources=["ad-sync-task-policy-construct"],
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
                                            identity_stack.nested_stack.resolve(
                                                identity_stack.cluster_name
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
                                            identity_stack.nested_stack.resolve(
                                                identity_stack.cluster_name
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
                                            identity_stack.nested_stack.resolve(
                                                identity_stack.cluster_name
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
                                            identity_stack.nested_stack.resolve(
                                                identity_stack.cluster_name
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
                                            identity_stack.nested_stack.resolve(
                                                identity_stack.cluster_name
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
                                            identity_stack.nested_stack.resolve(
                                                identity_stack.cluster_name
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
                                            identity_stack.nested_stack.resolve(
                                                identity_stack.cluster_name
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
                                            identity_stack.nested_stack.resolve(
                                                identity_stack.cluster_name
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
                                            identity_stack.nested_stack.resolve(
                                                identity_stack.cluster_name
                                            ),
                                            ".authz.role-assignments/index/*",
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
                                            identity_stack.nested_stack.resolve(
                                                identity_stack.cluster_name
                                            ),
                                            f".{AD_SYNC_STATUS_TABLE}",
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
                                            identity_stack.nested_stack.resolve(
                                                identity_stack.cluster_name
                                            ),
                                            f".{AD_SYNC_STATUS_TABLE}/index/*",
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
                                        identity_stack.nested_stack.resolve(
                                            identity_stack.cluster_name
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
                            identity_stack.nested_stack.resolve(
                                identity_stack.parameters.iam_resource_prefix_string
                            ),
                            identity_stack.nested_stack.resolve(
                                identity_stack.cluster_name
                            ),
                            "-ad-sync-task-policy",
                        ],
                    ]
                },
                "Roles": [
                    {
                        "Ref": util.get_logical_id(
                            identity_stack.nested_stack, ["ad-sync-task-role-construct"]
                        )
                    }
                ],
            }
        },
    )


def test_ad_sync_task_definition_creation(
    identity_stack: IdentityStack,
    identity_template: Template,
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        identity_stack.nested_stack,
        identity_template,
        resources=["ad-sync-task-definition"],
        cfn_type="AWS::ECS::TaskDefinition",
        props={
            "Properties": {
                "ContainerDefinitions": [
                    {
                        "Command": [
                            "/bin/sh",
                            "-exc",
                            "source venv/bin/activate && exec res-ad-sync",
                        ],
                        "Environment": [
                            {
                                "Name": "environment_name",
                                "Value": identity_stack.nested_stack.resolve(
                                    identity_stack.cluster_name
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
                                        identity_stack.nested_stack,
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
                            identity_stack.nested_stack, ["ad-sync-task-role-construct"]
                        ),
                        "Arn",
                    ]
                },
                "Family": {
                    "Fn::Join": [
                        "",
                        [
                            identity_stack.nested_stack.resolve(
                                identity_stack.cluster_name
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
                                    identity_stack.nested_stack.resolve(
                                        identity_stack.cluster_name
                                    ),
                                    "-identity",
                                ],
                            ]
                        },
                    },
                    {
                        "Key": constants.IDEA_TAG_ENVIRONMENT_NAME,
                        "Value": identity_stack.nested_stack.resolve(
                            identity_stack.cluster_name
                        ),
                    },
                ],
                "TaskRoleArn": {
                    "Fn::GetAtt": [
                        util.get_logical_id(
                            identity_stack.nested_stack, ["ad-sync-task-role-construct"]
                        ),
                        "Arn",
                    ]
                },
            }
        },
    )


def test_ad_sync_task_log_group_creation(
    identity_stack: IdentityStack,
    identity_template: Template,
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        identity_stack.nested_stack,
        identity_template,
        resources=["ad-sync-task-log-group"],
        cfn_type="AWS::Logs::LogGroup",
        props={
            "Properties": {
                "LogGroupName": {
                    "Fn::Join": [
                        "",
                        [
                            identity_stack.nested_stack.resolve(
                                identity_stack.cluster_name
                            ),
                            "/ad-sync",
                        ],
                    ]
                },
            }
        },
    )


def test_terminate_ad_sync_ecs_task_role_creation(
    identity_stack: IdentityStack,
    identity_template: Template,
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        identity_stack.nested_stack,
        identity_template,
        resources=["terminate-ad-sync-ecs-task-construct", "ServiceRole"],
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
                        identity_stack.nested_stack.resolve(
                            identity_stack.parameters.get_str(
                                CommonKey.IAM_PERMISSION_BOUNDARY
                            )
                        ),
                        {"Ref": "AWS::NoValue"},
                    ]
                },
                "Path": identity_stack.nested_stack.resolve(
                    identity_stack.parameters.iam_resource_path_string
                ),
                "Tags": [
                    {
                        "Key": constants.IDEA_TAG_NAME,
                        "Value": {
                            "Fn::Join": [
                                "",
                                [
                                    identity_stack.nested_stack.resolve(
                                        identity_stack.cluster_name
                                    ),
                                    "-terminate-ad-sync-ecs-task",
                                ],
                            ]
                        },
                    },
                    {
                        "Key": constants.IDEA_TAG_ENVIRONMENT_NAME,
                        "Value": identity_stack.nested_stack.resolve(
                            identity_stack.cluster_name
                        ),
                    },
                ],
            }
        },
    )


def test_terminate_ad_sync_ecs_task_role_policy_creation(
    identity_stack: IdentityStack,
    identity_template: Template,
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        identity_stack.nested_stack,
        identity_template,
        resources=[
            "terminate-ad-sync-ecs-task-construct",
            "ServiceRole",
            "DefaultPolicy",
        ],
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
                                        identity_stack.nested_stack.resolve(
                                            identity_stack.cluster_name
                                        ),
                                        ".ad-sync.distributed-lock",
                                    ],
                                ]
                            },
                            "Sid": "ADSyncLockTablePermissions",
                        },
                        {
                            "Action": [
                                "dynamodb:Query",
                                "dynamodb:Scan",
                                "dynamodb:UpdateItem",
                                "dynamodb:PutItem",
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
                                        identity_stack.nested_stack.resolve(
                                            identity_stack.cluster_name
                                        ),
                                        ".ad-sync.status",
                                    ],
                                ]
                            },
                            "Sid": "ADSyncStatusTablePermissions",
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
                                        "Fn::Join": [
                                            "",
                                            [
                                                "arn:",
                                                {"Ref": "AWS::Partition"},
                                                ":ecs:",
                                                {"Ref": "AWS::Region"},
                                                ":",
                                                {"Ref": "AWS::AccountId"},
                                                ":cluster/",
                                                identity_stack.nested_stack.resolve(
                                                    identity_stack.cluster_name
                                                ),
                                                "-ad-sync-cluster",
                                            ],
                                        ]
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
                                        ":role",
                                        identity_stack.nested_stack.resolve(
                                            identity_stack.parameters.iam_resource_path_string
                                        ),
                                        identity_stack.nested_stack.resolve(
                                            identity_stack.parameters.iam_resource_prefix_string
                                        ),
                                        identity_stack.nested_stack.resolve(
                                            identity_stack.cluster_name
                                        ),
                                        "-ad-sync-task-role",
                                    ],
                                ]
                            },
                        },
                    ],
                },
                "Roles": [
                    {
                        "Ref": util.get_logical_id(
                            identity_stack.nested_stack,
                            ["terminate-ad-sync-ecs-task-construct", "ServiceRole"],
                        )
                    }
                ],
            }
        },
    )


def test_terminate_ad_sync_ecs_task_lambda_creation(
    identity_stack: IdentityStack,
    identity_template: Template,
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        identity_stack.nested_stack,
        identity_template,
        resources=["terminate-ad-sync-ecs-task-construct"],
        cfn_type="AWS::Lambda::Function",
        props={
            "Properties": {
                "FunctionName": {
                    "Fn::Join": [
                        "",
                        [
                            identity_stack.nested_stack.resolve(
                                identity_stack.cluster_name
                            ),
                            "-terminate-ad-sync-ecs-task",
                        ],
                    ]
                },
                "Handler": "handler.handler",
                "Role": {
                    "Fn::GetAtt": [
                        util.get_logical_id(
                            identity_stack.nested_stack,
                            ["terminate-ad-sync-ecs-task-construct", "ServiceRole"],
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
                                    identity_stack.nested_stack.resolve(
                                        identity_stack.cluster_name
                                    ),
                                    "-terminate-ad-sync-ecs-task",
                                ],
                            ]
                        },
                    },
                    {
                        "Key": constants.IDEA_TAG_ENVIRONMENT_NAME,
                        "Value": identity_stack.nested_stack.resolve(
                            identity_stack.cluster_name
                        ),
                    },
                ],
            }
        },
    )


def test_terminate_ad_sync_ecs_task_custom_resource_creation(
    identity_stack: IdentityStack,
    identity_template: Template,
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        identity_stack.nested_stack,
        identity_template,
        resources=["terminate-ad-sync-ecs-task-custom-resource"],
        cfn_type="Custom::TerminateADSyncECSTask",
        props={
            "Properties": {
                "ServiceToken": {
                    "Fn::GetAtt": [
                        util.get_logical_id(
                            identity_stack.nested_stack,
                            ["terminate-ad-sync-ecs-task-construct"],
                        ),
                        "Arn",
                    ]
                },
            }
        },
    )


def test_ad_automation_sqs_queue_creation(
    identity_stack: IdentityStack,
    identity_template: Template,
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        identity_stack.nested_stack,
        identity_template,
        resources=["ad-automation-construct"],
        cfn_type="AWS::SQS::Queue",
        props={
            "Properties": {
                "FifoQueue": True,
                "QueueName": {
                    "Fn::Join": [
                        "",
                        [
                            identity_stack.nested_stack.resolve(
                                identity_stack.cluster_name
                            ),
                            "-ad-automation.fifo",
                        ],
                    ]
                },
                "RedrivePolicy": {
                    "deadLetterTargetArn": {
                        "Fn::GetAtt": [
                            util.get_logical_id(
                                identity_stack.nested_stack,
                                ["ad-automation-dlq-construct"],
                            ),
                            "Arn",
                        ]
                    },
                },
            }
        },
    )


def test_cognito_user_pool_creation(
    identity_stack: IdentityStack,
    identity_template: Template,
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        identity_stack.nested_stack,
        identity_template,
        resources=["cognito-user-pool-construct", "cognito-user-pool"],
        cfn_type="AWS::Cognito::UserPool",
        props={
            "Properties": {
                "AccountRecoverySetting": {
                    "RecoveryMechanisms": [{"Name": "verified_email", "Priority": 1}]
                },
                "DeletionProtection": "ACTIVE",
                "UserPoolName": {
                    "Fn::Join": [
                        "",
                        [
                            identity_stack.nested_stack.resolve(
                                identity_stack.cluster_name
                            ),
                            "-user-pool",
                        ],
                    ]
                },
                "UserPoolTags": {
                    constants.IDEA_TAG_NAME: {
                        "Fn::Join": [
                            "",
                            [
                                identity_stack.nested_stack.resolve(
                                    identity_stack.cluster_name
                                ),
                                "-cognito-user-pool",
                            ],
                        ]
                    },
                    constants.IDEA_TAG_ENVIRONMENT_NAME: identity_stack.nested_stack.resolve(
                        identity_stack.cluster_name
                    ),
                },
            }
        },
    )


def test_cognito_user_domain_creation(
    identity_stack: IdentityStack,
    identity_template: Template,
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        identity_stack.nested_stack,
        identity_template,
        resources=["cognito-user-pool-construct", "cognito-user-pool", "domain"],
        cfn_type="AWS::Cognito::UserPoolDomain",
        props={
            "Properties": {
                "UserPoolId": identity_stack.nested_stack.resolve(
                    identity_stack.new_user_pool.user_pool.user_pool_id
                ),
                "Domain": {
                    "Fn::Join": [
                        "",
                        [
                            identity_stack.nested_stack.resolve(
                                identity_stack.cluster_name
                            ),
                            "-",
                            {
                                "Fn::GetAtt": [
                                    util.get_logical_id(
                                        identity_stack.nested_stack,
                                        [
                                            "get-cluster-setting-cluster.random-uuid",
                                            "Resource",
                                            "Default",
                                        ],
                                    ),
                                    "Item.value.S",
                                ]
                            },
                        ],
                    ]
                },
            }
        },
    )


def test_oauth_credentials_lambda_creation(
    identity_stack: IdentityStack,
    identity_template: Template,
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        identity_stack.nested_stack,
        identity_template,
        resources=["oauth-credentials-construct"],
        cfn_type="AWS::Lambda::Function",
        props={
            "Properties": {
                "FunctionName": {
                    "Fn::Join": [
                        "",
                        [
                            identity_stack.nested_stack.resolve(
                                identity_stack.cluster_name
                            ),
                            "-oauth-credentials",
                        ],
                    ]
                },
                "Handler": "get_user_pool_client_secret_handler.handler",
                "Role": {
                    "Fn::GetAtt": [
                        util.get_logical_id(
                            identity_stack.nested_stack,
                            ["oauth-credentials-construct", "ServiceRole"],
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
                                    identity_stack.nested_stack.resolve(
                                        identity_stack.cluster_name
                                    ),
                                    "-oauth-credentials",
                                ],
                            ]
                        },
                    },
                    {
                        "Key": constants.IDEA_TAG_ENVIRONMENT_NAME,
                        "Value": identity_stack.nested_stack.resolve(
                            identity_stack.cluster_name
                        ),
                    },
                ],
            }
        },
    )


def test_disable_cognito_protection_lambda_creation(
    identity_stack: IdentityStack,
    identity_template: Template,
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        identity_stack.nested_stack,
        identity_template,
        resources=["disable-cognito-protection-construct"],
        cfn_type="AWS::Lambda::Function",
        props={
            "Properties": {
                "FunctionName": {
                    "Fn::Join": [
                        "",
                        [
                            identity_stack.nested_stack.resolve(
                                identity_stack.cluster_name
                            ),
                            "-disable-cognito-protection",
                        ],
                    ]
                },
                "Handler": "handler.disable_cognito_protection_handler",
                "Role": {
                    "Fn::GetAtt": [
                        util.get_logical_id(
                            identity_stack.nested_stack,
                            ["disable-cognito-protection-construct", "ServiceRole"],
                        ),
                        "Arn",
                    ]
                },
                "Runtime": RES_COMMON_LAMBDA_RUNTIME.to_string(),
                "Tags": [
                    {
                        "Key": "Name",
                        "Value": {
                            "Fn::Join": [
                                "",
                                [
                                    identity_stack.nested_stack.resolve(
                                        identity_stack.cluster_name
                                    ),
                                    "-disable-cognito-protection",
                                ],
                            ]
                        },
                    },
                    {
                        "Key": "res:EnvironmentName",
                        "Value": identity_stack.nested_stack.resolve(
                            identity_stack.cluster_name
                        ),
                    },
                ],
            }
        },
    )
