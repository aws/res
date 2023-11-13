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
from tasks.tools.build_tool import BuildTool
from tasks.apispec import (
    cluster_manager as apispec_cluster_manager,
    virtual_desktop_controller as apispec_virtual_desktop_controller
)

from invoke import task, Context
import os
import shutil


@task
def data_model(c):
    """
    build data-model
    """
    BuildTool(c, 'idea-data-model').build()


@task
def sdk(c):
    # type: (Context) -> None
    """
    build sdk
    """
    BuildTool(c, 'idea-sdk').build()


@task
def administrator(c):
    # type: (Context) -> None
    """
    build administrator
    """
    BuildTool(c, 'idea-administrator').build()


@task
def cluster_manager(c):
    # type: (Context) -> None
    """
    build cluster manager
    """
    tool = BuildTool(c, 'idea-cluster-manager')
    tool.build()
    apispec_cluster_manager(c, output_file=os.path.join(tool.output_dir, 'resources', 'api', 'openapi.yml'))


def dcv_connection_gateway(c):
    # type: (Context) -> None
    """
    build dcv connection gateway
    """
    tool = BuildTool(c, 'idea-dcv-connection-gateway')
    output_dir = tool.output_dir
    shutil.rmtree(output_dir, ignore_errors=True)
    os.makedirs(output_dir, exist_ok=True)
    shutil.copytree(idea.props.dcv_connection_gateway_dir, os.path.join(tool.output_dir, 'static_resources'))


@task
def virtual_desktop_controller(c):
    # type: (Context) -> None
    """
    build virtual desktop controller
    """
    tool = BuildTool(c, 'idea-virtual-desktop-controller')
    tool.build()
    apispec_virtual_desktop_controller(c, output_file=os.path.join(tool.output_dir, 'resources', 'api', 'openapi.yml'))
    dcv_connection_gateway(c)


@task(name='all', default=True)
def build_all(c):
    # type: (Context) -> None
    """
    build all
    """

    idea.console.print_header_block('begin: build all', style='main')

    data_model(c)

    sdk(c)

    administrator(c)

    cluster_manager(c)

    virtual_desktop_controller(c)

    idea.console.print_header_block('end: build all', style='main')
