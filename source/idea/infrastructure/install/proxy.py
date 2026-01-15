#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import Any, TypedDict, Union

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

from idea.batteries_included.parameters.parameters import BIParameters
from idea.infrastructure.install.constants import RES_COMMON_LAMBDA_RUNTIME
from idea.infrastructure.install.constructs import lambda_
from idea.infrastructure.install.constructs.iam import Role
from idea.infrastructure.install.infra_utils.arn_builder import ArnBuilder
from idea.infrastructure.install.infra_utils.cluster_settings import ClusterSettings
from idea.infrastructure.install.infra_utils.utils import InfraUtils
from idea.infrastructure.install.parameters.common import CommonKey
from idea.infrastructure.install.parameters.internet_proxy import InternetProxyKey
from idea.infrastructure.install.parameters.parameters import RESParameters
from idea.infrastructure.install.policies import (
    ProxyLambdaAssumeRolePolicy,
    ProxyLambdaPolicy,
)
from idea.infrastructure.install.stacks.cluster_stack import ClusterStack
from idea.infrastructure.install.stacks.identity_stack import IdentityStack
from idea.infrastructure.resources.lambda_functions.proxy_lambda import proxy_handler

proxy_lambda_security_group_name = "proxy-lambda-security-group-id"
proxy_lambda_name = "aws-api-proxy-lambda"
proxy_lambda_target_group_priority = 101


class Proxy(Construct):
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
        self.params = params
        self.lambda_layer = lambda_layer
        self.cluster_name = self.params.get_str(CommonKey.CLUSTER_NAME)
        cluster_settings = ClusterSettings(self.cluster_name, self)
        self.arn_builder = ArnBuilder(
            self.cluster_name, cluster_settings, parameters=params
        )

        # Get existing resources in RES to integrate with the Proxy
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

        security_group_id = self.create_security_group(alb_security_group_id, vpc_id)
        proxy_lambda = self.create_proxy_lambda(
            cognito_domain_url,  # type: ignore
            cognito_provider_url,
            cluster_stack.vpc,
            [security_group_id],
            cluster_stack.cluster_settings.infrastructure_host_subnets,  # type: ignore
        )

        self.remove_ingress_rule_for_alb_sg_on_delete(
            security_group_id, alb_security_group_id
        )

        self.target_group = self.create_proxy_target_group(proxy_lambda)
        self.add_target_group_to_alb(
            external_alb_https_listener_arn, endpoint_custom_lambda_arn
        )

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
                "priority": proxy_lambda_target_group_priority,
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
        security_group = ec2.CfnSecurityGroup(
            self,
            "ProxyLambdaSecurityGroup",
            group_description="Security group for Proxy Lambda",
            group_name=f"{self.cluster_name}_{proxy_lambda_security_group_name}",
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
                        resources=["*"],
                    )
                ]
            ),
        )

        return remove_ingress_rule

    def create_proxy_lambda(
        self,
        cognito_domain_url: str,
        cognito_provider_url: str,
        vpc: ec2.IVpc,
        security_group_ids: list[str],
        subnet_ids: list[str],
    ) -> Function:

        users_table_name = f"{self.cluster_name}.accounts.users"
        groups_table_name = f"{self.cluster_name}.accounts.groups"
        cluster_settings_table_name = f"{self.cluster_name}.cluster-settings"
        cluster_name = self.params.get_str(CommonKey.CLUSTER_NAME)

        execution_role = InfraUtils.create_execution_role(
            self,
            "proxy-lambda-role",
        )
        assume_role = self.create_assume_role(execution_role.role_arn, cluster_name)

        proxy_lambda = lambda_.Function(
            self,
            proxy_lambda_name,
            runtime=RES_COMMON_LAMBDA_RUNTIME,
            description="Lambda to act as AWS API Proxy",  # type: ignore
            timeout=aws_cdk.Duration.seconds(10),  # type: ignore
            handler=proxy_handler.handle_proxy_event,
            role=execution_role,  # type: ignore
            parameters=self.params,
            environment={
                "COGNITO_USER_POOL_PROVIDER_URL": cognito_provider_url,
                "COGNITO_USER_POOL_DOMAIN_URL": cognito_domain_url,
                "DDB_USERS_TABLE_NAME": users_table_name,
                "DDB_GROUPS_TABLE_NAME": groups_table_name,
                "DDB_CLUSTER_SETTINGS_TABLE_NAME": cluster_settings_table_name,
                "ASSUME_ROLE_ARN": assume_role.role_arn,
                "HTTP_PROXY": self.params.get_str(InternetProxyKey.HTTP_PROXY),
                "HTTPS_PROXY": self.params.get_str(InternetProxyKey.HTTPS_PROXY),
                "NO_PROXY": self.params.get_str(InternetProxyKey.NO_PROXY),
            },
            layers=[self.lambda_layer],  # type: ignore
            vpc=vpc,  # type: ignore
            security_groups=[  # type: ignore
                ec2.SecurityGroup.from_security_group_id(
                    self, f"proxy-lambda-sg-{i}", security_group_id
                )
                for i, security_group_id in enumerate(security_group_ids)
            ],
        )
        cfn_proxy_lambda: aws_cdk.aws_lambda.CfnFunction = (
            proxy_lambda.node.default_child  # type: ignore
        )
        cfn_proxy_lambda.add_property_override(
            "VpcConfig.SubnetIds",
            subnet_ids,
        )

        proxy_lambda_policy = ProxyLambdaPolicy(
            self,
            "proxy-lambda-role-policy",
            self.arn_builder,
            self.params,
        )
        execution_role.attach_inline_policy(
            proxy_lambda_policy,
        )
        execution_role.add_managed_policy(
            aws_iam.ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AWSLambdaVPCAccessExecutionRole"
            )
        )
        proxy_lambda.node.add_dependency(proxy_lambda_policy)

        return proxy_lambda

    def create_assume_role(
        self, execution_role_arn: str, cluster_name: str
    ) -> aws_iam.Role:
        proxy_assume_role = Role(
            scope=self,
            name="proxy-lambda-assume-role",
            description="proxy-lambda-assume-role",
            assumed_by=[aws_iam.ArnPrincipal(execution_role_arn)],
            inline_policies=[
                ProxyLambdaAssumeRolePolicy(
                    self,
                    "proxy-lambda-assume-role-policy",
                    self.arn_builder,
                    self.params,
                ),
            ],
            parameters=self.params,
            arn_builder=self.arn_builder,
        )

        return proxy_assume_role
