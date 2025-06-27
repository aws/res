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
import shutil

from invoke import Context, task

import tasks.idea as idea
import tasks.requirements
from tasks.apispec import cluster_manager as apispec_cluster_manager
from tasks.apispec import (
    virtual_desktop_controller as apispec_virtual_desktop_controller,
)
from tasks.tools.build_tool import BuildTool


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
def bootstrap(c):
    # type: (Context) -> None
    """
    build bootstrap
    """
    BuildTool(c, 'idea-bootstrap', skip_resources=True).build()


@task
def administrator(c):
    # type: (Context) -> None
    """
    build administrator
    """
    BuildTool(c, 'idea-administrator').build()


@task
def ad_sync(c):
    # type: (Context) -> None
    """
    build ad sync
    """
    BuildTool(c, 'ad-sync').build()


@task
def cluster_manager(c):
    # type: (Context) -> None
    """
    build cluster manager
    """
    tool = BuildTool(c, 'idea-cluster-manager')
    tool.build()
    apispec_cluster_manager(c, output_file=os.path.join(tool.output_dir, 'resources', 'api', 'openapi.yml'))

@task
def dcv_connection_gateway(c):
    # type: (Context) -> None
    """
    build dcv connection gateway
    """
    tool = BuildTool(c, 'idea-dcv-connection-gateway')
    tool.build()
    shutil.copytree(idea.props.dcv_connection_gateway_dir, os.path.join(tool.output_dir, 'resources'), ignore=shutil.ignore_patterns("src"))


@task
def virtual_desktop_controller(c):
    # type: (Context) -> None
    """
    build virtual desktop controller
    """
    tool = BuildTool(c, 'idea-virtual-desktop-controller')
    tool.build()
    apispec_virtual_desktop_controller(c, output_file=os.path.join(tool.output_dir, 'resources', 'api', 'openapi.yml'))


@task
def dcv_broker(c):
    # type: (Context) -> None
    """
    build DCV broker
    """
    BuildTool(c, 'idea-dcv-broker').build()


@task
def library(c):
    # type: (Context) -> None
    """
    build library
    """
    BuildTool(c, 'library').build()


@task
def bastion_host(c):
    # type: (Context) -> None
    """
    build bastion host
    """
    BuildTool(c, 'idea-bastion-host').build()

@task
def virtual_desktop(c):
    # type: (Context) -> None
    """
    build virtual desktop app
    """
    BuildTool(c, 'idea-virtual-desktop').build()


@task(name='all', default=True)
def build_all(c):
    # type: (Context) -> None
    """
    build all
    """

    # Prebuild environment sync
    # By default, we will update the dev environment. However, in pipeline, we will skip this step and use the version pinned
    # in the requirements/dev.txt.
    if os.environ.get('SKIP_ENV_UPDATE', 'false') != 'true':
        tasks.requirements.update(c, upgrade=True)
    tasks.requirements.sync_env(c, package_group_name='dev')

    # Real build steps
    idea.console.print_header_block('begin: build all', style='main')

    data_model(c)

    sdk(c)

    bootstrap(c)

    administrator(c)

    ad_sync(c)

    cluster_manager(c)

    dcv_connection_gateway(c)

    virtual_desktop_controller(c)

    dcv_broker(c)

    library(c)

    bastion_host(c)

    virtual_desktop(c)

    idea.console.print_header_block('end: build all', style='main')
