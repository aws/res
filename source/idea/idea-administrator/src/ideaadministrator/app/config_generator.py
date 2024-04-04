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

from ideasdk.utils import Utils, Jinja2Utils
from ideadatamodel import exceptions, constants

from ideaadministrator.app_props import AdministratorProps
from ideaadministrator.app.vpc_endpoints_helper import VpcEndpointsHelper

import os
from typing import Dict, List, Optional
from pathlib import Path


class ConfigGenerator:

    def __init__(self, values: Dict):
        self.props = AdministratorProps()

        self.user_values = values

    # Begin: User Values Getters and Validations

    def get_cluster_name(self) -> str:
        cluster_name = Utils.get_value_as_string('cluster_name', self.user_values)
        if Utils.is_empty(cluster_name):
            raise exceptions.invalid_params('cluster_name is required')
        return cluster_name

    def get_cluster_timezone(self) -> Optional[str]:
        aws_region = self.get_aws_region()
        region_timezone_file = self.props.region_timezone_config_file()
        with open(region_timezone_file, 'r') as f:
            region_timezone_config = Utils.from_yaml(f.read())

        default_timezone_id = Utils.get_value_as_string('default', region_timezone_config, 'America/Los_Angeles')
        region_timezone_id = Utils.get_value_as_string(aws_region, region_timezone_config, default_timezone_id)
        return region_timezone_id

    def get_cluster_locale(self) -> Optional[str]:
        return Utils.get_value_as_string('cluster_locale', self.user_values, 'en_US')

    def get_administrator_email(self) -> str:
        value = Utils.get_value_as_string('administrator_email', self.user_values, None)
        if Utils.is_empty(value):
            raise exceptions.invalid_params('administrator_email is required')
        return value

    def get_administrator_username(self) -> str:
        return Utils.get_value_as_string('administrator_username', self.user_values, 'clusteradmin')

    def get_aws_account_id(self) -> str:
        value = Utils.get_value_as_string('aws_account_id', self.user_values, None)
        if Utils.is_empty(value):
            raise exceptions.invalid_params('aws_account_id is required')
        return value

    def get_aws_dns_suffix(self) -> str:
        value = Utils.get_value_as_string('aws_dns_suffix', self.user_values, None)
        if Utils.is_empty(value):
            raise exceptions.invalid_params('aws_dns_suffix is required')
        return value

    def get_aws_partition(self) -> str:
        value = Utils.get_value_as_string('aws_partition', self.user_values, None)
        if Utils.is_empty(value):
            raise exceptions.invalid_params('aws_partition is required')
        return value

    def get_aws_region(self) -> str:
        value = Utils.get_value_as_string('aws_region', self.user_values)
        if Utils.is_empty(value):
            raise exceptions.invalid_params('aws_region is required')
        return value

    def get_aws_profile(self) -> Optional[str]:
        return Utils.get_value_as_string('aws_profile', self.user_values, None)

    def get_storage_internal_provider(self) -> str:
        return Utils.get_value_as_string('storage_internal_provider', self.user_values, 'efs')

    def get_internal_mount_dir(self) -> str:
        return Utils.get_value_as_string('internal_mount_dir', self.user_values, '/internal')

    def get_storage_home_provider(self) -> str:
        return Utils.get_value_as_string('storage_home_provider', self.user_values, 'efs')

    def get_home_mount_dir(self) -> str:
        return Utils.get_value_as_string('home_mount_dir', self.user_values, '/home')

    def get_prefix_list_ids(self) -> List[str]:
        return Utils.get_value_as_list('prefix_list_ids', self.user_values, [])
    
    def get_permission_boundary_arn(self) -> str:
        return Utils.get_value_as_string('permission_boundary_arn', self.user_values, None)

    def get_client_ip(self) -> List[str]:
        return Utils.get_value_as_list('client_ip', self.user_values, [])

    def get_ssh_key_pair_name(self) -> str:
        value = Utils.get_value_as_string('ssh_key_pair_name', self.user_values)
        if Utils.is_empty(value):
            raise exceptions.invalid_params('ssh_key_pair_name is required')
        return value

    def get_vpc_cidr_block(self) -> Optional[str]:
        if self.get_use_existing_vpc():
            return None
        value = Utils.get_value_as_string('vpc_cidr_block', self.user_values)
        if Utils.is_empty(value):
            raise exceptions.invalid_params('vpc_cidr_block is required')
        return value

    def get_use_vpc_endpoints(self) -> bool:
        return Utils.get_value_as_bool('use_vpc_endpoints', self.user_values, False)

    def get_alb_public(self) -> bool:
        return Utils.get_value_as_bool('alb_public', self.user_values, True)

    def get_directory_service_provider(self) -> str:
        return Utils.get_value_as_string('directory_service_provider', self.user_values, 'openldap')

    def get_use_existing_directory_service(self) -> Optional[bool]:
        value = Utils.get_value_as_bool('use_existing_directory_service', self.user_values, False)
        if value and not self.get_use_existing_vpc():
            raise exceptions.invalid_params('use_existing_directory_service cannot be True if use_existing_vpc = False')
        return value

    def get_directory_id(self) -> Optional[str]:
        value = Utils.get_value_as_string('directory_id', self.user_values)
        if Utils.is_empty(value) and self.get_use_existing_directory_service():
            raise exceptions.invalid_params('directory_id is required when use_existing_directory_service = True')
        return value

    def get_directory_service_root_username_secret_arn(self) -> Optional[str]:
        value = Utils.get_value_as_string('directory_service_root_username_secret_arn', self.user_values)
        if Utils.is_empty(value) and self.get_use_existing_directory_service():
            raise exceptions.invalid_params('directory_service_root_password_secret_arn is required when use_existing_directory_service = True')
        return value

    def get_directory_service_root_password_secret_arn(self) -> Optional[str]:
        value = Utils.get_value_as_string('directory_service_root_password_secret_arn', self.user_values)
        if Utils.is_empty(value) and self.get_use_existing_directory_service():
            raise exceptions.invalid_params('directory_service_root_password_secret_arn is required when use_existing_directory_service = True')
        return value

    def get_identity_provider(self) -> str:
        return Utils.get_value_as_string('identity_provider', self.user_values, 'cognito-idp')

    def get_enable_aws_backup(self) -> bool:
        return Utils.get_value_as_bool('enable_aws_backup', self.user_values, True)

    def get_kms_key_type(self) -> str:
        return Utils.get_value_as_string('kms_key_type', self.user_values, None)

    def get_kms_key_id(self) -> str:
        return Utils.get_value_as_string('kms_key_id', self.user_values, None)

    def get_instance_type(self) -> str:
        return Utils.get_value_as_string('instance_type', self.user_values, 'm5.large')

    def get_base_os(self) -> str:
        return Utils.get_value_as_string('base_os', self.user_values, 'amazonlinux2')

    def get_dcv_connection_gateway_instance_type(self) -> str:
        return Utils.get_value_as_string('dcv_connection_gateway_instance_type', self.user_values, 'm5.xlarge')

    def get_dcv_connection_gateway_volume_size(self) -> int:
        return Utils.get_value_as_int('dcv_connection_gateway_volume_size', self.user_values, 200)

    def get_dcv_connection_gateway_instance_ami(self) -> str:
        dcv_connection_gateway_instance_ami = Utils.get_value_as_string('dcv_connection_gateway_instance_ami', self.user_values)
        if Utils.is_not_empty(dcv_connection_gateway_instance_ami):
            return dcv_connection_gateway_instance_ami

        aws_region = self.get_aws_region()
        regions_config_file = self.props.region_ami_config_file()
        with open(regions_config_file, 'r') as f:
            regions_config = Utils.from_yaml(f.read())
        ami_config = Utils.get_value_as_dict(aws_region, regions_config)
        if ami_config is None:
            raise exceptions.general_exception(f'aws_region: {aws_region} not found in region_ami_config.yml')
        base_os = self.get_base_os()
        ami_id = Utils.get_value_as_string(base_os, ami_config)
        if Utils.is_empty(ami_id):
            raise exceptions.general_exception(f'instance_ami not found for base_os: {base_os}, region: {aws_region}')
        return ami_id

    def get_dcv_broker_instance_type(self) -> str:
        return Utils.get_value_as_string('dcv_broker_instance_type', self.user_values, 'm5.xlarge')

    def get_dcv_broker_volume_size(self) -> int:
        return Utils.get_value_as_int('dcv_broker_volume_size', self.user_values, 200)

    def get_dcv_broker_instance_ami(self) -> str:
        dcv_broker_instance_ami = Utils.get_value_as_string('dcv_broker_instance_ami', self.user_values)
        if Utils.is_not_empty(dcv_broker_instance_ami):
            return dcv_broker_instance_ami
        aws_region = self.get_aws_region()
        regions_config_file = self.props.region_ami_config_file()
        with open(regions_config_file, 'r') as f:
            regions_config = Utils.from_yaml(f.read())
        ami_config = Utils.get_value_as_dict(aws_region, regions_config)
        if ami_config is None:
            raise exceptions.general_exception(f'aws_region: {aws_region} not found in region_ami_config.yml')
        base_os = self.get_base_os()
        ami_id = Utils.get_value_as_string(base_os, ami_config)
        if Utils.is_empty(ami_id):
            raise exceptions.general_exception(f'instance_ami not found for base_os: {base_os}, region: {aws_region}')
        return ami_id

    def get_instance_ami(self) -> str:
        instance_ami = Utils.get_value_as_string('instance_ami', self.user_values)
        if Utils.is_not_empty(instance_ami):
            return instance_ami
        aws_region = self.get_aws_region()
        regions_config_file = self.props.region_ami_config_file()
        with open(regions_config_file, 'r') as f:
            regions_config = Utils.from_yaml(f.read())
        ami_config = Utils.get_value_as_dict(aws_region, regions_config)
        if ami_config is None:
            raise exceptions.general_exception(f'aws_region: {aws_region} not found in region_ami_config.yml')
        base_os = self.get_base_os()
        ami_id = Utils.get_value_as_string(base_os, ami_config)
        if Utils.is_empty(ami_id):
            raise exceptions.general_exception(f'instance_ami not found for base_os: {base_os}, region: {aws_region}')
        return ami_id

    def get_volume_size(self) -> int:
        return Utils.get_value_as_int('volume_size', self.user_values, 200)

    def get_enabled_modules(self) -> List[str]:
        enabled_modules = Utils.get_value_as_list('enabled_modules', self.user_values)
        if Utils.is_not_empty(enabled_modules):
            return enabled_modules
        return []

    def get_metrics_provider(self) -> Optional[str]:
        return Utils.get_value_as_string('metrics_provider', self.user_values, 'cloudwatch')

    def get_prometheus_remote_write_url(self) -> Optional[str]:
        metrics_provider = self.get_metrics_provider()
        if metrics_provider != 'prometheus':
            return None
        remote_write_url = Utils.get_value_as_string('prometheus_remote_write_url', self.user_values)
        if Utils.is_empty(remote_write_url):
            raise exceptions.general_exception('prometheus_remote_write_url is required when metrics_provider = prometheus')
        return remote_write_url

    def get_use_existing_vpc(self) -> bool:
        return Utils.get_value_as_bool('use_existing_vpc', self.user_values, False)

    def get_vpc_id(self) -> Optional[str]:
        value = Utils.get_value_as_string('vpc_id', self.user_values)
        if Utils.is_empty(value) and self.get_use_existing_vpc():
            raise exceptions.invalid_params('vpc_id is required when use_existing_vpc = True')
        return value

    def get_private_subnet_ids(self) -> Optional[str]:
        # by default all infrastructure host subnets and dcv session subnets are private
        dcv_session_private_subnet_ids = self.user_values.get('dcv_session_private_subnet_ids', [])
        infrastructure_host_subnet_ids = self.user_values.get('infrastructure_host_subnet_ids', [])

        private_subnet_ids = list(set([*infrastructure_host_subnet_ids, *dcv_session_private_subnet_ids]))
        # if alb is not public, the external load balancer subnets are also considered private
        if not self.get_alb_public:
            load_balancer_subnet_ids = self.user_values.get('load_balancer_subnet_ids', [])
            private_subnet_ids = list(set([*private_subnet_ids, *load_balancer_subnet_ids]))

        if self.get_use_existing_vpc() and Utils.is_empty(private_subnet_ids):
            raise exceptions.invalid_params('private_subnet_ids is required when use_existing_vpc = True')
        return private_subnet_ids

    def get_public_subnet_ids(self) -> Optional[str]:
        public_subnet_ids = []
        # if alb is public, only the load_balancer_subnet_ids are public subnets
        if self.get_alb_public():
            load_balancer_subnet_ids = self.user_values.get('load_balancer_subnet_ids', [])
            public_subnet_ids = load_balancer_subnet_ids

        if self.get_use_existing_vpc() and self.get_alb_public() and Utils.is_empty(public_subnet_ids):
            raise exceptions.invalid_params('public_subnet_ids is required when use_existing_vpc = True')
        return public_subnet_ids
    
    def get_load_balancer_subnet_ids(self) -> Optional[str]:
        load_balancer_subnet_ids = self.user_values.get('load_balancer_subnet_ids', [])
        if self.get_use_existing_vpc() and Utils.is_empty(load_balancer_subnet_ids):
            raise exceptions.invalid_params('load_balancer_subnet_ids is required when use_existing_vpc = True')
        return load_balancer_subnet_ids

    def get_infrastructure_host_subnet_ids(self) -> Optional[str]:
        infrastructure_host_subnet_ids = self.user_values.get('infrastructure_host_subnet_ids', [])
        if self.get_use_existing_vpc() and Utils.is_empty(infrastructure_host_subnet_ids):
            raise exceptions.invalid_params('infrastructure_host_subnet_ids is required when use_existing_vpc = True')
        return infrastructure_host_subnet_ids

    def get_dcv_session_private_subnet_ids(self) -> Optional[str]:
        dcv_session_private_subnet_ids = self.user_values.get('dcv_session_private_subnet_ids', [])
        if self.get_use_existing_vpc() and Utils.is_empty(dcv_session_private_subnet_ids):
            raise exceptions.invalid_params('dcv_session_private_subnet_ids is required when use_existing_vpc = True')
        return dcv_session_private_subnet_ids

    def get_use_existing_internal_fs(self) -> Optional[bool]:
        value = Utils.get_value_as_bool('use_existing_internal_fs', self.user_values, False)
        if value and not self.get_use_existing_vpc():
            raise exceptions.invalid_params('use_existing_internal_fs cannot be True if use_existing_vpc = False')
        return value

    def get_existing_internal_fs_id(self) -> Optional[str]:
        value = Utils.get_value_as_string('existing_internal_fs_id', self.user_values)
        if Utils.is_empty(value) and self.get_use_existing_internal_fs():
            raise exceptions.invalid_params('existing_internal_fs_id is required when existing_internal_fs_id = True')
        return value

    def get_use_existing_home_fs(self) -> Optional[bool]:
        value = Utils.get_value_as_bool('use_existing_home_fs', self.user_values, False)
        if value and not self.get_use_existing_vpc():
            raise exceptions.invalid_params('use_existing_home_fs cannot be True if use_existing_vpc = False')
        return value

    def get_existing_home_fs_id(self) -> Optional[str]:
        value = Utils.get_value_as_string('existing_home_fs_id', self.user_values)
        if Utils.is_empty(value) and self.get_use_existing_internal_fs():
            raise exceptions.invalid_params('existing_home_fs_id is required when use_existing_home_fs = True')
        return value

    def get_alb_custom_certificate_provided(self) -> Optional[bool]:
        return Utils.get_value_as_bool('alb_custom_certificate_provided', self.user_values, default=False)

    def get_alb_custom_certificate_acm_certificate_arn(self) -> Optional[str]:
        alb_custom_certificate_provided = self.get_alb_custom_certificate_provided()
        alb_custom_certificate_acm_certificate_arn = Utils.get_value_as_string('alb_custom_certificate_acm_certificate_arn', self.user_values)
        if alb_custom_certificate_provided and Utils.is_empty(alb_custom_certificate_acm_certificate_arn):
            raise exceptions.cluster_config_error('Need to provide alb_custom_certificate_acm_certificate_arn if alb_custom_certificate_provided is true')
        return alb_custom_certificate_acm_certificate_arn

    def get_alb_get_custom_dns_name(self) -> Optional[str]:
        alb_custom_certificate_provided = self.get_alb_custom_certificate_provided()
        alb_custom_dns_name = Utils.get_value_as_string('alb_custom_dns_name', self.user_values)
        if alb_custom_certificate_provided and Utils.is_empty(alb_custom_dns_name):
            raise exceptions.cluster_config_error('Need to provide alb_custom_dns_name if alb_custom_certificate_provided is true')
        return alb_custom_dns_name

    def get_dcv_session_traffic_routing(self) -> str:
        value = Utils.get_value_as_string('dcv_session_traffic_routing', self.user_values, default='ALB')
        if value not in {'ALB', 'NLB'}:
            raise exceptions.cluster_config_error(f'Invalid value - "{value}" provided for dcv_session_traffic_routing. Can be one of ALB or NLB only.')
        return value

    def get_dcv_session_quic_support(self) -> Optional[bool]:
        return Utils.get_value_as_bool('dcv_session_quic_support', self.user_values, default=False)

    def get_dcv_connection_gateway_custom_certificate_provided(self) -> Optional[bool]:
        return Utils.get_value_as_bool('dcv_connection_gateway_custom_certificate_provided', self.user_values, default=False)

    def get_dcv_connection_gateway_custom_dns_hostname(self) -> Optional[str]:
        value = Utils.get_value_as_string('dcv_connection_gateway_custom_dns_hostname', self.user_values)
        custom_certificate_provided = self.get_dcv_connection_gateway_custom_certificate_provided()
        if custom_certificate_provided and Utils.is_empty(value):
            raise exceptions.cluster_config_error('Need to provide dcv_connection_gateway_custom_dns_hostname if dcv_connection_gateway_custom_certificate_provided is true')
        return value

    def get_dcv_connection_gateway_custom_certificate_certificate_secret_arn(self) -> Optional[str]:
        value = Utils.get_value_as_string('dcv_connection_gateway_custom_certificate_certificate_secret_arn', self.user_values)
        custom_certificate_provided = self.get_dcv_connection_gateway_custom_certificate_provided()
        if custom_certificate_provided and Utils.is_empty(value):
            raise exceptions.cluster_config_error('Need to provide dcv_connection_gateway_custom_certificate_certificate_secret_arn if dcv_connection_gateway_custom_certificate_provided is true')
        return value

    def get_dcv_connection_gateway_custom_certificate_private_key_secret_arn(self) -> Optional[str]:
        value = Utils.get_value_as_string('dcv_connection_gateway_custom_certificate_private_key_secret_arn', self.user_values)
        custom_certificate_provided = self.get_dcv_connection_gateway_custom_certificate_provided()
        if custom_certificate_provided and Utils.is_empty(value):
            raise exceptions.cluster_config_error('Need to provide dcv_connection_gateway_custom_certificate_private_key_secret_arn if dcv_connection_gateway_custom_certificate_provided is true')
        return value

    # End: User Values Getters and Validations

    def get_cluster_config_dir(self):
        return self.props.cluster_config_dir(self.get_cluster_name(), self.get_aws_region())

    def get_vpc_gateway_endpoints(self) -> Optional[List[str]]:
        if not self.get_use_vpc_endpoints():
            return None
        if self.get_use_existing_vpc():
            return []
        helper = VpcEndpointsHelper(aws_region=self.get_aws_region(), aws_profile=self.get_aws_profile())
        return helper.get_supported_gateway_endpoint_services()

    def get_vpc_interface_endpoints(self) -> Optional[Dict]:
        if not self.get_use_vpc_endpoints():
            return None
        if self.get_use_existing_vpc():
            return {}
        helper = VpcEndpointsHelper(aws_region=self.get_aws_region(), aws_profile=self.get_aws_profile())
        return helper.get_supported_interface_endpoint_services()

    def generate_config_from_templates(self, temp=False, path=None):
        values = {
            'utils': Utils,
            'cluster_name': self.get_cluster_name(),
            'cluster_timezone': self.get_cluster_timezone(),
            'cluster_locale': self.get_cluster_locale(),
            'administrator_email': self.get_administrator_email(),
            'administrator_username': self.get_administrator_username(),
            'aws_account_id': self.get_aws_account_id(),
            'aws_dns_suffix': self.get_aws_dns_suffix(),
            'aws_partition': self.get_aws_partition(),
            'aws_region': self.get_aws_region(),
            'storage_internal_provider': self.get_storage_internal_provider(),
            'storage_home_provider': self.get_storage_home_provider(),
            'internal_mount_dir': self.get_internal_mount_dir(),
            'home_mount_dir': self.get_home_mount_dir(),
            'prefix_list_ids': self.get_prefix_list_ids(),
            'permission_boundary_arn': self.get_permission_boundary_arn(),
            'client_ip': self.get_client_ip(),
            'ssh_key_pair_name': self.get_ssh_key_pair_name(),
            'vpc_cidr_block': self.get_vpc_cidr_block(),
            'use_vpc_endpoints': self.get_use_vpc_endpoints(),
            'vpc_gateway_endpoints': self.get_vpc_gateway_endpoints(),
            'vpc_interface_endpoints': self.get_vpc_interface_endpoints(),
            'identity_provider': self.get_identity_provider(),
            'directory_service_provider': self.get_directory_service_provider(),
            'use_existing_directory_service': self.get_use_existing_directory_service(),
            'directory_id': self.get_directory_id(),
            'directory_service_root_username_secret_arn': self.get_directory_service_root_username_secret_arn(),
            'directory_service_root_password_secret_arn': self.get_directory_service_root_password_secret_arn(),
            'enable_aws_backup': self.get_enable_aws_backup(),
            'kms_key_type': self.get_kms_key_type(),
            'kms_key_id': self.get_kms_key_id(),
            'instance_type': self.get_instance_type(),
            'base_os': self.get_base_os(),
            'instance_ami': self.get_instance_ami(),
            'volume_size': self.get_volume_size(),
            'enabled_modules': self.get_enabled_modules(),
            'metrics_provider': self.get_metrics_provider(),
            'prometheus_remote_write_url': self.get_prometheus_remote_write_url(),
            'use_existing_vpc': self.get_use_existing_vpc(),
            'vpc_id': self.get_vpc_id(),
            'private_subnet_ids': self.get_private_subnet_ids(),
            'public_subnet_ids': self.get_public_subnet_ids(),
            'load_balancer_subnet_ids': self.get_load_balancer_subnet_ids(),
            'infrastructure_host_subnet_ids': self.get_infrastructure_host_subnet_ids(),
            'dcv_session_private_subnet_ids': self.get_dcv_session_private_subnet_ids(),
            'use_existing_internal_fs': self.get_use_existing_internal_fs(),
            'existing_internal_fs_id': self.get_existing_internal_fs_id(),
            'use_existing_home_fs': self.get_use_existing_home_fs(),
            'existing_home_fs_id': self.get_existing_home_fs_id(),
            'alb_public': self.get_alb_public(),
            'alb_custom_certificate_provided': self.get_alb_custom_certificate_provided(),
            'alb_custom_certificate_acm_certificate_arn': self.get_alb_custom_certificate_acm_certificate_arn(),
            'alb_custom_dns_name': self.get_alb_get_custom_dns_name(),
            'dcv_session_quic_support': self.get_dcv_session_quic_support(),
            'dcv_connection_gateway_custom_certificate_provided': self.get_dcv_connection_gateway_custom_certificate_provided(),
            'dcv_connection_gateway_custom_dns_hostname': self.get_dcv_connection_gateway_custom_dns_hostname(),
            'dcv_connection_gateway_custom_certificate_certificate_secret_arn': self.get_dcv_connection_gateway_custom_certificate_certificate_secret_arn(),
            'dcv_connection_gateway_custom_certificate_private_key_secret_arn': self.get_dcv_connection_gateway_custom_certificate_private_key_secret_arn(),
            'dcv_connection_gateway_instance_ami': self.get_dcv_connection_gateway_instance_ami(),
            'dcv_connection_gateway_instance_type': self.get_dcv_connection_gateway_instance_type(),
            'dcv_connection_gateway_volume_size': self.get_dcv_connection_gateway_volume_size(),
            'dcv_broker_instance_ami': self.get_dcv_broker_instance_ami(),
            'dcv_broker_instance_type': self.get_dcv_broker_instance_type(),
            'dcv_broker_volume_size': self.get_dcv_broker_volume_size(),
        }

        env = Jinja2Utils.env_using_file_system_loader(search_path=self.props.cluster_config_templates_dir)

        if temp:
            cluster_config_dir = os.path.join(path, 'config')
            os.makedirs(cluster_config_dir, exist_ok=True)
        else:
            cluster_config_dir = self.get_cluster_config_dir()

        idea_config_template = env.get_template('idea.yml')
        idea_config_content = idea_config_template.render(**values)
        idea_config_file = Path(os.path.join(cluster_config_dir, 'idea.yml'))

        idea_config = Utils.from_yaml(idea_config_content)

        modules = idea_config['modules']
        for module in modules:
            module_name = module['name']
            module_id = module['id']
            print(f'processing module: {module_name}')
            config_files = module['config_files']
            for file in config_files:
                # templates should contain settings with module name,
                # target file generation will create directory with module_id
                template = env.get_template(os.path.join(module_name, file))
                settings = template.render(**values, module_id=module_id, module_name=module_name, supported_base_os=constants.SUPPORTED_OS)
                settings_file = Path(os.path.join(cluster_config_dir, module_id, file))
                settings_file.parent.mkdir(exist_ok=True)

                with open(settings_file, 'w') as f:
                    f.write(settings)
                print(f'generated config file: {settings_file}')

        with open(idea_config_file, 'w') as f:
            f.write(Utils.to_yaml(idea_config))

    def read_modules_from_files(self, directory: str = None) -> List[Dict]:
        if directory is not None:
            cluster_config_dir = directory
        else:
            cluster_config_dir = self.get_cluster_config_dir()
        idea_config_file = os.path.join(cluster_config_dir, 'idea.yml')
        with open(idea_config_file, 'r') as f:
            idea_config = Utils.from_yaml(f.read())
        modules = idea_config['modules']
        return modules

    def read_config_from_files(self, config_dir: Optional[str] = None) -> Dict:
        """
        read config files (settings.yml) from local file system and return as Dict
        :param config_dir: path to the `config` directory that contains `idea.yml`
        :return: cluster configuration as Dict
        """

        if Utils.is_not_empty(config_dir):
            cluster_config_dir = config_dir
        else:
            cluster_config_dir = self.get_cluster_config_dir()

        config = {}

        idea_config_file = os.path.join(cluster_config_dir, 'idea.yml')
        with open(idea_config_file, 'r') as f:
            idea_config = Utils.from_yaml(f.read())

        modules = idea_config['modules']
        for module in modules:
            module_id = module['id']

            config_files = module['config_files']
            module_settings = {}
            for file in config_files:
                settings_file = os.path.join(cluster_config_dir, module_id, file)
                with open(settings_file, 'r') as f:
                    settings = Utils.from_yaml(f.read())
                module_settings = {**module_settings, **settings}

            config[module_id] = module_settings

        return config

    def traverse_config(self, config_entries: List[Dict], prefix: str, config: Dict, filter_key_prefix: str = None):
        for key in config:

            if '.' in key or ':' in key:
                raise exceptions.general_exception(f'Config key name: {key} under: {prefix} cannot contain a dot(.), colon(:) or comma(,)')

            value = Utils.get_any_value(key, config)

            if Utils.is_not_empty(prefix):
                path_prefix = f'{prefix}.{key}'
            else:
                path_prefix = key

            if isinstance(value, dict):

                self.traverse_config(config_entries, path_prefix, value, filter_key_prefix)

            else:
                if Utils.is_not_empty(filter_key_prefix):
                    if not path_prefix.startswith(filter_key_prefix):
                        continue

                config_entries.append({
                    'key': path_prefix,
                    'value': value
                })

    def convert_config_to_key_value_pairs(self, key_prefix: str, path: str = None) -> List[Dict]:
        config = self.read_config_from_files(path)
        config_entries = []
        self.traverse_config(config_entries, '', config, filter_key_prefix=key_prefix)
        return config_entries

    def get_config_local(self, path: str = None):
        if path is not None:
            config_entries = self.convert_config_to_key_value_pairs('', path)
        else:
            config_entries = self.convert_config_to_key_value_pairs('')
        return config_entries
