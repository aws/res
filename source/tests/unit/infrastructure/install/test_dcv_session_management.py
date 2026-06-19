#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import aws_cdk
from aws_cdk.assertions import Match, Template

from idea.infrastructure.install.constants import RES_COMMON_LAMBDA_RUNTIME
from idea.infrastructure.install.stacks.virtual_desktop_controller_stack import (
    VirtualDesktopControllerStack,
)


def test_dcv_session_management_lambda_configuration(
    vdc_stack: VirtualDesktopControllerStack,
    vdc_template: Template,
) -> None:
    """Test DCV session management lambda has correct memory, timeout, runtime, and description."""
    resolved_name = vdc_stack.nested_stack.resolve(vdc_stack.cluster_name)
    vdc_template.has_resource_properties(
        "AWS::Lambda::Function",
        {
            "Description": "RES DCV Session Management Lambda",
            "FunctionName": {
                "Fn::Join": [
                    "",
                    [
                        resolved_name,
                        "-dcv-session-management-lambda",
                    ],
                ]
            },
            "MemorySize": 256,
            "Runtime": RES_COMMON_LAMBDA_RUNTIME.to_string(),
            "Timeout": 900,
        },
    )


def test_dcv_session_management_lambda_environment_variables(
    vdc_stack: VirtualDesktopControllerStack,
    vdc_template: Template,
) -> None:
    """Test DCV session management lambda has required environment variables."""
    resolved_name = vdc_stack.nested_stack.resolve(vdc_stack.cluster_name)
    vdc_template.has_resource_properties(
        "AWS::Lambda::Function",
        {
            "Description": "RES DCV Session Management Lambda",
            "Environment": {
                "Variables": {
                    "environment_name": resolved_name,
                    "HTTP_PROXY": Match.any_value(),
                    "HTTPS_PROXY": Match.any_value(),
                    "NO_PROXY": Match.any_value(),
                }
            },
        },
    )


def test_dcv_session_management_lambda_vpc_configuration(
    vdc_template: Template,
) -> None:
    """Test DCV session management lambda is deployed in VPC."""
    vdc_template.has_resource_properties(
        "AWS::Lambda::Function",
        {
            "Description": "RES DCV Session Management Lambda",
            "VpcConfig": {
                "SecurityGroupIds": Match.any_value(),
                "SubnetIds": Match.any_value(),
            },
        },
    )


def test_ssm_command_output_bucket_created(
    vdc_stack: VirtualDesktopControllerStack,
    vdc_template: Template,
) -> None:
    """Test S3 bucket for SSM command outputs is created with correct settings."""
    vdc_template.has_resource_properties(
        "AWS::S3::Bucket",
        {
            "BucketName": Match.any_value(),
            "BucketEncryption": {
                "ServerSideEncryptionConfiguration": Match.any_value(),
            },
            "PublicAccessBlockConfiguration": {
                "BlockPublicAcls": True,
                "BlockPublicPolicy": True,
                "IgnorePublicAcls": True,
                "RestrictPublicBuckets": True,
            },
            "VersioningConfiguration": {"Status": "Enabled"},
            "LifecycleConfiguration": {
                "Rules": Match.array_with(
                    [
                        {
                            "ExpirationInDays": 1,
                            "NoncurrentVersionExpiration": {
                                "NoncurrentDays": 1,
                            },
                            "Status": "Enabled",
                        }
                    ]
                )
            },
        },
    )


def test_ssm_command_output_bucket_enforces_ssl(
    vdc_stack: VirtualDesktopControllerStack,
    vdc_template: Template,
) -> None:
    """Test S3 bucket policy enforces SSL."""
    # Find the logical ID of our specific bucket
    buckets = vdc_template.find_resources(
        "AWS::S3::Bucket",
        {"Properties": {"BucketName": Match.any_value()}},
    )
    assert len(buckets) == 1, f"Expected exactly 1 named S3 bucket, found {len(buckets)}"
    bucket_logical_id = next(iter(buckets))
    vdc_template.has_resource_properties(
        "AWS::S3::BucketPolicy",
        {
            "Bucket": {"Ref": bucket_logical_id},
            "PolicyDocument": {
                "Statement": Match.array_with(
                    [
                        Match.object_like(
                            {
                                "Effect": "Deny",
                                "Condition": {"Bool": {"aws:SecureTransport": "false"}},
                            }
                        )
                    ]
                )
            },
        },
    )


def test_dcv_session_management_lambda_target_group(
    vdc_template: Template,
) -> None:
    """Test Lambda target group is created for DCV session management."""
    vdc_template.has_resource_properties(
        "AWS::ElasticLoadBalancingV2::TargetGroup",
        {
            "TargetType": "lambda",
            "Targets": Match.any_value(),
        },
    )


def test_dcv_session_management_lambda_alb_invoke_permission(
    vdc_template: Template,
) -> None:
    """Test ALB has permission to invoke the DCV session management Lambda."""
    vdc_template.has_resource_properties(
        "AWS::Lambda::Permission",
        {
            "Action": "lambda:InvokeFunction",
            "Principal": "elasticloadbalancing.amazonaws.com",
        },
    )


def test_dcv_session_management_lambda_has_own_security_group(
    vdc_template: Template,
) -> None:
    """Test DCV session management Lambda has its own security group."""
    sgs = vdc_template.find_resources(
        "AWS::EC2::SecurityGroup",
        {
            "Properties": {
                "GroupDescription": "DCV Session Management Lambda security group",
            }
        },
    )
    assert len(sgs) == 1, f"Expected 1 DCV session mgmt SG, found {len(sgs)}"


def test_dcv_session_management_lambda_alb_routing_rule(
    vdc_template: Template,
) -> None:
    """Test ALB routing rule is created with catch-all path at low precedence."""
    vdc_template.has_resource_properties(
        "Custom::DcvSessionMgmtEndpoint",
        {
            "endpoint_name": "dcv-session-mgmt-endpoint",
            "priority": 50000,
            "conditions": Match.array_with(
                [
                    Match.object_like(
                        {
                            "Field": "path-pattern",
                            "PathPatternConfig": {"Values": ["/*"]},
                        }
                    ),
                ]
            ),
            "actions": Match.array_with(
                [
                    Match.object_like(
                        {
                            "Type": "forward",
                            "TargetGroupArn": Match.any_value(),
                        }
                    ),
                ]
            ),
        },
    )


def test_dcv_connection_token_table_created(
    res_base_template: Template,
) -> None:
    """Test DynamoDB table for connection tokens is created with correct schema."""
    res_base_template.has_resource_properties(
        "AWS::DynamoDB::Table",
        {
            "KeySchema": [{"AttributeName": "auth_token", "KeyType": "HASH"}],
            "TimeToLiveSpecification": {
                "AttributeName": "expiration_time",
                "Enabled": True,
            },
        },
    )


def test_dcv_session_management_lambda_can_write_connection_tokens(
    vdc_template: Template,
) -> None:
    """Test Lambda IAM policy includes PutItem on connection token table."""
    vdc_template.has_resource_properties(
        "AWS::IAM::Policy",
        {
            "PolicyDocument": {
                "Statement": Match.array_with(
                    [
                        Match.object_like(
                            {
                                "Action": "dynamodb:PutItem",
                                "Effect": "Allow",
                            }
                        )
                    ]
                )
            },
            "Roles": Match.array_with(
                [{"Ref": Match.string_like_regexp(".*dcvsessionmanagement.*")}]
            ),
        },
    )
