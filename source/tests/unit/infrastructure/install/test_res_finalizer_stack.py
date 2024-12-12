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
                "RoleName": {
                    "Fn::Join": [
                        "",
                        [
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
