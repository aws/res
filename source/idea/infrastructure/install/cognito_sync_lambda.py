#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import Union

import res.constants as res_constants  # type: ignore
from aws_cdk import Duration
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as targets
from aws_cdk import aws_iam, aws_lambda
from aws_cdk import custom_resources as cr
from constructs import Construct

from idea.batteries_included.parameters.parameters import BIParameters
from idea.infrastructure.install import constants
from idea.infrastructure.install.constructs import lambda_
from idea.infrastructure.install.infra_utils.arn_builder import ArnBuilder
from idea.infrastructure.install.infra_utils.cluster_settings import ClusterSettings
from idea.infrastructure.install.infra_utils.utils import InfraUtils
from idea.infrastructure.install.parameters.common import CommonKey
from idea.infrastructure.install.parameters.internet_proxy import InternetProxyKey
from idea.infrastructure.install.parameters.parameters import RESParameters
from idea.infrastructure.install.policies import CognitoSyncPolicy
from idea.infrastructure.install.stacks.cluster_stack import ClusterStack
from idea.infrastructure.install.stacks.identity_stack import IdentityStack
from idea.infrastructure.resources.lambda_functions.cognito_sync_lambda import (
    cognito_sync_handler,
)

cognito_sync_lambda_security_group_name = "cognito-sync-lambda-security-group"
cognito_sync_lambda_name = "cognito-sync-lambda"


class CognitoSyncLambda(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        cluster_stack: ClusterStack,
        identity_stack: IdentityStack,
        params: Union[RESParameters, BIParameters],
    ):
        super().__init__(scope, id)
        # Get existing resource
        cluster_name = params.get_str(CommonKey.CLUSTER_NAME)
        cluster_settings = ClusterSettings(cluster_name, self)
        self.arn_builder = ArnBuilder(cluster_name, cluster_settings, parameters=params)
        self.params = params

        sudoer_group_name = InfraUtils.get_cluster_setting_string(
            self, "identity-provider.cognito.sudoers.group_name", cluster_name
        )
        cluster_admin_name = InfraUtils.get_cluster_setting_string(
            self, "cluster.administrator_username", cluster_name
        )
        vpc_id = params.get_str(CommonKey.VPC_ID)
        alb_security_group_id = cluster_stack.security_groups[
            "external-load-balancer"
        ].security_group_id

        complete_security_group_name = (
            f"{cluster_name}_{cognito_sync_lambda_security_group_name}"
        )
        security_group_id = InfraUtils.create_security_group(
            self, alb_security_group_id, vpc_id, complete_security_group_name
        )
        cognito_sync_lambda = self.create_lambda(
            cluster_name,
            sudoer_group_name,
            identity_stack.user_pool.user_pool_id,
            cluster_admin_name,
            cluster_stack.vpc,
            [security_group_id],
            cluster_stack.cluster_settings.infrastructure_host_subnets,  # type: ignore
        )
        self.remove_ingress_rule_for_alb_sg_on_delete(
            security_group_id, alb_security_group_id
        )

        self.create_event_bridge_rule(cluster_name, cognito_sync_lambda)

    def remove_ingress_rule_for_alb_sg_on_delete(
        self, security_group_id: str, alb_security_group_id: str
    ) -> cr.AwsCustomResource:
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

    def create_lambda(
        self,
        cluster_name: str,
        sudoer_group_name: str,
        user_pool_id: str,
        cluster_admin_name: str,
        vpc: ec2.IVpc,
        security_group_ids: list[str],
        subnet_ids: list[str],
    ) -> lambda_.Function:
        cognito_sync_lambda = lambda_.Function(
            self,
            cognito_sync_lambda_name,
            runtime=constants.RES_COMMON_LAMBDA_RUNTIME,
            description="Sync users and groups from Cognito to DDB",  # type: ignore
            timeout=Duration.minutes(15),  # type: ignore
            reserved_concurrent_executions=1,  # type: ignore
            handler=cognito_sync_handler.handle_cognito_sync,
            initial_policy=CognitoSyncPolicy.create_policy_statements(self.arn_builder),  # type: ignore
            parameters=self.params,
            environment={
                "CUSTOM_UID_ATTRIBUTE": f"custom:{res_constants.COGNITO_UID_ATTRIBUTE}",
                "COGNITO_SUDOER_GROUP_NAME": sudoer_group_name,
                "COGNITO_USER_POOL_ID": user_pool_id,
                "CLUSTER_NAME": cluster_name,
                "COGNITO_USER_IDP_TYPE": res_constants.COGNITO_USER_IDP_TYPE,
                "SSO_USER_IDP_TYPE": res_constants.SSO_USER_IDP_TYPE,
                "COGNITO_MIN_ID_INCLUSIVE": str(res_constants.COGNITO_MIN_ID_INCLUSIVE),
                "COGNITO_DEFAULT_USER_GROUP": res_constants.COGNITO_DEFAULT_USER_GROUP,
                "GROUP_TYPE_PROJECT": res_constants.GROUP_TYPE_PROJECT,
                "GROUP_TYPE_INTERNAL": res_constants.GROUP_TYPE_INTERNAL,
                "ADMIN_ROLE": res_constants.ADMIN_ROLE,
                "USER_ROLE": res_constants.USER_ROLE,
                "CLUSTER_ADMIN_NAME": cluster_admin_name,
                "HTTP_PROXY": self.params.get_str(InternetProxyKey.HTTP_PROXY),
                "HTTPS_PROXY": self.params.get_str(InternetProxyKey.HTTPS_PROXY),
                "NO_PROXY": self.params.get_str(InternetProxyKey.NO_PROXY),
            },
            vpc=vpc,  # type: ignore
            security_groups=[  # type: ignore
                ec2.SecurityGroup.from_security_group_id(
                    self, f"cognito-sync-lambda-sg-{i}", security_group_id
                )
                for i, security_group_id in enumerate(security_group_ids)
            ],
        )
        cfn_cognito_sync_lambda: aws_lambda.CfnFunction = (
            cognito_sync_lambda.node.default_child  # type: ignore
        )
        cfn_cognito_sync_lambda.add_property_override(
            "VpcConfig.SubnetIds",
            subnet_ids,
        )
        cognito_sync_lambda.role.add_managed_policy(  # type: ignore
            aws_iam.ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AWSLambdaVPCAccessExecutionRole"
            )
        )

        return cognito_sync_lambda

    def create_event_bridge_rule(
        self, cluster_name: str, lambda_function: lambda_.Function
    ) -> None:
        events.Rule(
            self,
            "cognito-sync-rule",
            description="trigger cognito sync lambda every hour",
            schedule=events.Schedule.rate(Duration.hours(1)),
            targets=[targets.LambdaFunction(lambda_function)],
            rule_name=f"{cluster_name}-cognito-sync-rule",
        )
