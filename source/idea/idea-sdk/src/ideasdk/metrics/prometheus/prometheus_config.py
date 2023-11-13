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
    'PrometheusConfigOptions',
    'PrometheusConfig'
)

from ideadatamodel import SocaBaseModel, exceptions, constants
from ideasdk.utils import Utils, Jinja2Utils
from ideasdk.config.cluster_config import ClusterConfig

from typing import Dict, Optional, List


class PrometheusConfigOptions(SocaBaseModel):
    module_id: str
    base_os: str
    namespace: Optional[str]
    # if set to True, node exporter scrape_config will be added to scrape_configs
    node_exporter: Optional[bool]
    # if set to True, IDEA application server scrape_config will be added to scrape_configs
    app_exporter: Optional[bool]
    # prometheus scrape configurations
    # if node_exporter and app_exporter is None or False, scrape_configs is required.
    # refer to: https://prometheus.io/docs/prometheus/latest/configuration/configuration/#scrape_config
    scrape_configs: Optional[List[Dict]]


class PrometheusConfig:

    def __init__(self, cluster_config: ClusterConfig, options: PrometheusConfigOptions):
        self.config = cluster_config
        if Utils.is_empty(options.module_id):
            raise exceptions.invalid_params('module_id is required')
        if Utils.is_empty(options.base_os):
            raise exceptions.invalid_params('base_os is required')
        if Utils.is_false(options.node_exporter, True) and Utils.is_false(options.app_exporter, True):
            if Utils.is_empty(options.scrape_configs):
                raise exceptions.invalid_params('scrape_configs is required')

        # platform
        self.platform = Utils.get_platform(base_os=options.base_os)
        if Utils.is_true(options.app_exporter, False) and self.platform == constants.PLATFORM_WINDOWS:
            raise exceptions.invalid_params(f'app_exporter is not supported for platform: {self.platform}')

        # global scrape config
        self.scrape_interval = self.config.get_string('metrics.prometheus.scrape_interval', default='60s')
        self.scrape_timeout = self.config.get_string('metrics.prometheus.scrape_timeout', default='10s')

        # module id
        self.module_id = options.module_id

        # cluster name
        self.cluster_name = self.config.get_string('cluster.cluster_name', required=True)

        # aws region
        self.aws_region = self.config.get_string('cluster.aws.region', required=True)

        # namespace
        if Utils.is_empty(options.namespace):
            self.metrics_namespace = f'{self.cluster_name}/{self.module_id}'
        else:
            self.metrics_namespace = options.namespace

        # external labels
        external_labels = self.config.get_config('metrics.prometheus.external_labels')
        if external_labels is not None:
            external_labels = external_labels.as_plain_ordered_dict()
        else:
            external_labels = {}

        namespace_tokens = self.metrics_namespace.split('/')
        for index, token in enumerate(namespace_tokens):
            if index == 0:
                external_labels['cluster_name'] = token
                continue
            if index == 1:
                external_labels['module_id'] = token
                continue
            if index == 2:
                external_labels['component'] = token

        self.external_labels = external_labels

        # remote write
        remote_write_config = self.config.get_config('metrics.prometheus.remote_write', required=True)
        self.remote_write = remote_write_config.as_plain_ordered_dict()
        provider = self.config.get_string('metrics.provider', required=True)
        if provider == constants.METRICS_PROVIDER_AMAZON_MANAGED_PROMETHEUS:
            self.remote_write['sigv4'] = {
                'region': self.aws_region
            }

        # scrape configs
        scrape_configs = Utils.get_as_list(options.scrape_configs, [])
        if Utils.is_true(options.node_exporter, False):
            scrape_configs.append(self.get_default_node_exporter_scrape_config())
        if Utils.is_true(options.app_exporter, False):
            scrape_configs.append(self.get_default_app_exporter_scrape_config())
        self.scrape_configs = scrape_configs

    @staticmethod
    def get_default_node_exporter_scrape_config() -> Dict:
        return {
            'job_name': 'node_exporter',
            'static_configs': [
                {
                    'targets': [
                        'localhost:9100'
                    ]
                }
            ]
        }

    def get_default_app_exporter_scrape_config(self) -> Dict:
        api_context_path = self.config.get_string(f'{self.module_id}.server.api_context_path', required=True)
        server_port = self.config.get_int(f'{self.module_id}.server.port', required=True)
        config = {
            'job_name': 'app_exporter',
            'metrics_path': f'{api_context_path}/metrics',
            'scheme': 'http',
            'authorization': {
                'type': 'Bearer',
                'credentials_file': '/root/metrics_api_token.txt'
            },
            'static_configs': [
                {
                    'targets': [
                        f'localhost:{server_port}'
                    ]
                }
            ]
        }
        enable_tls = self.config.get_bool(f'{self.module_id}.server.enable_tls', default=False)
        if enable_tls:
            config['scheme'] = 'https'
            config['tls_config'] = {
                'insecure_skip_verify': True
            }
        return config

    def build(self) -> Dict:

        context = {
            'utils': Utils,
            'scrape_interval': self.scrape_interval,
            'scrape_timeout': self.scrape_timeout,
            'external_labels': self.external_labels,
            'remote_write': self.remote_write,
            'scrape_configs': self.scrape_configs
        }

        env = Jinja2Utils.env_using_package_loader(
            package_name='ideasdk.metrics.prometheus',
            package_path='templates'
        )

        template = env.get_template(f'prometheus-{self.platform}.yml')
        content = template.render(**context)
        return Utils.from_yaml(content)
