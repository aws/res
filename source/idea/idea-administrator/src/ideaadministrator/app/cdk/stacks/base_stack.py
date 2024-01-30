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

from ideaadministrator.app.cdk.constructs import (
    SocaBaseConstruct
)
from ideadatamodel import constants, exceptions
from ideaadministrator.app_context import AdministratorContext
from ideasdk.utils import Utils, GroupNameHelper

import constructs
import aws_cdk as cdk
from aws_cdk import (
    aws_cognito as cognito
)

from typing import Optional, Dict, List


class IdeaBaseStack(SocaBaseConstruct):

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
        self.deployment_id = deployment_id

        super().__init__(self.context, module_id)

        if tags is None:
            tags = {}

        tags = {**tags, **{
            constants.IDEA_TAG_ENVIRONMENT_NAME: self.cluster_name
        }}

        custom_tags = self.context.config().get_list('global-settings.custom_tags', [])
        custom_tags_dict = Utils.convert_custom_tags_to_key_value_pairs(custom_tags)
        tags = {**custom_tags_dict, **tags}

        cdk_toolkit_qualifier = Utils.shake_256(cluster_name, 5)
        cluster_s3_bucket = self.context.config().get_string('cluster.cluster_s3_bucket', required=True)

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
                file_assets_bucket_name=cluster_s3_bucket
            )
        )

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

    def is_metrics_provider_amazon_managed_prometheus(self) -> bool:
        metrics_provider = self.context.config().get_string('metrics.provider')
        if Utils.is_empty(metrics_provider):
            return False
        return metrics_provider == constants.METRICS_PROVIDER_AMAZON_MANAGED_PROMETHEUS

    def get_ec2_instance_managed_policies(self) -> List[str]:
        ec2_managed_policies = [
            self.context.config().get_string('cluster.iam.policies.amazon_ssm_managed_instance_core_arn', required=True),
            # since we need logs to be pushed to cloud watch by default, we don't check if metrics provider is cloud watch.
            # additionally, some modules and services might not support prometheus metrics and in that case, metrics will be available via cloudwatch
            self.context.config().get_string('cluster.iam.policies.cloud_watch_agent_server_arn', required=True),
        ]

        if self.is_metrics_provider_amazon_managed_prometheus():
            ec2_managed_policies.append(self.context.config().get_string('cluster.iam.policies.amazon_prometheus_remote_write_arn', required=True))

        ec2_managed_policy_arns = self.context.config().get_list('cluster.iam.ec2_managed_policy_arns', [])
        ec2_managed_policies += ec2_managed_policy_arns
        return ec2_managed_policies

    def lookup_user_pool(self) -> cognito.IUserPool:
        return cognito.UserPool.from_user_pool_id(
            self.stack,
            f'{self.cluster_name}-user-pool',
            self.context.config().get_string('identity-provider.cognito.user_pool_id', required=True)
        )
