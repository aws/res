#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from typing import Union

import aws_cdk as cdk
import constructs
from aws_cdk import aws_iam as iam
from res.constants import ENVIRONMENT_NAME_KEY  # type: ignore
from res.resources import accounts, cluster_settings  # type: ignore

from idea.batteries_included.parameters.parameters import BIParameters
from idea.infrastructure.install.constants import RES_COMMON_LAMBDA_RUNTIME
from idea.infrastructure.install.constructs import lambda_
from idea.infrastructure.install.constructs.base import ResBaseConstruct
from idea.infrastructure.install.infra_utils.arn_builder import ArnBuilder
from idea.infrastructure.install.infra_utils.cluster_settings import ClusterSettings
from idea.infrastructure.install.infra_utils.utils import InfraUtils
from idea.infrastructure.install.parameters.common import CommonKey
from idea.infrastructure.install.parameters.parameters import RESParameters
from idea.infrastructure.install.policies import (
    CleanupEC2InstancePolicy,
    DetachVpcFromLambdaPolicy,
)
from idea.infrastructure.resources.lambda_functions.custom_resource.ddb_final_values_populator_lambda import (
    handler as populator_handler,
)
from idea.infrastructure.resources.lambda_functions.custom_resource.deletion_cleanup_resources_lambda import (
    handler as cleanup_handler,
)


class ResFinalizerStack(ResBaseConstruct):
    def __init__(
        self,
        scope: constructs.Construct,
        shared_library_lambda_layer: cdk.aws_lambda.LayerVersion,
        parameters: Union[RESParameters, BIParameters] = RESParameters(),
    ):
        self.parameters = parameters
        self.cluster_name = parameters.get_str(CommonKey.CLUSTER_NAME)
        self.shared_library_lambda_layer = shared_library_lambda_layer
        super().__init__(
            scope,
            "res-finalizer",
            self.cluster_name,
            self.parameters,
        )

        self.nested_stack = cdk.NestedStack(
            scope,
            "res-finalizer",
            description="Nested RES Finalizer Stack",
        )

        self.has_iam_prefix_condition = InfraUtils.get_iam_prefix_condition(
            self.nested_stack, parameters
        )
        self.has_iam_path_condition = InfraUtils.get_iam_path_condition(
            self.nested_stack, parameters
        )

        self.cluster_settings = ClusterSettings(self.cluster_name, self.nested_stack)
        self.arn_builder = ArnBuilder(self.cluster_name, self.cluster_settings)

        self.clean_up_ec2_instance()
        self.detach_vpc_from_lambda()
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
                    actions=["cognito-idp:AdminCreateUser", "cognito-idp:AdminGetUser"],
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

        final_values_populator_handler = cdk.aws_lambda.Function(
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
            **InfraUtils.get_handler_and_code_for_function(populator_handler.handler),
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

    def clean_up_ec2_instance(self) -> None:
        lambda_name = "clean-up-ec2-instance"
        clean_up_ec2_instance_lambda = lambda_.Function(
            self.nested_stack,
            lambda_name,
            runtime=RES_COMMON_LAMBDA_RUNTIME,
            description="Custom lambda to terminate ec2 instances when deleting RES environment",  # type: ignore
            timeout=cdk.Duration.seconds(900),  # type: ignore
            handler=cleanup_handler.clean_up_ec2_instance_handler,
            parameters=self.parameters,
            layers=[self.shared_library_lambda_layer],  # type: ignore
            initial_policy=CleanupEC2InstancePolicy.create_policy_statements(
                self.arn_builder
            ),  # type: ignore
            environment={
                ENVIRONMENT_NAME_KEY: self.cluster_name,
            },
        )

        self.clean_up_ec2_instance_custom_resource = cdk.CustomResource(
            self.nested_stack,
            id=f"{lambda_name}-custom-resource",
            service_token=clean_up_ec2_instance_lambda.function_arn,
            removal_policy=cdk.RemovalPolicy.DESTROY,
            resource_type="Custom::CleanupEC2Instance",
        )

    def detach_vpc_from_lambda(self) -> None:
        lambda_name = "detach-vpc-from-lambda"
        detach_vpc_from_lambda_lambda = lambda_.Function(
            self.nested_stack,
            lambda_name,
            runtime=RES_COMMON_LAMBDA_RUNTIME,
            description="Custom lambda to check for lambda network interface deletion when deleting RES environment",  # type: ignore
            timeout=cdk.Duration.seconds(900),  # type: ignore
            handler=cleanup_handler.detach_vpc_from_lambdas_handler,
            layers=[self.shared_library_lambda_layer],  # type: ignore
            initial_policy=DetachVpcFromLambdaPolicy.create_policy_statements(
                self.arn_builder
            ),  # type: ignore
            parameters=self.parameters,
            environment={
                ENVIRONMENT_NAME_KEY: self.cluster_name,
                "SECURITY_GROUP_IDS": self.clean_up_ec2_instance_custom_resource.get_att_string(
                    "SECURITY_GROUP_IDS"
                ),
            },
        )

        detach_vpc_from_lambda_custom_resource = cdk.CustomResource(
            self.nested_stack,
            id=f"{lambda_name}-custom-resource",
            service_token=detach_vpc_from_lambda_lambda.function_arn,
            removal_policy=cdk.RemovalPolicy.DESTROY,
            resource_type="Custom::DetachLambdaVPC",
            # Note: Timeout the custom resource if lambda doesn't response after half an hour
            # Lambda should send response after ENIs attached to lambdas are deleted.
            # Deletion of ENIs should takes at most 20 mintues (No official documentation).
            service_timeout=cdk.Duration.seconds(1800),
        )
        detach_vpc_from_lambda_custom_resource.node.add_dependency(
            self.clean_up_ec2_instance_custom_resource
        )
