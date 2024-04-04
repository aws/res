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

import ideaadministrator
from ideaadministrator.app_utils import AdministratorUtils
from ideadatamodel import exceptions

from ideasdk.shell import ShellInvoker
from ideasdk.utils import Utils


from enum import Enum
from typing import Dict
import os
import pathlib
import shutil


class SupportedLambdaPlatforms(str, Enum):
    PYTHON = 'PYTHON'


class IdeaCodeAsset:
    """
    Used to build lambda code assets with applicable package dependencies
    """
    SOURCE_CODE_CHECKSUM_FILE = 'source.checksum.sha'
    PKG_DIR = 'pkg'
    PKG_DIR_CHECKSUM_FILE = 'pkg.checksum.sha'

    def __init__(self, lambda_platform: SupportedLambdaPlatforms, lambda_package_name: str):
        self._lambda_platform = lambda_platform
        self._lambda_package_name = lambda_package_name
        self._build_location = os.path.join(AdministratorUtils.get_package_build_dir(), self.lambda_package_name)
        self._common_code_location = ideaadministrator.props.lambda_function_commons_dir

        self.PLATFORM_MANAGE_REQUIREMENTS_MAP: Dict[SupportedLambdaPlatforms, ()] = {
            SupportedLambdaPlatforms.PYTHON: self._manage_python_requirements
        }

        self.PLATFORM_BUILD_MAP: Dict[SupportedLambdaPlatforms, ()] = {
            SupportedLambdaPlatforms.PYTHON: self._build_python_lambda
        }

    @property
    def asset_hash(self) -> str:
        return Utils.compute_checksum_for_dir(os.path.join(self._build_location, self.PKG_DIR))

    @property
    def lambda_handler(self) -> str:
        return f'{self.lambda_package_name}.handler.handler'

    @property
    def lambda_platform(self) -> SupportedLambdaPlatforms:
        return self._lambda_platform

    @property
    def source_code_location(self) -> str:
        return os.path.join(ideaadministrator.props.lambda_functions_dir, self.lambda_package_name)

    @property
    def lambda_package_name(self) -> str:
        return self._lambda_package_name

    @staticmethod
    def _manage_python_requirements(build_src: str, lambda_package_name: str):
        requirements_file = os.path.join(build_src, lambda_package_name, 'requirements.txt')
        if Utils.is_file(requirements_file):
            shutil.move(requirements_file, build_src)

    @staticmethod
    def _build_python_lambda(build_location: str, lambda_package_name: str):
        if not Utils.is_file(os.path.join(build_location, 'requirements.txt')):
            return

        installed_dependencies_dir = os.path.join(build_location, lambda_package_name, 'dependencies')
        if os.path.isdir(installed_dependencies_dir):
            try:
                shutil.copytree(src=installed_dependencies_dir, dst=build_location, dirs_exist_ok=True)
                shutil.rmtree(installed_dependencies_dir)
            except Exception as e:
                raise exceptions.general_exception(f'Issue copying dependencies: {e}')
        else:
            shell = ShellInvoker(cwd=build_location)
            response = shell.invoke(
                shell=True,
                cmd=['pip install -r requirements.txt --platform manylinux2014_x86_64 --only-binary=:all: --target . --upgrade'],
                env=ideaadministrator.props.get_env()
            )
            if response.returncode != 0:
                raise exceptions.general_exception(f'Issue building the lambda: {response}')

    def _validate_checksum_for_source_code(self) -> bool:
        if not Utils.is_dir(self.source_code_location):
            return False

        if not Utils.is_dir(self._common_code_location):
            return False

        if not Utils.is_file(os.path.join(self._build_location, self.SOURCE_CODE_CHECKSUM_FILE)):
            return False

        checksum = Utils.compute_checksum_for_dirs([self.source_code_location, self._common_code_location])
        with open(os.path.join(self._build_location, self.SOURCE_CODE_CHECKSUM_FILE)) as f:
            existing_checksum = str(f.read().strip())

        return existing_checksum == checksum

    def _validate_checksum_for_package(self) -> bool:
        if not Utils.is_dir(os.path.join(self._build_location, self.PKG_DIR)):
            return False

        if not Utils.is_file(os.path.join(self._build_location, self.PKG_DIR_CHECKSUM_FILE)):
            return False

        with open(os.path.join(self._build_location, self.PKG_DIR_CHECKSUM_FILE)) as f:
            existing_checksum = str(f.read().strip())

        return existing_checksum == self.asset_hash

    def build_lambda(self):
        if self.lambda_platform not in self.PLATFORM_BUILD_MAP.keys():
            raise exceptions.general_exception(f'Invalid lambda_platform: {self.lambda_platform}. Supported only {self.PLATFORM_BUILD_MAP.keys()}')

        if Utils.is_dir(self._build_location):
            if not self._validate_checksum_for_source_code():
                print(f'source updated for {self.lambda_package_name}...')
                shutil.rmtree(self._build_location)
            elif not self._validate_checksum_for_package():
                print(f'existing package corrupted for lambda: {self.lambda_package_name} ...')
                shutil.rmtree(self._build_location)
            else:
                print(f're-use code assets for lambda: {self.lambda_package_name} ...')
                return os.path.join(self._build_location, self.PKG_DIR)

        print(f'building code assets for lambda: {self.lambda_package_name} ...')
        build_src = os.path.join(self._build_location, self.PKG_DIR)
        parent = pathlib.Path(build_src).parent
        if not parent.is_dir():
            os.makedirs(parent)

        # if we have reached here, then we need to build the code again
        shutil.copytree(self._common_code_location, os.path.join(build_src, ideaadministrator.props.lambda_function_commons_package_name))
        shutil.copytree(self.source_code_location, os.path.join(build_src, self.lambda_package_name))

        self.PLATFORM_MANAGE_REQUIREMENTS_MAP[self.lambda_platform](
            build_src=build_src,
            lambda_package_name=self.lambda_package_name
        )

        self.PLATFORM_BUILD_MAP[self.lambda_platform](
            build_location=build_src,
            lambda_package_name=self.lambda_package_name,
        )

        shell = ShellInvoker(cwd=self._build_location)
        shell.invoke(
            shell=True,
            cmd=[f'echo {self.asset_hash} > {self.PKG_DIR_CHECKSUM_FILE}'],
            env=ideaadministrator.props.get_env(),
        )

        checksum = Utils.compute_checksum_for_dirs([self.source_code_location, self._common_code_location])
        shell.invoke(
            shell=True,
            cmd=[f'echo {checksum} > {self.SOURCE_CODE_CHECKSUM_FILE}'],
            env=ideaadministrator.props.get_env(),
        )
        return os.path.join(self._build_location, self.PKG_DIR)
