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

from ideadatamodel import Project, GetProjectRequest, GetProjectResult
from ideasdk.utils import Utils, Jinja2Utils

from typing import List


class MockProjects:

    @staticmethod
    def get_project_by_template(template: str = 'default') -> Project:
        env = Jinja2Utils.env_using_package_loader(
            package_name='ideatestutils.projects',
            package_path='templates'
        )
        template = env.get_template(f'{template}.json')
        content = template.render()
        return Project(**Utils.from_json(content))

    def get_project(self, _: GetProjectRequest) -> GetProjectResult:
        project = MockProjects.get_project_by_template()
        return GetProjectResult(
            project=project
        )

    def get_user_projects(self, _: str) -> List[Project]:
        project = MockProjects.get_project_by_template()
        return [
            project
        ]
