#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
import inspect
import os
import pathlib
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TypedDict, Union

import aws_cdk as cdk
import constructs
from aws_cdk import CfnCondition, Fn, RemovalPolicy
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_elasticloadbalancingv2 as lb
from aws_cdk import aws_elasticloadbalancingv2_targets as targets
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda
from aws_cdk import custom_resources as cr

from idea.batteries_included.parameters.parameters import BIParameters
from idea.infrastructure.install.parameters.common import CommonKey
from idea.infrastructure.install.parameters.parameters import RESParameters


class LambdaCodeParams(TypedDict):
    handler: str
    code: aws_lambda.Code


class InfraUtils:

    @staticmethod
    def create_permission_boundary_applier(
        parameters: Union[RESParameters, BIParameters] = RESParameters(),
    ) -> Callable[[constructs.Construct], None]:
        def apply_permission_boundary(scope: constructs.Construct) -> None:
            InfraUtils._attach_permission_boundaries(scope, parameters)

        return apply_permission_boundary

    @staticmethod
    def _attach_permission_boundaries(
        scope: constructs.Construct,
        parameters: Union[RESParameters, BIParameters] = RESParameters(),
    ) -> None:
        # Determine if IAMPermissionBoundary ARN input was provided in CFN.
        permission_boundary_provided = CfnCondition(
            scope,
            "PermissionBoundaryProvided",
            expression=Fn.condition_not(
                Fn.condition_equals(
                    parameters.get(CommonKey.IAM_PERMISSION_BOUNDARY), ""
                )
            ),
        )
        permission_boundary_policy = iam.ManagedPolicy.from_managed_policy_arn(
            scope,
            "PermissionBoundaryPolicy",
            Fn.condition_if(
                permission_boundary_provided.logical_id,
                parameters.get(CommonKey.IAM_PERMISSION_BOUNDARY),
                cdk.Aws.NO_VALUE,
            ).to_string(),
        )
        iam.PermissionsBoundary.of(scope).apply(permission_boundary_policy)

    @staticmethod
    def infra_root_dir() -> str:
        script_dir = Path(os.path.abspath(__file__))
        return str(script_dir.parent.parent)

    @staticmethod
    def resources_dir() -> str:
        return os.path.join(InfraUtils.infra_root_dir(), "resources")

    @staticmethod
    def lambda_functions_dir() -> str:
        return os.path.join(InfraUtils.resources_dir(), "lambda_functions")

    @staticmethod
    def get_handler_and_code_for_function(
        function: Callable[[Dict[str, Any], Any], Any]
    ) -> LambdaCodeParams:
        module = inspect.getmodule(function)
        if module is None or module.__file__ is None:
            raise ValueError("module not found")
        module_name = module.__name__.rsplit(".", 1)[1]
        folder = str(pathlib.Path(module.__file__).parent)

        return LambdaCodeParams(
            handler=f"{module_name}.{function.__name__}",
            code=aws_lambda.Code.from_asset(folder),
        )

    @staticmethod
    def get_cluster_setting_custom_resource(
        scope: constructs.Construct, setting_to_retrieve: str, cluster_name: str
    ) -> cr.AwsCustomResource:
        settings_table_name = f"{cluster_name}.cluster-settings"
        get_cluster_settings_custom_resource = cr.AwsCustomResource(
            scope,
            f"get-cluster-setting-{setting_to_retrieve}",
            on_update=cr.AwsSdkCall(  # will also be called for a CREATE event
                service="dynamodb",
                action="GetItem",
                parameters={
                    "TableName": settings_table_name,
                    "Key": {
                        "key": {"S": setting_to_retrieve},
                    },
                },
                physical_resource_id=cr.PhysicalResourceId.of(setting_to_retrieve),
            ),
            policy=cr.AwsCustomResourcePolicy.from_sdk_calls(
                resources=[
                    f"arn:{cdk.Aws.PARTITION}:dynamodb:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:table/{settings_table_name}"
                ]
            ),
        )
        return get_cluster_settings_custom_resource

    @staticmethod
    def get_cluster_setting_string(
        scope: constructs.Construct, setting_to_retrieve: str, cluster_name: str
    ) -> str:
        get_cluster_settings_custom_resource = (
            InfraUtils.get_cluster_setting_custom_resource(
                scope, setting_to_retrieve, cluster_name
            )
        )
        return get_cluster_settings_custom_resource.get_response_field("Item.value.S")

    @staticmethod
    def get_cluster_setting_array(
        scope: constructs.Construct,
        setting_to_retrieve: str,
        cluster_name: str,
        max_index: int = 2,
    ) -> List[str]:
        get_cluster_settings_custom_resource = (
            InfraUtils.get_cluster_setting_custom_resource(
                scope, setting_to_retrieve, cluster_name
            )
        )

        setting_array = []
        for index in range(max_index):
            try:
                setting_array.append(
                    get_cluster_settings_custom_resource.get_response_field(
                        f"Item.value.L.{index}.S"
                    )
                )
            except Exception:
                break
        return setting_array

    @staticmethod
    def create_security_group(
        scope: constructs.Construct,
        alb_security_group_id: str,
        vpc_id: str,
        security_group_name: str,
        suffix: str = "",
    ) -> str:
        security_group = ec2.CfnSecurityGroup(
            scope,
            f"LambdaSecurityGroup{suffix}",
            group_description="Lambda security group",
            group_name=security_group_name,
            security_group_egress=[
                ec2.CfnSecurityGroup.EgressProperty(
                    ip_protocol="tcp",
                    cidr_ip="0.0.0.0/0",
                    from_port=443,
                    to_port=443,
                ),
                # DNS resolution egress rule
                ec2.CfnSecurityGroup.EgressProperty(
                    ip_protocol="udp",
                    cidr_ip="0.0.0.0/0",
                    from_port=53,
                    to_port=53,
                ),
                #  Open ports outside well-known range for internet proxy
                ec2.CfnSecurityGroup.EgressProperty(
                    ip_protocol="tcp",
                    cidr_ip="0.0.0.0/0",
                    from_port=1024,
                    to_port=65535,
                ),
            ],
            security_group_ingress=[
                ec2.CfnSecurityGroup.IngressProperty(
                    ip_protocol="tcp",
                    source_security_group_id=alb_security_group_id,
                    from_port=443,
                    to_port=443,
                )
            ],
            vpc_id=vpc_id,
        )
        security_group.apply_removal_policy(RemovalPolicy.RETAIN)
        return security_group.attr_group_id

    @staticmethod
    def add_vpc_config_to_lambda(
        scope: constructs.Construct,
        lambda_function: aws_lambda.Function,
        security_group_ids: List[str],
        subnet_ids: List[str],
        custom_id: Optional[str] = None,
    ) -> None:
        function_name = lambda_function.function_name
        lambda_id = custom_id if custom_id else "add-vpc-config-to-lambda"
        policy = cr.AwsCustomResourcePolicy.from_statements(
            [
                iam.PolicyStatement(
                    actions=["lambda:UpdateFunctionConfiguration"],
                    resources=["*"],
                ),
                # These three actions only takes * as resource
                iam.PolicyStatement(
                    actions=[
                        "ec2:DescribeSecurityGroups",
                        "ec2:DescribeSubnets",
                        "ec2:DescribeVpcs",
                    ],
                    resources=["*"],
                ),
            ]
        )
        vpc_setting_cr = cr.AwsCustomResource(
            scope,
            lambda_id,
            on_update=cr.AwsSdkCall(  # will also be called for a CREATE event
                service="@aws-sdk/client-lambda",
                action="UpdateFunctionConfigurationCommand",
                parameters={
                    "FunctionName": function_name,
                    "VpcConfig": {
                        "SubnetIds": subnet_ids,
                        "SecurityGroupIds": security_group_ids,
                    },
                },
                physical_resource_id=cr.PhysicalResourceId.of(
                    f"add-vpc-{function_name}"
                ),
            ),
            policy=policy,
        )
        vpc_setting_cr.node.add_dependency(lambda_function)
        vpc_removing_cr = cr.AwsCustomResource(
            scope,
            f"remove-vpc-{lambda_id}",
            on_delete=cr.AwsSdkCall(
                service="@aws-sdk/client-lambda",
                action="UpdateFunctionConfigurationCommand",
                parameters={
                    "FunctionName": function_name,
                    "VpcConfig": {"SubnetIds": [], "SecurityGroupIds": []},
                },
                physical_resource_id=cr.PhysicalResourceId.of(
                    f"remove-vpc{function_name}"
                ),
            ),
            policy=policy,
        )
        vpc_removing_cr.node.add_dependency(lambda_function)

    @staticmethod
    def create_execution_role(
        scope: constructs.Construct, custom_id: Optional[str] = None
    ) -> iam.Role:
        role_id = custom_id if custom_id else "LambdaExecutionRole"
        lambda_execution_role = iam.Role(
            scope,
            role_id,
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaVPCAccessExecutionRole"
                ),
            ],
        )
        return lambda_execution_role

    @staticmethod
    def create_target_group(
        scope: constructs.Construct, lambda_fn: aws_lambda.Function
    ) -> lb.ApplicationTargetGroup:
        lambda_target = targets.LambdaTarget(lambda_fn)
        target_group = lb.ApplicationTargetGroup(
            scope,
            "TargetGroup",
            targets=[lambda_target],
        )
        lambda_fn.add_permission(
            "AllowInvocationFromALBTargetGroup",
            action="lambda:InvokeFunction",
            principal=iam.ServicePrincipal("elasticloadbalancing.amazonaws.com"),
            source_arn=target_group.target_group_arn,
        )
        return target_group

    @staticmethod
    def get_ddb_table_arn(cluster_name: str, table_name: str) -> str:
        return f"arn:{cdk.Aws.PARTITION}:dynamodb:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:table/{cluster_name}.{table_name}"
