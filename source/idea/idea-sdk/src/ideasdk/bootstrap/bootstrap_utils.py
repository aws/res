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

from ideadatamodel import constants

from ideasdk.utils import Utils
from ideasdk.context import BootstrapContext
from ideasdk.metrics.cloudwatch.cloudwatch_agent_config import (
    CloudWatchAgentMetricsOptions,
    CloudWatchAgentLogFileOptions,
    CloudWatchAgentLogsOptions,
    CloudWatchAgentConfigOptions,
    CloudWatchAgentConfig
)
from ideasdk.metrics.prometheus.prometheus_config import (
    PrometheusConfigOptions,
    PrometheusConfig
)

from typing import List


class BootstrapUtils:

    @staticmethod
    def check_and_attach_cloudwatch_logging_and_metrics(bootstrap_context: BootstrapContext,
                                                        metrics_namespace: str,
                                                        node_type: str,
                                                        enable_logging: bool,
                                                        log_files: List[CloudWatchAgentLogFileOptions],
                                                        enable_metrics: bool = None):
        cluster_config = bootstrap_context.config
        cloudwatch_logs_enabled = cluster_config.get_bool('cluster.cloudwatch_logs.enabled', False) and enable_logging

        metrics_provider = cluster_config.get_string('metrics.provider')

        cloudwatch_metrics_enabled = Utils.is_not_empty(metrics_provider) and metrics_provider == constants.METRICS_PROVIDER_CLOUDWATCH
        cloudwatch_metrics_enabled = cloudwatch_metrics_enabled and Utils.is_true(enable_metrics, default=True)

        include_metrics = ['cpu', 'disk', 'diskio', 'swap', 'mem', 'net', 'netstat', 'processes']
        if bootstrap_context.is_nvidia_gpu():
            include_metrics.append('nvidia_gpu')
        bootstrap_context.vars.cloudwatch_agent_config = CloudWatchAgentConfig(
            cluster_config=cluster_config,
            options=CloudWatchAgentConfigOptions(
                module_id=bootstrap_context.module_id,
                base_os=bootstrap_context.base_os,
                enable_logs=cloudwatch_logs_enabled,
                logs=CloudWatchAgentLogsOptions(
                    files=log_files
                ),
                enable_metrics=cloudwatch_metrics_enabled,
                metrics=CloudWatchAgentMetricsOptions.default_options(namespace=metrics_namespace, include=include_metrics)
            )
        ).build()

        prometheus_metrics_enabled = Utils.is_not_empty(metrics_provider) and metrics_provider in (constants.METRICS_PROVIDER_PROMETHEUS, constants.METRICS_PROVIDER_AMAZON_MANAGED_PROMETHEUS)
        prometheus_metrics_enabled = prometheus_metrics_enabled and Utils.is_true(enable_metrics, default=True)

        if prometheus_metrics_enabled:
            bootstrap_context.vars.prometheus_config = PrometheusConfig(
                cluster_config=cluster_config,
                options=PrometheusConfigOptions(
                    module_id=bootstrap_context.module_id,
                    base_os=bootstrap_context.base_os,
                    namespace=metrics_namespace,
                    node_exporter=True,
                    app_exporter=node_type == constants.NODE_TYPE_APP
                )
            ).build()
            exporters = ['node_exporter']
            if node_type == constants.NODE_TYPE_APP:
                exporters.append('app_exporter')
            bootstrap_context.vars.prometheus_exporters = exporters
