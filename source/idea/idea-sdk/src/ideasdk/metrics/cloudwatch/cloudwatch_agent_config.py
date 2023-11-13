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

__all__ = (
    'CloudWatchAgentMetricsCollectedOptions',
    'CloudWatchAgentMetricsOptions',
    'CloudWatchAgentLogFileFilter',
    'CloudWatchAgentLogFileOptions',
    'CloudWatchAgentLogsOptions',
    'CloudWatchAgentConfigOptions',
    'CloudWatchAgentConfig'
)

from ideadatamodel import SocaBaseModel, exceptions
from ideasdk.utils import Utils, Jinja2Utils
from ideasdk.config.cluster_config import ClusterConfig

from typing import Dict, Optional, List, Union, Any


class CloudWatchAgentMetricsCollectedOptions(SocaBaseModel):
    # refer to https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Agent-Configuration-File-Details.html for more details
    name: str  # can be one of [cpu, disk, diskio, swap, mem, net, netstat, processes, nvidia_gpu, collectd, statsd]
    enabled: bool
    # if config is not provided, applicable defaults will be used from amazon-cloudwatch-agent-[linux|windows].yml jinja2 template
    # refer to cloudwatch agent config docs for config details on each metric section
    config: Optional[Dict]


class CloudWatchAgentMetricsOptions(SocaBaseModel):
    namespace: str
    metrics_collection_interval: Optional[int]
    force_flush_interval: Optional[int]
    # eg: "aggregation_dimensions" : [["AutoScalingGroupName"], ["InstanceId", "InstanceType"],[]]
    aggregation_dimensions: Optional[Union[List[str], List[List[str]]]]
    append_dimensions: Optional[Dict]
    # eg. ['ImageId', 'InstanceId', 'InstanceType', 'AutoScalingGroupName']
    include_dimensions: Optional[List[str]]
    metrics_collected: List[CloudWatchAgentMetricsCollectedOptions]

    @staticmethod
    def default_options(namespace: str, include: List[str] = None, exclude: List[str] = None) -> 'CloudWatchAgentMetricsOptions':
        metrics_collected = []
        sections = ['cpu', 'disk', 'diskio', 'swap', 'mem', 'net', 'netstat', 'processes']
        for section_name in sections:
            if Utils.is_not_empty(exclude):
                if section_name in exclude:
                    continue
            if Utils.is_not_empty(include):
                if section_name not in include:
                    continue
            metrics_collected.append(CloudWatchAgentMetricsCollectedOptions(
                name=section_name,
                enabled=True
            ))

        # ensures nvidia_gpu is also added
        for section_name in include:
            if section_name not in sections:
                metrics_collected.append(CloudWatchAgentMetricsCollectedOptions(
                    name=section_name,
                    enabled=True
                ))

        return CloudWatchAgentMetricsOptions(
            namespace=namespace,
            metrics_collected=metrics_collected
        )


class CloudWatchAgentLogFileFilter(SocaBaseModel):
    # can be one of [exclude, include]
    # Denotes the type of filter. Valid values are include and exclude.
    # With include, the log entry must match the expression to be published to CloudWatch Logs.
    # With exclude, each log entry that matches the filter is not sent to CloudWatch Logs.
    type: str
    # A regular expression string
    expression: str


class CloudWatchAgentLogFileOptions(SocaBaseModel):
    file_path: str
    # As part of the log_group_name and log_stream_name, you can use {instance_id}, {hostname}, {local_hostname}, and {ip_address} as variables within the name.
    # {hostname} retrieves the hostname from the EC2 metadata, and {local_hostname} uses the hostname from the network configuration file.
    # Specifies what to use as the log group name in CloudWatch Logs.
    log_group_name: str
    log_stream_name: str
    retention_in_days: Optional[int]
    auto_removal: Optional[bool]
    filters: Optional[List[CloudWatchAgentLogFileFilter]]
    # valid values are UTC and Local
    timezone: Optional[str]


class CloudWatchAgentLogsOptions(SocaBaseModel):
    force_flush_interval: Optional[int]
    default_log_stream_name: Optional[str]
    files: List[CloudWatchAgentLogFileOptions]


class CloudWatchAgentConfigOptions(SocaBaseModel):
    module_id: str
    base_os: str
    # metrics may be enabled at cluster level, but an individual module might not want to use metrics.
    enable_metrics: bool
    # cloud watch logging may be enabled at cluster level, but an individual module might not want to use cloud watch logs
    enable_logs: bool
    metrics: Optional[CloudWatchAgentMetricsOptions]
    logs: Optional[CloudWatchAgentLogsOptions]


class CloudWatchAgentConfig:

    def __init__(self, cluster_config: ClusterConfig, options: CloudWatchAgentConfigOptions):

        self.config = cluster_config

        if Utils.is_empty(options.module_id):
            raise exceptions.invalid_params('module_id is required')
        if Utils.is_empty(options.base_os):
            raise exceptions.invalid_params('base_os is required')

        self.options = options

        # defaults
        self.DEFAULT_METRICS_COLLECTION_INTERVAL = self.config.get_int('metrics.cloudwatch.metrics_collection_interval', 60)
        self.DEFAULT_METRICS_FORCE_FLUSH_INTERVAL = self.config.get_int('metrics.cloudwatch.force_flush_interval', 60)
        self.DEFAULT_LOGS_FORCE_FLUSH_INTERVAL = self.config.get_int('cluster.cloudwatch_logs.force_flush_interval', 5)
        self.DEFAULT_LOGS_RETENTION_IN_DAYS = self.config.get_int('cluster.cloudwatch_logs.retention_in_days', 90)

        # module id
        self.module_id = options.module_id

        # cluster name, aws region
        self.cluster_name = self.config.get_string('cluster.cluster_name', required=True)
        self.aws_region = self.config.get_string('cluster.aws.region', required=True)

        # platform
        self.platform = Utils.get_platform(base_os=options.base_os)

        # vpc endpoints
        self.logs_endpoint_override: Optional[str] = None
        self.metrics_endpoint_override: Optional[str] = None
        use_vpc_endpoints = self.config.get_bool('cluster.network.use_vpc_endpoints', False)
        if use_vpc_endpoints:
            logs_vpc_endpoint_enabled = self.config.get_bool('cluster.network.vpc_interface_endpoints.logs.enabled', False)
            if logs_vpc_endpoint_enabled:
                logs_endpoint_url = self.config.get_string('cluster.network.vpc_interface_endpoints.logs.endpoint_url', required=True)
                # "endpoint_override": "vpce-XXXXXXXXXXXXXXXXXXXXXXXXX.logs.us-east-1.vpce.amazonaws.com"
                self.logs_endpoint_override = logs_endpoint_url.replace('https://', '')

            metrics_vpc_endpoint_enabled = self.config.get_bool('cluster.network.vpc_interface_endpoints.monitoring.enabled', False)
            if metrics_vpc_endpoint_enabled:
                metrics_endpoint_url = self.config.get_string('cluster.network.vpc_interface_endpoints.monitoring.endpoint_url', required=True)
                # "endpoint_override": "vpce-XXXXXXXXXXXXXXXXXXXXXXXXX.monitoring.us-east-1.vpce.amazonaws.com"
                self.metrics_endpoint_override = metrics_endpoint_url.replace('https://', '')

        # metrics
        self.enable_metrics = Utils.get_as_bool(options.enable_metrics, False)
        self.metrics_collection_interval: Optional[int] = None
        self.metrics_namespace: Optional[str] = None
        self.metrics_force_flush_interval: Optional[int] = None
        self.aggregation_dimensions: Optional[Union[List[str], List[List[str]]]] = None
        self.metrics_collected: Dict[str, Dict[str, Any]] = {}
        self.append_dimensions: Optional[Dict] = None
        self.include_dimensions: Optional[List[str]] = None
        if self.enable_metrics:
            if Utils.is_empty(options.metrics):
                raise exceptions.invalid_params('metrics is required when enable_metrics = True')
            if Utils.is_empty(options.metrics.metrics_collected):
                raise exceptions.invalid_params('metrics.metrics_collected is required')

            if Utils.is_empty(options.metrics.namespace):
                self.metrics_namespace = f'{self.cluster_name}/{self.module_id}'
            else:
                self.metrics_namespace = options.metrics.namespace
            self.metrics_collection_interval = Utils.get_as_int(options.metrics.metrics_collection_interval, self.DEFAULT_METRICS_COLLECTION_INTERVAL)
            self.metrics_force_flush_interval = Utils.get_as_int(options.metrics.force_flush_interval, self.DEFAULT_METRICS_FORCE_FLUSH_INTERVAL)
            self.aggregation_dimensions = options.metrics.aggregation_dimensions
            self.append_dimensions = options.metrics.append_dimensions
            self.include_dimensions = options.metrics.include_dimensions
            for collected_metric in options.metrics.metrics_collected:
                metric_config = {
                    'enabled': Utils.get_as_bool(collected_metric.enabled, False),
                }
                if collected_metric.config is not None:
                    metric_config['config'] = collected_metric.config
                self.metrics_collected[collected_metric.name] = metric_config

        # logs
        self.enable_logs = Utils.get_as_bool(options.enable_logs, False)
        self.collected_log_files: Optional[List[Dict]] = None
        self.logs_force_flush_interval: Optional[int] = None
        self.default_log_stream_name: Optional[str] = None
        if self.enable_logs:
            if Utils.is_empty(options.logs):
                raise exceptions.invalid_params('logs is required when enable_logs = True')
            if Utils.is_empty(options.logs.files):
                raise exceptions.invalid_params('logs.files is required')
            for index, file_config in enumerate(options.logs.files):
                if Utils.is_empty(file_config.file_path):
                    raise exceptions.invalid_params(f'logs.files[{index}].file_path is required')
                if Utils.is_empty(file_config.log_group_name):
                    raise exceptions.invalid_params(f'logs.files[{index}].log_group_name is required')
                if Utils.is_empty(file_config.log_stream_name):
                    raise exceptions.invalid_params(f'logs.files[{index}].log_stream_name is required')

            self.default_log_stream_name = Utils.get_as_string(options.logs.default_log_stream_name, f'{self.module_id}_default_{{ip_address}}')
            self.logs_force_flush_interval = Utils.get_as_int(options.logs.force_flush_interval, self.DEFAULT_LOGS_FORCE_FLUSH_INTERVAL)
            collected_log_files = []
            for file_config in options.logs.files:
                if file_config.retention_in_days is None:
                    file_config.retention_in_days = self.DEFAULT_LOGS_RETENTION_IN_DAYS
                collected_log_files.append(Utils.to_dict(file_config))
            self.collected_log_files = collected_log_files

    def build(self) -> Dict:

        context = {
            # common
            'utils': Utils,
            'aws_region': self.aws_region,

            # logs
            'enable_logs': self.enable_logs,
            'logs_endpoint_override': self.logs_endpoint_override,
            'logs_force_flush_interval': self.logs_force_flush_interval,
            'default_log_stream_name': self.default_log_stream_name,
            'collected_log_files': self.collected_log_files,

            # metrics
            'enable_metrics': self.enable_metrics,
            'metrics_endpoint_override': self.metrics_endpoint_override,
            'metrics_collection_interval': self.metrics_collection_interval,
            'metrics_namespace': self.metrics_namespace,
            'metrics_force_flush_interval': self.metrics_force_flush_interval,
            'aggregation_dimensions': self.aggregation_dimensions,
            'append_dimensions': self.append_dimensions,
            'include_dimensions': self.include_dimensions,
            'metrics_collected': self.metrics_collected
        }

        env = Jinja2Utils.env_using_package_loader(
            package_name='ideasdk.metrics.cloudwatch',
            package_path='templates'
        )

        template = env.get_template(f'amazon-cloudwatch-agent-{self.platform}.yml')
        content = template.render(**context)
        return Utils.from_yaml(content)
