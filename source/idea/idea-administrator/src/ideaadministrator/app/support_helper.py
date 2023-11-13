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
from ideasdk.context import SocaCliContext
from ideasdk.utils import Utils
from ideasdk.config.cluster_config import ClusterConfig
from ideadatamodel import (
    exceptions, errorcodes,
    SocaUserInputParamMetadata,
    SocaUserInputParamType,
    SocaUserInputValidate,
    SocaUserInputChoice
)

from typing import Dict
import os
import shutil
import arrow

PKG_CONTENTS_DEPLOYMENT_LOGS = 'deployment-logs'
PKG_CONTENTS_DEPLOYMENTS_DIR = 'deployments-dir'
PKG_CONTENTS_CDK_CONFIG = 'cdk-config'
PKG_CONTENTS_CONFIG_VALUES_FILE = 'config-values-file'
PKG_CONTENTS_CLUSTER_CONFIG_DB = 'cluster-config-db'
PKG_CONTENTS_CLUSTER_CONFIG_LOCAL = 'cluster-config-local'


class SupportHelper:
    """
    Support Helper
    helper class to orchestrate support related commands, starting with support package for deployment.
    will be extended further to implement/export support packages for individual modules using SSM + S3
    """

    def __init__(self, cluster_name: str, aws_region: str, aws_profile: str, module_set: str):
        self.cluster_name = cluster_name
        self.aws_region = aws_region
        self.aws_profile = aws_profile
        self.module_set = module_set
        self.context = SocaCliContext()

    def get_deployment_debug_user_input(self) -> Dict:

        result = self.context.ask(
            title='Engineering Studio Deployment Support',
            description='Use deployment support to gather all applicable artifacts to build a support package (zip file) to be sent to Engineering Studio Support team.',
            questions=[
                SocaUserInputParamMetadata(
                    name='package_contents',
                    title='Package Contents',
                    description='Select applicable artifacts to be added to support package',
                    data_type='str',
                    param_type=SocaUserInputParamType.CHECKBOX,
                    multiple=True,
                    default=[
                        PKG_CONTENTS_DEPLOYMENT_LOGS,
                        PKG_CONTENTS_CONFIG_VALUES_FILE,
                        PKG_CONTENTS_CLUSTER_CONFIG_DB,
                        PKG_CONTENTS_CLUSTER_CONFIG_LOCAL
                        # PKG_CONTENTS_DEPLOYMENTS_DIR is not added by design. contents can get a bit large.
                        # after @madbajaj completes P70264990, this can be added.
                    ],
                    choices=[
                        SocaUserInputChoice(title='Deployment Logs', value=PKG_CONTENTS_DEPLOYMENT_LOGS),
                        SocaUserInputChoice(title='Configuration (values.yml)', value=PKG_CONTENTS_CONFIG_VALUES_FILE),
                        SocaUserInputChoice(title='Cluster Configuration (DB)', value=PKG_CONTENTS_CLUSTER_CONFIG_DB),
                        SocaUserInputChoice(title='Cluster Configuration (Local)', value=PKG_CONTENTS_CLUSTER_CONFIG_LOCAL),
                        SocaUserInputChoice(title='Bootstrap Packages', value=PKG_CONTENTS_DEPLOYMENTS_DIR)
                    ],
                    validate=SocaUserInputValidate(
                        required=True
                    )
                )
            ])
        return result

    def get_deployment_debug_package_dir(self) -> str:
        support_dir = ideaadministrator.props.cluster_support_dir(cluster_name=self.cluster_name, aws_region=self.aws_region)
        support_package_dir = os.path.join(support_dir, f'idea-deployment-debug-pkg-{Utils.file_system_friendly_timestamp()}')
        os.makedirs(support_package_dir, exist_ok=True)
        return support_package_dir

    def add_deployment_logs(self, target_dir: str):
        logs_dir = ideaadministrator.props.cluster_logs_dir(self.cluster_name, self.aws_region)
        self.context.info(f'copying deployment logs: {logs_dir} ...')
        shutil.copytree(logs_dir, os.path.join(target_dir, 'logs'))

    def add_cdk_config_dir(self, target_dir: str):
        cdk_dir = ideaadministrator.props.cluster_cdk_dir(self.cluster_name, self.aws_region)
        self.context.info(f'copying cdk config: {cdk_dir} ...')
        shutil.copytree(cdk_dir, os.path.join(target_dir, '_cdk'))

    def add_deployments_dir(self, target_dir: str):
        deployments_dir = ideaadministrator.props.cluster_deployments_dir(self.cluster_name, self.aws_region)
        self.context.info(f'copying deployments: {deployments_dir} ...')
        shutil.copytree(deployments_dir, os.path.join(target_dir, 'deployments'))

    def add_values_file(self, target_dir: str):
        values_file = ideaadministrator.props.values_file(self.cluster_name, self.aws_region)
        if not Utils.is_file(values_file):
            return
        self.context.info(f'copying values.yml: {values_file} ...')
        shutil.copy(values_file, target_dir)

    def add_cluster_config_local(self, target_dir: str):
        config_dir = ideaadministrator.props.cluster_config_dir(self.cluster_name, self.aws_region)
        if not Utils.is_dir(config_dir):
            return
        self.context.info(f'copying cluster config (local): {config_dir} ...')
        shutil.copytree(config_dir, os.path.join(target_dir, 'config_local'))

    def add_cluster_config_db(self, target_dir: str):
        try:
            cluster_config = ClusterConfig(
                cluster_name=self.cluster_name,
                aws_region=self.aws_region,
                aws_profile=self.aws_profile,
                module_set=self.module_set
            )
        except exceptions.SocaException as e:
            if e.error_code == errorcodes.CLUSTER_CONFIG_NOT_INITIALIZED:
                return
            else:
                raise e

        config_db_dir = os.path.join(target_dir, 'config_db')
        os.makedirs(config_db_dir, exist_ok=True)

        config_db_file = os.path.join(config_db_dir, 'config.yml')
        self.context.info(f'copying cluster config from db: {config_db_file} ...')
        with open(config_db_file, 'w') as f:
            f.write(cluster_config.as_yaml())

        modules_db_file = os.path.join(config_db_dir, 'modules.yml')
        self.context.info(f'copying modules from db: {modules_db_file} ...')
        cluster_modules = cluster_config.db.get_cluster_modules()
        with open(modules_db_file, 'w') as f:
            f.write(Utils.to_yaml(cluster_modules))

    def build_deployment_debug_package(self, user_input: Dict) -> str:

        package_dir = self.get_deployment_debug_package_dir()

        with open(os.path.join(package_dir, 'package.yml'), 'w') as f:
            package_data = {
                'type': 'deployment-debug',
                'created_on': arrow.utcnow().format(),
                'options': user_input
            }
            f.write(Utils.to_yaml(package_data))

        self.context.info(f'building debug package: {package_dir} ...')
        package_contents = Utils.get_value_as_list('package_contents', user_input, [])

        if PKG_CONTENTS_DEPLOYMENT_LOGS in package_contents:
            self.add_deployment_logs(package_dir)
        if PKG_CONTENTS_CDK_CONFIG in package_contents:
            self.add_cdk_config_dir(package_dir)
        if PKG_CONTENTS_DEPLOYMENTS_DIR in package_contents:
            self.add_deployments_dir(package_dir)
        if PKG_CONTENTS_CONFIG_VALUES_FILE in package_contents:
            self.add_values_file(package_dir)
        if PKG_CONTENTS_CLUSTER_CONFIG_LOCAL in package_contents:
            self.add_cluster_config_local(package_dir)
        if PKG_CONTENTS_CLUSTER_CONFIG_DB in package_contents:
            self.add_cluster_config_db(package_dir)

        shutil.make_archive(package_dir, 'zip', package_dir)
        return f'{package_dir}.zip'

    def invoke(self):
        # ask for user input for applicable package components
        user_input = self.get_deployment_debug_user_input()

        # build package based on user input
        with self.context.spinner('building debug package ...'):
            package_file = self.build_deployment_debug_package(user_input=user_input)

        # print support information template
        self.context.new_line()
        self.context.print_rule('IDEA Support')
        self.context.new_line()
        self.context.print_title('Step 1) Upload the below package (zip file) to a secured location accessible by Engineering Studio support team.')
        self.context.info(f'Debug Package: {package_file}')
        self.context.new_line()
        self.context.print_title('Step 2) Send an email to idea-support@amazon.com with below details')
        self.context.info('* Subject: [Deployment] {short description of your problem}')
        self.context.info('* Description: {Describe your use-case and the problem}')
        self.context.info('* Debug Package Download Link: {package download link}')
        self.context.info('* Full Name: ')
        self.context.info('* Email: ')
        self.context.info('* Company Name: ')
        self.context.info('* City: ')
        self.context.info('* Country: ')
        self.context.info('* AWS Business Development or AWS Partner Network SA Contact: ')
        self.context.new_line()
        self.context.print_rule()
