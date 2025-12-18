#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from aws_cdk.assertions import Template

from idea.infrastructure.install.constants import RES_COMMON_LAMBDA_RUNTIME
from idea.infrastructure.install.constructs.base import ResBaseConstruct
from idea.infrastructure.install.parameters.common import CommonKey
from idea.infrastructure.install.parameters.customdomain import CustomDomainKey
from idea.infrastructure.install.stacks.cluster_stack import ClusterStack
from ideadatamodel import constants  # type: ignore
from tests.unit.infrastructure.install import util


def test_stack_description(cluster_template: Template) -> None:
    cluster_template.template_matches(
        {
            "Description": f"ModuleId: cluster, Version: {ResBaseConstruct.get_res_release_version()}"
        }
    )


def test_cluster_prefix_list_creation(
    cluster_stack: ClusterStack, cluster_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        cluster_stack.nested_stack,
        cluster_template,
        resources=["prefix-list-construct"],
        cfn_type="AWS::EC2::PrefixList",
        props={
            "Properties": {
                "AddressFamily": "IPv4",
                "MaxEntries": 10,
                "PrefixListName": {
                    "Fn::Join": [
                        "",
                        [
                            cluster_stack.nested_stack.resolve(
                                cluster_stack.cluster_name
                            ),
                            "-prefix-list",
                        ],
                    ]
                },
            }
        },
    )


def test_default_security_group_creation(
    cluster_stack: ClusterStack, cluster_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        cluster_stack.nested_stack,
        cluster_template,
        resources=["default-security-group-construct"],
        cfn_type="AWS::EC2::SecurityGroup",
        props={
            "Properties": {
                "GroupDescription": "Default Cluster Security",
                "SecurityGroupEgress": [
                    {
                        "CidrIp": "255.255.255.255/32",
                        "Description": "Disallow all traffic",
                        "FromPort": 252,
                        "IpProtocol": "icmp",
                        "ToPort": 86,
                    }
                ],
            }
        },
    )


def test_bastion_host_security_group_creation(
    cluster_stack: ClusterStack, cluster_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        cluster_stack.nested_stack,
        cluster_template,
        resources=["bastion-host-security-group-construct"],
        cfn_type="AWS::EC2::SecurityGroup",
        props={
            "Properties": {
                "GroupDescription": "Bastion host security group",
                "SecurityGroupEgress": [
                    {
                        "CidrIp": "0.0.0.0/0",
                        "Description": "Allow all egress for TCP",
                        "IpProtocol": "tcp",
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
                                    cluster_stack.nested_stack,
                                    ["existing-vpc-vpc-lookup-custom-resource"],
                                ),
                                "cidr_block",
                            ]
                        },
                        "Description": "Allow SSH traffic from all VPC nodes",
                        "FromPort": 22,
                        "IpProtocol": "tcp",
                        "ToPort": 22,
                    },
                    {
                        "CidrIp": {
                            "Fn::GetAtt": [
                                util.get_logical_id(
                                    cluster_stack.nested_stack,
                                    ["existing-vpc-vpc-lookup-custom-resource"],
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


def test_external_load_balancer_security_group_creation(
    cluster_stack: ClusterStack, cluster_template: Template
) -> None:

    external_load_balancer_security_group_logic_id = util.get_logical_id(
        cluster_stack.nested_stack,
        ["external-load-balancer-security-group-construct"],
    )

    util.assert_resource_name_has_correct_type_and_props(
        cluster_stack.nested_stack,
        cluster_template,
        resources=["external-load-balancer-security-group-construct"],
        cfn_type="AWS::EC2::SecurityGroup",
        props={
            "Properties": {
                "GroupDescription": "External Application Load Balancer security group",
                "SecurityGroupEgress": [
                    {
                        "CidrIp": "0.0.0.0/0",
                        "Description": "Allow all egress for TCP",
                        "FromPort": 0,
                        "IpProtocol": "tcp",
                        "ToPort": 65535,
                    }
                ],
            }
        },
    )

    util.assert_resource_name_has_correct_type_and_props(
        cluster_stack.nested_stack,
        cluster_template,
        resources=[
            "external-load-balancer-security-group-construct",
            "from {IndirectPeer}:443",
        ],
        cfn_type="AWS::EC2::SecurityGroupIngress",
        props={
            "Properties": {
                "Description": "Allow HTTPS access from Cluster Prefix List to ALB",
                "FromPort": 443,
                "GroupId": {
                    "Fn::GetAtt": [
                        external_load_balancer_security_group_logic_id,
                        "GroupId",
                    ]
                },
                "IpProtocol": "tcp",
                "SourcePrefixListId": {
                    "Fn::GetAtt": [
                        util.get_logical_id(
                            cluster_stack.nested_stack,
                            ["prefix-list-construct"],
                        ),
                        "PrefixListId",
                    ]
                },
                "ToPort": 443,
            }
        },
    )

    util.assert_resource_name_has_correct_type_and_props(
        cluster_stack.nested_stack,
        cluster_template,
        resources=[
            "external-load-balancer-security-group-construct",
            "from '{IndirectPeer2}':80",
        ],
        cfn_type="AWS::EC2::SecurityGroupIngress",
        props={
            "Properties": {
                "Description": "Allow HTTP access from Cluster Prefix List to ALB",
                "FromPort": 80,
                "GroupId": {
                    "Fn::GetAtt": [
                        external_load_balancer_security_group_logic_id,
                        "GroupId",
                    ]
                },
                "IpProtocol": "tcp",
                "SourcePrefixListId": {
                    "Fn::GetAtt": [
                        util.get_logical_id(
                            cluster_stack.nested_stack,
                            ["prefix-list-construct"],
                        ),
                        "PrefixListId",
                    ]
                },
                "ToPort": 80,
            }
        },
    )

    util.assert_resource_name_has_correct_type_and_props(
        cluster_stack.nested_stack,
        cluster_template,
        resources=[
            "bastion-host-http-ingress",
        ],
        cfn_type="AWS::EC2::SecurityGroupIngress",
        props={
            "Properties": {
                "Description": "Allow HTTP from Bastion Host",
                "FromPort": 80,
                "GroupId": {
                    "Fn::GetAtt": [
                        external_load_balancer_security_group_logic_id,
                        "GroupId",
                    ]
                },
                "IpProtocol": "tcp",
                "SourceSecurityGroupId": {
                    "Fn::GetAtt": [
                        util.get_logical_id(
                            cluster_stack.nested_stack,
                            ["bastion-host-security-group-construct"],
                        ),
                        "GroupId",
                    ]
                },
                "ToPort": 80,
            }
        },
    )

    util.assert_resource_name_has_correct_type_and_props(
        cluster_stack.nested_stack,
        cluster_template,
        resources=[
            "bastion-host-https-ingress",
        ],
        cfn_type="AWS::EC2::SecurityGroupIngress",
        props={
            "Properties": {
                "Description": "Allow HTTPS from Bastion Host",
                "FromPort": 443,
                "GroupId": {
                    "Fn::GetAtt": [
                        external_load_balancer_security_group_logic_id,
                        "GroupId",
                    ]
                },
                "IpProtocol": "tcp",
                "SourceSecurityGroupId": {
                    "Fn::GetAtt": [
                        util.get_logical_id(
                            cluster_stack.nested_stack,
                            ["bastion-host-security-group-construct"],
                        ),
                        "GroupId",
                    ]
                },
                "ToPort": 443,
            }
        },
    )


def test_internal_load_balancer_security_group_creation(
    cluster_stack: ClusterStack, cluster_template: Template
) -> None:
    vpc_lookup_custom_resource_logical_id = util.get_logical_id(
        cluster_stack.nested_stack,
        ["existing-vpc-vpc-lookup-custom-resource"],
    )
    util.assert_resource_name_has_correct_type_and_props(
        cluster_stack.nested_stack,
        cluster_template,
        resources=["internal-load-balancer-security-group-construct"],
        cfn_type="AWS::EC2::SecurityGroup",
        props={
            "Properties": {
                "GroupDescription": "Internal load balancer security group",
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
                                vpc_lookup_custom_resource_logical_id,
                                "cidr_block",
                            ]
                        },
                        "Description": "Allow HTTPS traffic from all VPC nodes",
                        "FromPort": 443,
                        "IpProtocol": "tcp",
                        "ToPort": 443,
                    },
                    {
                        "CidrIp": {
                            "Fn::GetAtt": [
                                vpc_lookup_custom_resource_logical_id,
                                "cidr_block",
                            ]
                        },
                        "Description": "Allow HTTPS traffic from DCV Clients to DCV Broker",
                        "FromPort": 8444,
                        "IpProtocol": "tcp",
                        "ToPort": 8444,
                    },
                    {
                        "CidrIp": {
                            "Fn::GetAtt": [
                                vpc_lookup_custom_resource_logical_id,
                                "cidr_block",
                            ]
                        },
                        "Description": "Allow HTTPS traffic from DCV Agents to DCV Broker",
                        "FromPort": 8445,
                        "IpProtocol": "tcp",
                        "ToPort": 8445,
                    },
                    {
                        "CidrIp": {
                            "Fn::GetAtt": [
                                vpc_lookup_custom_resource_logical_id,
                                "cidr_block",
                            ]
                        },
                        "Description": "Allow HTTPS traffic from DCV Connection Gateway to DCV Broker",
                        "FromPort": 8446,
                        "IpProtocol": "tcp",
                        "ToPort": 8446,
                    },
                ],
            }
        },
    )


def test_private_hosted_zone_creation(
    cluster_stack: ClusterStack, cluster_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        cluster_stack.nested_stack,
        cluster_template,
        resources=["private-hosted-zone"],
        cfn_type="AWS::Route53::HostedZone",
        props={
            "Properties": {
                "HostedZoneConfig": {
                    "Comment": {
                        "Fn::Join": [
                            "",
                            [
                                "Private Hosted Zone for IDEA Cluster: ",
                                cluster_stack.nested_stack.resolve(
                                    cluster_stack.cluster_name
                                ),
                            ],
                        ]
                    }
                },
                "Name": {
                    "Fn::Join": [
                        "",
                        [
                            {
                                "Fn::GetAtt": [
                                    util.get_logical_id(
                                        cluster_stack.nested_stack,
                                        [
                                            "get-cluster-setting-cluster.route53.private_hosted_zone_name",
                                            "Resource",
                                            "Default",
                                        ],
                                    ),
                                    "Item.value.S",
                                ]
                            },
                            ".",
                        ],
                    ]
                },
                "VPCs": [
                    {
                        "VPCId": cluster_stack.nested_stack.resolve(
                            cluster_stack.parameters.get_str(CommonKey.VPC_ID),
                        ),
                    }
                ],
            }
        },
    )


def test_log_retention_role_creation(
    cluster_stack: ClusterStack, cluster_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        cluster_stack.nested_stack,
        cluster_template,
        resources=["log-retention-construct"],
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
                        }
                    ],
                },
                "PermissionsBoundary": {
                    "Fn::If": [
                        "PermissionBoundaryProvided",
                        cluster_stack.nested_stack.resolve(
                            cluster_stack.parameters.get_str(
                                CommonKey.IAM_PERMISSION_BOUNDARY
                            )
                        ),
                        {"Ref": "AWS::NoValue"},
                    ]
                },
                "Path": cluster_stack.nested_stack.resolve(
                    cluster_stack.parameters.iam_resource_path_string
                ),
                "RoleName": {
                    "Fn::Join": [
                        "",
                        [
                            cluster_stack.nested_stack.resolve(
                                cluster_stack.parameters.iam_resource_prefix_string
                            ),
                            cluster_stack.nested_stack.resolve(
                                cluster_stack.cluster_name
                            ),
                            "-log-retention",
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
                                    cluster_stack.nested_stack.resolve(
                                        cluster_stack.cluster_name
                                    ),
                                    "-log-retention",
                                ],
                            ]
                        },
                    },
                    {
                        "Key": constants.IDEA_TAG_ENVIRONMENT_NAME,
                        "Value": cluster_stack.nested_stack.resolve(
                            cluster_stack.cluster_name
                        ),
                    },
                    {"Key": "res:ModuleId", "Value": "cluster"},
                    {"Key": "res:ModuleName", "Value": "cluster"},
                ],
            }
        },
    )


def test_self_signed_certificate_lambda_creation(
    cluster_stack: ClusterStack, cluster_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        cluster_stack.nested_stack,
        cluster_template,
        resources=["self-signed-certificate-construct"],
        cfn_type="AWS::Lambda::Function",
        props={
            "Properties": {
                "FunctionName": {
                    "Fn::Join": [
                        "",
                        [
                            cluster_stack.nested_stack.resolve(
                                cluster_stack.cluster_name
                            ),
                            "-self-signed-certificate",
                        ],
                    ]
                },
                "Handler": "self_signed_certificate_handler.handler",
                "Role": {
                    "Fn::GetAtt": [
                        util.get_logical_id(
                            cluster_stack.nested_stack,
                            ["self-signed-certificate-construct", "ServiceRole"],
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
                                    cluster_stack.nested_stack.resolve(
                                        cluster_stack.cluster_name
                                    ),
                                    "-self-signed-certificate",
                                ],
                            ]
                        },
                    },
                    {
                        "Key": constants.IDEA_TAG_ENVIRONMENT_NAME,
                        "Value": cluster_stack.nested_stack.resolve(
                            cluster_stack.cluster_name
                        ),
                    },
                    {"Key": "res:ModuleId", "Value": "cluster"},
                    {"Key": "res:ModuleName", "Value": "cluster"},
                ],
            }
        },
    )


def test_cluster_settings_lambda_creation(
    cluster_stack: ClusterStack, cluster_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        cluster_stack.nested_stack,
        cluster_template,
        resources=["cluster-settings-lambda-construct"],
        cfn_type="AWS::Lambda::Function",
        props={
            "Properties": {
                "FunctionName": {
                    "Fn::Join": [
                        "",
                        [
                            cluster_stack.nested_stack.resolve(
                                cluster_stack.cluster_name
                            ),
                            "-cluster-settings-lambda",
                        ],
                    ]
                },
                "Handler": "update_cluster_settings_handler.handler",
                "Role": {
                    "Fn::GetAtt": [
                        util.get_logical_id(
                            cluster_stack.nested_stack,
                            ["cluster-settings-lambda-construct", "ServiceRole"],
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
                                    cluster_stack.nested_stack.resolve(
                                        cluster_stack.cluster_name
                                    ),
                                    "-cluster-settings-lambda",
                                ],
                            ]
                        },
                    },
                    {
                        "Key": constants.IDEA_TAG_ENVIRONMENT_NAME,
                        "Value": cluster_stack.nested_stack.resolve(
                            cluster_stack.cluster_name
                        ),
                    },
                    {"Key": "res:ModuleId", "Value": "cluster"},
                    {"Key": "res:ModuleName", "Value": "cluster"},
                ],
            }
        },
    )


def test_solution_metrics_lambda_creation(
    cluster_stack: ClusterStack, cluster_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        cluster_stack.nested_stack,
        cluster_template,
        resources=["solution-metrics-construct"],
        cfn_type="AWS::Lambda::Function",
        props={
            "Properties": {
                "FunctionName": {
                    "Fn::Join": [
                        "",
                        [
                            cluster_stack.nested_stack.resolve(
                                cluster_stack.cluster_name
                            ),
                            "-solution-metrics",
                        ],
                    ]
                },
                "Handler": "solution_metrics_handler.handler",
                "Role": {
                    "Fn::GetAtt": [
                        util.get_logical_id(
                            cluster_stack.nested_stack,
                            ["solution-metrics-construct", "ServiceRole"],
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
                                    cluster_stack.nested_stack.resolve(
                                        cluster_stack.cluster_name
                                    ),
                                    "-solution-metrics",
                                ],
                            ]
                        },
                    },
                    {
                        "Key": constants.IDEA_TAG_ENVIRONMENT_NAME,
                        "Value": cluster_stack.nested_stack.resolve(
                            cluster_stack.cluster_name
                        ),
                    },
                    {"Key": "res:ModuleId", "Value": "cluster"},
                    {"Key": "res:ModuleName", "Value": "cluster"},
                ],
            }
        },
    )


def test_cluster_endpoints_lambda_creation(
    cluster_stack: ClusterStack, cluster_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        cluster_stack.nested_stack,
        cluster_template,
        resources=["cluster-endpoints-construct"],
        cfn_type="AWS::Lambda::Function",
        props={
            "Properties": {
                "FunctionName": {
                    "Fn::Join": [
                        "",
                        [
                            cluster_stack.nested_stack.resolve(
                                cluster_stack.cluster_name
                            ),
                            "-cluster-endpoints",
                        ],
                    ]
                },
                "Handler": "cluster_endpoints_handler.handler",
                "Role": {
                    "Fn::GetAtt": [
                        util.get_logical_id(
                            cluster_stack.nested_stack,
                            ["cluster-endpoints-construct", "ServiceRole"],
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
                                    cluster_stack.nested_stack.resolve(
                                        cluster_stack.cluster_name
                                    ),
                                    "-cluster-endpoints",
                                ],
                            ]
                        },
                    },
                    {
                        "Key": constants.IDEA_TAG_ENVIRONMENT_NAME,
                        "Value": cluster_stack.nested_stack.resolve(
                            cluster_stack.cluster_name
                        ),
                    },
                    {"Key": "res:ModuleId", "Value": "cluster"},
                    {"Key": "res:ModuleName", "Value": "cluster"},
                ],
            }
        },
    )


def test_get_alb_listener_default_actions_lambda_creation(
    cluster_stack: ClusterStack, cluster_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        cluster_stack.nested_stack,
        cluster_template,
        resources=["get-default-actions-construct"],
        cfn_type="AWS::Lambda::Function",
        props={
            "Properties": {
                "FunctionName": {
                    "Fn::Join": [
                        "",
                        [
                            cluster_stack.nested_stack.resolve(
                                cluster_stack.cluster_name
                            ),
                            "-get-default-actions",
                        ],
                    ]
                },
                "Handler": "get_alb_listener_default_actions_handler.handler",
                "Role": {
                    "Fn::GetAtt": [
                        util.get_logical_id(
                            cluster_stack.nested_stack,
                            ["get-default-actions-construct", "ServiceRole"],
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
                                    cluster_stack.nested_stack.resolve(
                                        cluster_stack.cluster_name
                                    ),
                                    "-get-default-actions",
                                ],
                            ]
                        },
                    },
                    {
                        "Key": constants.IDEA_TAG_ENVIRONMENT_NAME,
                        "Value": cluster_stack.nested_stack.resolve(
                            cluster_stack.cluster_name
                        ),
                    },
                    {"Key": "res:ModuleId", "Value": "cluster"},
                    {"Key": "res:ModuleName", "Value": "cluster"},
                ],
            }
        },
    )


def test_external_alb_creation(
    cluster_stack: ClusterStack, cluster_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        cluster_stack.nested_stack,
        cluster_template,
        resources=["external-alb"],
        cfn_type="AWS::ElasticLoadBalancingV2::LoadBalancer",
        props={
            "Properties": {
                "Name": {
                    "Fn::Join": [
                        "",
                        [
                            cluster_stack.nested_stack.resolve(
                                cluster_stack.cluster_name
                            ),
                            "-external-alb",
                        ],
                    ]
                },
                "Scheme": {
                    "Fn::If": ["isexternalalbpublic", "internet-facing", "internal"]
                },
                "SecurityGroups": [
                    {
                        "Fn::GetAtt": [
                            util.get_logical_id(
                                cluster_stack.nested_stack,
                                ["external-load-balancer-security-group-construct"],
                            ),
                            "GroupId",
                        ]
                    }
                ],
                "Type": "application",
                "LoadBalancerAttributes": [
                    {"Key": "access_logs.s3.enabled", "Value": "true"},
                    {
                        "Key": "access_logs.s3.bucket",
                        "Value": {
                            "Fn::GetAtt": [
                                util.get_logical_id(
                                    cluster_stack.nested_stack,
                                    [
                                        "get-cluster-setting-cluster.logging_bucket_name",
                                        "Resource",
                                        "Default",
                                    ],
                                ),
                                "Item.value.S",
                            ]
                        },
                    },
                    {
                        "Key": "access_logs.s3.prefix",
                        "Value": "logs/cluster/alb-access-logs/external-alb",
                    },
                    {"Key": "routing.http2.enabled", "Value": "true"},
                    {
                        "Key": "routing.http.drop_invalid_header_fields.enabled",
                        "Value": "true",
                    },
                ],
            }
        },
    )


def test_internal_alb_creation(
    cluster_stack: ClusterStack, cluster_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        cluster_stack.nested_stack,
        cluster_template,
        resources=["internal-alb"],
        cfn_type="AWS::ElasticLoadBalancingV2::LoadBalancer",
        props={
            "Properties": {
                "Name": {
                    "Fn::Join": [
                        "",
                        [
                            cluster_stack.nested_stack.resolve(
                                cluster_stack.cluster_name
                            ),
                            "-internal-alb",
                        ],
                    ]
                },
                "Type": "application",
                "Scheme": "internal",
                "LoadBalancerAttributes": [
                    {"Key": "access_logs.s3.enabled", "Value": "true"},
                    {
                        "Key": "access_logs.s3.bucket",
                        "Value": {
                            "Fn::GetAtt": [
                                util.get_logical_id(
                                    cluster_stack.nested_stack,
                                    [
                                        "get-cluster-setting-cluster.logging_bucket_name",
                                        "Resource",
                                        "Default",
                                    ],
                                ),
                                "Item.value.S",
                            ]
                        },
                    },
                    {
                        "Key": "access_logs.s3.prefix",
                        "Value": "logs/cluster/alb-access-logs/internal-alb",
                    },
                    {"Key": "routing.http2.enabled", "Value": "true"},
                    {
                        "Key": "routing.http.drop_invalid_header_fields.enabled",
                        "Value": "true",
                    },
                ],
            }
        },
    )


def test_external_alb_https_listener_creation(
    cluster_stack: ClusterStack, cluster_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        cluster_stack.nested_stack,
        cluster_template,
        resources=["external-alb", "external-alb-https-listener"],
        cfn_type="AWS::ElasticLoadBalancingV2::Listener",
        props={
            "Properties": {
                "Certificates": [
                    {
                        "CertificateArn": {
                            "Fn::If": [
                                util.get_logical_id(
                                    cluster_stack.nested_stack,
                                    ["external-cert-is-not-provided"],
                                ),
                                {
                                    "Fn::GetAtt": [
                                        util.get_logical_id(
                                            cluster_stack.nested_stack,
                                            ["external-cert"],
                                        ),
                                        "acm_certificate_arn",
                                    ]
                                },
                                cluster_stack.nested_stack.resolve(
                                    cluster_stack.parameters.get_str(
                                        CustomDomainKey.ACM_CERTIFICATE_ARN_FOR_WEB_APP
                                    )
                                ),
                            ]
                        }
                    }
                ],
                "DefaultActions": {
                    "Fn::GetAtt": [
                        util.get_logical_id(
                            cluster_stack.nested_stack,
                            [
                                "get-alb-listener-default-actions-external-alb-https-listener"
                            ],
                        ),
                        "default_actions",
                    ]
                },
                "LoadBalancerArn": {
                    "Fn::GetAtt": [
                        util.get_logical_id(
                            cluster_stack.nested_stack, ["external-alb"]
                        ),
                        "LoadBalancerArn",
                    ]
                },
                "Port": 443,
                "Protocol": "HTTPS",
                "SslPolicy": "ELBSecurityPolicy-TLS13-1-2-2021-06",
            }
        },
    )


def test_internal_alb_https_listener_creation(
    cluster_stack: ClusterStack, cluster_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        cluster_stack.nested_stack,
        cluster_template,
        resources=["internal-alb", "internal-alb-https-listener"],
        cfn_type="AWS::ElasticLoadBalancingV2::Listener",
        props={
            "Properties": {
                "Certificates": [
                    {
                        "CertificateArn": {
                            "Fn::GetAtt": [
                                util.get_logical_id(
                                    cluster_stack.nested_stack, ["internal-cert"]
                                ),
                                "acm_certificate_arn",
                            ]
                        }
                    }
                ],
                "DefaultActions": [
                    {
                        "FixedResponseConfig": {
                            "ContentType": "application/json",
                            "MessageBody": '{"success":true,"message":"OK"}',
                            "StatusCode": "200",
                        },
                        "Type": "fixed-response",
                    }
                ],
                "LoadBalancerArn": {
                    "Fn::GetAtt": [
                        util.get_logical_id(
                            cluster_stack.nested_stack, ["internal-alb"]
                        ),
                        "LoadBalancerArn",
                    ]
                },
                "Port": 443,
                "Protocol": "HTTPS",
                "SslPolicy": "ELBSecurityPolicy-TLS13-1-2-2021-06",
            }
        },
    )


def test_ec2_events_sns_topic_creation(
    cluster_stack: ClusterStack, cluster_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        cluster_stack.nested_stack,
        cluster_template,
        resources=["ec2-state-change-sns-topic-construct"],
        cfn_type="AWS::SNS::Topic",
        props={
            "Properties": {
                "DisplayName": {
                    "Fn::Join": [
                        "",
                        [
                            cluster_stack.nested_stack.resolve(
                                cluster_stack.cluster_name
                            ),
                            "-cluster-ec2-state-change-sns-topic",
                        ],
                    ]
                },
                "TopicName": {
                    "Fn::Join": [
                        "",
                        [
                            cluster_stack.nested_stack.resolve(
                                cluster_stack.cluster_name
                            ),
                            "-cluster-ec2-state-change-sns-topic",
                        ],
                    ]
                },
            }
        },
    )


def test_ec2_state_event_transformation_lambda_creation(
    cluster_stack: ClusterStack, cluster_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        cluster_stack.nested_stack,
        cluster_template,
        resources=["ec2-event-xformer-construct"],
        cfn_type="AWS::Lambda::Function",
        props={
            "Properties": {
                "FunctionName": {
                    "Fn::Join": [
                        "",
                        [
                            cluster_stack.nested_stack.resolve(
                                cluster_stack.cluster_name
                            ),
                            "-ec2-event-xformer",
                        ],
                    ]
                },
                "Handler": "ec2_state_event_transformation_handler.handler",
                "Role": {
                    "Fn::GetAtt": [
                        util.get_logical_id(
                            cluster_stack.nested_stack,
                            ["ec2-event-xformer-construct", "ServiceRole"],
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
                                    cluster_stack.nested_stack.resolve(
                                        cluster_stack.cluster_name
                                    ),
                                    "-ec2-event-xformer",
                                ],
                            ]
                        },
                    },
                    {
                        "Key": constants.IDEA_TAG_ENVIRONMENT_NAME,
                        "Value": cluster_stack.nested_stack.resolve(
                            cluster_stack.cluster_name
                        ),
                    },
                    {"Key": "res:ModuleId", "Value": "cluster"},
                    {"Key": "res:ModuleName", "Value": "cluster"},
                ],
            }
        },
    )


def test_ec2_monitoring_rule_creation(
    cluster_stack: ClusterStack, cluster_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        cluster_stack.nested_stack,
        cluster_template,
        resources=["ec2-state-monitoring-rule"],
        cfn_type="AWS::Events::Rule",
        props={
            "Properties": {
                "Name": {
                    "Fn::Join": [
                        "",
                        [
                            cluster_stack.nested_stack.resolve(
                                cluster_stack.cluster_name
                            ),
                            "-cluster-ec2-state-monitoring-rule",
                        ],
                    ]
                },
                "Description": "Event Rule to monitor state changes on EC2 Instances",
                "EventPattern": {
                    "source": ["aws.ec2"],
                    "detail-type": ["EC2 Instance State-change Notification"],
                    "region": [{"Ref": "AWS::Region"}],
                },
                "State": "ENABLED",
            }
        },
    )


def test_external_certificate_custom_resource_creation(
    cluster_stack: ClusterStack, cluster_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        cluster_stack.nested_stack,
        cluster_template,
        resources=["external-cert"],
        cfn_type="Custom::SelfSignedCertificateExternal",
        props={
            "Properties": {
                "ServiceToken": {
                    "Fn::GetAtt": [
                        util.get_logical_id(
                            cluster_stack.nested_stack,
                            ["self-signed-certificate-construct"],
                        ),
                        "Arn",
                    ]
                },
                "domain_name": {
                    "Fn::Join": [
                        "",
                        [
                            cluster_stack.nested_stack.resolve(
                                cluster_stack.cluster_name
                            ),
                            ".idea.default",
                        ],
                    ]
                },
                "certificate_name": {
                    "Fn::Join": [
                        "",
                        [
                            cluster_stack.nested_stack.resolve(
                                cluster_stack.cluster_name
                            ),
                            "-external",
                        ],
                    ]
                },
                "create_acm_certificate": True,
            }
        },
    )


def test_internal_certificate_custom_resource_creation(
    cluster_stack: ClusterStack, cluster_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        cluster_stack.nested_stack,
        cluster_template,
        resources=["internal-cert"],
        cfn_type="Custom::SelfSignedCertificateInternal",
        props={
            "Properties": {
                "ServiceToken": {
                    "Fn::GetAtt": [
                        util.get_logical_id(
                            cluster_stack.nested_stack,
                            ["self-signed-certificate-construct"],
                        ),
                        "Arn",
                    ]
                },
                "domain_name": {
                    "Fn::Join": [
                        "",
                        [
                            "*.",
                            {
                                "Fn::GetAtt": [
                                    util.get_logical_id(
                                        cluster_stack.nested_stack,
                                        [
                                            "get-cluster-setting-cluster.route53.private_hosted_zone_name",
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
                "certificate_name": {
                    "Fn::Join": [
                        "",
                        [
                            cluster_stack.nested_stack.resolve(
                                cluster_stack.cluster_name
                            ),
                            "-internal",
                        ],
                    ]
                },
                "create_acm_certificate": True,
            }
        },
    )


def test_cluster_settings_custom_resource_creation(
    cluster_stack: ClusterStack, cluster_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        cluster_stack.nested_stack,
        cluster_template,
        resources=["cluster-settings"],
        cfn_type="Custom::ClusterSettings",
        props={
            "Properties": {
                "ServiceToken": {
                    "Fn::GetAtt": [
                        util.get_logical_id(
                            cluster_stack.nested_stack,
                            ["cluster-settings-lambda-construct"],
                        ),
                        "Arn",
                    ]
                },
                "cluster_name": cluster_stack.nested_stack.resolve(
                    cluster_stack.cluster_name
                ),
                "module_id": "cluster",
                "version": ResBaseConstruct.get_res_release_version(),
            }
        },
    )


def test_amazon_ssm_managed_instance_core_policy_creation(
    cluster_stack: ClusterStack, cluster_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        cluster_stack.nested_stack,
        cluster_template,
        resources=["amazon-ssm-managed-instance-core-construct"],
        cfn_type="AWS::IAM::ManagedPolicy",
        props={
            "Properties": {
                "Description": "The policy for Amazon EC2 Role to enable AWS Systems Manager service core functionality",
                "ManagedPolicyName": {
                    "Fn::Join": [
                        "",
                        [
                            cluster_stack.nested_stack.resolve(
                                cluster_stack.parameters.iam_resource_prefix_string
                            ),
                            cluster_stack.nested_stack.resolve(
                                cluster_stack.cluster_name
                            ),
                            "-amazon-ssm-managed-instance-core",
                        ],
                    ]
                },
                "Path": cluster_stack.nested_stack.resolve(
                    cluster_stack.parameters.iam_resource_path_string
                ),
            }
        },
    )


def test_cloud_watch_agent_server_policy_creation(
    cluster_stack: ClusterStack, cluster_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        cluster_stack.nested_stack,
        cluster_template,
        resources=["cloud-watch-agent-server-policy-construct"],
        cfn_type="AWS::IAM::ManagedPolicy",
        props={
            "Properties": {
                "Description": "Permissions required to use AmazonCloudWatchAgent on servers",
                "ManagedPolicyName": {
                    "Fn::Join": [
                        "",
                        [
                            cluster_stack.nested_stack.resolve(
                                cluster_stack.parameters.iam_resource_prefix_string
                            ),
                            cluster_stack.nested_stack.resolve(
                                cluster_stack.cluster_name
                            ),
                            "-cloud-watch-agent-server-policy",
                        ],
                    ]
                },
                "Path": cluster_stack.nested_stack.resolve(
                    cluster_stack.parameters.iam_resource_path_string
                ),
            }
        },
    )
