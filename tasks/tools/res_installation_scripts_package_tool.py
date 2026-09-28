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
import tarfile
import gzip

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
            "idea-virtual-desktop",
            "idea-dcv-connection-gateway",
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
                    if re.match(r'^\w', package):
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
        # Create deterministic tar archive by setting fixed timestamps
        # Use a fixed timestamp (Unix epoch) for deterministic builds
        fixed_timestamp = 0
        
        archive_path = f'{self.output_dir}.tar.gz'
        
        # Collect all paths and sort them for deterministic ordering
        all_paths = []
        for root, dirs, files in os.walk(self.output_dir):
            # Sort directories and files for consistent ordering
            dirs.sort()
            files.sort()
            
            # Add all files (directories will be created automatically by tarfile)
            for file_name in files:
                file_path = os.path.join(root, file_name)
                all_paths.append(file_path)
        
        # Sort all paths to ensure deterministic order
        all_paths.sort()
        
        # Create tar file first, then compress with deterministic gzip
        tar_path = f'{self.output_dir}.tar'
        
        with tarfile.open(tar_path, 'w') as tar:
            for file_path in all_paths:
                # Calculate the archive name (relative path within the tar)
                arcname = os.path.relpath(file_path, self.output_dir)
                
                # Get tarinfo and set fixed timestamp
                tarinfo = tar.gettarinfo(file_path, arcname)
                tarinfo.mtime = fixed_timestamp
                tarinfo.uid = 0
                tarinfo.gid = 0
                tarinfo.uname = 'root'
                tarinfo.gname = 'root'
                
                # Add the file to the archive
                if tarinfo.isfile():
                    with open(file_path, 'rb') as f:
                        tar.addfile(tarinfo, f)
                else:
                    # Handle directories, symlinks, etc.
                    tar.addfile(tarinfo)
        
        # Compress with deterministic gzip (no timestamp in gzip header)
        with open(tar_path, 'rb') as f_in:
            with gzip.GzipFile(archive_path, 'wb', mtime=fixed_timestamp) as f_out:
                f_out.write(f_in.read())
        
        # Remove the intermediate tar file
        os.remove(tar_path)

    def package(self):
        idea.console.print_header_block(f'package RES ready AMI installation scripts')

        shutil.rmtree(self.output_dir, ignore_errors=True)
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.scripts_dir, exist_ok=True)

        self.build_python_requirements()

        self.copy_resources()

        self.archive()
