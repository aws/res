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
from typing import Dict
from ideatestutils import IdeaTestProps
import os

test_props = IdeaTestProps()

DEFAULT_MOCK_CLUSTER_NAME = 'idea-mock'


class MockConfig:

    def get_config(self, template: str = 'default', cluster_name: str = DEFAULT_MOCK_CLUSTER_NAME) -> Dict:
        env = Jinja2Utils.env_using_package_loader(
            package_name='ideatestutils.config',
            package_path='templates'
        )
        template = env.get_template(f'{template}.yml')

        if Utils.is_empty(cluster_name):
            cluster_name = DEFAULT_MOCK_CLUSTER_NAME

        tests_dir = test_props.get_test_dir(cluster_name)
        internal_mount_dir = os.path.join(tests_dir, 'internal')
        home_mount_dir = os.path.join(tests_dir, 'home')
        cluster_home_dir = os.path.join(internal_mount_dir, cluster_name)

        content = template.render(context={
            'cluster_name': cluster_name,
            'cluster_home_dir': cluster_home_dir,
            'internal_mount_dir': internal_mount_dir,
            'home_mount_dir': home_mount_dir
        })
        return Utils.from_yaml(content)
