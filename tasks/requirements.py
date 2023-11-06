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

from invoke import task, Context

from typing import Optional
import os
import sys


def _update_requirement(c: Context, name: str, upgrade: bool = False, package_name: str = None):
    project_root = idea.props.project_root_dir

    name = name.strip().lower()

    if name.endswith('.txt'):
        name = name.replace('.txt', '')
    if '.' in name:
        name = name[:name.rfind('.')]

    in_file = f'{name}.in'
    in_file_abs_path = os.path.join(project_root, 'requirements', in_file)

    if not os.path.isfile(in_file_abs_path):
        idea.console.error(f'Requirements .in file not found: {in_file_abs_path}')
        sys.exit(1)

    cmd = 'pip-compile --no-header --no-annotate '
    if upgrade:
        cmd += '--upgrade '
    if package_name:
        cmd += f'--upgrade-package {package_name} '
    cmd += in_file_abs_path
    c.run(cmd, echo=True)

    out_file = f'{name}.txt'
    out_file_abs_path = os.path.join(project_root, 'requirements', out_file)
    idea.console.success(f'Requirements file updated: {out_file_abs_path}')


@task(optional=['name'])
def update(c, name=None, upgrade=False, package_name=None):
    # type: (Context, Optional[str], bool, str) -> None
    """
    Update python requirements using pip-compile.
    """
    if name is not None:
        _update_requirement(c, name, upgrade, package_name)
        return

    for name in ('dev',
                 'doc',
                 'tests',
                 'idea-dev-lambda',
                 'idea-administrator',
                 # 'idea-scheduler',
                 'idea-cluster-manager',
                 'idea-virtual-desktop-controller'):
        _update_requirement(c, name, upgrade, package_name)


@task(optional=['name'])
def install(c, name=None):
    # type: (Context, Optional[str]) -> None
    """
    Install python requirements
    """
    project_root = idea.props.project_root_dir

    if name is None:
        name = 'dev'

    req_txt = os.path.join(project_root, 'requirements', f'{name}.txt')
    if not os.path.isfile(req_txt):
        idea.console.error(f'Requirements .txt file not found: {req_txt}')
        sys.exit(1)

    c.run(f'pip install -r {req_txt}', echo=True)
