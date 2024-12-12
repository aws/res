#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
import typing
from typing import Any, Optional, Union

import aws_cdk.aws_elasticloadbalancingv2 as lb
from aws_cdk import Aws, Duration, Environment, IStackSynthesizer, RemovalPolicy, Stack
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as targets
from aws_cdk import aws_iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import custom_resources as cr
from constructs import Construct

from idea.batteries_included.parameters.parameters import BIParameters
from idea.infrastructure.install import cognito_sync_handler, utils
from idea.infrastructure.install.parameters.common import CommonKey
from idea.infrastructure.install.parameters.internet_proxy import InternetProxyKey
from idea.infrastructure.install.parameters.parameters import RESParameters
from idea.infrastructure.install.utils import InfraUtils
from ideadatamodel import SocaBaseModel, constants  # type: ignore

cognito_sync_lambda_security_group_name = "cognito-sync-lambda-security-group"
cognito_sync_lambda_name = "cognito-sync-lambda"


class CognitoSyncLambda(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        params: Union[RESParameters, BIParameters],
    ):
        super().__init__(scope, id)
        # Get existing resource
        cluster_name = params.get_str(CommonKey.CLUSTER_NAME)
        self.params = params
        sudoer_group_name = InfraUtils.get_cluster_setting_string(
            self, "identity-provider.cognito.sudoers.group_name", cluster_name
        )
        user_pool_id = InfraUtils.get_cluster_setting_string(
            self, "identity-provider.cognito.user_pool_id", cluster_name
        )
        cluster_admin_name = InfraUtils.get_cluster_setting_string(
            self, "cluster.administrator_username", cluster_name
        )
        alb_security_group_id = InfraUtils.get_cluster_setting_string(
            self, "cluster.network.security_groups.external-load-balancer", cluster_name
        )
        vpc_id = InfraUtils.get_cluster_setting_string(
            self, "cluster.network.vpc_id", cluster_name
        )
        subnet_ids = InfraUtils.get_cluster_setting_array(
            self, "cluster.network.private_subnets", cluster_name
        )

        # Create new resources
        cognito_sync_lambda = self.create_lambda(
            cluster_name,
            sudoer_group_name,
            user_pool_id,
            cluster_admin_name,
        )
        complete_security_group_name = (
            f"{cluster_name}_{cognito_sync_lambda_security_group_name}"
        )
        security_group_id = InfraUtils.create_security_group(
            self, alb_security_group_id, vpc_id, complete_security_group_name
        )
        InfraUtils.add_vpc_config_to_lambda(
            self,
            cognito_sync_lambda,
            [security_group_id],
            subnet_ids,
        )
        self.remove_ingress_rule_for_alb_sg_on_delete(
            security_group_id, alb_security_group_id
        )

        self.create_event_bridge_rule(cognito_sync_lambda)

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
    ) -> lambda_.Function:
        execution_role = InfraUtils.create_execution_role(self)
        cognito_sync_lambda = lambda_.Function(
            self,
            "cognito-sync",
            runtime=lambda_.Runtime.PYTHON_3_11,
            function_name=f"{cluster_name}_{cognito_sync_lambda_name}",
            role=execution_role,
            timeout=Duration.minutes(15),
            description="Sync users and groups from Cognito to DDB",
            **InfraUtils.get_handler_and_code_for_function(
                cognito_sync_handler.handle_cognito_sync
            ),
            reserved_concurrent_executions=1,
            environment={
                "CUSTOM_UID_ATTRIBUTE": f"custom:{constants.COGNITO_UID_ATTRIBUTE}",
                "COGNITO_SUDOER_GROUP_NAME": sudoer_group_name,
                "COGNITO_USER_POOL_ID": user_pool_id,
                "CLUSTER_NAME": cluster_name,
                "COGNITO_USER_IDP_TYPE": constants.COGNITO_USER_IDP_TYPE,
                "SSO_USER_IDP_TYPE": constants.SSO_USER_IDP_TYPE,
                "COGNITO_MIN_ID_INCLUSIVE": str(constants.COGNITO_MIN_ID_INCLUSIVE),
                "COGNITO_DEFAULT_USER_GROUP": constants.COGNITO_DEFAULT_USER_GROUP,
                "GROUP_TYPE_PROJECT": constants.GROUP_TYPE_PROJECT,
                "GROUP_TYPE_INTERNAL": constants.GROUP_TYPE_INTERNAL,
                "ADMIN_ROLE": constants.ADMIN_ROLE,
                "USER_ROLE": constants.USER_ROLE,
                "CLUSTER_ADMIN_NAME": cluster_admin_name,
                "HTTP_PROXY": self.params.get_str(InternetProxyKey.HTTP_PROXY),
                "HTTPS_PROXY": self.params.get_str(InternetProxyKey.HTTPS_PROXY),
                "NO_PROXY": self.params.get_str(InternetProxyKey.NO_PROXY),
            },
        )

        ddb_user_table_arn = f"arn:{Aws.PARTITION}:dynamodb:{Aws.REGION}:{Aws.ACCOUNT_ID}:table/{cluster_name}.accounts.users"
        ddb_group_table_arn = f"arn:{Aws.PARTITION}:dynamodb:{Aws.REGION}:{Aws.ACCOUNT_ID}:table/{cluster_name}.accounts.groups"
        ddb_group_member_table_arn = f"arn:{Aws.PARTITION}:dynamodb:{Aws.REGION}:{Aws.ACCOUNT_ID}:table/{cluster_name}.accounts.group-members"

        cognito_user_pool_arn = f"arn:{Aws.PARTITION}:cognito-idp:{Aws.REGION}:{Aws.ACCOUNT_ID}:userpool/{user_pool_id}"
        cognito_sync_lambda.add_to_role_policy(
            aws_iam.PolicyStatement(
                actions=[
                    "dynamodb:PutItem",
                    "dynamodb:DeleteItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:BatchWriteItem",
                    "dynamodb:Scan",
                ],
                resources=[
                    ddb_user_table_arn,
                    ddb_group_table_arn,
                    ddb_group_member_table_arn,
                ],
            )
        )
        cognito_sync_lambda.add_to_role_policy(
            aws_iam.PolicyStatement(
                actions=[
                    "cognito-idp:ListGroups",
                    "cognito-idp:ListUsers",
                    "cognito-idp:ListUsersInGroup",
                    "cognito-idp:AdminDisableUser",
                ],
                resources=[cognito_user_pool_arn],
            )
        )
        cognito_sync_lambda.apply_removal_policy(RemovalPolicy.RETAIN)
        return cognito_sync_lambda

    def create_event_bridge_rule(self, lambda_function: lambda_.Function) -> None:
        events.Rule(
            self,
            "cognito-sync-rule",
            description="trigger cognito sync lambda every hour",
            schedule=events.Schedule.rate(Duration.hours(1)),
            targets=[targets.LambdaFunction(lambda_function)],
        )


class CognitoSyncLambdaStack(Stack):
    def __init__(
        self,
        scope: Construct,
        stack_id: str,
        params: Union[RESParameters, BIParameters],
        synthesizer: Optional[IStackSynthesizer] = None,
        env: Union[Environment, dict[str, Any], None] = None,
    ):
        super().__init__(
            scope,
            stack_id,
            env=env,
            synthesizer=synthesizer,
            description="RESCognitoSyncLambda",
        )
        self.cognitoSyncLambda = CognitoSyncLambda(self, "cognito-sync-lambda", params)
