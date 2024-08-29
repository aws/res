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

import tasks.idea as idea
from tasks.tools.build_tool import BuildTool
from tasks.tools.package_tool import PackageTool

from invoke import Context
from typing import Optional


class CleanTool:

    def __init__(self, c: Context, app_name: str):
        self.c = c
        if app_name is None:
            raise idea.exceptions.invalid_params('app_name is required')
        self.app_name = app_name

        self.build_tool: Optional[BuildTool] = None
        self.package_tool: Optional[PackageTool] = None

        if app_name != 'all':
            self.build_tool = BuildTool(c, app_name)
            self.package_tool = PackageTool(c, app_name)

    def clean(self):
        idea.console.print_header_block(f'clean {self.app_name}')
        if self.build_tool:
            self.build_tool.clean()
        if self.package_tool:
            self.package_tool.clean()

    @staticmethod
    def clean_non_project_items():
        idea.console.print_header_block(f'clean non-project items')

        # lambda assets clean-up (all directories that start with 'idea_')
        if os.path.isdir(idea.props.project_build_dir):
            for file in os.listdir(idea.props.project_build_dir):
                if file.startswith('idea_'):
                    function_build_dir = os.path.join(idea.props.project_build_dir, file)
                    if os.path.isdir(function_build_dir):
                        idea.console.print(f'deleting {function_build_dir} ...')
                        shutil.rmtree(function_build_dir)

        dist_dir = idea.props.project_dist_dir
        if os.path.isdir(dist_dir):
            files = os.listdir(dist_dir)
            for file in files:
                file_path = os.path.join(dist_dir, file)
                if os.path.isdir(file_path):
                    idea.console.print(f'deleting {file_path} ...')
                    shutil.rmtree(file_path, ignore_errors=True)
                if os.path.isfile(file_path):
                    idea.console.print(f'deleting {file_path} ...')
                    os.remove(file_path)
