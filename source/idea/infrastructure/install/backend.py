#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
import importlib.metadata
import inspect
import pathlib
from typing import Any, Callable, Dict, List, TypedDict

import aws_cdk
import aws_cdk.aws_elasticloadbalancingv2 as lb
import aws_cdk.aws_elasticloadbalancingv2_targets as targets
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import custom_resources as cr
from aws_cdk.aws_iam import ServicePrincipal
from aws_cdk.aws_lambda import Function
from aws_cdk.custom_resources import AwsCustomResource
from constructs import Construct

import idea
from idea.infrastructure.install import utils
from idea.infrastructure.install.constants import RES_BACKEND_LAMBDA_RUNTIME
from idea.infrastructure.install.handlers import installer_handlers
from idea.infrastructure.install.utils import InfraUtils


class LambdaCodeParams(TypedDict):
    handler: str
    code: lambda_.Code


backend_lambda_security_group_name = "backend-lambda-security-group-name"
backend_lambda_name = "backend-lambda"


class BackendLambda(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        params: Dict[str, Any],
        lambda_layer: lambda_.LayerVersion,
    ):
        super().__init__(scope, id)
        self.lambda_layer = lambda_layer
        self.params = params

        # Get existing resources in RES to integrate with this lambda
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

        backend_lambda = self.create_backend_lambda(
            cognito_domain_url,
            cognito_provider_url,
        )
        security_group_id = InfraUtils.create_security_group(
            self,
            alb_security_group_id,
            vpc_id,
            f'{self.params["cluster_name"]}_{backend_lambda_security_group_name}',
            "backend",
        )
        InfraUtils.add_vpc_config_to_lambda(
            self,
            backend_lambda,
            [security_group_id],
            subnet_ids,
        )
        self.remove_ingress_rule_for_alb_sg_on_delete(
            security_group_id, alb_security_group_id
        )

        self.target_group = self.create_backend_target_group(backend_lambda)

        self.add_target_group_to_alb(
            external_alb_https_listener_arn, endpoint_custom_lambda_arn
        )

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
                        resources=["*"],
                    )
                ]
            ),
        )

        return remove_ingress_rule

    def create_backend_target_group(
        self, backend_lambda: Any
    ) -> lb.ApplicationTargetGroup:
        lambda_target = targets.LambdaTarget(backend_lambda)
        target_group = lb.ApplicationTargetGroup(
            self, "backendTargetGroup", targets=[lambda_target]
        )
        backend_lambda.add_permission(
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
    ) -> List[str]:
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

        settings_table_name = f'{self.params["cluster_name"]}.cluster-settings'
        get_cluster_settings_custom_resource = cr.AwsCustomResource(
            self,
            f"getClusterSetting-{setting_to_retrieve}",
            on_update=cr.AwsSdkCall(
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
                    f"arn:{aws_cdk.Aws.PARTITION}:dynamodb:{aws_cdk.Aws.REGION}:{aws_cdk.Aws.ACCOUNT_ID}:table/{settings_table_name}"
                ]
            ),
        )
        return get_cluster_settings_custom_resource

    def add_target_group_to_alb(
        self, external_alb_https_listener_arn: str, endpoint_custom_lambda_arn: str
    ) -> None:
        endpoint_id = "aws-backend-client-endpoint"
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
                        "PathPatternConfig": {"Values": ["/res/*"]},
                    }
                ],
                "actions": [
                    {
                        "Type": "forward",
                        "TargetGroupArn": self.target_group.target_group_arn,
                    }
                ],
            },
            resource_type="Custom::BackendLambdaEndpointInternal",
        )

    def create_backend_lambda(
        self,
        cognito_domain_url: str,
        cognito_provider_url: str,
    ) -> Function:

        execution_role = self.create_execution_role()

        backend_lambda = lambda_.Function(
            self,
            "backendLambda",
            runtime=RES_BACKEND_LAMBDA_RUNTIME,
            role=execution_role,
            timeout=aws_cdk.Duration.seconds(30),
            function_name=f'{self.params["cluster_name"]}_{backend_lambda_name}',
            description="RES Backend Lambda",
            code=lambda_.Code.from_asset("source/idea/backend"),
            handler="handler.handle_backend_event",
            environment={
                "COGNITO_USER_POOL_PROVIDER_URL": cognito_provider_url,
                "COGNITO_USER_POOL_DOMAIN_URL": cognito_domain_url,
                "environment_name": str(self.params["cluster_name"]),
                "version": str(importlib.metadata.version(idea.__package__)),
                "aws_region": aws_cdk.Aws.REGION,
                "HTTP_PROXY": self.params["http_proxy"],
                "HTTPS_PROXY": self.params["https_proxy"],
                "NO_PROXY": self.params["no_proxy"],
            },
            # Pass Shared Lambda Layer here
            layers=[self.lambda_layer],
        )
        backend_lambda.add_to_role_policy(
            aws_cdk.aws_iam.PolicyStatement(
                actions=[
                    "dynamodb:GetItem",
                    "dynamodb:PutItem",
                    "dynamodb:BatchGetItem",
                    "dynamodb:DeleteItem",
                    "dynamodb:Scan",
                ],
                resources=[
                    f"arn:{aws_cdk.Aws.PARTITION}:dynamodb:{aws_cdk.Aws.REGION}:{aws_cdk.Aws.ACCOUNT_ID}:table/{self.params['cluster_name']}.*"
                ],
            )
        )
        backend_lambda.add_to_role_policy(
            aws_cdk.aws_iam.PolicyStatement(
                actions=["cognito-idp:DescribeUserPoolClient"],
                resources=[
                    f"arn:{aws_cdk.Aws.PARTITION}:cognito-idp:{aws_cdk.Aws.REGION}:{aws_cdk.Aws.ACCOUNT_ID}:userpool/{cognito_provider_url.split('/')[-1]}",
                ],
            )
        )
        backend_lambda.add_to_role_policy(
            aws_cdk.aws_iam.PolicyStatement(
                actions=[
                    "ec2:TerminateInstances",
                    "ec2:RunInstances",
                    "ec2:CreateTags",
                    "ec2:MonitorInstances",
                ],
                resources=[
                    f"arn:{aws_cdk.Aws.PARTITION}:ec2:{aws_cdk.Aws.REGION}:{aws_cdk.Aws.ACCOUNT_ID}:*/*",
                    f"arn:{aws_cdk.Aws.PARTITION}:ec2:{aws_cdk.Aws.REGION}::image/*",
                ],
            )
        )
        backend_lambda.add_to_role_policy(
            aws_cdk.aws_iam.PolicyStatement(
                actions=[
                    "ec2:DescribeInstances",
                    "ec2:DescribeInstanceStatus",
                ],
                resources=["*"],
            )
        )
        backend_lambda.add_to_role_policy(
            aws_cdk.aws_iam.PolicyStatement(
                actions=[
                    "ssm:SendCommand",
                    "ssm:GetCommandInvocation",
                ],
                resources=[
                    f"arn:{aws_cdk.Aws.PARTITION}:ec2:{aws_cdk.Aws.REGION}:{aws_cdk.Aws.ACCOUNT_ID}:instance/*",
                    f"arn:{aws_cdk.Aws.PARTITION}:ssm:{aws_cdk.Aws.REGION}::document/AWS-RunShellScript",
                ],
            )
        )
        backend_lambda.add_to_role_policy(
            aws_cdk.aws_iam.PolicyStatement(
                actions=["route53:ChangeResourceRecordSets", "route53:GetHostedZone"],
                resources=[
                    f"arn:{aws_cdk.Aws.PARTITION}:route53:::hostedzone/*",
                ],
            )
        )
        backend_lambda.add_to_role_policy(
            aws_cdk.aws_iam.PolicyStatement(
                actions=["iam:PassRole"],
                resources=[
                    f"arn:{aws_cdk.Aws.PARTITION}:iam::{aws_cdk.Aws.ACCOUNT_ID}:role/{self.params['cluster_name']}-bastion-host-role-{aws_cdk.Aws.REGION}",
                ],
            )
        )
        backend_lambda.apply_removal_policy(aws_cdk.RemovalPolicy.RETAIN)
        return backend_lambda

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

    def get_handler_and_code_for_function(
        self, function: Callable[[Dict[str, Any], Any], Any]
    ) -> LambdaCodeParams:
        module = inspect.getmodule(function)
        if module is None or module.__file__ is None:
            raise ValueError("module not found")
        module_name = module.__name__.rsplit(".", 1)[1]
        folder = str(pathlib.Path(module.__file__).parent)

        return LambdaCodeParams(
            handler=f"{module_name}.{function.__name__}",
            code=lambda_.Code.from_asset(folder),
        )


# Construct to clean up bastion host instance and Route53 record
class BastionHostCleanup(Construct):
    def __init__(self, scope: Construct, id: str, cluster_name: str):
        super().__init__(scope, id)

        cleanup_function = lambda_.Function(
            self,
            "cr-to-cleanup-bastion-host-and-route53",
            description="Lambda to remove the bastion host instance and Route53 record.",
            runtime=lambda_.Runtime.PYTHON_3_9,
            **utils.InfraUtils.get_handler_and_code_for_function(
                installer_handlers.handle_bastion_host_delete
            ),
            timeout=aws_cdk.Duration.seconds(600),
        )

        # Create an IAM policy for the Lambda function
        cleanup_policy = aws_cdk.aws_iam.PolicyStatement(
            effect=aws_cdk.aws_iam.Effect.ALLOW,
            actions=[
                "ec2:TerminateInstances",
                "route53:ChangeResourceRecordSets",
                "route53:ListResourceRecordSets",
                "dynamodb:GetItem",
            ],
            resources=[
                f"arn:{aws_cdk.Aws.PARTITION}:ec2:{aws_cdk.Aws.REGION}:{aws_cdk.Aws.ACCOUNT_ID}:instance/*",
                f"arn:{aws_cdk.Aws.PARTITION}:route53:::hostedzone/*",
                f"arn:{aws_cdk.Aws.PARTITION}:dynamodb:{aws_cdk.Aws.REGION}:{aws_cdk.Aws.ACCOUNT_ID}:table/{cluster_name}.*",
            ],
        )
        describe_instances_policy = aws_cdk.aws_iam.PolicyStatement(
            effect=aws_cdk.aws_iam.Effect.ALLOW,
            actions=["ec2:DescribeInstances"],
            resources=["*"],
        )

        # Add the policy to the Lambda function's role
        cleanup_function.add_to_role_policy(cleanup_policy)
        cleanup_function.add_to_role_policy(describe_instances_policy)

        aws_cdk.CustomResource(
            self,
            "cleanup-bastion-host-and-route53",
            service_token=cleanup_function.function_arn,
            properties={
                "cluster_name": cluster_name,
            },
            resource_type="Custom::BastionHostAndRoute53Cleanup",
        )
