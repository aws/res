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

import os


class EnvironmentUtils:

    @staticmethod
    def get_environment_variable(key, required=False, default=None):
        if required:
            if key not in os.environ:
                raise Exception(f'Environment variable: {key} not found')
        if key not in os.environ:
            return default
        return os.environ[key]

    @staticmethod
    def idea_dev_mode(required=False, default=None):
        return EnvironmentUtils.get_environment_variable(
            key='RES_DEV_MODE',
            required=required,
            default=default
        )

    @staticmethod
    def idea_cluster_name(required=False, default=None):
        return EnvironmentUtils.get_environment_variable(
            key='IDEA_CLUSTER_NAME',
            required=required,
            default=default
        )

    @staticmethod
    def idea_cluster_home(required=False, default=None):
        return EnvironmentUtils.get_environment_variable(
            key='IDEA_CLUSTER_HOME',
            required=required,
            default=default
        )

    @staticmethod
    def idea_module_name(required=False, default=None):
        return EnvironmentUtils.get_environment_variable(
            key='IDEA_MODULE_NAME',
            required=required,
            default=default
        )

    @staticmethod
    def idea_module_id(required=False, default=None):
        return EnvironmentUtils.get_environment_variable(
            key='IDEA_MODULE_ID',
            required=required,
            default=default
        )

    @staticmethod
    def idea_module_set(required=False, default=None):
        return EnvironmentUtils.get_environment_variable(
            key='IDEA_MODULE_SET',
            required=required,
            default=default
        )

    @staticmethod
    def idea_app_deploy_dir(required=False, default=None):
        return EnvironmentUtils.get_environment_variable(
            key='IDEA_APP_DEPLOY_DIR',
            required=required,
            default=default
        )

    @staticmethod
    def aws_default_region(required=False, default=None):
        return EnvironmentUtils.get_environment_variable(
            key='AWS_DEFAULT_REGION',
            required=required,
            default=default
        )

    @staticmethod
    def res_test_mode(required=False, default=None):
        return EnvironmentUtils.get_environment_variable(
            key='RES_TEST_MODE',
            required=required,
            default=default
        )
