#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from os import path
from typing import Union

import aws_cdk as cdk
import constructs
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from res.constants import ENVIRONMENT_NAME_KEY  # type: ignore
from res.resources import accounts, cluster_settings  # type: ignore

from idea.batteries_included.parameters.parameters import BIParameters
from idea.infrastructure.install.constants import RES_COMMON_LAMBDA_RUNTIME
from idea.infrastructure.install.constructs.base import ResBaseConstruct
from idea.infrastructure.install.parameters.common import CommonKey
from idea.infrastructure.install.parameters.parameters import RESParameters
from idea.infrastructure.install.utils import InfraUtils
from idea.infrastructure.resources.lambda_functions.custom_resource.ddb_final_values_populator_lambda import (
    handler,
)


class ResFinalizerStack(ResBaseConstruct):
    def __init__(
        self,
        scope: constructs.Construct,
        shared_library_lambda_layer: lambda_.LayerVersion,
        parameters: Union[RESParameters, BIParameters] = RESParameters(),
    ):
        self.parameters = parameters
        self.cluster_name = parameters.get_str(CommonKey.CLUSTER_NAME)
        self.shared_library_lambda_layer = shared_library_lambda_layer
        super().__init__(
            self.cluster_name,
            cdk.Aws.REGION,
            "res-finalizer",
            scope,
            self.parameters,
        )

        self.nested_stack = cdk.NestedStack(
            scope,
            "res-finalizer",
            description="Nested RES Finalizer Stack",
        )

        self.populate_final_values()
        self.apply_permission_boundary(self.nested_stack)

    def populate_final_values(self) -> None:
        lambda_name = f"{self.cluster_name}-DDBFinalValuesPopulator"
        scope = self.nested_stack
        user_pool_id = InfraUtils.get_cluster_setting_string(
            scope, "identity-provider.cognito.user_pool_id", self.cluster_name
        )
        ddb_final_values_populator_role = iam.Role(
            scope,
            id="DDBFinalValuesPopulatorRole",
            role_name=f"{lambda_name}Role",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
        )
        ddb_final_values_populator_role_policy = iam.Policy(
            scope,
            id="DDBFinalValuesPopulatorRolePolicy",
            policy_name=f"{lambda_name}Policy",
            statements=[
                iam.PolicyStatement(
                    actions=[
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents",
                        "logs:DeleteLogStream",
                    ],
                    sid="CloudWatchLogStreamPermissions",
                    resources=["*"],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["dynamodb:GetItem", "dynamodb:PutItem"],
                    resources=[
                        f"arn:{cdk.Aws.PARTITION}:dynamodb:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:table/{self.cluster_name}.{accounts.USERS_TABLE_NAME}",
                        f"arn:{cdk.Aws.PARTITION}:dynamodb:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:table/{self.cluster_name}.{cluster_settings.CLUSTER_SETTINGS_TABLE_NAME}",
                    ],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["cognito-idp:AdminCreateUser"],
                    resources=[
                        f"arn:{cdk.Aws.PARTITION}:cognito-idp:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:userpool/{user_pool_id}"
                    ],
                ),
            ],
        )
        ddb_final_values_populator_role.attach_inline_policy(
            ddb_final_values_populator_role_policy
        )
        self.add_common_tags(ddb_final_values_populator_role)

        final_values_populator_handler = lambda_.Function(
            scope,
            "DDBFinalValuesPopulator",
            function_name=lambda_name,
            runtime=RES_COMMON_LAMBDA_RUNTIME,
            timeout=cdk.Duration.seconds(300),
            environment={
                ENVIRONMENT_NAME_KEY: self.cluster_name,
            },
            role=ddb_final_values_populator_role,
            description="Lambda to populate final values in ddb",
            layers=[self.shared_library_lambda_layer],
            **InfraUtils.get_handler_and_code_for_function(handler.handler),
        )
        self.add_common_tags(final_values_populator_handler)

        final_values_populator_handler.node.add_dependency(
            ddb_final_values_populator_role_policy
        )

        cdk.CustomResource(
            scope,
            "CustomResourceDDBFinalValuesPopulator",
            service_token=final_values_populator_handler.function_arn,
            removal_policy=cdk.RemovalPolicy.DESTROY,
            resource_type="Custom::RESDdbPopulator",
            properties={ENVIRONMENT_NAME_KEY: self.cluster_name},
        )
