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
import re

import ideasdk
from ideasdk.utils import Utils
from ideadatamodel import SocaAnyPayload, exceptions, constants
from ideasdk.protocols import SocaConfigType
from typing import List, Dict, Optional

DEFAULT_APP_DEPLOY_DIR = '/opt/idea/app'


class BootstrapContext:
    """
    BootstrapContext
    """

    def __init__(self, config: SocaConfigType,
                 module_name: str,
                 module_id: str,
                 base_os: str,
                 instance_type: str,
                 module_set: str):

        if Utils.is_empty(config):
            raise exceptions.invalid_params('config is required')
        if Utils.is_empty(module_name):
            raise exceptions.invalid_params('module_name is required')
        if Utils.is_empty(module_id):
            raise exceptions.invalid_params('module_id is required')
        if Utils.is_empty(module_set):
            raise exceptions.invalid_params('module_set is required')
        if Utils.is_empty(base_os):
            raise exceptions.invalid_params('base_os is required')
        if Utils.is_empty(instance_type):
            raise exceptions.invalid_params('instance_type is required')

        self.config = config
        self.base_os = base_os
        self.instance_type = instance_type
        self.module_name = module_name
        self.module_id = module_id
        self.module_set = module_set
        self.vars = SocaAnyPayload()
        self.utils = Utils

    @property
    def cluster_name(self) -> str:
        return self.config.get_string('cluster.cluster_name', required=True)

    @property
    def cluster_s3_bucket(self) -> str:
        return self.config.get_string('cluster.cluster_s3_bucket', required=True)

    @property
    def cluster_home_dir(self) -> str:
        return self.config.get_string('cluster.home_dir', required=True)

    @property
    def aws_region(self) -> str:
        return self.config.get_string('cluster.aws.region', required=True)

    @property
    def module_version(self) -> str:
        return ideasdk.__version__

    @property
    def app_deploy_dir(self) -> str:
        return DEFAULT_APP_DEPLOY_DIR

    @property
    def https_proxy(self) -> str:
        https_proxy = self.config.get_string('cluster.network.https_proxy', required=False, default='')
        if Utils.is_not_empty(https_proxy):
            return https_proxy
        else:
            return ''

    @property
    def no_proxy(self) -> str:
        https_proxy = self.config.get_string('cluster.network.https_proxy', required=False, default='')
        if Utils.is_not_empty(https_proxy):
            return self.config.get_string('cluster.network.no_proxy', required=False, default='')
        else:
            return ''

    @property
    def default_system_user(self) -> str:
        if self.base_os in ('amazonlinux2', 'rhel8', 'rhel9'):
            return 'ec2-user'
        raise exceptions.general_exception(f'unknown system user name for base_os: {self.base_os}')

    def has_storage_provider(self, provider: str) -> bool:
        storage_config = self.config.get_config('shared-storage')
        for name, storage in storage_config.items():
            if not isinstance(storage, Dict):
                continue
            if 'provider' not in storage:
                continue
            if storage['provider'] == provider:
                return True
        return False

    def eval_shared_storage_scope(self, shared_storage: Dict) -> bool:
        scope = Utils.get_value_as_list('scope', shared_storage, [])
        if Utils.is_empty(scope):
            return True
        if 'cluster' in scope:
            return True

        context_vars = vars(self.vars)

        def eval_project() -> bool:
            if 'project' not in context_vars:
                return False
            projects = Utils.get_value_as_list('projects', shared_storage, [])
            return self.vars.project in projects

        def eval_module() -> bool:
            modules = Utils.get_value_as_list('modules', shared_storage, [])
            # empty list = allow all
            if Utils.is_empty(modules):
                return True
            return self.module_name in modules

        def eval_scheduler_queue_profile() -> bool:
            if 'queue_profile' not in context_vars:
                return False
            queue_profiles = Utils.get_value_as_list('queue_profiles', shared_storage, [])
            # empty list = allow all
            if Utils.is_empty(queue_profiles):
                return True
            return self.vars.queue_profile in queue_profiles

        if 'module' in scope and 'project' in scope:
            return eval_module() and eval_project()

        if 'project' in scope and 'scheduler:queue-profile' in scope:
            return eval_project() and eval_scheduler_queue_profile()

        if 'module' in scope:
            return eval_module()

        if 'project' in scope:
            return eval_project()

        if 'scheduler:queue-profile' in scope:
            return eval_scheduler_queue_profile()

        return False

    def is_gpu_instance_type(self) -> bool:
        instance_family = self.instance_type.split('.')[0]
        gpu_instance_families = self.config.get_list('global-settings.gpu_settings.instance_families', [])
        return instance_family in gpu_instance_families

    def is_nvidia_gpu(self) -> bool:
        instance_family = self.instance_type.split('.')[0]
        nvidia_public_driver_versions = self.config.get_config('global-settings.gpu_settings.nvidia_public_driver_versions')
        return instance_family in nvidia_public_driver_versions

    def is_amd_gpu(self) -> bool:
        return self.is_gpu_instance_type() and not self.is_nvidia_gpu()

    def get_nvidia_gpu_driver_version(self) -> str:
        instance_family = self.instance_type.split('.')[0]
        return self.config.get_string(f'global-settings.gpu_settings.nvidia_public_driver_versions.{instance_family}', required=True)

    def get_custom_aws_tags(self) -> List[Dict]:
        custom_tags = self.config.get_list('global-settings.custom_tags', [])
        custom_tags_dict = Utils.convert_custom_tags_to_key_value_pairs(custom_tags)
        result = []
        for key, value in custom_tags_dict.items():
            result.append({
                'Key': key,
                'Value': value
            })
        return result

    def get_cloudwatch_agent_config(self, additional_log_files: Optional[List[Dict]] = None) -> Optional[Dict]:
        context_vars = vars(self.vars)
        if 'cloudwatch_agent_config' not in context_vars:
            return None
        agent_config = self.vars.cloudwatch_agent_config

        additional_log_files = Utils.get_as_list(additional_log_files, None)
        if Utils.is_empty(additional_log_files):
            return agent_config
        logs = Utils.get_value_as_dict('logs', agent_config)
        if logs is None:
            return agent_config
        logs_collected = Utils.get_value_as_dict('logs_collected', logs)
        if logs_collected is None:
            logs_collected = {}
            logs['logs_collected'] = logs_collected
        files = Utils.get_value_as_dict('files', logs_collected)
        if files is None:
            files = {}
            logs_collected['files'] = files
        collect_list = Utils.get_value_as_list('collect_list', files)
        if collect_list is None:
            collect_list = []
            files['collect_list'] = files
        collect_list += additional_log_files
        return agent_config

    def is_metrics_provider_prometheus(self) -> bool:
        provider = self.config.get_string('metrics.provider')
        if Utils.is_empty(provider):
            return False
        return provider in (constants.METRICS_PROVIDER_PROMETHEUS,
                            constants.METRICS_PROVIDER_AMAZON_MANAGED_PROMETHEUS)

    def get_prometheus_config(self, additional_scrape_configs: Optional[List[Dict]] = None) -> Optional[Dict]:
        context_vars = vars(self.vars)
        if 'prometheus_config' not in context_vars:
            return None
        prometheus_config = self.vars.prometheus_config

        additional_scrape_configs = Utils.get_as_list(additional_scrape_configs, None)
        if Utils.is_empty(additional_scrape_configs):
            return prometheus_config

        scrape_configs = Utils.get_value_as_list('scrape_configs', prometheus_config, [])
        prometheus_config['scrape_configs'] = scrape_configs + additional_scrape_configs

        return prometheus_config

    def is_prometheus_exporter_enabled(self, name: str) -> bool:
        context_vars = vars(self.vars)
        if 'prometheus_exporters' not in context_vars:
            return False
        prometheus_exporters = self.vars.prometheus_exporters
        if Utils.is_empty(prometheus_exporters):
            return False
        return name in prometheus_exporters

    def get_bucket_name(self, bucket_arn: str) -> str:
        bucket_arn_regex = re.compile(constants.S3_BUCKET_ARN_REGEX)
        match = bucket_arn_regex.match(bucket_arn)
        if match:
            return match.group(1)
        return ""

    def get_prefix_for_object_storage(self, bucket_arn: str, read_only: bool, custom_prefix: str = None) -> str:
        match = re.match(constants.S3_BUCKET_ARN_PREFIX_REGEX, bucket_arn)
        if not match:
            return ""

        prefix = match.group(1).rstrip("/")

        if read_only:
            return f"{prefix}/"

        if not custom_prefix:
            raise exceptions.invalid_params('custom_bucket_prefix is required for read/write object storage')

        if custom_prefix == constants.OBJECT_STORAGE_CUSTOM_PROJECT_NAME_AND_USERNAME_PREFIX:
            return f"{prefix}/{self.vars.project}/{self.vars.session_owner}/"
        elif custom_prefix == constants.OBJECT_STORAGE_CUSTOM_PROJECT_NAME_PREFIX:
            return f"{prefix}/{self.vars.project}/"
        elif custom_prefix == constants.OBJECT_STORAGE_NO_CUSTOM_PREFIX:
            return f"{prefix}/"

        raise exceptions.invalid_params('invalid custom_prefix')
