# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from aws_cdk.assertions import Template

from idea.infrastructure.install.constants import RES_COMMON_LAMBDA_RUNTIME
from idea.infrastructure.install.parameters.common import CommonKey
from idea.infrastructure.install.stacks.res_finalizer_stack import ResFinalizerStack
from ideadatamodel import constants  # type: ignore
from tests.unit.infrastructure.install import util


def test_stack_description(res_finalizer_template: Template) -> None:
    res_finalizer_template.template_matches(
        {"Description": "Nested RES Finalizer Stack"}
    )


def test_res_finalizer_stack_has_custom_resource(
    res_finalizer_template: Template,
) -> None:
    res_finalizer_template.resource_count_is(type="Custom::RESDdbPopulator", count=1)
    res_finalizer_template.resource_count_is(type="Custom::CleanupEC2Instance", count=1)
    res_finalizer_template.resource_count_is(type="Custom::DetachLambdaVPC", count=1)


def test_ddb_final_populator_lambda_role_creation(
    res_finalizer_stack: ResFinalizerStack,
    res_finalizer_template: Template,
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        res_finalizer_stack.nested_stack,
        res_finalizer_template,
        resources=["DDBFinalValuesPopulatorRole"],
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
                        res_finalizer_stack.nested_stack.resolve(
                            res_finalizer_stack.parameters.get_str(
                                CommonKey.IAM_PERMISSION_BOUNDARY
                            )
                        ),
                        {"Ref": "AWS::NoValue"},
                    ]
                },
                "Path": res_finalizer_stack.nested_stack.resolve(
                    res_finalizer_stack.parameters.iam_resource_path_string
                ),
                "RoleName": {
                    "Fn::Join": [
                        "",
                        [
                            res_finalizer_stack.nested_stack.resolve(
                                res_finalizer_stack.parameters.iam_resource_prefix_string
                            ),
                            res_finalizer_stack.nested_stack.resolve(
                                res_finalizer_stack.cluster_name
                            ),
                            "-DDBFinalValuesPopulatorRole",
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
                                    res_finalizer_stack.nested_stack.resolve(
                                        res_finalizer_stack.cluster_name
                                    ),
                                    "-res-finalizer",
                                ],
                            ]
                        },
                    },
                    {
                        "Key": constants.IDEA_TAG_ENVIRONMENT_NAME,
                        "Value": res_finalizer_stack.nested_stack.resolve(
                            res_finalizer_stack.cluster_name
                        ),
                    },
                ],
            }
        },
    )


def test_ddb_final_populator_lambda_creation(
    res_finalizer_stack: ResFinalizerStack,
    res_finalizer_template: Template,
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        res_finalizer_stack.nested_stack,
        res_finalizer_template,
        resources=["DDBFinalValuesPopulator"],
        cfn_type="AWS::Lambda::Function",
        props={
            "Properties": {
                "FunctionName": {
                    "Fn::Join": [
                        "",
                        [
                            res_finalizer_stack.nested_stack.resolve(
                                res_finalizer_stack.cluster_name
                            ),
                            "-DDBFinalValuesPopulator",
                        ],
                    ]
                },
                "Handler": "handler.handler",
                "Role": {
                    "Fn::GetAtt": [
                        util.get_logical_id(
                            res_finalizer_stack.nested_stack,
                            ["DDBFinalValuesPopulatorRole"],
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
                                    res_finalizer_stack.nested_stack.resolve(
                                        res_finalizer_stack.cluster_name
                                    ),
                                    "-res-finalizer",
                                ],
                            ]
                        },
                    },
                    {
                        "Key": constants.IDEA_TAG_ENVIRONMENT_NAME,
                        "Value": res_finalizer_stack.nested_stack.resolve(
                            res_finalizer_stack.cluster_name
                        ),
                    },
                ],
            }
        },
    )


def test_clean_up_ec2_instance_role_policy_creation(
    res_finalizer_stack: ResFinalizerStack,
    res_finalizer_template: Template,
) -> None:

    tag_condition = {
        "StringEquals": {
            "aws:ResourceTag/res:EnvironmentName": res_finalizer_stack.nested_stack.resolve(
                res_finalizer_stack.cluster_name
            )
        }
    }
    util.assert_resource_name_has_correct_type_and_props(
        res_finalizer_stack.nested_stack,
        res_finalizer_template,
        resources=[
            "clean-up-ec2-instance-construct",
            "ServiceRole",
            "DefaultPolicy",
        ],
        cfn_type="AWS::IAM::Policy",
        props={
            "Properties": {
                "PolicyDocument": {
                    "Statement": [
                        {
                            "Action": [
                                "ec2:DescribeInstances",
                                "lambda:ListFunctions",
                                "lambda:ListTags",
                            ],
                            "Effect": "Allow",
                            "Resource": "*",
                        },
                        {
                            "Action": [
                                "ec2:DescribeInstanceAttribute",
                                "ec2:ModifyInstanceAttribute",
                                "ec2:TerminateInstances",
                            ],
                            "Effect": "Allow",
                            "Resource": {
                                "Fn::Join": [
                                    "",
                                    [
                                        "arn:",
                                        {"Ref": "AWS::Partition"},
                                        ":ec2:",
                                        {"Ref": "AWS::Region"},
                                        ":",
                                        {"Ref": "AWS::AccountId"},
                                        ":instance/*",
                                    ],
                                ]
                            },
                            "Condition": tag_condition,
                        },
                        {
                            "Action": "logs:CreateLogGroup",
                            "Effect": "Allow",
                            "Resource": {
                                "Fn::Join": [
                                    "",
                                    [
                                        "arn:",
                                        {"Ref": "AWS::Partition"},
                                        ":logs:",
                                        {"Ref": "AWS::Region"},
                                        ":",
                                        {"Ref": "AWS::AccountId"},
                                        ":log-group:/aws/lambda/",
                                        res_finalizer_stack.nested_stack.resolve(
                                            res_finalizer_stack.cluster_name
                                        ),
                                        "*",
                                    ],
                                ]
                            },
                            "Sid": "CloudWatchLogsPermissions",
                        },
                        {
                            "Action": [
                                "logs:CreateLogStream",
                                "logs:PutLogEvents",
                                "logs:DeleteLogStream",
                            ],
                            "Effect": "Allow",
                            "Resource": {
                                "Fn::Join": [
                                    "",
                                    [
                                        "arn:",
                                        {"Ref": "AWS::Partition"},
                                        ":logs:",
                                        {"Ref": "AWS::Region"},
                                        ":",
                                        {"Ref": "AWS::AccountId"},
                                        ":log-group:/aws/lambda/",
                                        res_finalizer_stack.nested_stack.resolve(
                                            res_finalizer_stack.cluster_name
                                        ),
                                        "*:log-stream:*",
                                    ],
                                ]
                            },
                            "Sid": "CloudWatchLogStreamPermissions",
                        },
                    ],
                },
                "Roles": [
                    {
                        "Ref": util.get_logical_id(
                            res_finalizer_stack.nested_stack,
                            ["clean-up-ec2-instance-construct", "ServiceRole"],
                        )
                    }
                ],
            }
        },
    )


def test_clean_up_ec2_instance_lambda_role_creation(
    res_finalizer_stack: ResFinalizerStack,
    res_finalizer_template: Template,
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        res_finalizer_stack.nested_stack,
        res_finalizer_template,
        resources=["clean-up-ec2-instance-construct", "ServiceRole"],
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
                        res_finalizer_stack.nested_stack.resolve(
                            res_finalizer_stack.parameters.get_str(
                                CommonKey.IAM_PERMISSION_BOUNDARY
                            )
                        ),
                        {"Ref": "AWS::NoValue"},
                    ]
                },
                "Path": res_finalizer_stack.nested_stack.resolve(
                    res_finalizer_stack.parameters.iam_resource_path_string
                ),
                "Tags": [
                    {
                        "Key": "Name",
                        "Value": {
                            "Fn::Join": [
                                "",
                                [
                                    res_finalizer_stack.nested_stack.resolve(
                                        res_finalizer_stack.cluster_name
                                    ),
                                    "-clean-up-ec2-instance",
                                ],
                            ]
                        },
                    },
                    {
                        "Key": "res:EnvironmentName",
                        "Value": res_finalizer_stack.nested_stack.resolve(
                            res_finalizer_stack.cluster_name
                        ),
                    },
                ],
            }
        },
    )


def test_clean_up_ec2_instance_lambda_creation(
    res_finalizer_stack: ResFinalizerStack,
    res_finalizer_template: Template,
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        res_finalizer_stack.nested_stack,
        res_finalizer_template,
        resources=["clean-up-ec2-instance-construct"],
        cfn_type="AWS::Lambda::Function",
        props={
            "Properties": {
                "FunctionName": {
                    "Fn::Join": [
                        "",
                        [
                            res_finalizer_stack.nested_stack.resolve(
                                res_finalizer_stack.cluster_name
                            ),
                            "-clean-up-ec2-instance",
                        ],
                    ]
                },
                "Handler": "handler.clean_up_ec2_instance_handler",
                "Role": {
                    "Fn::GetAtt": [
                        util.get_logical_id(
                            res_finalizer_stack.nested_stack,
                            ["clean-up-ec2-instance-construct", "ServiceRole"],
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
                                    res_finalizer_stack.nested_stack.resolve(
                                        res_finalizer_stack.cluster_name
                                    ),
                                    "-clean-up-ec2-instance",
                                ],
                            ]
                        },
                    },
                    {
                        "Key": "res:EnvironmentName",
                        "Value": res_finalizer_stack.nested_stack.resolve(
                            res_finalizer_stack.cluster_name
                        ),
                    },
                ],
            }
        },
    )
