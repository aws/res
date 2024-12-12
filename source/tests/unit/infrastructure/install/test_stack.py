#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
import importlib.metadata

from aws_cdk.assertions import Match, Template

import idea
from idea.infrastructure.install.constants import (
    RES_ADMINISTRATOR_LAMBDA_RUNTIME,
    RES_BACKEND_LAMBDA_RUNTIME,
    RES_COMMON_LAMBDA_RUNTIME,
)
from idea.infrastructure.install.parameters.common import CommonKey
from idea.infrastructure.install.stacks.install_stack import InstallStack
from ideadatamodel import constants  # type: ignore
from tests.unit.infrastructure.install import util


def test_stack_description(stack: InstallStack, template: Template) -> None:
    template.template_matches(
        {"Description": f"RES_{importlib.metadata.version(idea.__package__)}"}
    )


def test_shared_res_library_lambda_layer_creation(
    stack: InstallStack,
    template: Template,
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        stack,
        template,
        resources=["RES-library"],
        cfn_type="AWS::Lambda::LayerVersion",
        props={
            "Properties": {
                "CompatibleRuntimes": [
                    RES_ADMINISTRATOR_LAMBDA_RUNTIME.name,
                    RES_COMMON_LAMBDA_RUNTIME.name,
                    RES_BACKEND_LAMBDA_RUNTIME.name,
                ],
                "Content": {
                    "S3Bucket": Match.any_value(),
                    "S3Key": Match.any_value(),
                },
                "Description": "Shared RES library for Lambda functions",
            },
        },
    )


def test_res_ecr_repository_creation(
    stack: InstallStack,
    template: Template,
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        stack,
        template,
        resources=["ResEcrRepo"],
        cfn_type="AWS::ECR::Repository",
        props={
            "Properties": {
                "RepositoryName": {
                    "Fn::Join": ["", [{"Ref": CommonKey.CLUSTER_NAME}, "-res-ecr"]]
                }
            },
            "UpdateReplacePolicy": "Delete",
            "DeletionPolicy": "Delete",
        },
    )


def test_ecr_images_duplication_project_creation(
    stack: InstallStack,
    template: Template,
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        stack,
        template,
        resources=["CopyImagesToRESEcr"],
        cfn_type="AWS::CodeBuild::Project",
        props={
            "Properties": {
                "Environment": {
                    "ComputeType": "BUILD_GENERAL1_SMALL",
                    "EnvironmentVariables": [
                        {
                            "Name": "AWS_REGION",
                            "Type": "PLAINTEXT",
                            "Value": {"Ref": "AWS::Region"},
                        },
                        {
                            "Name": "DEST_INSTALLER_REGISTRY",
                            "Type": "PLAINTEXT",
                            "Value": "fake-registry-name",
                        },
                        {
                            "Name": "DEST_AD_SYNC_REGISTRY",
                            "Type": "PLAINTEXT",
                            "Value": "fake-registry-name",
                        },
                        {
                            "Name": "RES_REPO_URI",
                            "Type": "PLAINTEXT",
                            "Value": stack.resolve(stack.res_ecr_repo.repository_uri),
                        },
                    ],
                    "Image": "aws/codebuild/amazonlinux2-x86_64-standard:5.0",
                    "ImagePullCredentialsType": "CODEBUILD",
                    "PrivilegedMode": False,
                    "Type": "LINUX_CONTAINER",
                },
                "Name": {
                    "Fn::Join": [
                        "-",
                        [{"Ref": CommonKey.CLUSTER_NAME}, "copy-images-to-res-ecr"],
                    ]
                },
                "Source": {
                    "BuildSpec": '{\n  "version": "0.2",\n  "phases": {\n    "build": {\n      "commands": [\n        "aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin fake-registry-name",\n        "docker pull fake-registry-name",\n        "docker tag fake-registry-name ${DEST_INSTALLER_REGISTRY}",\n        "aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${RES_REPO_URI}",\n        "docker push ${DEST_INSTALLER_REGISTRY}",\n        "aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin fake-registry-name",\n        "docker pull fake-registry-name",\n        "docker tag fake-registry-name ${DEST_AD_SYNC_REGISTRY}",\n        "aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${RES_REPO_URI}",\n        "docker push ${DEST_AD_SYNC_REGISTRY}"\n      ]\n    }\n  }\n}',
                    "Type": "NO_SOURCE",
                },
            },
        },
    )


def test_custom_resource_ecr_images_handler_creation(
    stack: InstallStack,
    template: Template,
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        stack,
        template,
        resources=["CustomResourceEcrImageHandler"],
        cfn_type="Custom::RES",
        props={
            "Properties": {
                "ProjectName": {
                    "Ref": util.get_logical_id(stack, ["CopyImagesToRESEcr"]),
                },
                "ResEcrRepositoryName": {
                    "Ref": util.get_logical_id(stack, ["ResEcrRepo"]),
                },
                "InstallerRegistryName": "fake-registry-name",
                "ADSyncRegistryName": "fake-registry-name",
            },
            "UpdateReplacePolicy": "Delete",
            "DeletionPolicy": "Delete",
        },
    )


def test_ecr_images_handler_creation(
    stack: InstallStack,
    template: Template,
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        stack,
        template,
        resources=["EcrImageHandler"],
        cfn_type="AWS::Lambda::Function",
        props={
            "Properties": {
                "Role": {
                    "Fn::GetAtt": [
                        util.get_logical_id(stack, ["EcrImageHandlerRole"]),
                        "Arn",
                    ]
                },
                "Runtime": "python3.11",
                "Timeout": 300,
            }
        },
    )


def test_ecr_images_handler_role_creation(
    stack: InstallStack,
    template: Template,
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        stack,
        template,
        resources=["EcrImageHandlerRole"],
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
                        stack.resolve(
                            stack.parameters.get_str(CommonKey.IAM_PERMISSION_BOUNDARY)
                        ),
                        {"Ref": "AWS::NoValue"},
                    ]
                },
                "RoleName": {
                    "Fn::Join": [
                        "",
                        [
                            {
                                "Ref": CommonKey.CLUSTER_NAME,
                            },
                            "-ecr-image-handler-role",
                        ],
                    ]
                },
            }
        },
    )


def test_ecr_images_handler_role_policy_creation(
    stack: InstallStack,
    template: Template,
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        stack,
        template,
        resources=["EcrImageHandlerRolePolicy"],
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
                                "codebuild:StartBuild",
                                "codebuild:BatchGetBuilds",
                            ],
                            "Effect": "Allow",
                            "Resource": {
                                "Fn::GetAtt": [
                                    util.get_logical_id(stack, ["CopyImagesToRESEcr"]),
                                    "Arn",
                                ]
                            },
                        },
                        {
                            "Action": ["ecr:ListImages", "ecr:BatchDeleteImage"],
                            "Effect": "Allow",
                            "Resource": {
                                "Fn::GetAtt": [
                                    util.get_logical_id(stack, ["ResEcrRepo"]),
                                    "Arn",
                                ]
                            },
                        },
                    ],
                },
                "PolicyName": {
                    "Fn::Join": [
                        "",
                        [
                            {
                                "Ref": CommonKey.CLUSTER_NAME,
                            },
                            "-custom-resource-ecr-image-handler-role-policy",
                        ],
                    ],
                },
                "Roles": [
                    {
                        "Ref": util.get_logical_id(stack, ["EcrImageHandlerRole"]),
                    }
                ],
            }
        },
    )


def test_params_transformer_custom_resource_creation(
    stack: InstallStack, template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        stack,
        template,
        resources=["CustomResourceParamsListToStringTransformer"],
        cfn_type="Custom::ParamsListToStringTransformer",
        props={
            "Properties": {
                "ServiceToken": {
                    "Fn::GetAtt": [
                        util.get_logical_id(
                            stack, ["ParameterListToStringTransformLambda"]
                        ),
                        "Arn",
                    ]
                },
            },
            "UpdateReplacePolicy": "Delete",
            "DeletionPolicy": "Delete",
        },
    )


def test_params_transformer_handler_creation(
    stack: InstallStack,
    template: Template,
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        stack,
        template,
        resources=["ParameterListToStringTransformLambda"],
        cfn_type="AWS::Lambda::Function",
        props={
            "Properties": {
                "Role": {
                    "Fn::GetAtt": [
                        util.get_logical_id(
                            stack, ["ParameterListToStringTransformLambdaRole"]
                        ),
                        "Arn",
                    ]
                },
                "Runtime": "python3.11",
                "Timeout": 300,
            }
        },
    )


def test_params_transformer_handler_role_creation(
    stack: InstallStack,
    template: Template,
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        stack,
        template,
        resources=["ParameterListToStringTransformLambdaRole"],
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
                        stack.resolve(
                            stack.parameters.get_str(CommonKey.IAM_PERMISSION_BOUNDARY)
                        ),
                        {"Ref": "AWS::NoValue"},
                    ]
                },
                "RoleName": {
                    "Fn::Join": [
                        "",
                        [
                            {
                                "Ref": CommonKey.CLUSTER_NAME,
                            },
                            "-ParameterListToStringTransformLambdaRole",
                        ],
                    ]
                },
            }
        },
    )


def test_params_transformer_handler_role_policy_creation(
    stack: InstallStack,
    template: Template,
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        stack,
        template,
        resources=["ParameterListToStringTransformLambdaRolePolicy"],
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
                    ],
                },
                "PolicyName": {
                    "Fn::Join": [
                        "",
                        [
                            {
                                "Ref": CommonKey.CLUSTER_NAME,
                            },
                            "-ParameterListToStringTransformLambdaRolePolicy",
                        ],
                    ],
                },
                "Roles": [
                    {
                        "Ref": util.get_logical_id(
                            stack, ["ParameterListToStringTransformLambdaRole"]
                        ),
                    }
                ],
            }
        },
    )
