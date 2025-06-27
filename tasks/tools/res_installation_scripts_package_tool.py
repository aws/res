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
from invoke import Context
import shutil
import os
import re
from typing import List

class ResInstallationScriptsPackageTool:

    def __init__(self, c: Context):
        self.c = c

    @property
    def bash_script_name(self) -> str:
        return 'install.sh'

    @property
    def output_archive_basename(self) -> str:
        return 'res-installation-scripts'

    @property
    def requirements_file_name(self) -> str:
        return 'requirements.txt'

    @property
    def output_archive_name(self) -> str:
        return f'{self.output_archive_basename}.tar.gz'

    @property
    def output_dir(self) -> str:
        return os.path.join(idea.props.project_dist_dir, self.output_archive_basename)

    @property
    def scripts_dir(self) -> str:
        return os.path.join(self.output_dir, 'scripts')

    @property
    def package_names(self) -> List[str]:
        return [
            "idea-bastion-host",
            "idea-cluster-manager",
            "idea-virtual-desktop-controller",
            "idea-virtual-desktop",
            "idea-dcv-connection-gateway",
            "idea-dcv-broker",
            "idea-sdk",
            "library",
        ]

    def get_all_requirement_files(self) -> List[str]:
        idea.console.print('getting all requirements file ...')
        requirement_files = []
        for package_name in self.package_names:
            requirements_file = os.path.join(idea.props.requirements_dir, f'{package_name}.txt')
            requirement_files.append(requirements_file)
            if not os.path.isfile(requirements_file):
                raise idea.exceptions.build_failed(f'project requirements file not found: {requirements_file}')
        return requirement_files

    def build_python_requirements(self) -> None:
        idea.console.print('building Python requirements ...')
        requirement_files = self.get_all_requirement_files()
        packages = dict()
        package_list = []
        for requirement_file in requirement_files:
            with open(requirement_file, 'r') as f:
                for line in f:
                    package = line.strip()
                    if re.match('^\w', package):
                        package_name, package_version = package.split('==')
                        if package_name not in packages:
                            packages[package_name] = package_version
                            package_list.append(package)

        with open(os.path.join(self.output_dir, self.requirements_file_name), 'w') as f:
            for package in package_list:
                f.write(package + '\n')

    def copy_resources(self) -> None:
        idea.console.print('copying installation scripts ...')
        resources_dir = os.path.join(idea.props.bootstrap_dir, 'resources')
        shutil.copytree(resources_dir, self.output_dir, dirs_exist_ok=True)

    def archive(self) -> None:
        idea.console.print('creating archive ...')
        shutil.make_archive(self.output_dir, 'gztar', self.output_dir)

    def package(self):
        idea.console.print_header_block(f'package RES ready AMI installation scripts')

        shutil.rmtree(self.output_dir, ignore_errors=True)
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.scripts_dir, exist_ok=True)

        self.build_python_requirements()

        self.copy_resources()

        self.archive()
