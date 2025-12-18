#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from aws_cdk.assertions import Template

from idea.infrastructure.install.constants import (
    MODULE_ID_VDC_CONTROLLER,
    RES_COMMON_LAMBDA_RUNTIME,
)
from idea.infrastructure.install.constructs.base import ResBaseConstruct
from idea.infrastructure.install.parameters.common import CommonKey
from idea.infrastructure.install.parameters.internet_proxy import InternetProxyKey
from idea.infrastructure.install.stacks.virtual_desktop_controller_stack import (
    VirtualDesktopControllerStack,
)
from ideadatamodel import constants  # type: ignore
from tests.unit.infrastructure.install import util


def test_stack_description(vdc_template: Template) -> None:
    vdc_template.template_matches(
        {
            "Description": f"ModuleId: {MODULE_ID_VDC_CONTROLLER}, Version: {ResBaseConstruct.get_res_release_version()}"
        }
    )


def test_oauth2_client_secret_creation(
    vdc_stack: VirtualDesktopControllerStack, vdc_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        vdc_stack.nested_stack,
        vdc_template,
        resources=[f"{MODULE_ID_VDC_CONTROLLER}-client-secret"],
        cfn_type="AWS::SecretsManager::Secret",
        props={
            "Properties": {
                "KmsKeyId": vdc_stack.nested_stack.resolve(
                    vdc_stack.cluster_settings.kms_secretsmanager_key_id
                ),
                "Name": {
                    "Fn::Join": [
                        "",
                        [
                            vdc_stack.nested_stack.resolve(vdc_stack.cluster_name),
                            f"-{MODULE_ID_VDC_CONTROLLER}-client-secret",
                        ],
                    ]
                },
            }
        },
    )

    util.assert_resource_name_has_correct_type_and_props(
        vdc_stack.nested_stack,
        vdc_template,
        resources=["vdc-get-user-pool", "resource-server"],
        cfn_type="AWS::Cognito::UserPoolResourceServer",
        props={
            "Properties": {
                "Identifier": {
                    "Fn::Join": [
                        "",
                        [
                            vdc_stack.nested_stack.resolve(vdc_stack.cluster_name),
                            f"-{MODULE_ID_VDC_CONTROLLER}",
                        ],
                    ]
                },
                "Scopes": [
                    {"ScopeDescription": "Allow Read Access", "ScopeName": "read"},
                    {"ScopeDescription": "Allow Write Access", "ScopeName": "write"},
                ],
            }
        },
    )

    util.assert_resource_name_has_correct_type_and_props(
        vdc_stack.nested_stack,
        vdc_template,
        resources=["vdc-get-user-pool", "dcv-session-manager-resource-server"],
        cfn_type="AWS::Cognito::UserPoolResourceServer",
        props={
            "Properties": {
                "Identifier": {
                    "Fn::Join": [
                        "",
                        [
                            vdc_stack.nested_stack.resolve(vdc_stack.cluster_name),
                            "-dcv-session-manager",
                        ],
                    ]
                },
                "Scopes": [
                    {"ScopeDescription": "sm_scope", "ScopeName": "sm_scope"},
                ],
            }
        },
    )

    util.assert_resource_name_has_correct_type_and_props(
        vdc_stack.nested_stack,
        vdc_template,
        resources=["vdc-get-user-pool", "vdc-client"],
        cfn_type="AWS::Cognito::UserPoolClient",
        props={
            "Properties": {
                "AccessTokenValidity": 60,
                "GenerateSecret": True,
                "IdTokenValidity": 60,
                "RefreshTokenValidity": 43200,
                "SupportedIdentityProviders": ["COGNITO"],
                "ClientName": {
                    "Fn::Join": [
                        "",
                        [
                            vdc_stack.nested_stack.resolve(vdc_stack.cluster_name),
                            f"-{MODULE_ID_VDC_CONTROLLER}",
                        ],
                    ]
                },
                "AllowedOAuthFlows": ["client_credentials"],
                "AllowedOAuthFlowsUserPoolClient": True,
            }
        },
    )

    util.assert_resource_name_has_correct_type_and_props(
        vdc_stack.nested_stack,
        vdc_template,
        resources=[f"{MODULE_ID_VDC_CONTROLLER}-creds"],
        cfn_type="Custom::GetOAuthCredentials",
        props={
            "Properties": {
                "ServiceToken": vdc_stack.nested_stack.resolve(
                    vdc_stack.identity_stack.oauth_credentials_lambda.function_arn
                ),
            }
        },
    )


def test_custom_broker_secret_creation(
    vdc_stack: VirtualDesktopControllerStack, vdc_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        vdc_stack.nested_stack,
        vdc_template,
        resources=[f"{MODULE_ID_VDC_CONTROLLER}-custom-credential-broker-secret"],
        cfn_type="AWS::SecretsManager::Secret",
        props={
            "Properties": {
                "Description": "Custom credential broker secret used for generating JWT bootstrap token",
                "GenerateSecretString": {
                    "ExcludeCharacters": " %+~`#$&*()|[]{}:;<>?!'/\"\\@",
                    "IncludeSpace": False,
                    "PasswordLength": 32,
                },
                "Name": {
                    "Fn::Join": [
                        "",
                        [
                            vdc_stack.nested_stack.resolve(vdc_stack.cluster_name),
                            "-custom-credential-broker-secret",
                        ],
                    ]
                },
            }
        },
    )


def test_sqs_kms_key_creation(
    vdc_stack: VirtualDesktopControllerStack, vdc_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        vdc_stack.nested_stack,
        vdc_template,
        resources=["res-sqs-kms"],
        cfn_type="AWS::KMS::Key",
        props={
            "Properties": {
                "EnableKeyRotation": True,
                "KeyPolicy": {
                    "Statement": [
                        {
                            "Action": "kms:*",
                            "Effect": "Allow",
                            "Principal": {
                                "AWS": {
                                    "Fn::Join": [
                                        "",
                                        [
                                            "arn:",
                                            {"Ref": "AWS::Partition"},
                                            f":iam::{vdc_stack.nested_stack.account}:root",
                                        ],
                                    ]
                                }
                            },
                            "Resource": "*",
                        },
                        {
                            "Action": [
                                "kms:GenerateDataKey",
                                "kms:Decrypt",
                                "kms:ReEncrypt*",
                                "kms:DescribeKey",
                                "kms:Encrypt",
                            ],
                            "Effect": "Allow",
                            "Principal": {
                                "Service": ["sns.amazonaws.com", "sqs.amazonaws.com"]
                            },
                            "Resource": "*",
                        },
                    ],
                    "Version": "2012-10-17",
                },
            }
        },
    )

    util.assert_resource_name_has_correct_type_and_props(
        vdc_stack.nested_stack,
        vdc_template,
        resources=["res-sqs-kms", "Alias"],
        cfn_type="AWS::KMS::Alias",
        props={
            "Properties": {
                "AliasName": {
                    "Fn::Join": [
                        "",
                        [
                            "alias/",
                            vdc_stack.nested_stack.resolve(vdc_stack.cluster_name),
                            "/sqs",
                        ],
                    ]
                },
                "TargetKeyId": {
                    "Fn::GetAtt": [
                        util.get_logical_id(
                            vdc_stack.nested_stack,
                            ["res-sqs-kms"],
                        ),
                        "Arn",
                    ],
                },
            }
        },
    )


def test_event_sqs_queue_creation(
    vdc_stack: VirtualDesktopControllerStack, vdc_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        vdc_stack.nested_stack,
        vdc_template,
        resources=[f"{MODULE_ID_VDC_CONTROLLER}-events-construct"],
        cfn_type="AWS::SQS::Queue",
        props={
            "Properties": {
                "ContentBasedDeduplication": True,
                "DeduplicationScope": "messageGroup",
                "FifoQueue": True,
                "FifoThroughputLimit": "perMessageGroupId",
                "KmsMasterKeyId": "alias/aws/sqs",
                "QueueName": {
                    "Fn::Join": [
                        "",
                        [
                            vdc_stack.nested_stack.resolve(vdc_stack.cluster_name),
                            f"-{MODULE_ID_VDC_CONTROLLER}-events.fifo",
                        ],
                    ]
                },
                "RedrivePolicy": {
                    "deadLetterTargetArn": {
                        "Fn::GetAtt": [
                            util.get_logical_id(
                                vdc_stack.nested_stack,
                                [f"{MODULE_ID_VDC_CONTROLLER}-events-dlq-construct"],
                            ),
                            "Arn",
                        ]
                    },
                    "maxReceiveCount": 60,
                },
            }
        },
    )

    util.assert_resource_name_has_correct_type_and_props(
        vdc_stack.nested_stack,
        vdc_template,
        resources=[f"{MODULE_ID_VDC_CONTROLLER}-events-dlq-construct"],
        cfn_type="AWS::SQS::Queue",
        props={
            "Properties": {
                "ContentBasedDeduplication": True,
                "DeduplicationScope": "messageGroup",
                "FifoQueue": True,
                "FifoThroughputLimit": "perMessageGroupId",
                "KmsMasterKeyId": "alias/aws/sqs",
                "QueueName": {
                    "Fn::Join": [
                        "",
                        [
                            vdc_stack.nested_stack.resolve(vdc_stack.cluster_name),
                            f"-{MODULE_ID_VDC_CONTROLLER}-events-dlq.fifo",
                        ],
                    ]
                },
            }
        },
    )


def test_controller_sqs_queue_creation(
    vdc_stack: VirtualDesktopControllerStack, vdc_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        vdc_stack.nested_stack,
        vdc_template,
        resources=[f"{MODULE_ID_VDC_CONTROLLER}-controller-construct"],
        cfn_type="AWS::SQS::Queue",
        props={
            "Properties": {
                "KmsMasterKeyId": {
                    "Fn::Join": [
                        "",
                        [
                            "arn:",
                            {"Ref": "AWS::Partition"},
                            ":kms:",
                            {"Ref": "AWS::Region"},
                            ":",
                            {"Ref": "AWS::AccountId"},
                            ":key/",
                            {
                                "Ref": util.get_logical_id(
                                    vdc_stack.nested_stack,
                                    ["res-sqs-kms"],
                                ),
                            },
                        ],
                    ]
                },
                "QueueName": {
                    "Fn::Join": [
                        "",
                        [
                            vdc_stack.nested_stack.resolve(vdc_stack.cluster_name),
                            f"-{MODULE_ID_VDC_CONTROLLER}-controller",
                        ],
                    ]
                },
                "RedrivePolicy": {
                    "deadLetterTargetArn": {
                        "Fn::GetAtt": [
                            util.get_logical_id(
                                vdc_stack.nested_stack,
                                [
                                    f"{MODULE_ID_VDC_CONTROLLER}-controller-dlq-construct"
                                ],
                            ),
                            "Arn",
                        ]
                    },
                    "maxReceiveCount": 30,
                },
            }
        },
    )

    util.assert_resource_name_has_correct_type_and_props(
        vdc_stack.nested_stack,
        vdc_template,
        resources=[f"{MODULE_ID_VDC_CONTROLLER}-controller-dlq-construct"],
        cfn_type="AWS::SQS::Queue",
        props={
            "Properties": {
                "KmsMasterKeyId": {
                    "Fn::Join": [
                        "",
                        [
                            "arn:",
                            {"Ref": "AWS::Partition"},
                            ":kms:",
                            {"Ref": "AWS::Region"},
                            ":",
                            {"Ref": "AWS::AccountId"},
                            ":key/",
                            {
                                "Ref": util.get_logical_id(
                                    vdc_stack.nested_stack,
                                    ["res-sqs-kms"],
                                ),
                            },
                        ],
                    ]
                },
                "QueueName": {
                    "Fn::Join": [
                        "",
                        [
                            vdc_stack.nested_stack.resolve(vdc_stack.cluster_name),
                            f"-{MODULE_ID_VDC_CONTROLLER}-controller-dlq",
                        ],
                    ]
                },
            }
        },
    )


def test_scheduled_event_transformer_lambda_creation(
    vdc_stack: VirtualDesktopControllerStack, vdc_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        vdc_stack.nested_stack,
        vdc_template,
        resources=["vdc-scheduled-event-transformer-construct"],
        cfn_type="AWS::Lambda::Function",
        props={
            "Properties": {
                "Handler": "scheduled_event_transformer_handler.handler",
                "Runtime": RES_COMMON_LAMBDA_RUNTIME.to_string(),
                "Timeout": 180,
                "Description": f"{MODULE_ID_VDC_CONTROLLER} lambda to intercept all scheduled events and transform to the required event object.",
                "Layers": [
                    vdc_stack.nested_stack.resolve(
                        vdc_stack.lambda_layer.layer_version_arn
                    )
                ],
                "Environment": {
                    "Variables": {
                        "IDEA_CONTROLLER_EVENTS_QUEUE_URL": vdc_stack.nested_stack.resolve(
                            vdc_stack.event_sqs_queue.queue_url  # type: ignore
                        )
                    }
                },
                "Role": vdc_stack.nested_stack.resolve(
                    vdc_stack.scheduled_event_transformer_lambda_role.role_arn  # type: ignore
                ),
            }
        },
    )


def test_custom_credential_broker_lambda_creation(
    vdc_stack: VirtualDesktopControllerStack, vdc_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        vdc_stack.nested_stack,
        vdc_template,
        resources=["vdc-custom-credential-broker-lambda-construct"],
        cfn_type="AWS::Lambda::Function",
        props={
            "Properties": {
                "Handler": "custom_credential_broker_lambda.custom_credential_broker_handler.handler",
                "Runtime": RES_COMMON_LAMBDA_RUNTIME.to_string(),
                "Timeout": 60,
                "Description": f"{MODULE_ID_VDC_CONTROLLER} lambda to provide temporary credentials for mounting object storage to virtual desktop infrastructure (VDI) instances.",
                "Layers": [
                    vdc_stack.nested_stack.resolve(
                        vdc_stack.lambda_layer.layer_version_arn
                    )
                ],
                "Environment": {
                    "Variables": {
                        "CLUSTER_NAME": vdc_stack.nested_stack.resolve(
                            vdc_stack.cluster_name
                        ),
                        "CLUSTER_SETTINGS_TABLE_NAME": {
                            "Fn::Join": [
                                "",
                                [
                                    vdc_stack.nested_stack.resolve(
                                        vdc_stack.cluster_name
                                    ),
                                    ".cluster-settings",
                                ],
                            ]
                        },
                        "DCV_HOST_DB_HASH_KEY": "instance_id",
                        "DCV_HOST_DB_IDEA_SESSION_ID_KEY": "idea_session_id",
                        "DCV_HOST_DB_IDEA_SESSION_OWNER_KEY": "idea_session_owner",
                        "MODULE_ID": MODULE_ID_VDC_CONTROLLER,
                        "OBJECT_STORAGE_CUSTOM_PROJECT_NAME_AND_USERNAME_PREFIX": constants.OBJECT_STORAGE_CUSTOM_PROJECT_NAME_AND_USERNAME_PREFIX,
                        "OBJECT_STORAGE_CUSTOM_PROJECT_NAME_PREFIX": constants.OBJECT_STORAGE_CUSTOM_PROJECT_NAME_PREFIX,
                        "OBJECT_STORAGE_NO_CUSTOM_PREFIX": constants.OBJECT_STORAGE_NO_CUSTOM_PREFIX,
                        "READ_AND_WRITE_ROLE_NAME_ARN": vdc_stack.nested_stack.resolve(
                            vdc_stack.arn_builder.get_iam_arn(
                                "s3-mount-bucket-read-write"
                            )
                        ),
                        "READ_ONLY_ROLE_NAME_ARN": vdc_stack.nested_stack.resolve(
                            vdc_stack.arn_builder.get_iam_arn(
                                "s3-mount-bucket-read-only"
                            )
                        ),
                        "SHARED_STORAGE_PREFIX": constants.MODULE_SHARED_STORAGE,
                        "STORAGE_PROVIDER_S3_BUCKET": constants.STORAGE_PROVIDER_S3_BUCKET,
                        "USER_SESSION_OWNER_KEY": "owner",
                        "USER_SESSION_SESSION_ID_KEY": "idea_session_id",
                        "HTTP_PROXY": vdc_stack.nested_stack.resolve(
                            vdc_stack.parameters.get_str(InternetProxyKey.HTTP_PROXY)
                        ),
                        "HTTPS_PROXY": vdc_stack.nested_stack.resolve(
                            vdc_stack.parameters.get_str(InternetProxyKey.HTTPS_PROXY)
                        ),
                        "NO_PROXY": vdc_stack.nested_stack.resolve(
                            vdc_stack.parameters.get_str(InternetProxyKey.NO_PROXY)
                        ),
                    }
                },
                "Role": vdc_stack.nested_stack.resolve(
                    vdc_stack.custom_credential_broker_lambda_role.role_arn  # type: ignore
                ),
            }
        },
    )


def test_vdi_helper_lambda_creation(
    vdc_stack: VirtualDesktopControllerStack, vdc_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        vdc_stack.nested_stack,
        vdc_template,
        resources=["vdc-vdi-helper-lambda-construct"],
        cfn_type="AWS::Lambda::Function",
        props={
            "Properties": {
                "Handler": "vdi_helper_lambda.handler.handler",
                "Runtime": RES_COMMON_LAMBDA_RUNTIME.to_string(),
                "Timeout": 60,
                "Description": f"{MODULE_ID_VDC_CONTROLLER} general purpose lambda for VDI operations.",
                "Layers": [
                    vdc_stack.nested_stack.resolve(
                        vdc_stack.lambda_layer.layer_version_arn
                    )
                ],
                "Environment": {
                    "Variables": {
                        "environment_name": vdc_stack.nested_stack.resolve(
                            vdc_stack.cluster_name
                        ),
                        "HTTPS_PROXY": vdc_stack.nested_stack.resolve(
                            vdc_stack.parameters.get_str(InternetProxyKey.HTTPS_PROXY)
                        ),
                        "HTTP_PROXY": vdc_stack.nested_stack.resolve(
                            vdc_stack.parameters.get_str(InternetProxyKey.HTTP_PROXY)
                        ),
                        "NO_PROXY": vdc_stack.nested_stack.resolve(
                            vdc_stack.parameters.get_str(InternetProxyKey.NO_PROXY)
                        ),
                    }
                },
            }
        },
    )


def test_api_gateway_vpc_endpoint_creation(
    vdc_stack: VirtualDesktopControllerStack, vdc_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        vdc_stack.nested_stack,
        vdc_template,
        resources=["vdc-existing-vpc-vpc", "execute-api-vpc-endpoint-construct"],
        cfn_type="AWS::EC2::VPCEndpoint",
        props={
            "Properties": {
                "VpcEndpointType": "Interface",
                "PrivateDnsEnabled": False,
                "ServiceName": f"com.amazonaws.{vdc_stack.nested_stack.region}.execute-api",
                "VpcId": vdc_stack.nested_stack.resolve(vdc_stack.vpc.vpc_id),
                "SubnetIds": vdc_stack.nested_stack.resolve(
                    vdc_stack.cluster_settings.infrastructure_host_subnets
                ),
            }
        },
    )


def test_custom_credential_broker_api_gateway_creation(
    vdc_stack: VirtualDesktopControllerStack, vdc_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        vdc_stack.nested_stack,
        vdc_template,
        resources=[f"{MODULE_ID_VDC_CONTROLLER}-custom-credential-broker-api-gateway"],
        cfn_type="AWS::ApiGateway::RestApi",
        props={
            "Properties": {
                "Description": f"{MODULE_ID_VDC_CONTROLLER} API Gateway for custom credential broker",
                "EndpointConfiguration": {
                    "Types": ["PRIVATE"],
                },
                "Name": f"{MODULE_ID_VDC_CONTROLLER}-custom-credential-broker-api-gateway",
            }
        },
    )


def test_vdi_helper_api_gateway_creation(
    vdc_stack: VirtualDesktopControllerStack, vdc_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        vdc_stack.nested_stack,
        vdc_template,
        resources=[f"{MODULE_ID_VDC_CONTROLLER}-vdi-helper-api-gateway"],
        cfn_type="AWS::ApiGateway::RestApi",
        props={
            "Properties": {
                "Description": f"{MODULE_ID_VDC_CONTROLLER} API Gateway for VDI Helper",
                "EndpointConfiguration": {
                    "Types": ["PRIVATE"],
                },
                "Name": f"{MODULE_ID_VDC_CONTROLLER}-vdi-helper-api-gateway",
            }
        },
    )


def test_dcv_host_role_creation(
    vdc_stack: VirtualDesktopControllerStack, vdc_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        vdc_stack.nested_stack,
        vdc_template,
        resources=[f"{MODULE_ID_VDC_CONTROLLER}-host-role-construct"],
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
                                        ["ssm.", {"Ref": "AWS::URLSuffix"}],
                                    ]
                                }
                            },
                        },
                        {
                            "Action": "sts:AssumeRole",
                            "Effect": "Allow",
                            "Principal": {
                                "Service": {
                                    "Fn::Join": [
                                        "",
                                        ["ec2.", {"Ref": "AWS::URLSuffix"}],
                                    ]
                                }
                            },
                        },
                        {
                            "Action": "sts:AssumeRole",
                            "Effect": "Allow",
                            "Principal": {
                                "AWS": {
                                    "Fn::GetAtt": [
                                        util.get_logical_id(
                                            vdc_stack.nested_stack,
                                            [
                                                "vdc-custom-credential-broker-lambda-role-construct"
                                            ],
                                        ),
                                        "Arn",
                                    ]
                                }
                            },
                        },
                    ],
                },
                "Description": "IAM role assigned to virtual-desktop-host",
                "RoleName": {
                    "Fn::Join": [
                        "",
                        [
                            vdc_stack.nested_stack.resolve(
                                vdc_stack.parameters.iam_resource_prefix_string
                            ),
                            vdc_stack.nested_stack.resolve(vdc_stack.cluster_name),
                            f"-{MODULE_ID_VDC_CONTROLLER}-host-role",
                        ],
                    ]
                },
            },
        },
    )


def test_dcv_host_scoped_down_role_creation(
    vdc_stack: VirtualDesktopControllerStack, vdc_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        vdc_stack.nested_stack,
        vdc_template,
        resources=[f"{MODULE_ID_VDC_CONTROLLER}-host-scoped-down-role-construct"],
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
                                        ["ssm.", {"Ref": "AWS::URLSuffix"}],
                                    ]
                                }
                            },
                        },
                        {
                            "Action": "sts:AssumeRole",
                            "Effect": "Allow",
                            "Principal": {
                                "Service": {
                                    "Fn::Join": [
                                        "",
                                        ["ec2.", {"Ref": "AWS::URLSuffix"}],
                                    ]
                                }
                            },
                        },
                    ],
                },
                "PermissionsBoundary": {
                    "Fn::If": [
                        "PermissionBoundaryProvided",
                        vdc_stack.nested_stack.resolve(
                            vdc_stack.parameters.get_str(
                                CommonKey.IAM_PERMISSION_BOUNDARY
                            )
                        ),
                        {"Ref": "AWS::NoValue"},
                    ]
                },
                "Path": vdc_stack.nested_stack.resolve(
                    vdc_stack.parameters.iam_resource_path_string
                ),
                "RoleName": {
                    "Fn::Join": [
                        "",
                        [
                            vdc_stack.nested_stack.resolve(
                                vdc_stack.parameters.iam_resource_prefix_string
                            ),
                            vdc_stack.nested_stack.resolve(vdc_stack.cluster_name),
                            f"-{MODULE_ID_VDC_CONTROLLER}-host-scoped-down-role",
                        ],
                    ]
                },
            }
        },
    )


def test_controller_role_creation(
    vdc_stack: VirtualDesktopControllerStack, vdc_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        vdc_stack.nested_stack,
        vdc_template,
        resources=[f"{MODULE_ID_VDC_CONTROLLER}-controller-role-construct"],
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
                                        ["ssm.", {"Ref": "AWS::URLSuffix"}],
                                    ]
                                }
                            },
                        },
                        {
                            "Action": "sts:AssumeRole",
                            "Effect": "Allow",
                            "Principal": {
                                "Service": {
                                    "Fn::Join": [
                                        "",
                                        ["ec2.", {"Ref": "AWS::URLSuffix"}],
                                    ]
                                }
                            },
                        },
                    ],
                },
                "PermissionsBoundary": {
                    "Fn::If": [
                        "PermissionBoundaryProvided",
                        vdc_stack.nested_stack.resolve(
                            vdc_stack.parameters.get_str(
                                CommonKey.IAM_PERMISSION_BOUNDARY
                            )
                        ),
                        {"Ref": "AWS::NoValue"},
                    ]
                },
                "Path": vdc_stack.nested_stack.resolve(
                    vdc_stack.parameters.iam_resource_path_string
                ),
                "RoleName": {
                    "Fn::Join": [
                        "",
                        [
                            vdc_stack.nested_stack.resolve(
                                vdc_stack.parameters.iam_resource_prefix_string
                            ),
                            vdc_stack.nested_stack.resolve(vdc_stack.cluster_name),
                            f"-{MODULE_ID_VDC_CONTROLLER}-controller-role",
                        ],
                    ]
                },
            }
        },
    )


def test_dcv_broker_role_creation(
    vdc_stack: VirtualDesktopControllerStack, vdc_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        vdc_stack.nested_stack,
        vdc_template,
        resources=[f"{MODULE_ID_VDC_CONTROLLER}-broker-role-construct"],
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
                                        ["ssm.", {"Ref": "AWS::URLSuffix"}],
                                    ]
                                }
                            },
                        },
                        {
                            "Action": "sts:AssumeRole",
                            "Effect": "Allow",
                            "Principal": {
                                "Service": {
                                    "Fn::Join": [
                                        "",
                                        ["ec2.", {"Ref": "AWS::URLSuffix"}],
                                    ]
                                }
                            },
                        },
                    ],
                },
                "PermissionsBoundary": {
                    "Fn::If": [
                        "PermissionBoundaryProvided",
                        vdc_stack.nested_stack.resolve(
                            vdc_stack.parameters.get_str(
                                CommonKey.IAM_PERMISSION_BOUNDARY
                            )
                        ),
                        {"Ref": "AWS::NoValue"},
                    ]
                },
                "Path": vdc_stack.nested_stack.resolve(
                    vdc_stack.parameters.iam_resource_path_string
                ),
                "RoleName": {
                    "Fn::Join": [
                        "",
                        [
                            vdc_stack.nested_stack.resolve(
                                vdc_stack.parameters.iam_resource_prefix_string
                            ),
                            vdc_stack.nested_stack.resolve(vdc_stack.cluster_name),
                            f"-{MODULE_ID_VDC_CONTROLLER}-broker-role",
                        ],
                    ]
                },
            }
        },
    )


def test_dcv_host_security_group(
    vdc_stack: VirtualDesktopControllerStack, vdc_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        vdc_stack.nested_stack,
        vdc_template,
        resources=[f"{MODULE_ID_VDC_CONTROLLER}-dcv-host-security-group-construct"],
        cfn_type="AWS::EC2::SecurityGroup",
        props={
            "Properties": {
                "GroupDescription": "Security Group for DCV Host",
                "GroupName": {
                    "Fn::Join": [
                        "",
                        [
                            vdc_stack.nested_stack.resolve(vdc_stack.cluster_name),
                            "-vdc-dcv-host-security-group",
                        ],
                    ]
                },
                "SecurityGroupEgress": [
                    {
                        "CidrIp": "0.0.0.0/0",
                        "Description": "Allow all egress for TCP",
                        "FromPort": 0,
                        "IpProtocol": "tcp",
                        "ToPort": 65535,
                    },
                    {
                        "CidrIp": "0.0.0.0/0",
                        "Description": "Allow UDP Traffic. Required for Directory Service",
                        "FromPort": 0,
                        "IpProtocol": "udp",
                        "ToPort": 1024,
                    },
                ],
                "SecurityGroupIngress": [
                    {
                        "CidrIp": {
                            "Fn::GetAtt": [
                                util.get_logical_id(
                                    vdc_stack.nested_stack,
                                    [
                                        f"{MODULE_ID_VDC_CONTROLLER}-existing-vpc-vpc-lookup-custom-resource"
                                    ],
                                ),
                                "cidr_block",
                            ]
                        },
                        "Description": "Allow HTTP traffic from all VPC nodes for API access",
                        "FromPort": 8443,
                        "IpProtocol": "tcp",
                        "ToPort": 8443,
                    },
                    {
                        "CidrIp": {
                            "Fn::GetAtt": [
                                util.get_logical_id(
                                    vdc_stack.nested_stack,
                                    [
                                        f"{MODULE_ID_VDC_CONTROLLER}-existing-vpc-vpc-lookup-custom-resource"
                                    ],
                                ),
                                "cidr_block",
                            ]
                        },
                        "Description": "Allow all Internal traffic TO DCV Host",
                        "IpProtocol": "-1",
                    },
                    {
                        "CidrIp": {
                            "Fn::GetAtt": [
                                util.get_logical_id(
                                    vdc_stack.nested_stack,
                                    [
                                        f"{MODULE_ID_VDC_CONTROLLER}-existing-vpc-vpc-lookup-custom-resource"
                                    ],
                                ),
                                "cidr_block",
                            ]
                        },
                        "Description": "Allow UDP Traffic from VPC. Required for Directory Service",
                        "FromPort": 0,
                        "IpProtocol": "udp",
                        "ToPort": 1024,
                    },
                ],
                "VpcId": vdc_stack.nested_stack.resolve(vdc_stack.vpc.vpc_id),
            }
        },
    )

    vdc_template.has_resource_properties(
        "AWS::EC2::SecurityGroupIngress",
        {
            "IpProtocol": "tcp",
            "FromPort": 22,
            "ToPort": 22,
            "SourceSecurityGroupId": vdc_stack.nested_stack.resolve(
                vdc_stack.bastion_host_security_group.security_group_id
            ),
            "Description": "Allow SSH from Bastion Host",
            "GroupId": {
                "Fn::GetAtt": [
                    util.get_logical_id(
                        vdc_stack.nested_stack,
                        [
                            f"{MODULE_ID_VDC_CONTROLLER}-dcv-host-security-group-construct"
                        ],
                    ),
                    "GroupId",
                ]
            },
        },
    )


def test_controller_security_group(
    vdc_stack: VirtualDesktopControllerStack, vdc_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        vdc_stack.nested_stack,
        vdc_template,
        resources=[f"{MODULE_ID_VDC_CONTROLLER}-controller-security-group-construct"],
        cfn_type="AWS::EC2::SecurityGroup",
        props={
            "Properties": {
                "GroupDescription": "Security Group for Virtual Desktop Controller",
                "SecurityGroupEgress": [
                    {
                        "CidrIp": "0.0.0.0/0",
                        "Description": "Allow all egress for TCP",
                        "FromPort": 0,
                        "IpProtocol": "tcp",
                        "ToPort": 65535,
                    },
                    {
                        "CidrIp": "0.0.0.0/0",
                        "Description": "Allow UDP Traffic. Required for Directory Service",
                        "FromPort": 0,
                        "IpProtocol": "udp",
                        "ToPort": 1024,
                    },
                ],
                "SecurityGroupIngress": [
                    {
                        "CidrIp": {
                            "Fn::GetAtt": [
                                util.get_logical_id(
                                    vdc_stack.nested_stack,
                                    [
                                        f"{MODULE_ID_VDC_CONTROLLER}-existing-vpc-vpc-lookup-custom-resource"
                                    ],
                                ),
                                "cidr_block",
                            ]
                        },
                        "Description": "Allow HTTP traffic from all VPC nodes for API access",
                        "FromPort": 8443,
                        "IpProtocol": "tcp",
                        "ToPort": 8443,
                    },
                    {
                        "CidrIp": {
                            "Fn::GetAtt": [
                                util.get_logical_id(
                                    vdc_stack.nested_stack,
                                    [
                                        f"{MODULE_ID_VDC_CONTROLLER}-existing-vpc-vpc-lookup-custom-resource"
                                    ],
                                ),
                                "cidr_block",
                            ]
                        },
                        "Description": "Allow all Internal traffic TO Virtual Desktop Controller",
                        "IpProtocol": "-1",
                    },
                    {
                        "CidrIp": {
                            "Fn::GetAtt": [
                                util.get_logical_id(
                                    vdc_stack.nested_stack,
                                    [
                                        f"{MODULE_ID_VDC_CONTROLLER}-existing-vpc-vpc-lookup-custom-resource"
                                    ],
                                ),
                                "cidr_block",
                            ]
                        },
                        "Description": "Allow UDP Traffic from VPC. Required for Directory Service",
                        "FromPort": 0,
                        "IpProtocol": "udp",
                        "ToPort": 1024,
                    },
                ],
            }
        },
    )

    vdc_template.has_resource_properties(
        "AWS::EC2::SecurityGroupIngress",
        {
            "IpProtocol": "tcp",
            "FromPort": 22,
            "ToPort": 22,
            "SourceSecurityGroupId": vdc_stack.nested_stack.resolve(
                vdc_stack.bastion_host_security_group.security_group_id
            ),
            "Description": "Allow SSH from Bastion Host",
            "GroupId": {
                "Fn::GetAtt": [
                    util.get_logical_id(
                        vdc_stack.nested_stack,
                        [
                            f"{MODULE_ID_VDC_CONTROLLER}-controller-security-group-construct"
                        ],
                    ),
                    "GroupId",
                ]
            },
        },
    )

    vdc_template.has_resource_properties(
        "AWS::EC2::SecurityGroupIngress",
        {
            "IpProtocol": "tcp",
            "FromPort": 8443,
            "ToPort": 8443,
            "SourceSecurityGroupId": vdc_stack.nested_stack.resolve(
                vdc_stack.external_loadbalancer_security_group.security_group_id
            ),
            "Description": "Allow HTTPs traffic from Load Balancer",
            "GroupId": {
                "Fn::GetAtt": [
                    util.get_logical_id(
                        vdc_stack.nested_stack,
                        [
                            f"{MODULE_ID_VDC_CONTROLLER}-controller-security-group-construct"
                        ],
                    ),
                    "GroupId",
                ]
            },
        },
    )


def test_dcv_connection_gateway_security_group(
    vdc_stack: VirtualDesktopControllerStack, vdc_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        vdc_stack.nested_stack,
        vdc_template,
        resources=[f"{MODULE_ID_VDC_CONTROLLER}-gateway-security-group-construct"],
        cfn_type="AWS::EC2::SecurityGroup",
        props={
            "Properties": {
                "GroupDescription": "Security Group for Virtual Desktop DCV Connection Gateway",
                "SecurityGroupEgress": [
                    {
                        "CidrIp": "0.0.0.0/0",
                        "Description": "Allow all egress for TCP",
                        "FromPort": 0,
                        "IpProtocol": "tcp",
                        "ToPort": 65535,
                    },
                    {
                        "CidrIp": "0.0.0.0/0",
                        "Description": "Allow all egress for UDP on DCV Connection Gateway",
                        "FromPort": 0,
                        "IpProtocol": "udp",
                        "ToPort": 65535,
                    },
                ],
                "SecurityGroupIngress": [
                    {
                        "CidrIp": {
                            "Fn::GetAtt": [
                                util.get_logical_id(
                                    vdc_stack.nested_stack,
                                    [
                                        f"{MODULE_ID_VDC_CONTROLLER}-existing-vpc-vpc-lookup-custom-resource"
                                    ],
                                ),
                                "cidr_block",
                            ]
                        },
                        "Description": "Allow HTTP traffic from all VPC nodes for API access",
                        "FromPort": 8443,
                        "IpProtocol": "tcp",
                        "ToPort": 8443,
                    },
                    {
                        "CidrIp": {
                            "Fn::GetAtt": [
                                util.get_logical_id(
                                    vdc_stack.nested_stack,
                                    [
                                        f"{MODULE_ID_VDC_CONTROLLER}-existing-vpc-vpc-lookup-custom-resource"
                                    ],
                                ),
                                "cidr_block",
                            ]
                        },
                        "Description": "Allow all Internal traffic TO DCV Connection Gateway",
                        "IpProtocol": "-1",
                    },
                    {
                        "CidrIp": {
                            "Fn::GetAtt": [
                                util.get_logical_id(
                                    vdc_stack.nested_stack,
                                    [
                                        f"{MODULE_ID_VDC_CONTROLLER}-existing-vpc-vpc-lookup-custom-resource"
                                    ],
                                ),
                                "cidr_block",
                            ]
                        },
                        "Description": "Allow TCP traffic access for HealthCheck to DCV Connection Gateway",
                        "FromPort": 8989,
                        "IpProtocol": "tcp",
                        "ToPort": 8989,
                    },
                ],
            }
        },
    )

    vdc_template.has_resource_properties(
        "AWS::EC2::SecurityGroupIngress",
        {
            "IpProtocol": "tcp",
            "FromPort": 22,
            "ToPort": 22,
            "SourceSecurityGroupId": vdc_stack.nested_stack.resolve(
                vdc_stack.bastion_host_security_group.security_group_id
            ),
            "Description": "Allow SSH from Bastion Host",
            "GroupId": {
                "Fn::GetAtt": [
                    util.get_logical_id(
                        vdc_stack.nested_stack,
                        [
                            f"{MODULE_ID_VDC_CONTROLLER}-gateway-security-group-construct"
                        ],
                    ),
                    "GroupId",
                ]
            },
        },
    )

    vdc_template.has_resource_properties(
        "AWS::EC2::SecurityGroupIngress",
        {
            "IpProtocol": "tcp",
            "FromPort": 8443,
            "ToPort": 8443,
            "SourceSecurityGroupId": vdc_stack.nested_stack.resolve(
                vdc_stack.external_loadbalancer_security_group.security_group_id
            ),
            "Description": "Allow HTTPs traffic from Load Balancer",
            "GroupId": {
                "Fn::GetAtt": [
                    util.get_logical_id(
                        vdc_stack.nested_stack,
                        [
                            f"{MODULE_ID_VDC_CONTROLLER}-gateway-security-group-construct"
                        ],
                    ),
                    "GroupId",
                ]
            },
        },
    )

    vdc_template.has_resource_properties(
        "AWS::EC2::SecurityGroupIngress",
        {
            "IpProtocol": "-1",
            "Description": "Allow all Traffic access from Cluster Prefix List to DCV Connection Gateway",
            "GroupId": {
                "Fn::GetAtt": [
                    util.get_logical_id(
                        vdc_stack.nested_stack,
                        [
                            f"{MODULE_ID_VDC_CONTROLLER}-gateway-security-group-construct"
                        ],
                    ),
                    "GroupId",
                ]
            },
        },
    )

    util.assert_resource_name_has_correct_type_and_props(
        vdc_stack.nested_stack,
        vdc_template,
        resources=["dcv-connection-gateway-nlb-security-group-ingress-rule"],
        cfn_type="AWS::EC2::SecurityGroupIngress",
        props={
            "Condition": "clientprefixlistprovided",
            "Properties": {
                "Description": "Allow all traffic access from Prefix List to DCV Connection Gateway",
                "FromPort": -1,
                "GroupId": {
                    "Fn::GetAtt": [
                        util.get_logical_id(
                            vdc_stack.nested_stack,
                            [
                                f"{MODULE_ID_VDC_CONTROLLER}-gateway-security-group-construct"
                            ],
                        ),
                        "GroupId",
                    ]
                },
                "IpProtocol": "-1",
                "SourcePrefixListId": vdc_stack.nested_stack.resolve(
                    vdc_stack.parameters.get(CommonKey.CLIENT_PREFIX_LIST)
                ),
                "ToPort": -1,
            },
        },
    )


def test_dcv_broker_security_group(
    vdc_stack: VirtualDesktopControllerStack, vdc_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        vdc_stack.nested_stack,
        vdc_template,
        resources=[f"{MODULE_ID_VDC_CONTROLLER}-broker-security-group-construct"],
        cfn_type="AWS::EC2::SecurityGroup",
        props={
            "Properties": {
                "GroupDescription": "Security Group for Virtual Desktop DCV Broker",
                "SecurityGroupEgress": [
                    {
                        "CidrIp": "0.0.0.0/0",
                        "Description": "Allow all egress for TCP",
                        "FromPort": 0,
                        "IpProtocol": "tcp",
                        "ToPort": 65535,
                    }
                ],
                "SecurityGroupIngress": [
                    {
                        "CidrIp": {
                            "Fn::GetAtt": [
                                util.get_logical_id(
                                    vdc_stack.nested_stack,
                                    [
                                        f"{MODULE_ID_VDC_CONTROLLER}-existing-vpc-vpc-lookup-custom-resource"
                                    ],
                                ),
                                "cidr_block",
                            ]
                        },
                        "Description": "Allow HTTP traffic from all VPC nodes for API access",
                        "FromPort": 8443,
                        "IpProtocol": "tcp",
                        "ToPort": 8443,
                    },
                    {
                        "CidrIp": {
                            "Fn::GetAtt": [
                                util.get_logical_id(
                                    vdc_stack.nested_stack,
                                    [
                                        f"{MODULE_ID_VDC_CONTROLLER}-existing-vpc-vpc-lookup-custom-resource"
                                    ],
                                ),
                                "cidr_block",
                            ]
                        },
                        "Description": "Allow all Internal traffic TO DCV Broker",
                        "IpProtocol": "-1",
                    },
                ],
            }
        },
    )

    vdc_template.has_resource_properties(
        "AWS::EC2::SecurityGroupIngress",
        {
            "IpProtocol": "tcp",
            "FromPort": 22,
            "ToPort": 22,
            "SourceSecurityGroupId": vdc_stack.nested_stack.resolve(
                vdc_stack.bastion_host_security_group.security_group_id
            ),
            "Description": "Allow SSH from Bastion Host",
            "GroupId": {
                "Fn::GetAtt": [
                    util.get_logical_id(
                        vdc_stack.nested_stack,
                        [f"{MODULE_ID_VDC_CONTROLLER}-broker-security-group-construct"],
                    ),
                    "GroupId",
                ]
            },
        },
    )


def test_external_nlb_creation(
    vdc_stack: VirtualDesktopControllerStack, vdc_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        vdc_stack.nested_stack,
        vdc_template,
        resources=[f"{MODULE_ID_VDC_CONTROLLER}-external-nlb"],
        cfn_type="AWS::ElasticLoadBalancingV2::LoadBalancer",
        props={
            "Properties": {
                "Name": {
                    "Fn::Join": [
                        "",
                        [
                            vdc_stack.nested_stack.resolve(vdc_stack.cluster_name),
                            f"-{MODULE_ID_VDC_CONTROLLER}-external-nlb",
                        ],
                    ]
                },
                "Type": "network",
                "Scheme": {
                    "Fn::If": [
                        "ispublic",
                        "internet-facing",
                        "internal",
                    ]
                },
                "LoadBalancerAttributes": [
                    {"Key": "deletion_protection.enabled", "Value": "false"},
                    {"Key": "access_logs.s3.enabled", "Value": "true"},
                    {
                        "Key": "access_logs.s3.bucket",
                        "Value": {
                            "Fn::GetAtt": [
                                util.get_logical_id(
                                    vdc_stack.nested_stack,
                                    [
                                        "get-cluster-setting-cluster.logging_bucket_name",
                                        "Resource",
                                    ],
                                ),
                                "Item.value.S",
                            ]
                        },
                    },
                    {
                        "Key": "access_logs.s3.prefix",
                        "Value": f"logs/{MODULE_ID_VDC_CONTROLLER}/external-nlb-access-logs",
                    },
                ],
                "Subnets": vdc_stack.nested_stack.resolve(
                    vdc_stack.cluster_settings.load_balancer_subnets
                ),
            }
        },
    )


def test_controller_auto_scaling_group_creation(
    vdc_stack: VirtualDesktopControllerStack, vdc_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        vdc_stack.nested_stack,
        vdc_template,
        resources=["controller-asg"],
        cfn_type="AWS::AutoScaling::AutoScalingGroup",
        props={
            "Properties": {
                "AutoScalingGroupName": {
                    "Fn::Join": [
                        "",
                        [
                            vdc_stack.nested_stack.resolve(vdc_stack.cluster_name),
                            f"-{MODULE_ID_VDC_CONTROLLER}-controller-asg",
                        ],
                    ]
                },
                "VPCZoneIdentifier": vdc_stack.nested_stack.resolve(
                    vdc_stack.cluster_settings.infrastructure_host_subnets
                ),
                "LaunchTemplate": {
                    "LaunchTemplateId": {
                        "Ref": util.get_logical_id(
                            vdc_stack.nested_stack,
                            ["controller-lt"],
                        )
                    },
                    "Version": {
                        "Fn::GetAtt": [
                            util.get_logical_id(
                                vdc_stack.nested_stack,
                                ["controller-lt"],
                            ),
                            "LatestVersionNumber",
                        ]
                    },
                },
                "MinSize": "1",
                "MaxSize": "3",
                "Cooldown": "300",
                "DefaultInstanceWarmup": 1500,
                "HealthCheckGracePeriod": 1500,
                "HealthCheckType": "ELB",
                "NewInstancesProtectedFromScaleIn": False,
                "MetricsCollection": [{"Granularity": "1Minute"}],
                "TerminationPolicies": ["Default"],
                "TargetGroupARNs": [
                    {
                        "Ref": util.get_logical_id(
                            vdc_stack.nested_stack,
                            ["controller-target-group-int"],
                        )
                    },
                    {
                        "Ref": util.get_logical_id(
                            vdc_stack.nested_stack,
                            ["controller-target-group-ext"],
                        )
                    },
                ],
                "Tags": [
                    {
                        "Key": "Name",
                        "PropagateAtLaunch": True,
                        "Value": {
                            "Fn::Join": [
                                "",
                                [
                                    vdc_stack.nested_stack.resolve(
                                        vdc_stack.cluster_name
                                    ),
                                    "-vdc-controller",
                                ],
                            ]
                        },
                    },
                    {
                        "Key": "res:EnvironmentName",
                        "PropagateAtLaunch": True,
                        "Value": vdc_stack.nested_stack.resolve(vdc_stack.cluster_name),
                    },
                    {"Key": "res:ModuleId", "PropagateAtLaunch": True, "Value": "vdc"},
                    {
                        "Key": "res:ModuleName",
                        "PropagateAtLaunch": True,
                        "Value": "virtual-desktop-controller",
                    },
                    {"Key": "res:NodeType", "PropagateAtLaunch": True, "Value": "app"},
                ],
            },
            "UpdatePolicy": {
                "AutoScalingRollingUpdate": {
                    "MaxBatchSize": 1,
                    "MinInstancesInService": 1,
                    "SuspendProcesses": [
                        "HealthCheck",
                        "ReplaceUnhealthy",
                        "AZRebalance",
                        "AlarmNotification",
                        "ScheduledActions",
                        "InstanceRefresh",
                    ],
                    "PauseTime": "PT25M",
                },
                "AutoScalingScheduledAction": {
                    "IgnoreUnmodifiedGroupSizeProperties": True
                },
            },
        },
    )

    vdc_template.has_resource_properties(
        "AWS::AutoScaling::ScalingPolicy",
        {
            "PolicyType": "TargetTrackingScaling",
            "TargetTrackingConfiguration": {
                "TargetValue": 80.0,
                "PredefinedMetricSpecification": {
                    "PredefinedMetricType": "ASGAverageCPUUtilization"
                },
            },
            "AutoScalingGroupName": {
                "Ref": util.get_logical_id(
                    vdc_stack.nested_stack,
                    ["controller-asg"],
                )
            },
        },
    )


def test_dcv_broker_auto_scaling_group_creation(
    vdc_stack: VirtualDesktopControllerStack, vdc_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        vdc_stack.nested_stack,
        vdc_template,
        resources=["dcv_broker-asg"],
        cfn_type="AWS::AutoScaling::AutoScalingGroup",
        props={
            "Properties": {
                "AutoScalingGroupName": {
                    "Fn::Join": [
                        "",
                        [
                            vdc_stack.nested_stack.resolve(vdc_stack.cluster_name),
                            f"-{MODULE_ID_VDC_CONTROLLER}-dcv_broker-asg",
                        ],
                    ]
                },
                "VPCZoneIdentifier": vdc_stack.nested_stack.resolve(
                    vdc_stack.cluster_settings.infrastructure_host_subnets
                ),
                "LaunchTemplate": {
                    "LaunchTemplateId": {
                        "Ref": util.get_logical_id(
                            vdc_stack.nested_stack,
                            ["dcv_broker-lt"],
                        )
                    },
                    "Version": {
                        "Fn::GetAtt": [
                            util.get_logical_id(
                                vdc_stack.nested_stack,
                                ["dcv_broker-lt"],
                            ),
                            "LatestVersionNumber",
                        ]
                    },
                },
                "MinSize": "1",
                "MaxSize": "3",
                "Cooldown": "300",
                "DefaultInstanceWarmup": 1500,
                "HealthCheckGracePeriod": 1500,
                "HealthCheckType": "ELB",
                "NewInstancesProtectedFromScaleIn": False,
                "MetricsCollection": [{"Granularity": "1Minute"}],
                "TerminationPolicies": ["Default"],
                "TargetGroupARNs": [
                    {
                        "Ref": util.get_logical_id(
                            vdc_stack.nested_stack,
                            ["broker-agent-target-group"],
                        )
                    },
                    {
                        "Ref": util.get_logical_id(
                            vdc_stack.nested_stack,
                            ["broker-client-target-group"],
                        )
                    },
                    {
                        "Ref": util.get_logical_id(
                            vdc_stack.nested_stack,
                            ["broker-gateway-target-group"],
                        )
                    },
                ],
                "Tags": [
                    {
                        "Key": "Name",
                        "PropagateAtLaunch": True,
                        "Value": {
                            "Fn::Join": [
                                "",
                                [
                                    vdc_stack.nested_stack.resolve(
                                        vdc_stack.cluster_name
                                    ),
                                    "-vdc-broker",
                                ],
                            ]
                        },
                    },
                    {
                        "Key": "res:EnvironmentName",
                        "PropagateAtLaunch": True,
                        "Value": vdc_stack.nested_stack.resolve(vdc_stack.cluster_name),
                    },
                    {"Key": "res:ModuleId", "PropagateAtLaunch": True, "Value": "vdc"},
                    {
                        "Key": "res:ModuleName",
                        "PropagateAtLaunch": True,
                        "Value": "virtual-desktop-controller",
                    },
                    {
                        "Key": "res:NodeType",
                        "PropagateAtLaunch": True,
                        "Value": "infra",
                    },
                ],
            },
            "UpdatePolicy": {
                "AutoScalingRollingUpdate": {
                    "MaxBatchSize": 1,
                    "MinInstancesInService": 1,
                    "SuspendProcesses": [
                        "HealthCheck",
                        "ReplaceUnhealthy",
                        "AZRebalance",
                        "AlarmNotification",
                        "ScheduledActions",
                        "InstanceRefresh",
                    ],
                    "PauseTime": "PT25M",
                },
                "AutoScalingScheduledAction": {
                    "IgnoreUnmodifiedGroupSizeProperties": True
                },
            },
        },
    )

    vdc_template.has_resource_properties(
        "AWS::AutoScaling::ScalingPolicy",
        {
            "PolicyType": "TargetTrackingScaling",
            "EstimatedInstanceWarmup": 1500,
            "TargetTrackingConfiguration": {
                "TargetValue": 80.0,
                "PredefinedMetricSpecification": {
                    "PredefinedMetricType": "ASGAverageCPUUtilization"
                },
            },
            "AutoScalingGroupName": {
                "Ref": util.get_logical_id(
                    vdc_stack.nested_stack,
                    ["dcv_broker-asg"],
                )
            },
        },
    )


def test_dcv_connection_gateway_auto_scaling_group_creation(
    vdc_stack: VirtualDesktopControllerStack, vdc_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        vdc_stack.nested_stack,
        vdc_template,
        resources=["dcv_connection_gateway-asg"],
        cfn_type="AWS::AutoScaling::AutoScalingGroup",
        props={
            "Properties": {
                "AutoScalingGroupName": {
                    "Fn::Join": [
                        "",
                        [
                            vdc_stack.nested_stack.resolve(vdc_stack.cluster_name),
                            f"-{MODULE_ID_VDC_CONTROLLER}-dcv_connection_gateway-asg",
                        ],
                    ]
                },
                "VPCZoneIdentifier": vdc_stack.nested_stack.resolve(
                    vdc_stack.cluster_settings.infrastructure_host_subnets
                ),
                "LaunchTemplate": {
                    "LaunchTemplateId": {
                        "Ref": util.get_logical_id(
                            vdc_stack.nested_stack,
                            ["dcv_connection_gateway-lt"],
                        )
                    },
                    "Version": {
                        "Fn::GetAtt": [
                            util.get_logical_id(
                                vdc_stack.nested_stack,
                                ["dcv_connection_gateway-lt"],
                            ),
                            "LatestVersionNumber",
                        ]
                    },
                },
                "MinSize": "1",
                "MaxSize": "3",
                "Cooldown": "300",
                "DefaultInstanceWarmup": 1500,
                "HealthCheckGracePeriod": 1500,
                "HealthCheckType": "ELB",
                "NewInstancesProtectedFromScaleIn": False,
                "MetricsCollection": [{"Granularity": "1Minute"}],
                "TerminationPolicies": ["Default"],
                "TargetGroupARNs": [
                    {
                        "Ref": util.get_logical_id(
                            vdc_stack.nested_stack,
                            ["dcv-connection-gateway-target-group-nlb"],
                        )
                    },
                ],
                "Tags": [
                    {
                        "Key": "Name",
                        "PropagateAtLaunch": True,
                        "Value": {
                            "Fn::Join": [
                                "",
                                [
                                    vdc_stack.nested_stack.resolve(
                                        vdc_stack.cluster_name
                                    ),
                                    "-vdc-gateway",
                                ],
                            ]
                        },
                    },
                    {
                        "Key": "res:EnvironmentName",
                        "PropagateAtLaunch": True,
                        "Value": vdc_stack.nested_stack.resolve(vdc_stack.cluster_name),
                    },
                    {"Key": "res:ModuleId", "PropagateAtLaunch": True, "Value": "vdc"},
                    {
                        "Key": "res:ModuleName",
                        "PropagateAtLaunch": True,
                        "Value": "virtual-desktop-controller",
                    },
                    {
                        "Key": "res:NodeType",
                        "PropagateAtLaunch": True,
                        "Value": "infra",
                    },
                ],
            },
            "UpdatePolicy": {
                "AutoScalingRollingUpdate": {
                    "MaxBatchSize": 1,
                    "MinInstancesInService": 1,
                    "SuspendProcesses": [
                        "HealthCheck",
                        "ReplaceUnhealthy",
                        "AZRebalance",
                        "AlarmNotification",
                        "ScheduledActions",
                        "InstanceRefresh",
                    ],
                    "PauseTime": "PT25M",
                },
                "AutoScalingScheduledAction": {
                    "IgnoreUnmodifiedGroupSizeProperties": True
                },
            },
        },
    )

    vdc_template.has_resource_properties(
        "AWS::AutoScaling::ScalingPolicy",
        {
            "PolicyType": "TargetTrackingScaling",
            "EstimatedInstanceWarmup": 1500,
            "TargetTrackingConfiguration": {
                "TargetValue": 80.0,
                "PredefinedMetricSpecification": {
                    "PredefinedMetricType": "ASGAverageCPUUtilization"
                },
            },
            "AutoScalingGroupName": {
                "Ref": util.get_logical_id(
                    vdc_stack.nested_stack,
                    ["dcv_connection_gateway-asg"],
                )
            },
        },
    )


def test_ssm_commands_sns_topic_creation(
    vdc_stack: VirtualDesktopControllerStack, vdc_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        vdc_stack.nested_stack,
        vdc_template,
        resources=["virtual-desktop-controller-sns-topic-construct"],
        cfn_type="AWS::SNS::Topic",
        props={
            "Properties": {
                "DisplayName": {
                    "Fn::Join": [
                        "",
                        [
                            vdc_stack.nested_stack.resolve(vdc_stack.cluster_name),
                            f"-{MODULE_ID_VDC_CONTROLLER}-ssm-commands-topic",
                        ],
                    ]
                },
                "TopicName": {
                    "Fn::Join": [
                        "",
                        [
                            vdc_stack.nested_stack.resolve(vdc_stack.cluster_name),
                            f"-{MODULE_ID_VDC_CONTROLLER}-ssm-commands-sns-topic",
                        ],
                    ]
                },
            }
        },
    )

    vdc_template.has_resource_properties(
        "AWS::SNS::Subscription",
        {
            "Protocol": "sqs",
            "TopicArn": {
                "Ref": util.get_logical_id(
                    vdc_stack.nested_stack,
                    ["virtual-desktop-controller-sns-topic-construct"],
                )
            },
            "Endpoint": {
                "Fn::GetAtt": [
                    util.get_logical_id(
                        vdc_stack.nested_stack,
                        [f"{MODULE_ID_VDC_CONTROLLER}-controller-construct"],
                    ),
                    "Arn",
                ]
            },
        },
    )


def test_schedule_trigger_rule_creation(
    vdc_stack: VirtualDesktopControllerStack, vdc_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        vdc_stack.nested_stack,
        vdc_template,
        resources=[f"{MODULE_ID_VDC_CONTROLLER}-schedule-rule"],
        cfn_type="AWS::Events::Rule",
        props={
            "Properties": {
                "Name": {
                    "Fn::Join": [
                        "",
                        [
                            vdc_stack.nested_stack.resolve(vdc_stack.cluster_name),
                            f"-{MODULE_ID_VDC_CONTROLLER}-schedule-rule",
                        ],
                    ]
                },
                "Description": "Event Rule to Trigger schedule check EVERY 30 minutes on VDC Controller",
                "ScheduleExpression": "cron(0/30 * * * ? *)",
                "State": "ENABLED",
                "Targets": [
                    {
                        "Arn": {
                            "Fn::GetAtt": [
                                util.get_logical_id(
                                    vdc_stack.nested_stack,
                                    ["vdc-scheduled-event-transformer-construct"],
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


def test_cognito_user_pool_client_creation(
    vdc_stack: VirtualDesktopControllerStack, vdc_template: Template
) -> None:
    vdc_template.has_resource_properties(
        "AWS::Cognito::UserPoolClient",
        {
            "AccessTokenValidity": 60,
            "GenerateSecret": True,
            "IdTokenValidity": 60,
            "RefreshTokenValidity": 43200,
            "SupportedIdentityProviders": ["COGNITO"],
            "ClientName": {
                "Fn::Join": [
                    "",
                    [
                        vdc_stack.nested_stack.resolve(vdc_stack.cluster_name),
                        f"-{MODULE_ID_VDC_CONTROLLER}",
                    ],
                ]
            },
            "AllowedOAuthFlows": ["client_credentials"],
            "AllowedOAuthFlowsUserPoolClient": True,
            "AllowedOAuthScopes": [
                {
                    "Fn::Join": [
                        "",
                        [
                            vdc_stack.nested_stack.resolve(vdc_stack.cluster_name),
                            f"-{MODULE_ID_VDC_CONTROLLER}/read",
                        ],
                    ]
                },
                {
                    "Fn::Join": [
                        "",
                        [
                            vdc_stack.nested_stack.resolve(vdc_stack.cluster_name),
                            f"-{MODULE_ID_VDC_CONTROLLER}/write",
                        ],
                    ]
                },
                {
                    "Fn::Join": [
                        "",
                        [
                            vdc_stack.nested_stack.resolve(vdc_stack.cluster_name),
                            "-cluster-manager/read",
                        ],
                    ]
                },
                {
                    "Fn::Join": [
                        "",
                        [
                            vdc_stack.nested_stack.resolve(vdc_stack.cluster_name),
                            "-dcv-session-manager/sm_scope",
                        ],
                    ]
                },
            ],
            "TokenValidityUnits": {
                "AccessToken": "minutes",
                "IdToken": "minutes",
                "RefreshToken": "minutes",
            },
        },
    )


def test_cognito_resource_server_creation(
    vdc_stack: VirtualDesktopControllerStack, vdc_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        vdc_stack.nested_stack,
        vdc_template,
        resources=["vdc-get-user-pool", "resource-server"],
        cfn_type="AWS::Cognito::UserPoolResourceServer",
        props={
            "Properties": {
                "Identifier": {
                    "Fn::Join": [
                        "",
                        [
                            vdc_stack.nested_stack.resolve(vdc_stack.cluster_name),
                            f"-{MODULE_ID_VDC_CONTROLLER}",
                        ],
                    ]
                },
                "Scopes": [
                    {"ScopeDescription": "Allow Read Access", "ScopeName": "read"},
                    {"ScopeDescription": "Allow Write Access", "ScopeName": "write"},
                ],
            }
        },
    )


def test_dcv_session_manager_resource_server_creation(
    vdc_stack: VirtualDesktopControllerStack, vdc_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        vdc_stack.nested_stack,
        vdc_template,
        resources=["vdc-get-user-pool", "dcv-session-manager-resource-server"],
        cfn_type="AWS::Cognito::UserPoolResourceServer",
        props={
            "Properties": {
                "Identifier": {
                    "Fn::Join": [
                        "",
                        [
                            vdc_stack.nested_stack.resolve(vdc_stack.cluster_name),
                            "-dcv-session-manager",
                        ],
                    ]
                },
                "Scopes": [
                    {"ScopeDescription": "sm_scope", "ScopeName": "sm_scope"},
                ],
            }
        },
    )


def test_instance_profiles_creation(
    vdc_stack: VirtualDesktopControllerStack, vdc_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        vdc_stack.nested_stack,
        vdc_template,
        resources=[f"{MODULE_ID_VDC_CONTROLLER}-host-instance-profile-construct"],
        cfn_type="AWS::IAM::InstanceProfile",
        props={
            "Properties": {
                "InstanceProfileName": {
                    "Fn::Join": [
                        "",
                        [
                            vdc_stack.nested_stack.resolve(
                                vdc_stack.parameters.iam_resource_prefix_string
                            ),
                            vdc_stack.nested_stack.resolve(vdc_stack.cluster_name),
                            f"-{MODULE_ID_VDC_CONTROLLER}-host-instance-profile",
                        ],
                    ]
                },
                "Path": vdc_stack.nested_stack.resolve(
                    vdc_stack.parameters.iam_resource_path_string
                ),
                "Roles": [
                    {
                        "Ref": util.get_logical_id(
                            vdc_stack.nested_stack,
                            [f"{MODULE_ID_VDC_CONTROLLER}-host-role-construct"],
                        )
                    }
                ],
            }
        },
    )

    util.assert_resource_name_has_correct_type_and_props(
        vdc_stack.nested_stack,
        vdc_template,
        resources=[
            f"{MODULE_ID_VDC_CONTROLLER}-host-scoped-down-instance-profile-construct"
        ],
        cfn_type="AWS::IAM::InstanceProfile",
        props={
            "Properties": {
                "InstanceProfileName": {
                    "Fn::Join": [
                        "",
                        [
                            vdc_stack.nested_stack.resolve(
                                vdc_stack.parameters.iam_resource_prefix_string
                            ),
                            vdc_stack.nested_stack.resolve(vdc_stack.cluster_name),
                            f"-{MODULE_ID_VDC_CONTROLLER}-host-scoped-down-instance-profile",
                        ],
                    ]
                },
                "Path": vdc_stack.nested_stack.resolve(
                    vdc_stack.parameters.iam_resource_path_string
                ),
                "Roles": [
                    {
                        "Ref": util.get_logical_id(
                            vdc_stack.nested_stack,
                            [
                                f"{MODULE_ID_VDC_CONTROLLER}-host-scoped-down-role-construct"
                            ],
                        )
                    }
                ],
            }
        },
    )


def test_target_groups_creation(
    vdc_stack: VirtualDesktopControllerStack, vdc_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        vdc_stack.nested_stack,
        vdc_template,
        resources=["broker-client-target-group"],
        cfn_type="AWS::ElasticLoadBalancingV2::TargetGroup",
        props={
            "Properties": {
                "Port": 8444,
                "Protocol": "HTTPS",
                "TargetType": "instance",
                "VpcId": vdc_stack.nested_stack.resolve(vdc_stack.vpc.vpc_id),
                "HealthCheckEnabled": True,
                "HealthCheckPath": "/health",
            }
        },
    )

    util.assert_resource_name_has_correct_type_and_props(
        vdc_stack.nested_stack,
        vdc_template,
        resources=["broker-agent-target-group"],
        cfn_type="AWS::ElasticLoadBalancingV2::TargetGroup",
        props={
            "Properties": {
                "Port": 8445,
                "Protocol": "HTTPS",
                "TargetType": "instance",
                "VpcId": vdc_stack.nested_stack.resolve(vdc_stack.vpc.vpc_id),
                "HealthCheckEnabled": True,
                "HealthCheckPath": "/health",
            }
        },
    )

    util.assert_resource_name_has_correct_type_and_props(
        vdc_stack.nested_stack,
        vdc_template,
        resources=["broker-gateway-target-group"],
        cfn_type="AWS::ElasticLoadBalancingV2::TargetGroup",
        props={
            "Properties": {
                "Port": 8446,
                "Protocol": "HTTPS",
                "TargetType": "instance",
                "VpcId": vdc_stack.nested_stack.resolve(vdc_stack.vpc.vpc_id),
                "HealthCheckEnabled": True,
                "HealthCheckPath": "/health",
            }
        },
    )

    util.assert_resource_name_has_correct_type_and_props(
        vdc_stack.nested_stack,
        vdc_template,
        resources=["dcv-connection-gateway-target-group-nlb"],
        cfn_type="AWS::ElasticLoadBalancingV2::TargetGroup",
        props={
            "Properties": {
                "Port": 8443,
                "Protocol": "TCP",
                "TargetType": "instance",
                "VpcId": vdc_stack.nested_stack.resolve(vdc_stack.vpc.vpc_id),
                "HealthCheckPort": "8989",
                "HealthCheckProtocol": "TCP",
                "TargetGroupAttributes": [
                    {
                        "Key": "deregistration_delay.connection_termination.enabled",
                        "Value": "true",
                    },
                    {
                        "Key": "stickiness.enabled",
                        "Value": "true",
                    },
                    {
                        "Key": "stickiness.type",
                        "Value": "source_ip",
                    },
                ],
            }
        },
    )

    util.assert_resource_name_has_correct_type_and_props(
        vdc_stack.nested_stack,
        vdc_template,
        resources=["controller-target-group-ext"],
        cfn_type="AWS::ElasticLoadBalancingV2::TargetGroup",
        props={
            "Properties": {
                "Port": 8443,
                "Protocol": "HTTPS",
                "ProtocolVersion": "HTTP1",
                "TargetType": "instance",
                "VpcId": vdc_stack.nested_stack.resolve(vdc_stack.vpc.vpc_id),
                "HealthCheckEnabled": True,
                "HealthCheckPath": "/healthcheck",
            }
        },
    )

    util.assert_resource_name_has_correct_type_and_props(
        vdc_stack.nested_stack,
        vdc_template,
        resources=["controller-target-group-int"],
        cfn_type="AWS::ElasticLoadBalancingV2::TargetGroup",
        props={
            "Properties": {
                "Port": 8443,
                "Protocol": "HTTPS",
                "ProtocolVersion": "HTTP1",
                "TargetType": "instance",
                "VpcId": vdc_stack.nested_stack.resolve(vdc_stack.vpc.vpc_id),
                "HealthCheckEnabled": True,
                "HealthCheckPath": "/healthcheck",
            }
        },
    )


def test_managed_policies_creation(
    vdc_stack: VirtualDesktopControllerStack, vdc_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        vdc_stack.nested_stack,
        vdc_template,
        resources=["vdi-host-scoped-down-managed-policy-construct"],
        cfn_type="AWS::IAM::ManagedPolicy",
        props={
            "Properties": {
                "Description": "Required policy for custom VDI scoped down instance profile",
                "ManagedPolicyName": {
                    "Fn::Join": [
                        "",
                        [
                            vdc_stack.nested_stack.resolve(
                                vdc_stack.parameters.iam_resource_prefix_string
                            ),
                            vdc_stack.nested_stack.resolve(vdc_stack.cluster_name),
                            "-vdi-host-scoped-down-managed-policy",
                        ],
                    ]
                },
                "Path": vdc_stack.nested_stack.resolve(
                    vdc_stack.parameters.iam_resource_path_string
                ),
            }
        },
    )


def test_lambda_roles_creation(
    vdc_stack: VirtualDesktopControllerStack, vdc_template: Template
) -> None:
    vdc_template.has_resource_properties(
        "AWS::IAM::Role",
        {
            "AssumeRolePolicyDocument": {
                "Statement": [
                    {
                        "Action": "sts:AssumeRole",
                        "Effect": "Allow",
                        "Principal": {
                            "Service": {
                                "Fn::Join": ["", ["lambda.", {"Ref": "AWS::URLSuffix"}]]
                            }
                        },
                    }
                ],
            },
            "Description": f"{MODULE_ID_VDC_CONTROLLER}-custom-credential-broker-lambda-role",
        },
    )

    vdc_template.has_resource_properties(
        "AWS::IAM::Role",
        {
            "AssumeRolePolicyDocument": {
                "Statement": [
                    {
                        "Action": "sts:AssumeRole",
                        "Effect": "Allow",
                        "Principal": {
                            "Service": {
                                "Fn::Join": ["", ["lambda.", {"Ref": "AWS::URLSuffix"}]]
                            }
                        },
                    }
                ],
            },
            "Description": f"{MODULE_ID_VDC_CONTROLLER}-scheduled-event-transformer-role",
        },
    )

    vdc_template.has_resource_properties(
        "AWS::IAM::Role",
        {
            "AssumeRolePolicyDocument": {
                "Statement": [
                    {
                        "Action": "sts:AssumeRole",
                        "Effect": "Allow",
                        "Principal": {
                            "Service": {
                                "Fn::Join": ["", ["ssm.", {"Ref": "AWS::URLSuffix"}]]
                            }
                        },
                    }
                ],
            },
            "Description": "IAM role for SSM Commands to send notifications via SNS",
        },
    )


def test_s3_mount_roles_creation(
    vdc_stack: VirtualDesktopControllerStack, vdc_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        vdc_stack.nested_stack,
        vdc_template,
        resources=["s3-mount-bucket-read-only-construct"],
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
                                        ["lambda.", {"Ref": "AWS::URLSuffix"}],
                                    ]
                                }
                            },
                        },
                        {
                            "Action": "sts:AssumeRole",
                            "Effect": "Allow",
                            "Principal": {
                                "AWS": {
                                    "Fn::GetAtt": [
                                        util.get_logical_id(
                                            vdc_stack.nested_stack,
                                            [
                                                "vdc-custom-credential-broker-lambda-role-construct"
                                            ],
                                        ),
                                        "Arn",
                                    ]
                                }
                            },
                        },
                    ],
                },
                "Description": "Base bucket role for read only access to S3 buckets onboarded to RES.",
                "Path": vdc_stack.nested_stack.resolve(
                    vdc_stack.parameters.iam_resource_path_string
                ),
                "RoleName": {
                    "Fn::Join": [
                        "",
                        [
                            vdc_stack.nested_stack.resolve(
                                vdc_stack.parameters.iam_resource_prefix_string
                            ),
                            vdc_stack.nested_stack.resolve(vdc_stack.cluster_name),
                            "-s3-mount-bucket-read-only",
                        ],
                    ]
                },
            }
        },
    )

    util.assert_resource_name_has_correct_type_and_props(
        vdc_stack.nested_stack,
        vdc_template,
        resources=["s3-mount-bucket-read-write-construct"],
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
                                        ["lambda.", {"Ref": "AWS::URLSuffix"}],
                                    ]
                                }
                            },
                        },
                        {
                            "Action": "sts:AssumeRole",
                            "Effect": "Allow",
                            "Principal": {
                                "AWS": {
                                    "Fn::GetAtt": [
                                        util.get_logical_id(
                                            vdc_stack.nested_stack,
                                            [
                                                "vdc-custom-credential-broker-lambda-role-construct"
                                            ],
                                        ),
                                        "Arn",
                                    ]
                                }
                            },
                        },
                    ],
                },
                "Description": "Base bucket role for read and write access to S3 buckets onboarded to RES.",
                "Path": vdc_stack.nested_stack.resolve(
                    vdc_stack.parameters.iam_resource_path_string
                ),
                "RoleName": {
                    "Fn::Join": [
                        "",
                        [
                            vdc_stack.nested_stack.resolve(
                                vdc_stack.parameters.iam_resource_prefix_string
                            ),
                            vdc_stack.nested_stack.resolve(vdc_stack.cluster_name),
                            "-s3-mount-bucket-read-write",
                        ],
                    ]
                },
            }
        },
    )


def test_nlb_listener_creation(
    vdc_stack: VirtualDesktopControllerStack, vdc_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        vdc_stack.nested_stack,
        vdc_template,
        resources=["vdc-external-nlb", "dcv-connection-gateway-nlb-listener"],
        cfn_type="AWS::ElasticLoadBalancingV2::Listener",
        props={
            "Properties": {
                "Port": 443,
                "Protocol": "TCP",
                "LoadBalancerArn": {
                    "Ref": util.get_logical_id(
                        vdc_stack.nested_stack,
                        [f"{MODULE_ID_VDC_CONTROLLER}-external-nlb"],
                    )
                },
                "DefaultActions": [
                    {
                        "Type": "forward",
                        "TargetGroupArn": {
                            "Ref": util.get_logical_id(
                                vdc_stack.nested_stack,
                                ["dcv-connection-gateway-target-group-nlb"],
                            )
                        },
                    }
                ],
            }
        },
    )


def test_launch_templates_creation(
    vdc_stack: VirtualDesktopControllerStack, vdc_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        vdc_stack.nested_stack,
        vdc_template,
        resources=["controller-lt"],
        cfn_type="AWS::EC2::LaunchTemplate",
        props={
            "Properties": {
                "LaunchTemplateData": {
                    "BlockDeviceMappings": [
                        {
                            "DeviceName": "/dev/xvda",
                            "Ebs": {
                                "Encrypted": True,
                                "VolumeSize": 200,
                                "VolumeType": "gp3",
                            },
                        }
                    ],
                    "MetadataOptions": {
                        "HttpTokens": "required",
                    },
                    "IamInstanceProfile": {
                        "Arn": {
                            "Fn::GetAtt": [
                                util.get_logical_id(
                                    vdc_stack.nested_stack,
                                    ["controller-profile-construct"],
                                ),
                                "Arn",
                            ]
                        }
                    },
                    "KeyName": vdc_stack.nested_stack.resolve(
                        vdc_stack.parameters.get_str(CommonKey.SSH_KEY_PAIR)
                    ),
                },
                "VersionDescription": vdc_stack.nested_stack.resolve(
                    vdc_stack.deployment_id
                ),
            }
        },
    )

    util.assert_resource_name_has_correct_type_and_props(
        vdc_stack.nested_stack,
        vdc_template,
        resources=["dcv_broker-lt"],
        cfn_type="AWS::EC2::LaunchTemplate",
        props={
            "Properties": {
                "LaunchTemplateData": {
                    "BlockDeviceMappings": [
                        {
                            "DeviceName": "/dev/xvda",
                            "Ebs": {
                                "Encrypted": True,
                                "VolumeSize": 200,
                                "VolumeType": "gp3",
                            },
                        }
                    ],
                    "MetadataOptions": {
                        "HttpTokens": "required",
                    },
                    "IamInstanceProfile": {
                        "Arn": {
                            "Fn::GetAtt": [
                                util.get_logical_id(
                                    vdc_stack.nested_stack,
                                    ["dcv_broker-profile-construct"],
                                ),
                                "Arn",
                            ]
                        }
                    },
                    "KeyName": vdc_stack.nested_stack.resolve(
                        vdc_stack.parameters.get_str(CommonKey.SSH_KEY_PAIR)
                    ),
                },
                "VersionDescription": vdc_stack.nested_stack.resolve(
                    vdc_stack.deployment_id
                ),
            }
        },
    )

    util.assert_resource_name_has_correct_type_and_props(
        vdc_stack.nested_stack,
        vdc_template,
        resources=["dcv_connection_gateway-lt"],
        cfn_type="AWS::EC2::LaunchTemplate",
        props={
            "Properties": {
                "LaunchTemplateData": {
                    "BlockDeviceMappings": [
                        {
                            "DeviceName": "/dev/xvda",
                            "Ebs": {
                                "Encrypted": True,
                                "VolumeSize": 200,
                                "VolumeType": "gp3",
                            },
                        }
                    ],
                    "MetadataOptions": {
                        "HttpTokens": "required",
                    },
                    "IamInstanceProfile": {
                        "Arn": {
                            "Fn::GetAtt": [
                                util.get_logical_id(
                                    vdc_stack.nested_stack,
                                    ["dcv_connection_gateway-profile-construct"],
                                ),
                                "Arn",
                            ]
                        }
                    },
                    "KeyName": vdc_stack.nested_stack.resolve(
                        vdc_stack.parameters.get_str(CommonKey.SSH_KEY_PAIR)
                    ),
                },
                "VersionDescription": vdc_stack.nested_stack.resolve(
                    vdc_stack.deployment_id
                ),
            }
        },
    )

    vdc_template.has_resource_properties(
        "AWS::EC2::LaunchTemplate",
        {
            "LaunchTemplateData": {
                "NetworkInterfaces": [
                    {
                        "AssociatePublicIpAddress": False,
                        "DeviceIndex": 0,
                    }
                ],
            }
        },
    )


def test_custom_resources_creation(
    vdc_stack: VirtualDesktopControllerStack, vdc_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        vdc_stack.nested_stack,
        vdc_template,
        resources=[f"{MODULE_ID_VDC_CONTROLLER}-creds"],
        cfn_type="Custom::GetOAuthCredentials",
        props={
            "Properties": {
                "ServiceToken": vdc_stack.nested_stack.resolve(
                    vdc_stack.identity_stack.oauth_credentials_lambda.function_arn
                ),
            }
        },
    )

    util.assert_resource_name_has_correct_type_and_props(
        vdc_stack.nested_stack,
        vdc_template,
        resources=["cluster-settings"],
        cfn_type="Custom::ClusterSettings",
        props={
            "Properties": {
                "ServiceToken": vdc_stack.nested_stack.resolve(
                    vdc_stack.cluster_stack.cluster_settings_lambda.function_arn
                ),
                "cluster_name": vdc_stack.nested_stack.resolve(vdc_stack.cluster_name),
                "module_id": MODULE_ID_VDC_CONTROLLER,
                "version": ResBaseConstruct.get_res_release_version(),
            }
        },
    )

    util.assert_resource_name_has_correct_type_and_props(
        vdc_stack.nested_stack,
        vdc_template,
        resources=["asg-cluster-settings"],
        cfn_type="Custom::ClusterSettings",
        props={
            "Properties": {
                "ServiceToken": vdc_stack.nested_stack.resolve(
                    vdc_stack.cluster_stack.cluster_settings_lambda.function_arn
                ),
                "cluster_name": vdc_stack.nested_stack.resolve(vdc_stack.cluster_name),
                "module_id": MODULE_ID_VDC_CONTROLLER,
                "version": ResBaseConstruct.get_res_release_version(),
            }
        },
    )


def test_log_groups_creation(
    vdc_stack: VirtualDesktopControllerStack, vdc_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        vdc_stack.nested_stack,
        vdc_template,
        resources=[
            f"{MODULE_ID_VDC_CONTROLLER}-{MODULE_ID_VDC_CONTROLLER}-custom-credential-broker-api-gateway-access-logs"
        ],
        cfn_type="AWS::Logs::LogGroup",
        props={
            "Properties": {
                "RetentionInDays": 3653,  # TEN_YEARS
            },
            "DeletionPolicy": "Delete",
        },
    )

    util.assert_resource_name_has_correct_type_and_props(
        vdc_stack.nested_stack,
        vdc_template,
        resources=[
            f"{MODULE_ID_VDC_CONTROLLER}-{MODULE_ID_VDC_CONTROLLER}-vdi-helper-api-gateway-access-logs"
        ],
        cfn_type="AWS::Logs::LogGroup",
        props={
            "Properties": {
                "RetentionInDays": 3653,  # TEN_YEARS
            },
            "DeletionPolicy": "Delete",
        },
    )


def test_api_gateway_methods_creation(
    vdc_stack: VirtualDesktopControllerStack, vdc_template: Template
) -> None:
    vdc_template.has_resource_properties(
        "AWS::ApiGateway::Method",
        {
            "AuthorizationType": "AWS_IAM",
            "HttpMethod": "GET",
            "Integration": {
                "Type": "AWS_PROXY",
                "IntegrationHttpMethod": "POST",
                "Uri": {
                    "Fn::Join": [
                        "",
                        [
                            "arn:",
                            {"Ref": "AWS::Partition"},
                            ":apigateway:us-east-1:lambda:path/2015-03-31/functions/",
                            {
                                "Fn::GetAtt": [
                                    util.get_logical_id(
                                        vdc_stack.nested_stack,
                                        [
                                            "vdc-custom-credential-broker-lambda-construct"
                                        ],
                                    ),
                                    "Arn",
                                ]
                            },
                            "/invocations",
                        ],
                    ]
                },
            },
        },
    )

    vdc_template.has_resource_properties(
        "AWS::ApiGateway::Method",
        {
            "AuthorizationType": "AWS_IAM",
            "HttpMethod": "POST",
            "Integration": {
                "Type": "AWS_PROXY",
                "IntegrationHttpMethod": "POST",
                "Uri": {
                    "Fn::Join": [
                        "",
                        [
                            "arn:",
                            {"Ref": "AWS::Partition"},
                            ":apigateway:us-east-1:lambda:path/2015-03-31/functions/",
                            {
                                "Fn::GetAtt": [
                                    util.get_logical_id(
                                        vdc_stack.nested_stack,
                                        ["vdc-vdi-helper-lambda-construct"],
                                    ),
                                    "Arn",
                                ]
                            },
                            "/invocations",
                        ],
                    ]
                },
            },
        },
    )


def test_api_gateway_resources_creation(
    vdc_stack: VirtualDesktopControllerStack, vdc_template: Template
) -> None:
    vdc_template.has_resource_properties(
        "AWS::ApiGateway::Resource",
        {
            "PathPart": constants.API_GATEWAY_CUSTOM_CREDENTIAL_BROKER_RESOURCE,
            "RestApiId": {
                "Ref": util.get_logical_id(
                    vdc_stack.nested_stack,
                    [
                        f"{MODULE_ID_VDC_CONTROLLER}-custom-credential-broker-api-gateway"
                    ],
                )
            },
            "ParentId": {
                "Fn::GetAtt": [
                    util.get_logical_id(
                        vdc_stack.nested_stack,
                        [
                            f"{MODULE_ID_VDC_CONTROLLER}-custom-credential-broker-api-gateway"
                        ],
                    ),
                    "RootResourceId",
                ]
            },
        },
    )

    vdc_template.has_resource_properties(
        "AWS::ApiGateway::Resource",
        {
            "PathPart": constants.API_GATEWAY_VDI_HELPER_RESOURCE,
            "RestApiId": {
                "Ref": util.get_logical_id(
                    vdc_stack.nested_stack,
                    [f"{MODULE_ID_VDC_CONTROLLER}-vdi-helper-api-gateway"],
                )
            },
            "ParentId": {
                "Fn::GetAtt": [
                    util.get_logical_id(
                        vdc_stack.nested_stack,
                        [f"{MODULE_ID_VDC_CONTROLLER}-vdi-helper-api-gateway"],
                    ),
                    "RootResourceId",
                ]
            },
        },
    )


def test_api_gateway_deployments_creation(
    vdc_stack: VirtualDesktopControllerStack, vdc_template: Template
) -> None:
    vdc_template.has_resource_properties(
        "AWS::ApiGateway::Deployment",
        {
            "Description": f"{MODULE_ID_VDC_CONTROLLER} API Gateway for custom credential broker",
            "RestApiId": {
                "Ref": util.get_logical_id(
                    vdc_stack.nested_stack,
                    [
                        f"{MODULE_ID_VDC_CONTROLLER}-custom-credential-broker-api-gateway"
                    ],
                )
            },
        },
    )

    vdc_template.has_resource_properties(
        "AWS::ApiGateway::Deployment",
        {
            "Description": f"{MODULE_ID_VDC_CONTROLLER} API Gateway for VDI Helper",
            "RestApiId": {
                "Ref": util.get_logical_id(
                    vdc_stack.nested_stack,
                    [f"{MODULE_ID_VDC_CONTROLLER}-vdi-helper-api-gateway"],
                )
            },
        },
    )


def test_conditions_creation(
    vdc_stack: VirtualDesktopControllerStack, vdc_template: Template
) -> None:
    vdc_template.has_condition("vdicertprovided", {})
    vdc_template.has_condition("vdiprivatekeyprovided", {})
    vdc_template.has_condition("clientprefixlistprovided", {})
    vdc_template.has_condition("vdicertallprovided", {})
    vdc_template.has_condition("ispublic", {})
    vdc_template.has_condition("vdicertnotprovided", {})


def test_nested_stack_tags(
    vdc_stack: VirtualDesktopControllerStack, vdc_template: Template
) -> None:
    nested_stack_template = Template.from_stack(vdc_stack.nested_stack)

    assert len(vdc_stack.nested_stack.tags.tag_values()) > 0
