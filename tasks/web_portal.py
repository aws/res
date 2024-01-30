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

import tasks.idea as idea
from tasks.tools.typings_generator import TypingsGenerator
from ideasdk.utils import Utils

from invoke import task, Context
import os


@task
def serve(c):
    # type: (Context) -> None
    """
    serve web-portal frontend app in web-browser
    """
    with c.cd(idea.props.cluster_manager_webapp_dir):
        c.run('yarn serve')


@task
def typings(c):
    # type: (Context) -> None
    """
    convert idea python models to typescript
    """

    converter = TypingsGenerator()

    files = []

    project_root = idea.props.project_root_dir

    def add_model(module: str):
        prefix = 'source/idea/idea-data-model/src/ideadatamodel'

        model_file = f'{prefix}/{module}/{module}_model.py'
        api_file = f'{prefix}/{module}/{module}_api.py'

        if Utils.is_file(os.path.join(project_root, *model_file.split('/'))):
            files.append(model_file)

        if Utils.is_file(os.path.join(project_root, *api_file.split('/'))):
            files.append(api_file)

    add_model('user_input')
    add_model('auth')
    add_model('filesystem')
    add_model('virtual_desktop')
    add_model('cluster_settings')
    add_model('projects')
    add_model('app')
    add_model('email_templates')
    add_model('notifications')

    # prefix with project root and make platform-agnostic for linux, mac, windows support
    modules = []
    for file in files:
        tokens = file.split('/')
        modules.append(os.path.join(project_root, *tokens))

    target = os.path.join(project_root, *('source/idea/idea-cluster-manager/webapp/src/client/data-model.ts'.split('/')))

    converter.generate_typescript_defs(modules, target, exclude={'IdeaOpenAPISpecEntry'})
