#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from aws_cdk.assertions import Template

from idea.infrastructure.install import constants
from idea.infrastructure.install.constructs.base import ResBaseConstruct
from idea.infrastructure.install.parameters.common import CommonKey
from idea.infrastructure.install.stacks.cluster_manager_stack import ClusterManagerStack
from ideadatamodel import constants as idea_constants  # type: ignore
from tests.unit.infrastructure.install import util


def test_stack_description(cluster_manager_template: Template) -> None:
    description = cluster_manager_template.to_json()["Description"]
    assert "ModuleId: cluster-manager" in description
    assert "Version:" in description


def test_cognito_resource_server_creation(
    cluster_manager_stack: ClusterManagerStack, cluster_manager_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        cluster_manager_stack.nested_stack,
        cluster_manager_template,
        resources=["cluster-manager-get-user-pool", "resource-server"],
        cfn_type="AWS::Cognito::UserPoolResourceServer",
        props={
            "Properties": {
                "Identifier": {
                    "Fn::Join": [
                        "",
                        [
                            cluster_manager_stack.nested_stack.resolve(
                                cluster_manager_stack.cluster_name
                            ),
                            "-cluster-manager",
                        ],
                    ]
                },
                "Scopes": [
                    {
                        "ScopeName": "read",
                        "ScopeDescription": "Allow Read Access",
                    },
                    {
                        "ScopeName": "write",
                        "ScopeDescription": "Allow Write Access",
                    },
                ],
            }
        },
    )


def test_cognito_user_pool_client_creation(
    cluster_manager_stack: ClusterManagerStack, cluster_manager_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        cluster_manager_stack.nested_stack,
        cluster_manager_template,
        resources=["cluster-manager-get-user-pool", "cluster-manager-client"],
        cfn_type="AWS::Cognito::UserPoolClient",
        props={
            "Properties": {
                "AccessTokenValidity": 60,
                "AllowedOAuthFlows": ["client_credentials"],
                "AllowedOAuthFlowsUserPoolClient": True,
                "AllowedOAuthScopes": [
                    cluster_manager_stack.nested_stack.resolve(
                        f"{cluster_manager_stack.cluster_name}-{cluster_manager_stack.module_id}/read"
                    ),
                    cluster_manager_stack.nested_stack.resolve(
                        f"{cluster_manager_stack.cluster_name}-{cluster_manager_stack.module_id}/write"
                    ),
                ],
                "ClientName": cluster_manager_stack.nested_stack.resolve(
                    f"{cluster_manager_stack.cluster_name}-{cluster_manager_stack.module_id}"
                ),
                "ExplicitAuthFlows": [
                    "ALLOW_ADMIN_USER_PASSWORD_AUTH",
                    "ALLOW_REFRESH_TOKEN_AUTH",
                ],
                "GenerateSecret": True,
                "IdTokenValidity": 60,
                "RefreshTokenValidity": cluster_manager_stack.cluster_manager_settings.refresh_token_validity_hours
                * 60,
                "SupportedIdentityProviders": ["COGNITO"],
                "TokenValidityUnits": {
                    "AccessToken": "minutes",
                    "IdToken": "minutes",
                    "RefreshToken": "minutes",
                },
                "UserPoolId": cluster_manager_stack.nested_stack.resolve(
                    cluster_manager_stack.user_pool.user_pool_id
                ),
            }
        },
    )


def test_oauth_credentials_custom_resource_creation(
    cluster_manager_stack: ClusterManagerStack, cluster_manager_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        cluster_manager_stack.nested_stack,
        cluster_manager_template,
        resources=["cluster-manager-creds"],
        cfn_type="Custom::GetOAuthCredentials",
        props={
            "Properties": {
                "ServiceToken": cluster_manager_stack.nested_stack.resolve(
                    cluster_manager_stack.oauth_credentials_lambda_arn
                ),
                "UserPoolId": cluster_manager_stack.nested_stack.resolve(
                    cluster_manager_stack.user_pool.user_pool_id
                ),
                "ClientId": {
                    "Ref": util.get_logical_id(
                        cluster_manager_stack.nested_stack,
                        ["cluster-manager-get-user-pool", "cluster-manager-client"],
                    )
                },
            }
        },
    )


def test_oauth_client_id_secret_creation(
    cluster_manager_stack: ClusterManagerStack, cluster_manager_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        cluster_manager_stack.nested_stack,
        cluster_manager_template,
        resources=["cluster-manager-client-id"],
        cfn_type="AWS::SecretsManager::Secret",
        props={
            "Properties": {
                "Description": {
                    "Fn::Join": [
                        "",
                        [
                            "cluster-manager ClientId, Cluster: ",
                            cluster_manager_stack.nested_stack.resolve(
                                cluster_manager_stack.cluster_name
                            ),
                        ],
                    ]
                },
            }
        },
    )


def test_oauth_client_secret_creation(
    cluster_manager_stack: ClusterManagerStack, cluster_manager_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        cluster_manager_stack.nested_stack,
        cluster_manager_template,
        resources=["cluster-manager-client-secret"],
        cfn_type="AWS::SecretsManager::Secret",
        props={
            "Properties": {
                "Description": {
                    "Fn::Join": [
                        "",
                        [
                            "cluster-manager ClientSecret, Cluster: ",
                            cluster_manager_stack.nested_stack.resolve(
                                cluster_manager_stack.cluster_name
                            ),
                        ],
                    ]
                },
            }
        },
    )


def test_notifications_dlq_creation(
    cluster_manager_stack: ClusterManagerStack, cluster_manager_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        cluster_manager_stack.nested_stack,
        cluster_manager_template,
        resources=["cluster-manager-notifications-dlq-construct"],
        cfn_type="AWS::SQS::Queue",
        props={
            "Properties": {
                "ContentBasedDeduplication": True,
                "FifoQueue": True,
                "KmsMasterKeyId": "alias/aws/sqs",
                "QueueName": {
                    "Fn::Join": [
                        "",
                        [
                            cluster_manager_stack.nested_stack.resolve(
                                cluster_manager_stack.cluster_name
                            ),
                            "-cluster-manager-notifications-dlq.fifo",
                        ],
                    ]
                },
                "Tags": [
                    {"Key": "Module", "Value": "cluster-manager"},
                    {
                        "Key": "Name",
                        "Value": {
                            "Fn::Join": [
                                "",
                                [
                                    cluster_manager_stack.nested_stack.resolve(
                                        cluster_manager_stack.cluster_name
                                    ),
                                    "-cluster-manager-notifications-dlq",
                                ],
                            ]
                        },
                    },
                    {
                        "Key": "res:EnvironmentName",
                        "Value": cluster_manager_stack.nested_stack.resolve(
                            cluster_manager_stack.cluster_name
                        ),
                    },
                ],
            },
            "UpdateReplacePolicy": "Delete",
            "DeletionPolicy": "Delete",
        },
    )


def test_notifications_sqs_queue_creation(
    cluster_manager_stack: ClusterManagerStack, cluster_manager_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        cluster_manager_stack.nested_stack,
        cluster_manager_template,
        resources=["cluster-manager-notifications-construct"],
        cfn_type="AWS::SQS::Queue",
        props={
            "Properties": {
                "ContentBasedDeduplication": True,
                "FifoQueue": True,
                "KmsMasterKeyId": "alias/aws/sqs",
                "QueueName": {
                    "Fn::Join": [
                        "",
                        [
                            cluster_manager_stack.nested_stack.resolve(
                                cluster_manager_stack.cluster_name
                            ),
                            "-cluster-manager-notifications.fifo",
                        ],
                    ]
                },
                "RedrivePolicy": {
                    "deadLetterTargetArn": cluster_manager_stack.nested_stack.resolve(
                        cluster_manager_stack.notification_dlq.queue_arn
                    ),
                    "maxReceiveCount": 3,
                },
                "Tags": [
                    {"Key": "Module", "Value": "cluster-manager"},
                    {
                        "Key": "Name",
                        "Value": {
                            "Fn::Join": [
                                "",
                                [
                                    cluster_manager_stack.nested_stack.resolve(
                                        cluster_manager_stack.cluster_name
                                    ),
                                    "-cluster-manager-notifications",
                                ],
                            ]
                        },
                    },
                    {
                        "Key": "res:EnvironmentName",
                        "Value": cluster_manager_stack.nested_stack.resolve(
                            cluster_manager_stack.cluster_name
                        ),
                    },
                ],
            },
            "UpdateReplacePolicy": "Delete",
            "DeletionPolicy": "Delete",
        },
    )


def test_cluster_manager_iam_role_creation(
    cluster_manager_stack: ClusterManagerStack, cluster_manager_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        cluster_manager_stack.nested_stack,
        cluster_manager_template,
        resources=["cluster-manager-role-construct"],
        cfn_type="AWS::IAM::Role",
        props={
            "Properties": {
                "Description": "IAM role assigned to the cluster-manager",
                "PermissionsBoundary": {
                    "Fn::If": [
                        "PermissionBoundaryProvided",
                        cluster_manager_stack.nested_stack.resolve(
                            cluster_manager_stack.parameters.get_str(
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
                            cluster_manager_stack.nested_stack.resolve(
                                cluster_manager_stack.parameters.iam_resource_prefix_string
                            ),
                            cluster_manager_stack.nested_stack.resolve(
                                cluster_manager_stack.cluster_name
                            ),
                            "-cluster-manager-role",
                        ],
                    ]
                },
            }
        },
    )


def test_cluster_manager_iam_policy_creation(
    cluster_manager_stack: ClusterManagerStack, cluster_manager_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        cluster_manager_stack.nested_stack,
        cluster_manager_template,
        resources=["cluster-manager-policy"],
        cfn_type="AWS::IAM::Policy",
        props={
            "Properties": {
                "PolicyDocument": {"Version": "2012-10-17"},
                "Roles": [
                    {
                        "Ref": util.get_logical_id(
                            cluster_manager_stack.nested_stack,
                            ["cluster-manager-role-construct"],
                        )
                    }
                ],
            }
        },
    )


def test_instance_profile_creation(
    cluster_manager_stack: ClusterManagerStack, cluster_manager_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        cluster_manager_stack.nested_stack,
        cluster_manager_template,
        resources=["cluster-manager-instance-profile-construct"],
        cfn_type="AWS::IAM::InstanceProfile",
        props={
            "Properties": {
                "Roles": [
                    {
                        "Ref": util.get_logical_id(
                            cluster_manager_stack.nested_stack,
                            ["cluster-manager-role-construct"],
                        )
                    }
                ],
            }
        },
    )


def test_cluster_manager_security_group_creation(
    cluster_manager_stack: ClusterManagerStack, cluster_manager_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        cluster_manager_stack.nested_stack,
        cluster_manager_template,
        resources=["cluster-manager-security-group-construct"],
        cfn_type="AWS::EC2::SecurityGroup",
        props={
            "Properties": {
                "GroupDescription": "Cluster Manager security group",
                "GroupName": {
                    "Fn::Join": [
                        "",
                        [
                            cluster_manager_stack.nested_stack.resolve(
                                cluster_manager_stack.cluster_name
                            ),
                            "-cluster-manager-security-group",
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
                "VpcId": cluster_manager_stack.nested_stack.resolve(
                    cluster_manager_stack.vpc.vpc_id
                ),
            }
        },
    )


def test_launch_template_creation(
    cluster_manager_stack: ClusterManagerStack, cluster_manager_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        cluster_manager_stack.nested_stack,
        cluster_manager_template,
        resources=["cluster-manager-lt"],
        cfn_type="AWS::EC2::LaunchTemplate",
        props={
            "Properties": {
                "LaunchTemplateData": {
                    "InstanceType": "m5.large",
                    "KeyName": cluster_manager_stack.nested_stack.resolve(
                        cluster_manager_stack.parameters.get_str(CommonKey.SSH_KEY_PAIR)
                    ),
                }
            }
        },
    )


def test_auto_scaling_group_creation(
    cluster_manager_stack: ClusterManagerStack, cluster_manager_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        cluster_manager_stack.nested_stack,
        cluster_manager_template,
        resources=["cluster-manager-asg"],
        cfn_type="AWS::AutoScaling::AutoScalingGroup",
        props={
            "Properties": {
                "AutoScalingGroupName": {
                    "Fn::Join": [
                        "",
                        [
                            cluster_manager_stack.nested_stack.resolve(
                                cluster_manager_stack.cluster_name
                            ),
                            "-cluster-manager-asg",
                        ],
                    ]
                },
                "MinSize": "1",
                "MaxSize": "3",
            }
        },
    )


def test_web_portal_target_group_creation(
    cluster_manager_stack: ClusterManagerStack, cluster_manager_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        cluster_manager_stack.nested_stack,
        cluster_manager_template,
        resources=["web-portal-target-group"],
        cfn_type="AWS::ElasticLoadBalancingV2::TargetGroup",
        props={
            "Properties": {
                "Port": 8443,
                "Protocol": "HTTPS",
                "TargetType": "instance",
                "HealthCheckPath": "/healthcheck",
            }
        },
    )


def test_web_portal_endpoint_custom_resource_creation(
    cluster_manager_stack: ClusterManagerStack, cluster_manager_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        cluster_manager_stack.nested_stack,
        cluster_manager_template,
        resources=["web-portal-endpoint"],
        cfn_type="Custom::WebPortalEndpoint",
        props={
            "Properties": {
                "endpoint_name": "cluster-manager-web-portal-endpoint",
                "priority": 0,
                "default_action": True,
            }
        },
    )


def test_external_target_group_creation(
    cluster_manager_stack: ClusterManagerStack, cluster_manager_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        cluster_manager_stack.nested_stack,
        cluster_manager_template,
        resources=["cluster-manager-external-target-group"],
        cfn_type="AWS::ElasticLoadBalancingV2::TargetGroup",
        props={
            "Properties": {
                "Port": 8443,
                "Protocol": "HTTPS",
                "TargetType": "instance",
                "HealthCheckPath": "/healthcheck",
            }
        },
    )


def test_external_endpoint_custom_resource_creation(
    cluster_manager_stack: ClusterManagerStack, cluster_manager_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        cluster_manager_stack.nested_stack,
        cluster_manager_template,
        resources=["external-endpoint"],
        cfn_type="Custom::ClusterManagerEndpointExternal",
        props={
            "Properties": {
                "endpoint_name": "cluster-manager-external-endpoint",
            }
        },
    )


def test_internal_target_group_creation(
    cluster_manager_stack: ClusterManagerStack, cluster_manager_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        cluster_manager_stack.nested_stack,
        cluster_manager_template,
        resources=["cluster-manager-internal-target-group"],
        cfn_type="AWS::ElasticLoadBalancingV2::TargetGroup",
        props={
            "Properties": {
                "Port": 8443,
                "Protocol": "HTTPS",
                "TargetType": "instance",
                "HealthCheckPath": "/healthcheck",
            }
        },
    )


def test_internal_endpoint_custom_resource_creation(
    cluster_manager_stack: ClusterManagerStack, cluster_manager_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        cluster_manager_stack.nested_stack,
        cluster_manager_template,
        resources=["internal-endpoint"],
        cfn_type="Custom::ClusterManagerEndpointInternal",
        props={
            "Properties": {
                "endpoint_name": "cluster-manager-internal-endpoint",
            }
        },
    )


def test_configure_sso_lambda_role_creation(
    cluster_manager_stack: ClusterManagerStack, cluster_manager_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        cluster_manager_stack.nested_stack,
        cluster_manager_template,
        resources=["configure_sso-construct", "ServiceRole"],
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
            }
        },
    )


def test_configure_sso_lambda_creation(
    cluster_manager_stack: ClusterManagerStack, cluster_manager_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        cluster_manager_stack.nested_stack,
        cluster_manager_template,
        resources=["configure_sso-construct"],
        cfn_type="AWS::Lambda::Function",
        props={
            "Properties": {
                "Handler": "configure_sso_handler.handler",
                "Runtime": constants.RES_COMMON_LAMBDA_RUNTIME.to_string(),
                "Environment": {
                    "Variables": {
                        "environment_name": cluster_manager_stack.nested_stack.resolve(
                            cluster_manager_stack.cluster_name
                        ),
                    }
                },
            }
        },
    )


def test_cluster_settings_custom_resource_creation(
    cluster_manager_stack: ClusterManagerStack, cluster_manager_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        cluster_manager_stack.nested_stack,
        cluster_manager_template,
        resources=["cluster-manager-settings"],
        cfn_type="Custom::ClusterManagerSettings",
        props={
            "Properties": {
                "ServiceToken": cluster_manager_stack.nested_stack.resolve(
                    cluster_manager_stack.cluster_stack.cluster_settings_lambda.function_arn
                ),
                "cluster_name": cluster_manager_stack.nested_stack.resolve(
                    cluster_manager_stack.cluster_name
                ),
                "module_id": constants.MODULE_CLUSTER_MANAGER,
                "version": ResBaseConstruct.get_res_release_version(),
                "settings": {
                    "client_secret_name": cluster_manager_stack.nested_stack.resolve(
                        cluster_manager_stack.oauth2_client_secret.client_secret.name  # type: ignore
                    ),
                    "security_group_id": cluster_manager_stack.nested_stack.resolve(
                        cluster_manager_stack.cluster_manager_security_group.security_group_id  # type: ignore
                    ),
                    "iam_role_arn": cluster_manager_stack.nested_stack.resolve(
                        cluster_manager_stack.cluster_manager_role.role_arn  # type: ignore
                    ),
                },
            }
        },
    )
