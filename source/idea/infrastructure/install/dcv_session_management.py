#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

import aws_cdk
import aws_cdk.aws_elasticloadbalancingv2 as elbv2
import aws_cdk.aws_elasticloadbalancingv2_targets as targets
import aws_cdk.aws_s3 as s3
from aws_cdk import RemovalPolicy, aws_iam

from idea.dcv_session_management import handler as dcv_handler
from idea.infrastructure.install.constants import (
    RES_COMMON_LAMBDA_RUNTIME,
)
from idea.infrastructure.install.constructs import lambda_
from idea.infrastructure.install.constructs.ec2 import (
    DcvSessionManagementLambdaSecurityGroup,
)
from idea.infrastructure.install.policies.dcv_session_management_lambda_policy import (
    DcvSessionManagementLambdaPolicy,
)
from idea.infrastructure.install.parameters.internet_proxy import InternetProxyKey

if TYPE_CHECKING:
    from idea.infrastructure.install.stacks.virtual_desktop_controller_stack import (
        VirtualDesktopControllerStack,
    )

DCV_SESSION_MGMT_LAMBDA_NAME = "dcv-session-management-lambda"
SSM_COMMAND_OUTPUT_BUCKET_SUFFIX = "ssm-command-output"
# ALB listener rule priorities (lower number = higher precedence):
#   - Specific path rules (e.g. /vdc/*): 100-999
#   - Catch-all fallback to DCV session mgmt Lambda: 50000
DCV_SESSION_MGMT_LAMBDA_PRIORITY = 50000
# 256 MB provides ~2x headroom over observed peak usage (~113 MB) and
# improves cold-start latency since Lambda CPU scales with memory.
DCV_SESSION_MGMT_LAMBDA_MEMORY_MB = 256


def build_dcv_session_management_lambda(
    vdc: VirtualDesktopControllerStack,
) -> None:
    """Build the DCV Session Management Lambda and S3 bucket within the VDC nested stack."""
    scope = vdc.nested_stack

    # S3 bucket for SSM remote command outputs
    ssm_command_output_bucket = s3.Bucket(
        scope,
        "SsmCommandOutputBucket",
        bucket_name=vdc.cluster_settings.ssm_command_output_bucket,  # type: ignore
        block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
        encryption=s3.BucketEncryption.S3_MANAGED,
        removal_policy=RemovalPolicy.DESTROY,
        auto_delete_objects=True,
        versioned=True,
        enforce_ssl=True,
        lifecycle_rules=[
            s3.LifecycleRule(
                expiration=aws_cdk.Duration.days(1),
                noncurrent_version_expiration=aws_cdk.Duration.days(1),
            )
        ],
    )

    # Security group for the Lambda
    dcv_lambda_sg = DcvSessionManagementLambdaSecurityGroup(
        name="dcv-session-mgmt-lambda-sg",
        scope=scope,
        vpc=vdc.vpc,
        parameters=vdc.parameters,
    )

    # Lambda function
    dcv_lambda = lambda_.Function(
        scope,
        DCV_SESSION_MGMT_LAMBDA_NAME,
        handler=dcv_handler.handle_dcv_session_management_event,
        parameters=vdc.parameters,
        runtime=RES_COMMON_LAMBDA_RUNTIME,
        description="RES DCV Session Management Lambda",  # type: ignore
        timeout=aws_cdk.Duration.minutes(15),  # type: ignore
        memory_size=DCV_SESSION_MGMT_LAMBDA_MEMORY_MB,  # type: ignore
        layers=[vdc.lambda_layer],  # type: ignore
        initial_policy=DcvSessionManagementLambdaPolicy.create_policy_statements(  # type: ignore
            vdc.arn_builder,
        ),
        environment={
            "environment_name": str(vdc.cluster_name),
            "HTTP_PROXY": vdc.parameters.get_str(InternetProxyKey.HTTP_PROXY),
            "HTTPS_PROXY": vdc.parameters.get_str(InternetProxyKey.HTTPS_PROXY),
            "NO_PROXY": vdc.parameters.get_str(InternetProxyKey.NO_PROXY),
        },
        vpc=vdc.vpc,  # type: ignore
        security_groups=[dcv_lambda_sg],  # type: ignore
    )

    cfn_lambda: aws_cdk.aws_lambda.CfnFunction = dcv_lambda.node.default_child  # type: ignore
    cfn_lambda.add_property_override(
        "VpcConfig.SubnetIds",
        vdc.cluster_settings.infrastructure_host_subnets,
    )
    dcv_lambda.role.add_managed_policy(  # type: ignore
        aws_iam.ManagedPolicy.from_aws_managed_policy_name(
            "service-role/AWSLambdaVPCAccessExecutionRole"
        )
    )

    # ALB target group for the Lambda
    lambda_target = targets.LambdaTarget(dcv_lambda)
    target_group = elbv2.ApplicationTargetGroup(
        scope,
        "dcv-session-mgmt-target-group",
        targets=[lambda_target],
    )

    # Route all unmatched traffic on the internal ALB to the Lambda.
    # Uses a catch-all path pattern at a high priority number (low precedence)
    # so that more specific rules (e.g. /vdc/*) take precedence.
    aws_cdk.CustomResource(
        scope,
        "dcv-session-mgmt-endpoint",
        service_token=vdc.CLUSTER_ENDPOINTS_LAMBDA_ARN,
        properties={
            "endpoint_name": "dcv-session-mgmt-endpoint",
            "listener_arn": vdc.cluster_stack.internal_alb_https_listener.attr_listener_arn,  # type: ignore
            "priority": DCV_SESSION_MGMT_LAMBDA_PRIORITY,
            "conditions": [
                {
                    "Field": "path-pattern",
                    "PathPatternConfig": {"Values": ["/*"]},
                }
            ],
            "actions": [
                {
                    "Type": "forward",
                    "TargetGroupArn": target_group.target_group_arn,
                }
            ],
        },
        resource_type="Custom::DcvSessionMgmtEndpoint",
    )
