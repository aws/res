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
from tasks.tools.clean_tool import CleanTool

from invoke import task, Context


@task
def data_model(c):
    """
    clean data-model
    """
    CleanTool(c, 'idea-data-model').clean()


@task
def sdk(c):
    # type: (Context) -> None
    """
    clean sdk
    """
    CleanTool(c, 'idea-sdk').clean()


@task
def administrator(c):
    # type: (Context) -> None
    """
    clean administrator
    """
    CleanTool(c, 'idea-administrator').clean()


@task
def cluster_manager(c):
    # type: (Context) -> None
    """
    clean cluster manager
    """
    CleanTool(c, 'idea-cluster-manager').clean()


@task
def virtual_desktop_controller(c):
    # type: (Context) -> None
    """
    clean virtual desktop controller
    """
    CleanTool(c, 'idea-virtual-desktop-controller').clean()
    CleanTool(c, 'idea-dcv-connection-gateway').clean()


@task(name='all', default=True)
def clean_all(c):
    # type: (Context) -> None
    """
    clean all components
    """

    idea.console.print_header_block('begin: clean all', style='main')

    data_model(c)

    sdk(c)

    administrator(c)

    cluster_manager(c)

    virtual_desktop_controller(c)

    CleanTool(c, 'all').clean_non_project_items()

    idea.console.print_header_block('end: clean all', style='main')
