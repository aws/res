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
from ideadatamodel import constants, exceptions, SocaAnyPayload
from ideasdk.config.cluster_config import ClusterConfig
from ideasdk.context.arn_builder import ArnBuilder

import ideaadministrator
from ideaadministrator import app_constants

from typing import Optional, List, Tuple, Dict
import requests
import requests.exceptions
import os
import shutil
import yaml.parser


class AdministratorUtils:

    @staticmethod
    def detect_client_ip() -> Optional[str]:
        """
        Try to determine the IPv4 of the customer.
        If IP cannot be determined we will prompt the user to enter the value manually
        :return: IP Address or None
        """
        try:
            requests.packages.urllib3.util.connection.HAS_IPV6 = False # noqa
            http_result = requests.get('https://checkip.amazonaws.com/', timeout=15)
            if http_result.status_code != 200:
                return None

            ip_address = str(http_result.text).strip()
            return f'{ip_address}/32'

        except requests.exceptions.RequestException as e:
            raise e

    @staticmethod
    def sanitize_cluster_name(value: Optional[str]) -> str:
        if Utils.is_empty(value):
            return ''
        token = value.strip().lower()
        if token.startswith(app_constants.CLUSTER_NAME_PREFIX):
            token = token.replace(app_constants.CLUSTER_NAME_PREFIX, '')
        if Utils.is_empty(token):
            return ''
        return f'{app_constants.CLUSTER_NAME_PREFIX}{token}'

    @staticmethod
    def get_ssh_connection_string(os_: str, ip_address: str, keypair_name: str) -> Optional[str]:
        # todo - need to check if on windows, .exe or something else needs to be handled
        user = AdministratorUtils.get_ec2_username(os_)
        keypair_path = f'~/.ssh/{keypair_name}.pem'
        return str(f'ssh '
                   f'-i {keypair_path} '
                   f'{user}@{ip_address}')

    @staticmethod
    def get_ec2_username(os_: str) -> str:
        return 'ec2-user'

    @staticmethod
    def get_session_manager_url(aws_partition: str, aws_region: str, instance_id: str) -> str:
        # todo - implement this for other partitions (aws-iso, aws-iso-b)

        # console_prefix - comes before 'console' in the URI - including the '.'
        # console_suffix - comes after 'console' in the URI - including '.'
        console_prefix = ''
        console_suffix = '.aws.amazon.com'

        if aws_partition == 'aws-cn':
            console_prefix = ''
            console_suffix = '.amazonaws.cn'
        elif aws_partition == 'aws-us-gov':
            console_prefix = ''
            console_suffix = '.amazonaws-us-gov.com'
        else:
            console_prefix = f'{aws_region}.'
            console_suffix = '.aws.amazon.com'

        return str(f'https://{console_prefix}console{console_suffix}'
                   f'/systems-manager/session-manager'
                   f'/{instance_id}?region={aws_region}')

    @staticmethod
    def get_package_build_dir() -> str:
        if ideaadministrator.props.is_dev_mode():
            return ideaadministrator.props.dev_mode_project_build_dir
        else:
            return ideaadministrator.props.soca_build_dir

    @staticmethod
    def get_package_dist_dir() -> str:
        if ideaadministrator.props.is_dev_mode():
            return ideaadministrator.props.dev_mode_project_dist_dir
        else:
            return ideaadministrator.props.soca_downloads_dir

    @staticmethod
    def get_packages_to_upload() -> List[str]:
        """
        if RES_DEV_MODE=true, find packages from dist dir
        else, find packages in ~/.idea/downloads to be uploaded
        :return:
        """

        package_dist_dir = AdministratorUtils.get_package_dist_dir()

        packages_to_upload = []

        files = os.listdir(package_dist_dir)
        for file in files:
            if not file.endswith('tar.gz'):
                continue
            if 'docs' in file:
                continue
            if file.startswith('idea-administrator'):
                continue
            if file.startswith('all-'):
                continue
            if ideaadministrator.props.current_release_version not in file:
                continue
            packages_to_upload.append(os.path.join(package_dist_dir, file))

        return packages_to_upload

    @staticmethod
    def cluster_region_dir_exists_and_has_config(directory: str) -> bool:
        """
        check if cluster region dir has applicable configuration files/folders
        :param directory: path to cluster region dir
        :return:
        """
        if not os.path.isdir(directory):
            return False

        config_dir = os.path.join(directory, 'config')
        if Utils.is_dir(config_dir):
            return True

        values_file = os.path.join(directory, 'values.yml')
        if Utils.is_file(values_file):
            return True

        return False

    @staticmethod
    def cleanup_cluster_region_dir(directory: str, preserve_values_file: bool = False, scope: Tuple[str] = ('config', 'values.yml')):
        """
        Delete config generation related files and directories if the directory already exists and is not empty
        :param directory:
        :param preserve_values_file:
        :param scope: defaults to config/ and values.yml
        :return:
        """
        if not os.path.isdir(directory):
            raise exceptions.file_not_found(f'{directory} not found')

        files = os.listdir(directory)
        for file_name in files:
            if file_name not in scope:
                continue

            file_path = os.path.join(directory, file_name)
            if os.path.isdir(file_path):
                shutil.rmtree(file_path)
            elif os.path.isfile(file_path):
                if preserve_values_file:
                    continue
                os.remove(file_path)

    @staticmethod
    def render_policy(policy_template_name: str,
                      cluster_name: str,
                      module_id: str,
                      config: ClusterConfig,
                      vars: SocaAnyPayload = None) -> Dict: # noqa
        env = Jinja2Utils.env_using_file_system_loader(search_path=ideaadministrator.props.policy_templates_dir)
        policy_template = env.get_template(policy_template_name)

        if vars is None:
            vars = SocaAnyPayload() # noqa

        policy_content = policy_template.render(context={
            'cluster_name': cluster_name,
            'module_id': module_id,
            'aws_region': config.get_string('cluster.aws.region', required=True),
            'aws_dns_suffix': config.get_string('cluster.aws.dns_suffix', required=True),
            'aws_partition': config.get_string('cluster.aws.partition', required=True),
            'aws_account_id': config.get_string('cluster.aws.account_id', required=True),
            'config': config,
            'arns': ArnBuilder(config=config),
            'vars': vars,
            'utils': Utils
        })

        try:
            return Utils.from_yaml(policy_content)
        except yaml.parser.ParserError as e:
            lines = policy_content.splitlines()
            numbered_lines = []
            for index, line in enumerate(lines):
                numbered_lines.append('{:>5}: {}'.format(str(index+1), line))
            print(f'failed to decode policy json: {policy_template_name} - {e}. Content: {os.linesep}{os.linesep.join(numbered_lines)}')
            raise e
