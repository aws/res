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

from invoke import Context
import shutil
import os
from typing import Callable, Optional


class PackageTool:

    def __init__(self, c: Context, app_name: str, requirements_handler: Optional[Callable] = None):
        self.c = c
        self.requirements_handler = requirements_handler

        self.project_build_tool = BuildTool(c, app_name)
        self.data_model_build_tool: Optional[BuildTool] = None
        self.sdk_build_tool: Optional[BuildTool] = None

        if app_name not in {'idea-bootstrap', 'idea-dcv-connection-gateway'}:
            self.data_model_build_tool = BuildTool(c, 'idea-data-model')
            self.sdk_build_tool = BuildTool(c, 'idea-sdk')
            self.project_build_tool = BuildTool(c, app_name)

    @property
    def app_name(self) -> str:
        return self.project_build_tool.app_name

    @property
    def app_version(self) -> str:
        return self.project_build_tool.app_version

    @property
    def output_dir(self) -> str:
        return os.path.join(idea.props.project_dist_dir, self.output_archive_basename)

    @property
    def output_archive_basename(self) -> str:
        return f'{self.app_name}-{idea.props.idea_release_version}'

    @property
    def output_archive_name(self) -> str:
        return f'{self.output_archive_basename}.tar.gz'

    @property
    def output_archive_file(self) -> str:
        return os.path.join(idea.props.project_dist_dir, self.output_archive_name)

    def find_requirements_file(self) -> str:
        requirements_file = os.path.join(idea.props.requirements_dir, f'{self.app_name}.txt')
        if not os.path.isfile(requirements_file):
            raise idea.exceptions.build_failed(f'project requirements file not found: {requirements_file}')
        return requirements_file

    def clean(self):
        if os.path.isdir(self.output_dir):
            idea.console.print(f'deleting {self.output_dir} ...')
            shutil.rmtree(self.output_dir, ignore_errors=True)
        if os.path.isfile(self.output_archive_file):
            idea.console.print(f'deleting {self.output_archive_file} ...')
            os.remove(self.output_archive_file)

    def package(self, delete_output_dir=False):

        idea.console.print_header_block(f'package {self.app_name}')

        # create output dir
        output_dir = self.output_dir
        shutil.rmtree(output_dir, ignore_errors=True)
        os.makedirs(output_dir, exist_ok=True)

        if self.project_build_tool.has_src():
            # copy requirements
            idea.console.print(f'copying requirements.txt ...')
            if self.requirements_handler is not None:
                self.requirements_handler(self)
            else:
                shutil.copyfile(self.find_requirements_file(), os.path.join(output_dir, 'requirements.txt'))

        # copy sdk
        if self.sdk_build_tool is not None:
            self.sdk_build_tool.build()
            idea.console.print(f'copying sdk artifacts ...')
            for file in os.listdir(self.sdk_build_tool.output_dir):
                file_path = os.path.join(self.sdk_build_tool.output_dir, file)
                if os.path.isdir(file_path):
                    shutil.copytree(file_path, os.path.join(output_dir, file))
                else:
                    shutil.copy2(file_path, output_dir)

        # copy data-model
        if self.data_model_build_tool is not None:
            self.data_model_build_tool.build()
            idea.console.print(f'copying data-model artifacts ...')
            for file in os.listdir(self.data_model_build_tool.output_dir):
                file_path = os.path.join(self.data_model_build_tool.output_dir, file)
                if os.path.isdir(file_path):
                    shutil.copytree(file_path, os.path.join(output_dir, file))
                else:
                    shutil.copy2(file_path, output_dir)

        # copy project
        idea.console.print(f'copying {self.app_name} artifacts ...')
        for file in os.listdir(self.project_build_tool.output_dir):
            file_path = os.path.join(self.project_build_tool.output_dir, file)
            if os.path.isdir(file_path):
                shutil.copytree(file_path, os.path.join(output_dir, file))
            else:
                shutil.copy2(file_path, output_dir)

        # copy install scripts
        if self.project_build_tool.has_install():
            idea.console.print(f'copying {self.app_name} install scripts ...')
            install_dir = self.project_build_tool.install_dir
            files = os.listdir(install_dir)
            for file in files:
                shutil.copy2(os.path.join(install_dir, file), output_dir)

        idea.console.print(f'creating archive ...')
        shutil.make_archive(output_dir, 'gztar', output_dir)

        if delete_output_dir:
            shutil.rmtree(output_dir, ignore_errors=True)
