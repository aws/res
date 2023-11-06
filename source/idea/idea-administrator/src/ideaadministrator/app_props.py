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

from ideasdk.utils import Utils, EnvironmentUtils
from ideadatamodel import exceptions

from ideaadministrator import app_constants
import ideaadministrator_meta

from typing import Dict, Optional, List
from pathlib import Path
import os


class AdministratorProps:

    @staticmethod
    def is_dev_mode() -> bool:
        return Utils.get_as_bool(EnvironmentUtils.idea_dev_mode(), False)

    @property
    def current_release_version(self) -> str:
        return ideaadministrator_meta.__version__

    @property
    def dev_mode_admin_root_dir(self) -> str:
        script_dir = Path(os.path.abspath(__file__))
        return str(script_dir.parent.parent.parent)

    @property
    def dev_mode_admin_app_source_dir(self) -> str:
        return os.path.join(self.dev_mode_admin_root_dir, 'src')

    @property
    def dev_mode_resources_dir(self) -> str:
        return os.path.join(self.dev_mode_admin_root_dir, 'resources')

    @property
    def dev_mode_project_root_dir(self) -> str:
        script_dir = Path(os.path.abspath(__file__))
        return str(script_dir.parent.parent.parent.parent.parent.parent)

    @property
    def dev_mode_project_build_dir(self) -> str:
        return os.path.join(self.dev_mode_project_root_dir, 'build')

    @property
    def dev_mode_project_dist_dir(self) -> str:
        return os.path.join(self.dev_mode_project_root_dir, 'dist')

    @property
    def dev_mode_sdk_source_root(self) -> str:
        return os.path.join(self.dev_mode_project_root_dir, 'source', 'idea', 'idea-sdk', 'src')

    @property
    def dev_mode_bootstrap_source_dir(self) -> str:
        return os.path.join(self.dev_mode_project_root_dir, 'source', 'idea', 'idea-bootstrap')

    @property
    def dev_mode_data_model_src(self) -> str:
        return os.path.join(self.dev_mode_project_root_dir, 'source', 'idea', 'idea-data-model', 'src')

    @property
    def dev_mode_site_packages(self) -> str:
        virtual_env = EnvironmentUtils.get_environment_variable('VIRTUAL_ENV', required=True)
        return os.path.join(virtual_env, 'lib', 'python3.7', 'site-packages')

    @property
    def dev_mode_venv_bin_dir(self) -> str:
        virtual_env = EnvironmentUtils.get_environment_variable('VIRTUAL_ENV', required=True)
        return os.path.join(virtual_env, 'bin')

    @property
    def resources_dir(self) -> str:
        if self.is_dev_mode():
            return self.dev_mode_resources_dir
        else:
            return os.path.join(self.soca_admin_dir, 'resources')

    @property
    def lambda_function_commons_package_name(self) -> str:
        return 'idea_lambda_commons'

    @property
    def lambda_function_commons_dir(self) -> str:
        return os.path.join(self.lambda_functions_dir, self.lambda_function_commons_package_name)

    @property
    def lambda_functions_dir(self) -> str:
        return os.path.join(self.resources_dir, 'lambda_functions')

    @property
    def policy_templates_dir(self) -> str:
        return os.path.join(self.resources_dir, 'policies')

    @property
    def user_data_template_dir(self) -> str:
        return os.path.join(self.resources_dir, 'userdata')

    @property
    def installer_config_defaults_file(self) -> str:
        return os.path.join(self.resources_dir, app_constants.INSTALLER_CONFIG_DEFAULTS_FILE)

    @property
    def default_values_file(self) -> str:
        return os.path.join(self.resources_dir, 'config', 'values.yml')

    @property
    def install_params_file(self) -> str:
        return os.path.join(self.resources_dir, 'input_params', 'install_params.yml')

    @property
    def shared_storage_params_file(self) -> str:
        return os.path.join(self.resources_dir, 'input_params', 'shared_storage_params.yml')

    @property
    def aws_endpoints_file(self) -> str:
        return os.path.join(self.resources_dir, app_constants.AWS_ENDPOINTS_FILE)

    @property
    def cluster_default_config_dir(self) -> str:
        return os.path.join(self.resources_dir, 'config')

    @property
    def cluster_config_templates_dir(self) -> str:
        return os.path.join(self.cluster_default_config_dir, 'templates')

    @property
    def cluster_config_schema_dir(self) -> str:
        return os.path.join(self.cluster_default_config_dir, 'schema')

    @property
    def idea_user_home(self) -> str:
        return os.path.expanduser(os.path.join('~', '.idea'))

    @property
    def soca_build_dir(self) -> str:
        build_dir = os.path.join(self.idea_user_home, 'build')
        os.makedirs(build_dir, exist_ok=True)
        return build_dir

    @property
    def soca_downloads_dir(self) -> str:
        downloads_dir = os.path.join(self.idea_user_home, 'downloads')
        os.makedirs(downloads_dir, exist_ok=True)
        return downloads_dir

    @property
    def app_name(self) -> str:
        return ideaadministrator_meta.__name__

    @property
    def app_version(self) -> str:
        return ideaadministrator_meta.__version__

    @property
    def soca_admin_dir(self) -> str:
        home_dir = self.idea_user_home
        admin_dir = os.path.join(home_dir, self.app_name)
        os.makedirs(admin_dir, exist_ok=True)
        return admin_dir

    @property
    def soca_admin_logs_dir(self) -> str:
        logs_dir = os.path.join(self.idea_user_home, 'logs', self.app_name)
        if not Utils.is_dir(logs_dir):
            os.makedirs(logs_dir, exist_ok=True)
        return logs_dir

    def cluster_dir(self, cluster_name: str, create=True) -> str:
        idea_user_home = self.idea_user_home
        cluster_home = os.path.join(idea_user_home, 'clusters', cluster_name)
        if create:
            os.makedirs(cluster_home, exist_ok=True)
        return cluster_home

    @staticmethod
    def cluster_region_dir(cluster_home: str, aws_region: str, create=True) -> str:
        region_dir = os.path.join(cluster_home, aws_region)
        if create and not os.path.isdir(region_dir):
            os.makedirs(region_dir, exist_ok=True)
        return region_dir

    def values_file(self, cluster_name: str, aws_region: str, create=False) -> str:
        cluster_home = self.cluster_dir(cluster_name, create=create)
        region_dir = self.cluster_region_dir(cluster_home, aws_region, create=create)
        return os.path.join(region_dir, 'values.yml')

    def region_ami_config_file(self) -> str:
        return os.path.join(self.resources_dir, 'config', 'region_ami_config.yml')

    def region_timezone_config_file(self) -> str:
        return os.path.join(self.resources_dir, 'config', 'region_timezone_config.yml')

    def region_elb_account_id_file(self) -> str:
        return os.path.join(self.resources_dir, 'config', 'region_elb_account_id.yml')

    def cluster_cdk_dir(self, cluster_name: str, aws_region: str) -> str:
        cluster_home = self.cluster_dir(cluster_name)
        region_dir = self.cluster_region_dir(cluster_home, aws_region)
        cdk_home = os.path.join(region_dir, '_cdk')
        os.makedirs(cdk_home, exist_ok=True)
        return cdk_home

    def cluster_logs_dir(self, cluster_name: str, aws_region: str) -> str:
        cluster_home = self.cluster_dir(cluster_name)
        region_dir = self.cluster_region_dir(cluster_home, aws_region)
        logs_dir = os.path.join(region_dir, 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        return logs_dir

    def cluster_deployments_dir(self, cluster_name: str, aws_region: str) -> str:
        cluster_home = self.cluster_dir(cluster_name)
        region_dir = self.cluster_region_dir(cluster_home, aws_region)
        deployments_dir = os.path.join(region_dir, 'deployments')
        os.makedirs(deployments_dir, exist_ok=True)
        return deployments_dir

    def cluster_support_dir(self, cluster_name: str, aws_region: str) -> str:
        cluster_home = self.cluster_dir(cluster_name)
        region_dir = self.cluster_region_dir(cluster_home, aws_region)
        support_dir = os.path.join(region_dir, 'support')
        os.makedirs(support_dir, exist_ok=True)
        return support_dir

    def cluster_config_dir(self, cluster_name: str, aws_region: str) -> str:
        cluster_home = self.cluster_dir(cluster_name)
        region_dir = self.cluster_region_dir(cluster_home, aws_region)
        config_dir = os.path.join(region_dir, 'config')
        os.makedirs(config_dir, exist_ok=True)
        return config_dir

    @property
    def cdk_bin(self) -> str:
        if os.name == 'nt':
            # for windows, cdk.cmd needs to be invoked, which is located at a different place.
            cdk_bin = os.path.join(self.idea_user_home, 'lib', 'idea-cdk', 'node_modules', '.bin', 'cdk')
        else:
            cdk_bin = os.path.join(self.idea_user_home, 'lib', 'idea-cdk', 'node_modules', 'aws-cdk', 'bin', 'cdk')
        if not os.path.isfile(cdk_bin):
            raise exceptions.general_exception(f'Unable to find cdk binary at: {cdk_bin}.'
                                               f' Please ensure {self.app_name} is installed correctly or re-run installation.')
        return cdk_bin

    def get_env(self) -> Dict[str, str]:
        env = os.environ.copy()
        if not self.is_dev_mode():
            return env

        path = Utils.get_value_as_string('PATH', env)
        paths = path.split(os.pathsep)

        admin_app_sources = [
            self.dev_mode_venv_bin_dir,
            self.dev_mode_site_packages,
            self.dev_mode_data_model_src,
            self.dev_mode_sdk_source_root,
            self.dev_mode_admin_app_source_dir,
            self.dev_mode_project_root_dir
        ]

        for admin_path in admin_app_sources:
            paths.insert(0, admin_path)

        env['PATH'] = os.pathsep.join(paths)
        return env

    def get_get_cdk_app_cmd(self, config_file: str) -> str:
        """
        Returns the command to build the CDK app
        when dev_mode is true, invoke automation is used to ensure sources instead of calling idea-admin
        :return:
        """
        if self.is_dev_mode():
            return f'invoke ' \
                   f'--search-root "{self.dev_mode_project_root_dir}" ' \
                   f'cli.admin --args "cdk cdk-app --config-file {config_file}"'
        else:
            return f'res-admin cdk cdk-app --config-file "{config_file}"'

    def get_cdk_command(self, name: str, stacks: str = None, params: Optional[List[str]] = None, rollback=True) -> str:
        """
        build the cdk command. eg:
        $ cdk deploy --app "res-admin cdk-app -c user-config.json [--additional_cdk_params]
        """
        if params is None:
            params = []
        cmd = [self.cdk_bin] + name.split(' ') + params
        if name == 'deploy':
            cmd.append(f'--rollback {str(rollback).lower()}')
        if stacks is not None:
            cmd.append(stacks)
        return ' '.join(cmd)

    @staticmethod
    def use_ec2_instance_metadata_credentials() -> bool:
        """
        read an IDEA specific environment variable, indicating if administrator app is running within an ec2 instance.
        """
        aws_credential_provider = EnvironmentUtils.get_environment_variable('IDEA_ADMIN_AWS_CREDENTIAL_PROVIDER', default=None)
        if Utils.is_empty(aws_credential_provider):
            return False
        return aws_credential_provider == 'Ec2InstanceMetadata'
