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

from ideasdk.utils import Utils

import os
import shutil
from typing import List
from pathlib import Path


@task()
def update_version(c, version):
    # type: (Context, str) -> None
    """
    update idea release version in all applicable places
    """
    old_version = idea.props.idea_release_version
    if version is not None and len(version.strip()) > 0:
        print(f'updating RES_VERSION.txt with version: {version}')
        with open(os.path.join(idea.props.project_root_dir, 'RES_VERSION.txt'), 'w') as f:
            f.write(version)

        print(f'updating res-admin.sh with version: {version}')
        idea_admin_sh = os.path.join(idea.props.project_root_dir, 'res-admin.sh')
        with open(idea_admin_sh, 'r') as f:
            content = f.read()
            replace_old = f'IDEA_REVISION=${{IDEA_REVISION:-"v{old_version}"}}'
            replace_new = f'IDEA_REVISION=${{IDEA_REVISION:-"v{version}"}}'
            content = content.replace(replace_old, replace_new)
        with open(idea_admin_sh, 'w') as f:
            f.write(content)

        print(f'updating res_admin-windows.ps1 with version: {version}')
        idea_admin_ps1 = os.path.join(idea.props.project_root_dir, 'res-admin-windows.ps1')
        with open(idea_admin_ps1, 'r') as f:
            content = f.read()
            replace_old = f'$IDEARevision = if ($Env:IDEA_REVISION) {{$Env:IDEA_REVISION}} else {{"v{old_version}"}}'
            replace_new = f'$IDEARevision = if ($Env:IDEA_REVISION) {{$Env:IDEA_REVISION}} else {{"v{version}"}}'
            content = content.replace(replace_old, replace_new)
        with open(idea_admin_ps1, 'w') as f:
            f.write(content)
