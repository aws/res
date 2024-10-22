#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
import json
import typing
from typing import Any, Optional, TypedDict, Union

import aws_cdk
import aws_cdk.aws_elasticloadbalancingv2 as lb
import aws_cdk.aws_elasticloadbalancingv2_targets as targets
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import custom_resources as cr
from aws_cdk.aws_iam import ServicePrincipal
from aws_cdk.aws_lambda import Function
from aws_cdk.custom_resources import AwsCustomResource, AwsCustomResourcePolicy
from constructs import Construct

from idea.infrastructure.install import proxy_handler, utils
from idea.infrastructure.install.constants import RES_COMMON_LAMBDA_RUNTIME
from idea.infrastructure.install.handlers import installer_handlers


class LambdaCodeParams(TypedDict):
    handler: str
    code: lambda_.Code


class ProxyParams(TypedDict):
    target_group_priority: int
    ddb_users_table_name: str
    ddb_groups_table_name: str
    ddb_cluster_settings_table_name: str
    cluster_name: str


proxy_lambda_security_group_name = "proxy-lambda-security-group-id"
proxy_lambda_name = "aws-api-proxy-lambda"


class Proxy(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        params: ProxyParams,
        lambda_layer: lambda_.LayerVersion,
    ):
        super().__init__(scope, id)
        self.params: ProxyParams = params
        self.lambda_layer = lambda_layer

        # Get existing resources in RES to integrate with the Proxy
        cognito_domain_url = self.get_cluster_setting_string(
            "identity-provider.cognito.domain_url"
        )
        cognito_provider_url = self.get_cluster_setting_string(
            "identity-provider.cognito.provider_url"
        )
        external_alb_https_listener_arn = self.get_cluster_setting_string(
            "cluster.load_balancers.external_alb.https_listener_arn"
        )
        endpoint_custom_lambda_arn = self.get_cluster_setting_string(
            "cluster.cluster_endpoints_lambda_arn"
        )
        alb_security_group_id = self.get_cluster_setting_string(
            "cluster.network.security_groups.external-load-balancer"
        )
        vpc_id = self.get_cluster_setting_string("cluster.network.vpc_id")
        subnet_ids = self.get_cluster_setting_array("cluster.network.private_subnets")

        proxy_lambda = self.create_proxy_lambda(
            cognito_domain_url,
            cognito_provider_url,
        )

        security_group_id = self.create_security_group(alb_security_group_id, vpc_id)
        self.add_vpc_config_to_lambda(
            proxy_lambda,
            [security_group_id],
            subnet_ids,
        )
        self.remove_ingress_rule_for_alb_sg_on_delete(
            security_group_id, alb_security_group_id
        )

        self.target_group = self.create_proxy_target_group(proxy_lambda)
        self.add_target_group_to_alb(
            external_alb_https_listener_arn, endpoint_custom_lambda_arn
        )

    def add_vpc_config_to_lambda(
        self,
        proxy_lambda: Function,
        security_group_ids: typing.List[str],
        subnet_ids: typing.List[str],
    ) -> None:
        function_name = proxy_lambda.function_name
        vpc_setting_cr = cr.AwsCustomResource(
            self,
            "add-vpc-config-to-lambda",
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
                physical_resource_id=cr.PhysicalResourceId.of(function_name),
            ),
            on_delete=cr.AwsSdkCall(
                service="@aws-sdk/client-lambda",
                action="UpdateFunctionConfigurationCommand",
                parameters={
                    "FunctionName": function_name,
                    "VpcConfig": {"SubnetIds": [], "SecurityGroupIds": []},
                },
                physical_resource_id=cr.PhysicalResourceId.of(function_name),
            ),
            policy=cr.AwsCustomResourcePolicy.from_statements(
                [
                    aws_iam.PolicyStatement(
                        actions=["lambda:UpdateFunctionConfiguration"],
                        resources=[proxy_lambda.function_arn],
                    ),
                    # These three actions only takes * as resource
                    aws_iam.PolicyStatement(
                        actions=[
                            "ec2:DescribeSecurityGroups",
                            "ec2:DescribeSubnets",
                            "ec2:DescribeVpcs",
                        ],
                        resources=["*"],
                    ),
                ]
            ),
        )
        vpc_setting_cr.node.add_dependency(proxy_lambda)

    def create_proxy_target_group(self, proxy_lambda: Any) -> lb.ApplicationTargetGroup:
        lambda_target = targets.LambdaTarget(proxy_lambda)
        target_group = lb.ApplicationTargetGroup(
            self,
            "proxyTargetGroup",
            targets=[lambda_target],
        )
        proxy_lambda.add_permission(
            "AllowInvocationFromALBTargetGroup",
            action="lambda:InvokeFunction",
            principal=ServicePrincipal("elasticloadbalancing.amazonaws.com"),
            source_arn=target_group.target_group_arn,
        )
        return target_group

    def get_cluster_setting_string(self, setting_to_retrieve: str) -> str:
        get_cluster_settings_custom_resource = self.get_cluster_setting_custom_resource(
            setting_to_retrieve
        )
        return get_cluster_settings_custom_resource.get_response_field("Item.value.S")

    def get_cluster_setting_array(
        self, setting_to_retrieve: str, max_index: int = 2
    ) -> typing.List[str]:
        get_cluster_settings_custom_resource = self.get_cluster_setting_custom_resource(
            setting_to_retrieve
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

    def get_cluster_setting_custom_resource(
        self, setting_to_retrieve: str
    ) -> AwsCustomResource:
        settings_table_name = self.params["ddb_cluster_settings_table_name"]
        get_cluster_settings_custom_resource = cr.AwsCustomResource(
            self,
            f"getClusterSetting-{setting_to_retrieve}",
            on_update=cr.AwsSdkCall(  # will also be called for a CREATE event
                service="dynamodb",
                action="GetItem",
                parameters={
                    "TableName": settings_table_name,  # "res-new.cluster-settings",
                    "Key": {
                        "key": {"S": setting_to_retrieve},
                    },
                },
                physical_resource_id=cr.PhysicalResourceId.of(setting_to_retrieve),
            ),
            policy=cr.AwsCustomResourcePolicy.from_sdk_calls(
                resources=[
                    f"arn:{aws_cdk.Aws.PARTITION}:dynamodb:{aws_cdk.Aws.REGION}:{aws_cdk.Aws.ACCOUNT_ID}:table/{settings_table_name}"
                ]
            ),
        )
        return get_cluster_settings_custom_resource

    def add_target_group_to_alb(
        self, external_alb_https_listener_arn: str, endpoint_custom_lambda_arn: str
    ) -> None:
        endpoint_id = "aws-proxy-client-endpoint"
        aws_cdk.CustomResource(
            self,
            endpoint_id,
            service_token=endpoint_custom_lambda_arn,
            properties={
                "endpoint_name": endpoint_id,
                "listener_arn": external_alb_https_listener_arn,
                "priority": self.params["target_group_priority"],
                "conditions": [
                    {
                        "Field": "path-pattern",
                        "PathPatternConfig": {"Values": ["/awsproxy/*"]},
                    }
                ],
                "actions": [
                    {
                        "Type": "forward",
                        "TargetGroupArn": self.target_group.target_group_arn,
                    }
                ],
            },
            resource_type="Custom::AWSAPIProxyEndpointInternal",
        )

    def create_security_group(self, alb_security_group_id: str, vpc_id: str) -> str:
        cluster_name = self.params["cluster_name"]
        security_group = ec2.CfnSecurityGroup(
            self,
            "ProxyLambdaSecurityGroup",
            group_description="Security group for Proxy Lambda",
            group_name=f"{cluster_name}_{proxy_lambda_security_group_name}",
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
        security_group.apply_removal_policy(aws_cdk.RemovalPolicy.RETAIN)
        return security_group.attr_group_id

    def remove_ingress_rule_for_alb_sg_on_delete(
        self, security_group_id: str, alb_security_group_id: str
    ) -> AwsCustomResource:
        remove_ingress_rule = cr.AwsCustomResource(
            self,
            "RemoveIngressRuleOnALB",
            on_delete=cr.AwsSdkCall(
                service="EC2",
                action="revokeSecurityGroupIngress",
                parameters={
                    "GroupId": security_group_id,
                    "IpPermissions": [
                        {
                            "IpProtocol": "tcp",
                            "FromPort": 443,
                            "ToPort": 443,
                            "UserIdGroupPairs": [{"GroupId": alb_security_group_id}],
                        }
                    ],
                },
                physical_resource_id=cr.PhysicalResourceId.of(
                    f"{security_group_id}-specific-ingress-removal"
                ),
            ),
            policy=cr.AwsCustomResourcePolicy.from_statements(
                [
                    aws_iam.PolicyStatement(
                        actions=["ec2:RevokeSecurityGroupIngress"],
                        resources=[
                            f"arn:{aws_cdk.Aws.PARTITION}:ec2:{aws_cdk.Aws.REGION}:{aws_cdk.Aws.ACCOUNT_ID}:security-group/{security_group_id}"
                        ],
                    )
                ]
            ),
        )

        return remove_ingress_rule

    def create_proxy_lambda(
        self,
        cognito_domain_url: str,
        cognito_provider_url: str,
    ) -> Function:

        execution_role = self.create_execution_role()
        assume_role = self.create_assume_role(execution_role.role_arn)

        users_table_name = self.params["ddb_users_table_name"]
        groups_table_name = self.params["ddb_groups_table_name"]
        cluster_settings_table_name = self.params["ddb_cluster_settings_table_name"]
        cluster_name = self.params["cluster_name"]

        proxy_lambda = lambda_.Function(
            self,
            "proxyLambda",
            runtime=RES_COMMON_LAMBDA_RUNTIME,
            function_name=f"{cluster_name}_{proxy_lambda_name}",
            role=execution_role,
            timeout=aws_cdk.Duration.seconds(10),
            description="Lambda to act as AWS API Proxy",
            **utils.InfraUtils.get_handler_and_code_for_function(
                proxy_handler.handle_proxy_event
            ),
            environment={
                "COGNITO_USER_POOL_PROVIDER_URL": cognito_provider_url,
                "COGNITO_USER_POOL_DOMAIN_URL": cognito_domain_url,
                "DDB_USERS_TABLE_NAME": users_table_name,
                "DDB_GROUPS_TABLE_NAME": groups_table_name,
                "DDB_CLUSTER_SETTINGS_TABLE_NAME": cluster_settings_table_name,
                "ASSUME_ROLE_ARN": assume_role.role_arn,
            },
            # Pass Shared Lambda Layer here
            layers=[self.lambda_layer],
        )
        proxy_lambda.add_to_role_policy(
            aws_cdk.aws_iam.PolicyStatement(
                actions=["dynamodb:GetItem"],
                resources=[
                    f"arn:{aws_cdk.Aws.PARTITION}:dynamodb:{aws_cdk.Aws.REGION}:{aws_cdk.Aws.ACCOUNT_ID}:table/{users_table_name}",
                    f"arn:{aws_cdk.Aws.PARTITION}:dynamodb:{aws_cdk.Aws.REGION}:{aws_cdk.Aws.ACCOUNT_ID}:table/{cluster_settings_table_name}",
                ],
            )
        )
        proxy_lambda.add_to_role_policy(
            aws_cdk.aws_iam.PolicyStatement(
                actions=["dynamodb:Scan"],
                resources=[
                    f"arn:{aws_cdk.Aws.PARTITION}:dynamodb:{aws_cdk.Aws.REGION}:{aws_cdk.Aws.ACCOUNT_ID}:table/{groups_table_name}",
                ],
            )
        )
        proxy_lambda.add_to_role_policy(
            aws_cdk.aws_iam.PolicyStatement(
                actions=["cognito-idp:DescribeUserPoolClient"],
                resources=[
                    f"arn:{aws_cdk.Aws.PARTITION}:cognito-idp:{aws_cdk.Aws.REGION}:{aws_cdk.Aws.ACCOUNT_ID}:userpool/{cognito_provider_url.split('/')[-1]}",
                ],
            )
        )
        proxy_lambda.apply_removal_policy(aws_cdk.RemovalPolicy.RETAIN)
        return proxy_lambda

    def create_execution_role(self) -> aws_iam.Role:
        lambda_execution_role = aws_iam.Role(
            self,
            "LambdaExecutionRole",
            assumed_by=aws_iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                aws_iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                ),
                aws_iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaVPCAccessExecutionRole"
                ),
            ],
        )
        return lambda_execution_role

    def create_assume_role(self, execution_role_arn: str) -> aws_iam.Role:
        proxy_assume_role = aws_iam.Role(
            self,
            "ProxyLambdaAssumeRole",
            assumed_by=aws_iam.ArnPrincipal(execution_role_arn),
        )
        proxy_assume_role.add_to_policy(
            aws_iam.PolicyStatement(
                actions=[
                    "budgets:ViewBudget",
                    "fsx:DescribeFileSystems",
                    "elasticfilesystem:DescribeFileSystems",
                ],
                resources=["*"],
            )
        )
        return proxy_assume_role


# Construct to clean up retained security group and lambda function
class LambdaAndSecurityGroupCleanup(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        vpc_id: str,
        lambdas_to_cleanup: typing.List[str],
        security_groups_to_cleanup: typing.List[str],
    ):
        super().__init__(scope, id)

        self.remove_security_group_cr = self.remove_security_group(
            vpc_id, security_groups_to_cleanup
        )
        self.remove_lambda_function(lambdas_to_cleanup)

    def remove_security_group(
        self, vpc_id: str, security_groups_to_cleanup: typing.List[str]
    ) -> aws_cdk.CustomResource:
        security_group_cleanup_function = lambda_.Function(
            self,
            "cr-to-remove-leftover-security-groups",
            description="Lambda to remove left over security groups.",
            runtime=lambda_.Runtime.PYTHON_3_9,
            **utils.InfraUtils.get_handler_and_code_for_function(
                installer_handlers.handle_security_group_delete
            ),
            timeout=aws_cdk.Duration.seconds(300),
        )
        # Create an IAM policy for the Lambda function
        security_group_cleanup_policy = aws_cdk.aws_iam.PolicyStatement(
            effect=aws_cdk.aws_iam.Effect.ALLOW,
            actions=["ec2:DescribeSecurityGroups", "ec2:DeleteSecurityGroup"],
            resources=["*"],
        )

        # Add the policy to the Lambda function's role
        security_group_cleanup_function.add_to_role_policy(
            security_group_cleanup_policy
        )

        return aws_cdk.CustomResource(
            self,
            "remove-security-group",
            service_token=security_group_cleanup_function.function_arn,
            properties={
                "security_group_name": json.dumps(security_groups_to_cleanup),
                "vpc_id": vpc_id,
            },
            resource_type="Custom::SecurityGroupDeletion",
        )

    def remove_lambda_function(self, lambdas_to_cleanup: typing.List[str]) -> None:
        for function_name in lambdas_to_cleanup:
            remove_function_cr = cr.AwsCustomResource(
                self,
                "remove-lambda-function",
                on_delete=cr.AwsSdkCall(
                    service="@aws-sdk/client-lambda",
                    action="DeleteFunctionCommand",
                    parameters={
                        "FunctionName": function_name,
                    },
                    physical_resource_id=cr.PhysicalResourceId.of(
                        "remove-proxy-lambda-function-cr"
                    ),
                    ignore_error_codes_matching="ResourceNotFoundException",
                ),
                policy=AwsCustomResourcePolicy.from_statements(
                    [
                        aws_iam.PolicyStatement(
                            actions=["lambda:DeleteFunction", "lambda:GetFunction"],
                            resources=[
                                f"arn:{aws_cdk.Aws.PARTITION}:lambda:{aws_cdk.Aws.REGION}:{aws_cdk.Aws.ACCOUNT_ID}:function:{function_name}"
                            ],
                        ),
                    ]
                ),
            )
            remove_function_cr.node.add_dependency(self.remove_security_group_cr)


class ProxyStack(aws_cdk.Stack):
    def __init__(
        self,
        scope: Construct,
        stack_id: str,
        params: ProxyParams,
        lambda_layer_arn: str,
        vpc_id: str,
        synthesizer: Optional[aws_cdk.IStackSynthesizer] = None,
        env: Union[aws_cdk.Environment, dict[str, Any], None] = None,
    ):
        super().__init__(
            scope,
            stack_id,
            env=env,
            synthesizer=synthesizer,
            description=f"RES_proxyLambdaStack",
        )

        # Get the Lambda layer resource from its ARN
        lambda_layer = lambda_.LayerVersion.from_layer_version_arn(
            self, "ApiProxyDepsLayer", lambda_layer_arn
        )

        cluster_name = params["cluster_name"]
        self.proxyConstructCleanup = LambdaAndSecurityGroupCleanup(
            self,
            "remove-leftover-proxy-resource",
            vpc_id,
            [f"{cluster_name}_{proxy_lambda_name}"],
            [f"{cluster_name}_{proxy_lambda_security_group_name}"],
        )

        self.proxyLambda = Proxy(
            self,
            "proxy",
            params,
            lambda_layer=lambda_layer,  # type: ignore
        )

        self.proxyLambda.node.add_dependency(self.proxyConstructCleanup)
