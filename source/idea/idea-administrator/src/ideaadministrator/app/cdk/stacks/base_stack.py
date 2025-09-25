#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

import ideaadministrator
from ideaadministrator.app.cdk.constructs import (
    IAMResourcePrefixAspect,
    IAMResourcePathAspect,
    IdeaNagSuppression,
)
from ideadatamodel import constants, exceptions
from ideaadministrator.app_context import AdministratorContext
from ideasdk.utils import Utils

import constructs
import aws_cdk as cdk
from aws_cdk import (
    aws_cognito as cognito,
    aws_iam as iam,
    Aspects
)

from typing import Optional, Dict, List
from cdk_nag import NagSuppressions


# TODO: This class will be taken down after finishing moving stacks out of installer.
class IdeaBaseStack(constructs.Construct):

    def __init__(self,
                 scope: constructs.Construct,
                 cluster_name: str,
                 aws_region: str,
                 aws_profile: str,
                 module_id: str,
                 deployment_id: str,
                 description: Optional[str] = None,
                 tags: Optional[Dict] = None,
                 env: cdk.Environment = None,
                 termination_protection=True
                 ):

        self.context = AdministratorContext(
            cluster_name=cluster_name,
            aws_region=aws_region,
            aws_profile=aws_profile,
            module_id=module_id
        )

        self.stack_name = self.context.get_stack_name(module_id)
        self.module_id = module_id
        self.aws_region = aws_region
        self.cluster_name = cluster_name
        self.deployment_id = deployment_id
        self.account_id = env.account
        self.release_version = ideaadministrator.__version__
        self.iam_resource_prefix = self.context.config().get_string('cluster.iam.iam_resource_prefix', default="")
        self.iam_resource_path = self.context.config().get_string('cluster.iam.iam_resource_path', default="/")

        super().__init__(scope, module_id)

        if tags is None:
            tags = {}

        tags = {**tags, **{
            constants.IDEA_TAG_ENVIRONMENT_NAME: self.cluster_name
        }}

        custom_tags = self.context.config().get_list('global-settings.custom_tags', [])
        custom_tags_dict = Utils.convert_custom_tags_to_key_value_pairs(custom_tags)
        tags = {**custom_tags_dict, **tags}

        cdk_toolkit_qualifier = Utils.shake_256(cluster_name, 5)
        self.cdk_toolkit_qualifier = cdk_toolkit_qualifier
        cluster_s3_bucket = self.context.config().get_string('cluster.cluster_s3_bucket', required=True)

        permission_boundary_arn = self.context.config().get_string('cluster.iam.permission_boundary_arn')

        self.partition ='aws-us-gov' if self.aws_region.startswith('us-gov-') else 'aws'

        self.stack = cdk.Stack(
            scope,
            self.stack_name,
            description=description,
            env=env,
            stack_name=self.stack_name,
            tags=tags,
            termination_protection=termination_protection,
            synthesizer=cdk.DefaultStackSynthesizer(
                qualifier=cdk_toolkit_qualifier,
                bucket_prefix='cdk/',
                file_assets_bucket_name=cluster_s3_bucket,
                deploy_role_arn=f"{self.get_cdk_role_arn(role_name='deploy')}",
                lookup_role_arn=f"{self.get_cdk_role_arn(role_name='lookup')}",
                image_asset_publishing_role_arn=f"{self.get_cdk_role_arn(role_name='image-publishing')}",
                file_asset_publishing_role_arn=f"{self.get_cdk_role_arn(role_name='file-publishing')}",
                cloud_formation_execution_role=f"{self.get_cdk_role_arn(role_name='cfn-exec')}",
            )
        )

        if permission_boundary_arn:
            permission_boundary_policy = iam.ManagedPolicy.from_managed_policy_arn(self.stack, 'PermissionBoundaryPolicy', permission_boundary_arn)
            iam.PermissionsBoundary.of(self.stack).apply(permission_boundary_policy)

        if self.iam_resource_prefix:
            Aspects.of(self.stack).add(IAMResourcePrefixAspect(prefix=self.iam_resource_prefix))

        if self.iam_resource_path != "/":
            Aspects.of(self.stack).add(IAMResourcePathAspect(path=self.iam_resource_path))


    def get_target_group_name(self, identifier: str) -> str:
        # target group name cannot be more than 32 characters
        # max calculation - cluster name (max: 11) - (1) identifier (max: 11) - (1) suffix/hash (cluster_name + module_id) (8) = 32
        suffix = Utils.shake_256(f'{self.cluster_name}.{self.module_id}', 4)
        target_group_name = f'{self.cluster_name}-{identifier}-{suffix}'
        if len(target_group_name) > 32:
            raise exceptions.invalid_params(f'target group name: {target_group_name} cannot more more than 32 characters.')
        return target_group_name

    def update_cluster_settings(self, cluster_settings: Dict):
        cluster_settings_lambda_arn = self.context.config().get_string('cluster.cluster_settings_lambda_arn', required=True)
        cdk.CustomResource(
            self.stack,
            f'{self.cluster_name}-{self.module_id}-settings',
            service_token=cluster_settings_lambda_arn,
            properties={
                'cluster_name': self.cluster_name,
                'module_id': self.module_id,
                'version': self.release_version,
                'settings': cluster_settings
            },
            resource_type='Custom::ClusterSettings'
        )


    def get_ec2_instance_managed_policies(self) -> List[str]:
        ec2_managed_policies = [
            self.context.config().get_string('cluster.iam.policies.amazon_ssm_managed_instance_core_arn', required=True),
            # since we need logs to be pushed to cloud watch by default, we don't check if metrics provider is cloud watch.
            # additionally, some modules and services might not support prometheus metrics and in that case, metrics will be available via cloudwatch
            self.context.config().get_string('cluster.iam.policies.cloud_watch_agent_server_arn', required=True),
        ]

        ec2_managed_policy_arns = self.context.config().get_list('cluster.iam.ec2_managed_policy_arns', [])
        ec2_managed_policies += ec2_managed_policy_arns
        return ec2_managed_policies

    def lookup_user_pool(self) -> cognito.IUserPool:
        return cognito.UserPool.from_user_pool_id(
            self.stack,
            f'{self.cluster_name}-user-pool',
            self.context.config().get_string('identity-provider.cognito.user_pool_id', required=True)
        )

    def get_cdk_role_arn(self, role_name) -> str:
        return f"arn:{self.partition}:iam::{self.account_id}:role{self.iam_resource_path}{self.iam_resource_prefix}cdk-{self.cdk_toolkit_qualifier}-{role_name}-role-{self.aws_region}"

    def add_common_tags(
        self, construct: Optional[constructs.IConstruct] = None
    ) -> None:
        if construct is None:
            construct = self
        cdk.Tags.of(construct).add(constants.IDEA_TAG_NAME, f"{self.cluster_name}-{self.module_id}")
        cdk.Tags.of(construct).add(
            constants.IDEA_TAG_ENVIRONMENT_NAME, self.cluster_name
        )

    def add_nag_suppression(self, suppressions: List[IdeaNagSuppression], construct: constructs.IConstruct = None, apply_to_children: bool = False):
        if construct is None:
            construct = self
        cdk_nag_suppressions = []
        for suppression in suppressions:
            cdk_nag_suppressions.append({
                'id': suppression.rule_id,
                'reason': suppression.reason
            })
        if isinstance(construct, cdk.Stack):
            NagSuppressions.add_stack_suppressions(
                stack=construct,
                suppressions=cdk_nag_suppressions,
                apply_to_nested_stacks=apply_to_children
            )
        else:
            NagSuppressions.add_resource_suppressions(
                construct=construct,
                suppressions=cdk_nag_suppressions,
                apply_to_children=apply_to_children
        )

    def build_instance_profile_arn(self, instance_profile_ref: str):
        return f'arn:{self.partition}:iam::{self.account_id}:instance-profile{self.iam_resource_path}{instance_profile_ref}'

    def get_kms_key_arn(self, key_id: str) -> str:
        if key_id.startswith('arn:'):
            return key_id
        return f'arn:{self.partition}:kms:{self.aws_region}:{self.account_id}:key/{key_id}'
