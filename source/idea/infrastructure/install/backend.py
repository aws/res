#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
import importlib.metadata
import inspect
import pathlib
from typing import Any, Callable, Dict, TypedDict, Union

import aws_cdk
import aws_cdk.aws_elasticloadbalancingv2 as lb
import aws_cdk.aws_elasticloadbalancingv2_targets as targets
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam
from aws_cdk import custom_resources as cr
from aws_cdk.aws_iam import ServicePrincipal
from aws_cdk.aws_lambda import Function
from aws_cdk.custom_resources import AwsCustomResource
from constructs import Construct

import idea
from idea.batteries_included.parameters.parameters import BIParameters
from idea.infrastructure.install.constants import RES_COMMON_LAMBDA_RUNTIME
from idea.infrastructure.install.constructs import lambda_
from idea.infrastructure.install.infra_utils.arn_builder import ArnBuilder
from idea.infrastructure.install.infra_utils.cluster_settings import ClusterSettings
from idea.infrastructure.install.infra_utils.utils import InfraUtils
from idea.infrastructure.install.parameters.common import CommonKey
from idea.infrastructure.install.parameters.internet_proxy import InternetProxyKey
from idea.infrastructure.install.parameters.parameters import RESParameters
from idea.infrastructure.install.policies import BackendLambdaPolicy
from idea.infrastructure.install.stacks.cluster_stack import ClusterStack
from idea.infrastructure.install.stacks.identity_stack import IdentityStack
from idea.backend import handler

backend_lambda_security_group_name = "backend-lambda-security-group-name"
backend_lambda_name = "backend-lambda"
backend_lambda_target_group_priority = 102


class BackendLambda(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        cluster_stack: ClusterStack,
        identity_stack: IdentityStack,
        params: Union[RESParameters, BIParameters],
        lambda_layer: aws_cdk.aws_lambda.LayerVersion,
    ):
        super().__init__(scope, id)
        self.lambda_layer = lambda_layer
        self.params = params
        self.cluster_name = self.params.get_str(CommonKey.CLUSTER_NAME)
        cluster_settings = ClusterSettings(self.cluster_name, self)
        self.arn_builder = ArnBuilder(
            self.cluster_name, cluster_settings, parameters=params
        )

        cognito_domain_url = cluster_settings.user_pool_domain_url
        cognito_provider_url = f"https://cognito-idp.{aws_cdk.Aws.REGION}.amazonaws.com/{cluster_settings.user_pool_id}"
        external_alb_https_listener_arn = (
            cluster_stack.external_alb_https_listener.attr_listener_arn  # type: ignore
        )
        endpoint_custom_lambda_arn = cluster_stack.cluster_endpoints_lambda.function_arn  # type: ignore
        alb_security_group_id = cluster_stack.security_groups[
            "external-load-balancer"
        ].security_group_id
        vpc_id = self.params.get_str(CommonKey.VPC_ID)

        security_group_id = InfraUtils.create_security_group(
            self,
            alb_security_group_id,
            vpc_id,
            f"{self.cluster_name}_{backend_lambda_security_group_name}",
            "backend",
        )
        backend_lambda = self.create_backend_lambda(
            cognito_domain_url, # type: ignore
            cognito_provider_url,
            cluster_stack.vpc,
            [security_group_id],
            cluster_stack.cluster_settings.infrastructure_host_subnets,  # type: ignore
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
                "priority": backend_lambda_target_group_priority,
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
        vpc: ec2.IVpc,
        security_group_ids: list[str],
        subnet_ids: list[str],
    ) -> Function:
        backend_lambda = lambda_.Function(
            self,
            backend_lambda_name,
            handler=handler.handle_backend_event,
            parameters=self.params,
            runtime=RES_COMMON_LAMBDA_RUNTIME,
            description="RES Backend Lambda",  # type: ignore
            timeout=aws_cdk.Duration.minutes(15),  # type: ignore
            memory_size=4096,  # type: ignore
            layers=[self.lambda_layer],  # type: ignore
            initial_policy=BackendLambdaPolicy.create_policy_statements(self.arn_builder),  # type: ignore
            environment={
                "COGNITO_USER_POOL_PROVIDER_URL": cognito_provider_url,
                "COGNITO_USER_POOL_DOMAIN_URL": cognito_domain_url,
                "environment_name": str(self.cluster_name),
                "version": str(importlib.metadata.version(idea.__package__)),
                "aws_region": aws_cdk.Aws.REGION,
                "HTTP_PROXY": self.params.get_str(InternetProxyKey.HTTP_PROXY),
                "HTTPS_PROXY": self.params.get_str(InternetProxyKey.HTTPS_PROXY),
                "NO_PROXY": self.params.get_str(InternetProxyKey.NO_PROXY),
            },
            vpc=vpc,  # type: ignore
            security_groups=[  # type: ignore
                ec2.SecurityGroup.from_security_group_id(
                    self, f"backend-lambda-sg-{i}", security_group_id
                ) for i, security_group_id in enumerate(security_group_ids)
            ],
        )
        cfn_backend_lambda: aws_cdk.aws_lambda.CfnFunction = (
            backend_lambda.node.default_child  # type: ignore
        )
        cfn_backend_lambda.add_property_override(
            "VpcConfig.SubnetIds",
            subnet_ids,
        )
        backend_lambda.role.add_managed_policy(  # type: ignore
            aws_iam.ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AWSLambdaVPCAccessExecutionRole"
            )
        )

        return backend_lambda
