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
from tasks.tools.open_api_tool import OpenAPITool
from ideasdk.utils import Utils
from ideadatamodel import IdeaOpenAPISpecEntry, constants

from invoke import task, Context
import os
from typing import List
from pathlib import Path


def _build_output(module: str, api_doc_file: str, spec_entries: List[IdeaOpenAPISpecEntry], enable_file_transfer_entries: bool = False, server_url: str = None, output_file: str = None):
    with open(api_doc_file, 'r') as f:
        api_doc = Utils.from_yaml(f.read())

    tool = OpenAPITool(
        api_doc=api_doc,
        entries=spec_entries,
        server_url=server_url,
        module_version=idea.props.idea_release_version,
        enable_file_transfer_entries=enable_file_transfer_entries
    )

    output_format = 'json' if output_file is not None and output_file.endswith('.json') else 'yaml'
    idea.console.print_header_block(f'Building OpenAPI Spec for module: {module}')

    spec_content = tool.generate(output_format=output_format)

    if output_file is not None:
        output_file_parent = Path(output_file).parent
        if not output_file_parent.is_dir():
            os.makedirs(output_file_parent)

        with open(output_file, 'w') as f:
            f.write(spec_content)
        idea.console.print_header_block(f'OpenAPI spec for module: {module} wrote to: {output_file}', style='success')
    else:
        print(spec_content)


@task
def cluster_manager(_, output_file=None, server_url=None):
    # type: (Context, str, str) -> None
    """
    cluster-manager api spec
    """
    from ideadatamodel import (
        OPEN_API_SPEC_ENTRIES_AUTH,
        OPEN_API_SPEC_ENTRIES_EMAIL_TEMPLATES,
        OPEN_API_SPEC_ENTRIES_PROJECTS,
        OPEN_API_SPEC_ENTRIES_CLUSTER_SETTINGS,
        OPEN_API_SPEC_ENTRIES_FILE_BROWSER,
        OPEN_API_SPEC_ENTRIES_FILESYSTEM,
        OPEN_API_SPEC_ENTRIES_SNAPSHOTS
    )

    spec_entries = []
    spec_entries += OPEN_API_SPEC_ENTRIES_AUTH
    spec_entries += OPEN_API_SPEC_ENTRIES_EMAIL_TEMPLATES
    spec_entries += OPEN_API_SPEC_ENTRIES_PROJECTS
    spec_entries += OPEN_API_SPEC_ENTRIES_FILESYSTEM
    spec_entries += OPEN_API_SPEC_ENTRIES_CLUSTER_SETTINGS
    spec_entries += OPEN_API_SPEC_ENTRIES_FILE_BROWSER
    spec_entries += OPEN_API_SPEC_ENTRIES_SNAPSHOTS

    api_doc_file = os.path.join(idea.props.cluster_manager_project_dir, 'resources', 'api', 'api_doc.yml')

    _build_output(
        module=constants.MODULE_CLUSTER_MANAGER,
        api_doc_file=api_doc_file,
        spec_entries=spec_entries,
        server_url=server_url,
        output_file=output_file,
        enable_file_transfer_entries=True
    )


@task
def virtual_desktop_controller(_, output_file=None, server_url=None):
    # type: (Context, str, str) -> None
    """
    virtual desktop controller api spec
    """
    from ideadatamodel import OPEN_API_SPEC_ENTRIES_VIRTUAL_DESKTOP

    spec_entries = OPEN_API_SPEC_ENTRIES_VIRTUAL_DESKTOP

    api_doc_file = os.path.join(idea.props.virtual_desktop_project_dir, 'resources', 'api', 'api_doc.yml')

    _build_output(
        module=constants.MODULE_VIRTUAL_DESKTOP_CONTROLLER,
        api_doc_file=api_doc_file,
        spec_entries=spec_entries,
        server_url=server_url,
        output_file=output_file
    )


@task
def scheduler(_, output_file=None, server_url=None):
    # type: (Context, str, str) -> None
    """
    scheduler api spec
    """
    from ideadatamodel import OPEN_API_SPEC_ENTRIES_SCHEDULER

    spec_entries = OPEN_API_SPEC_ENTRIES_SCHEDULER

    api_doc_file = os.path.join(idea.props.scheduler_project_dir, 'resources', 'api', 'api_doc.yml')

    _build_output(
        module=constants.MODULE_SCHEDULER,
        api_doc_file=api_doc_file,
        spec_entries=spec_entries,
        server_url=server_url,
        output_file=output_file
    )


@task(name='all', default=True)
def build_all(c, target_dir=None):
    # type: (Context, str) -> None
    """
    build OpenAPI 3.0 spec for all modules
    """
    idea.console.info('building api spec for cluster-manager ...')
    cluster_manager(c, output_file=f'{os.path.join(target_dir, "cluster-manager.openapi.yml")}' if target_dir else None)

    idea.console.info('building api spec for virtual-desktop-controller ...')
    virtual_desktop_controller(c, output_file=f'{os.path.join(target_dir, "virtual-desktop-controller.openapi.yml")}' if target_dir else None)

    idea.console.info('building api spec for scheduler ...')
    scheduler(c, output_file=f'{os.path.join(target_dir, "scheduler.openapi.yml")}' if target_dir else None)

    idea.console.success('api specs built successfully')
