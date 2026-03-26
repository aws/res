#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from aws_cdk.assertions import Match, Template

from idea.infrastructure.install.constants import RES_COMMON_LAMBDA_RUNTIME
from idea.infrastructure.install.stacks.install_stack import InstallStack


def test_backend_lambda_configuration(
    stack: InstallStack,
    template: Template,
) -> None:
    """Test backend lambda has correct memory, timeout, runtime, and description."""
    template.has_resource_properties(
        "AWS::Lambda::Function",
        {
            "Description": "RES Backend Lambda",
            "FunctionName": {
                "Fn::Join": [
                    "",
                    [
                        stack.resolve(stack.cluster_name),
                        "-backend-lambda",
                    ],
                ]
            },
            "MemorySize": 4096,
            "Runtime": RES_COMMON_LAMBDA_RUNTIME.to_string(),
            "Timeout": 900,
        },
    )


def test_backend_lambda_environment_variables(
    stack: InstallStack,
    template: Template,
) -> None:
    """Test backend lambda has required environment variables."""
    template.has_resource_properties(
        "AWS::Lambda::Function",
        {
            "Description": "RES Backend Lambda",
            "Environment": {
                "Variables": {
                    "COGNITO_USER_POOL_PROVIDER_URL": Match.any_value(),
                    "COGNITO_USER_POOL_DOMAIN_URL": Match.any_value(),
                    "environment_name": stack.resolve(stack.cluster_name),
                    "version": Match.any_value(),
                    "aws_region": {"Ref": "AWS::Region"},
                }
            },
        },
    )


def test_backend_lambda_vpc_configuration(
    stack: InstallStack,
    template: Template,
) -> None:
    """Test backend lambda is deployed in VPC with security groups and subnets."""
    template.has_resource_properties(
        "AWS::Lambda::Function",
        {
            "Description": "RES Backend Lambda",
            "VpcConfig": {
                "SecurityGroupIds": Match.any_value(),
                "SubnetIds": Match.any_value(),
            },
        },
    )


def test_backend_lambda_has_layers(
    stack: InstallStack,
    template: Template,
) -> None:
    """Test backend lambda has lambda layers configured."""
    template.has_resource_properties(
        "AWS::Lambda::Function",
        {
            "Description": "RES Backend Lambda",
            "Layers": Match.any_value(),
        },
    )


def test_backend_target_group_creation(
    template: Template,
) -> None:
    """Test backend target group is created with lambda target type."""
    template.has_resource_properties(
        "AWS::ElasticLoadBalancingV2::TargetGroup",
        {
            "TargetType": "lambda",
        },
    )


def test_backend_lambda_alb_permission(
    template: Template,
) -> None:
    """Test backend lambda has permission to be invoked by ALB."""
    template.has_resource_properties(
        "AWS::Lambda::Permission",
        {
            "Action": "lambda:InvokeFunction",
            "Principal": "elasticloadbalancing.amazonaws.com",
        },
    )


def test_backend_alb_listener_rule(
    template: Template,
) -> None:
    """Test custom resource for ALB listener rule with /res/* path pattern."""
    template.has_resource_properties(
        "Custom::BackendLambdaEndpointInternal",
        {
            "endpoint_name": "aws-backend-client-endpoint",
            "priority": 102,
            "conditions": [
                {
                    "Field": "path-pattern",
                    "PathPatternConfig": {"Values": ["/res/*"]},
                }
            ],
            "actions": Match.array_with(
                [
                    {
                        "Type": "forward",
                        "TargetGroupArn": Match.any_value(),
                    }
                ]
            ),
        },
    )
