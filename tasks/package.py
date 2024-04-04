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
from tasks.tools.package_tool import PackageTool
from tasks.tools.infra_ami_package_tool import InfraAmiPackageTool

from invoke import task, Context
import os
import shutil

@task
def administrator(c):
    # type: (Context) -> None
    """
    package administrator
    """

    # requirements for administrator app need to be handled a bit differently
    # as administrator app needs to be supported on Windows too.
    # sanic - the web server component used to serve HTTP traffic uses uvloop for faster performance
    # uvloop is not available on windows, so we remove the uvloop from requirements and create
    # a separate requirements file for windows
    def requirements_handler(tool: PackageTool):

        requirements_file = tool.find_requirements_file()

        # linux/mac
        admin_requirements_txt_dest = os.path.join(tool.output_dir, 'requirements.txt')
        shutil.copyfile(requirements_file, admin_requirements_txt_dest)

        # windows
        admin_requirements_txt_windows = []
        with open(requirements_file, 'r') as f:
            lines = f.readlines()
            for line in lines:
                # skip uvloop as it is not supported on windows
                if line.startswith('uvloop=='):
                    continue
                admin_requirements_txt_windows.append(line)
        admin_requirements_txt_dest_windows = os.path.join(tool.output_dir, 'requirements-windows.txt')
        with open(admin_requirements_txt_dest_windows, 'w') as f:
            f.write(''.join(admin_requirements_txt_windows))

    package_tool = PackageTool(c, 'idea-administrator', requirements_handler=requirements_handler)
    package_tool.package()
    idea.console.success(f'distribution created: {package_tool.output_archive_name}')


@task
def cluster_manager(c):
    # type: (Context) -> None
    """
    package cluster manager
    """
    package_tool = PackageTool(c, 'idea-cluster-manager')
    package_tool.package()
    idea.console.success(f'distribution created: {package_tool.output_archive_name}')


@task
def virtual_desktop_controller(c):
    # type: (Context) -> None
    """
    package virtual desktop controller
    """
    package_tool = PackageTool(c, 'idea-virtual-desktop-controller')
    package_tool.package()
    idea.console.success(f'distribution created: {package_tool.output_archive_name}')

    package_tool = PackageTool(c, 'idea-dcv-connection-gateway')
    package_tool.package()
    idea.console.success(f'distribution created: {package_tool.output_archive_name}')

@task(name='infra_ami_deps')
def package_infra_ami_dependencies(c):
    """
    package infrastructure ami dependencies
    """
    package_tool = InfraAmiPackageTool(c)
    package_tool.package()
    idea.console.success(f'distribution created: {package_tool.output_archive_name}')

@task
def make_all_archive(c):
    # type: (Context) -> None
    """
    build an all archive containing all package archived
    """
    idea_release_version = idea.props.idea_release_version
    all_archive_basename = f'all-{idea_release_version}'
    all_archive_dir = os.path.join(idea.props.project_dist_dir, all_archive_basename)
    shutil.rmtree(all_archive_dir, ignore_errors=True)
    os.makedirs(all_archive_dir, exist_ok=True)

    def copy_archive(archive_src):
        archive_dest = os.path.join(all_archive_dir, os.path.basename(archive_src))
        shutil.copy(archive_src, archive_dest)

    archives = []
    files = os.listdir(idea.props.project_dist_dir)
    for file in files:
        file_path = os.path.join(idea.props.project_dist_dir, file)
        if os.path.isdir(file_path):
            continue
        if idea_release_version not in file:
            continue
        if not file.endswith('tar.gz'):
            continue
        archives.append(file_path)

    for archive in archives:
        copy_archive(archive)

    shutil.make_archive(all_archive_dir, 'gztar', all_archive_dir)


@task(name='all', default=True)
def package_all(c):
    # type: (Context) -> None
    """
    package all components
    """

    idea.console.print_header_block('begin: package all', style='main')

    administrator(c)

    cluster_manager(c)

    virtual_desktop_controller(c)

    # all archive
    make_all_archive(c)

    #infra ami dependencies
    package_infra_ami_dependencies(c)

    print()
    idea.console.print_header_block('end: package all', style='main')
