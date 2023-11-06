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

from ideasdk.utils import EnvironmentUtils
import os


class ClusterManagerUtils:

    @staticmethod
    def get_app_deploy_dir() -> str:
        app_deploy_dir = EnvironmentUtils.idea_app_deploy_dir(required=True)
        return os.path.join(app_deploy_dir, 'cluster-manager')

    @staticmethod
    def get_email_template_defaults_file() -> str:
        return os.path.join(ClusterManagerUtils.get_app_deploy_dir(), 'resources', 'defaults', 'email_templates.yml')
