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

from ideadatamodel import (
    constants,
    exceptions
)

import ideaadministrator
from ideaadministrator.app.cdk.stacks import IdeaBaseStack

from ideaadministrator.app.cdk.constructs import (
    ExistingSocaCluster
)

from typing import Optional
import aws_cdk as cdk
import constructs
from aws_cdk import (
    aws_aps as aps,
    aws_cloudwatch as cloudwatch
)


class MetricsStack(IdeaBaseStack):

    def __init__(self, scope: constructs.Construct,
                 cluster_name: str,
                 aws_region: str,
                 aws_profile: str,
                 module_id: str,
                 deployment_id: str,
                 termination_protection: bool = True,
                 env: cdk.Environment = None):
        super().__init__(
            scope=scope,
            cluster_name=cluster_name,
            aws_region=aws_region,
            aws_profile=aws_profile,
            module_id=module_id,
            deployment_id=deployment_id,
            termination_protection=termination_protection,
            description=f'ModuleId: {module_id}, Cluster: {cluster_name}, Version: {ideaadministrator.props.current_release_version}',
            tags={
                constants.IDEA_TAG_MODULE_ID: module_id,
                constants.IDEA_TAG_MODULE_NAME: constants.MODULE_METRICS,
                constants.IDEA_TAG_MODULE_VERSION: ideaadministrator.props.current_release_version
            },
            env=env
        )

        self.cluster = ExistingSocaCluster(self.context, self.stack)

        self.cloudwatch_dashboard: Optional[cloudwatch.Dashboard] = None
        self.amazon_prometheus_workspace: Optional[aps.CfnWorkspace] = None

        if self.is_cloudwatch():
            self.build_cloudwatch()
        elif self.is_amazon_managed_prometheus():
            self.build_amazon_managed_prometheus()
        elif self.is_prometheus():
            self.build_prometheus()
        else:
            raise exceptions.general_exception(f'metrics provider: {self.get_metrics_provider()} not supported')

        self.build_cluster_settings()

    def get_metrics_provider(self) -> str:
        return self.context.config().get_string('metrics.provider', required=True)

    def is_cloudwatch(self) -> bool:
        return self.get_metrics_provider() == constants.METRICS_PROVIDER_CLOUDWATCH

    def is_amazon_managed_prometheus(self) -> bool:
        return self.get_metrics_provider() == constants.METRICS_PROVIDER_AMAZON_MANAGED_PROMETHEUS

    def is_prometheus(self) -> bool:
        return self.get_metrics_provider() == constants.METRICS_PROVIDER_PROMETHEUS

    def build_cloudwatch(self):
        dashboard_name = self.context.config().get_string('metrics.cloudwatch.dashboard_name', required=True)
        # todo - add widgets based on modules deployed
        self.cloudwatch_dashboard = cloudwatch.Dashboard(
            scope=self.stack,
            id='cloudwatch-dashboard',
            dashboard_name=dashboard_name
        )

    def build_amazon_managed_prometheus(self):
        workspace_name = self.context.config().get_string('metrics.amazon_managed_prometheus.workspace_name', required=True)
        self.amazon_prometheus_workspace = aps.CfnWorkspace(
            scope=self.stack,
            id='prometheus-workspace',
            alias=workspace_name
        )
        self.add_common_tags(self.amazon_prometheus_workspace)

    def build_prometheus(self):
        # validate and do nothing as of now.
        # might need additional configurations to provision secrets to authenticate with remote write url
        self.context.config().get_string('metrics.prometheus.remote_write.url', required=True)
        self.context.config().get_string('metrics.prometheus.query.url', required=True)

    def build_cluster_settings(self):
        cluster_settings = {
            'deployment_id': self.deployment_id
        }

        if self.is_cloudwatch():
            cluster_settings['cloudwatch.dashboard_arn'] = self.cloudwatch_dashboard.dashboard_arn
        elif self.is_amazon_managed_prometheus():
            cluster_settings['amazon_managed_prometheus.workspace_id'] = self.amazon_prometheus_workspace.attr_workspace_id
            cluster_settings['amazon_managed_prometheus.workspace_arn'] = self.amazon_prometheus_workspace.attr_arn
            cluster_settings['prometheus.remote_write.url'] = f'{self.amazon_prometheus_workspace.attr_prometheus_endpoint}api/v1/remote_write'
            cluster_settings['prometheus.remote_read.url'] = f'{self.amazon_prometheus_workspace.attr_prometheus_endpoint}api/v1/query'
        elif self.is_prometheus():
            pass

        self.update_cluster_settings(cluster_settings)
