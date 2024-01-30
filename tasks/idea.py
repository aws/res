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

"""
IDEA Development Task Utils

Should not contain any idea-sdk dependencies!
"""

from typing import List, Dict, Optional, Set
import os
import sys
from pathlib import Path
from rich.console import Console
from rich.style import Style as RichStyle
import shutil
import subprocess
from questionary import unsafe_prompt
from invoke import Context
import yaml
import textwrap

IDEA_DEVELOPMENT_ERROR = 'IDEA_DEVELOPMENT_ERROR'
ERROR_CODE_VENV_NOT_SETUP = 'ERROR_CODE_VENV_NOT_SETUP'
INVALID_PYTHON_VERSION = 'INVALID_PYTHON_VERSION'
INVALID_PARAMS = 'INVALID_PARAMS'
BUILD_FAILED = 'BUILD_FAILED'
GENERAL_EXCEPTION = 'GENERAL_EXCEPTION'

DEVELOPER_ONBOARDING_NOTE = f'Please go through the Developer On-boarding docs before contributing to IDEA source code.'


class SocaDevelopmentProps:

    def __init__(self):
        self.software_versions: Optional[Dict] = None
        self.load_software_versions()

    @staticmethod
    def _run_cmd(cmd, shell=True) -> str:
        result = subprocess.run(
            args=cmd,
            shell=shell,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return str(result.stdout)
        else:
            return str(result.stdout)

    @property
    def software_versions_file(self) -> str:
        return os.path.join(self.project_root_dir, 'software_versions.yml')

    def load_software_versions(self):
        """
        load software_versions.yml from project root
        """
        with open(self.software_versions_file, 'r') as f:
            self.software_versions = yaml.safe_load(f.read())

    @property
    def idea_release_version(self) -> str:
        with open(os.path.join(self.project_root_dir, 'RES_VERSION.txt')) as f:
            return f.read().strip()

    @property
    def idea_python_version(self) -> str:
        return self.software_versions['python_version']

    @property
    def idea_node_version(self) -> str:
        return self.software_versions['node_version']

    @property
    def idea_nvm_version(self) -> str:
        return self.software_versions['nvm_version']

    @property
    def idea_cdk_version(self) -> str:
        cdk_version = self.software_versions['aws_cdk_version']
        return cdk_version.strip()

    @property
    def project_root_dir(self) -> str:
        path = Path(os.path.dirname(os.path.realpath(__file__)))
        return str(path.parent.absolute())

    @property
    def project_source_dir(self) -> str:
        return os.path.join(self.project_root_dir, 'source', 'idea')

    @property
    def project_unit_tests_dir(self) -> str:
        return os.path.join(self.project_root_dir, 'source', 'tests', 'unit')

    @property
    def project_deployment_dir(self) -> str:
        return os.path.join(self.project_root_dir, 'deployment')

    @property
    def project_scripts_dir(self) -> str:
        return os.path.join(self.project_root_dir, 'source', 'scripts')

    @property
    def which_python(self) -> str:
        return shutil.which('python')

    @property
    def python_version(self) -> str:
        python = self.which_python
        result = self._run_cmd(f'{python} --version')
        return result.split(' ')[1]

    @property
    def site_packages(self) -> str:
        virtual_env = os.environ.get('VIRTUAL_ENV', None)
        if virtual_env is None:
            python_bin = Path(self.which_python)
            virtual_env = python_bin.parent.parent
        return os.path.join(virtual_env, 'lib', 'python3.9', 'site-packages')

    @property
    def requirements_dir(self) -> str:
        return os.path.join(self.project_root_dir, 'requirements')

    @property
    def administrator_project_dir(self) -> str:
        return os.path.join(self.project_source_dir, 'idea-administrator')

    @property
    def administrator_integ_tests_dir(self) -> str:
        return os.path.join(self.administrator_project_dir, 'src', 'ideaadministrator', 'integration_tests')

    @property
    def end_to_end_integ_tests_dir(self) -> str:
        return os.path.join(self.project_root_dir, 'source', 'tests', 'integration', 'tests')

    @property
    def deployment_ecr_dir(self) -> str:
        return os.path.join(self.project_deployment_dir, 'ecr')

    @property
    def deployment_administrator_dir(self) -> str:
        return os.path.join(self.deployment_ecr_dir, 'idea-administrator')

    @property
    def administrator_webapp_dir(self) -> str:
        return os.path.join(self.administrator_project_dir, 'webapp')

    @property
    def administrator_src(self) -> str:
        return os.path.join(self.administrator_project_dir, 'src')

    @property
    def administrator_tests_src(self) -> str:
        return os.path.join(self.project_unit_tests_dir, 'idea-administrator')

    @property
    def virtual_desktop_project_dir(self) -> str:
        return os.path.join(self.project_source_dir, 'idea-virtual-desktop-controller')

    @property
    def virtual_desktop_src(self) -> str:
        return os.path.join(self.virtual_desktop_project_dir, 'src')

    @property
    def virtual_desktop_tests_src(self) -> str:
        return os.path.join(self.project_unit_tests_dir, 'idea-virtual-desktop-controller')

    @property
    def cluster_manager_project_dir(self) -> str:
        return os.path.join(self.project_source_dir, 'idea-cluster-manager')

    @property
    def dcv_connection_gateway_dir(self) -> str:
        return os.path.join(self.project_source_dir, 'idea-dcv-connection-gateway')

    @property
    def cluster_manager_webapp_dir(self) -> str:
        return os.path.join(self.cluster_manager_project_dir, 'webapp')

    @property
    def cluster_manager_src(self) -> str:
        return os.path.join(self.cluster_manager_project_dir, 'src')

    @property
    def cluster_manager_tests_src(self) -> str:
        return os.path.join(self.project_unit_tests_dir, 'idea-cluster-manager')

    @property
    def data_model_project_dir(self) -> str:
        return os.path.join(self.project_source_dir, 'idea-data-model')

    @property
    def sdk_project_dir(self) -> str:
        return os.path.join(self.project_source_dir, 'idea-sdk')

    @property
    def test_utils_project_dir(self) -> str:
        return os.path.join(self.project_source_dir, 'idea-test-utils')

    @property
    def test_utils_src(self) -> str:
        return os.path.join(self.test_utils_project_dir, 'src')

    @property
    def data_model_src(self) -> str:
        return os.path.join(self.data_model_project_dir, 'src')

    @property
    def sdk_src(self) -> str:
        return os.path.join(self.sdk_project_dir, 'src')

    @property
    def sdk_tests_src(self) -> str:
        return os.path.join(self.project_unit_tests_dir, 'idea-sdk')

    @property
    def scheduler_project_dir(self) -> str:
        return os.path.join(self.project_source_dir, 'idea-scheduler')

    @property
    def scheduler_src(self) -> str:
        return os.path.join(self.scheduler_project_dir, 'src')

    @property
    def scheduler_tests_src(self) -> str:
        return os.path.join(self.scheduler_project_dir, 'tests')

    @property
    def project_build_dir(self) -> str:
        return os.path.join(self.project_root_dir, 'build')

    @property
    def project_dist_dir(self) -> str:
        return os.path.join(self.project_root_dir, 'dist')

    @property
    def idea_downloads_dir(self) -> str:
        downloads_dir = os.path.join(self.idea_user_home, 'downloads', 'idea')
        os.makedirs(downloads_dir, exist_ok=True)
        return downloads_dir

    @property
    def idea_user_home(self) -> str:
        idea_user_home = os.environ.get('IDEA_USER_HOME', os.path.expanduser(os.path.join('~', '.idea')))
        os.makedirs(idea_user_home, exist_ok=True)
        return idea_user_home

    @property
    def idea_cdk_dir(self) -> str:
        idea_user_home = self.idea_user_home
        idea_cdk_dir = os.path.join(idea_user_home, 'lib', 'idea-cdk')
        os.makedirs(idea_cdk_dir, exist_ok=True)
        return idea_cdk_dir

    @property
    def idea_user_config_file(self) -> str:
        return os.path.join(self.idea_user_home, 'config.yml')


class SocaDevelopmentConsole:

    def __init__(self):
        self.console = Console()

    def error(self, msg):
        self.console.print(msg, style='bold red')

    def echo(self, msg):
        self.console.out(msg)

    def info(self, msg):
        self.console.print(msg, style='cyan')

    def warning(self, msg):
        self.console.print(msg, style='bold yellow')

    def success(self, msg):
        self.console.print(msg, style='bold green')

    def print(self, msg):
        self.console.print(msg)

    def spinner(self, message: str):
        return self.console.status(message)

    @staticmethod
    def confirm(message: str, default=False, auto_enter=True, icon='?') -> bool:
        try:
            result = unsafe_prompt(questions=[{
                'type': 'confirm',
                'name': 'result',
                'message': message,
                'default': default,
                'auto_enter': auto_enter,
                'qmark': icon
            }])
            if 'result' in result:
                return result['result']
            return False
        except KeyboardInterrupt:
            return False

    @staticmethod
    def ask(questions: List[Dict]) -> Dict:
        try:
            return unsafe_prompt(questions=questions)
        except KeyboardInterrupt:
            return {}

    def print_header_block(self, content: str, width: int = 120, break_long_words: bool = False, style=None):
        if style == 'main':
            header_char = '-'
            style = RichStyle(bold=True, color='bright_white')
        elif style == 'success':
            header_char = '-'
            style = 'bold green'
        elif style == 'error':
            header_char = '-'
            style = 'bold red'
        else:
            header_char = '-'
            style = None

        self.console.print(header_char * width, style=style)
        lines = textwrap.wrap(f'* {content}', width, break_on_hyphens=False, break_long_words=break_long_words, subsequent_indent='  ')
        for line in lines:
            self.console.print(line, style=style)
        self.console.print(header_char * width, style=style)


class SocaDevelopmentException(Exception):
    def __init__(self, message: str, error_code: str = 'IDEA_DEVELOPMENT_ERROR', ref=None):
        self.error_code = error_code
        self.message = message
        self.ref = ref

    def __repr__(self):
        return str(self)

    def __str__(self):
        return f'[{self.error_code}] {self.message}'


class SocaDevelopmentExceptions:

    @staticmethod
    def virtual_env_not_setup():
        return SocaDevelopmentException(
            error_code=IDEA_DEVELOPMENT_ERROR,
            message=f'VirtualEnv is not setup. Please setup a python virtual environment before proceeding. {os.linesep}'
                    f'{DEVELOPER_ONBOARDING_NOTE}'
        )

    @staticmethod
    def invalid_python_version():
        return SocaDevelopmentException(
            error_code=INVALID_PYTHON_VERSION,
            message=f'You are not running a valid Python version required by IDEA. {os.linesep}'
                    f'You must have Python {props.idea_python_version} installed for IDEA development.{os.linesep}'
                    f'{DEVELOPER_ONBOARDING_NOTE}'
        )

    @staticmethod
    def invalid_params(message: str):
        return SocaDevelopmentException(
            error_code=INVALID_PARAMS,
            message=message
        )

    @staticmethod
    def build_failed(message: str):
        return SocaDevelopmentException(
            error_code=BUILD_FAILED,
            message=message
        )

    @staticmethod
    def general_exception(message: str):
        return SocaDevelopmentException(
            error_code=GENERAL_EXCEPTION,
            message=message
        )

    @staticmethod
    def exception(error_code: str, message: str):
        return SocaDevelopmentException(error_code, message)


props = SocaDevelopmentProps()


class SocaDevelopmentUtils:

    @staticmethod
    def get_base_prefix_compat() -> str:
        """
        Get base/real prefix, or sys.prefix if there is none.
        Sourced From: https://stackoverflow.com/questions/1871549/determine-if-python-is-running-inside-virtualenv
        """
        return getattr(sys, "base_prefix", None) or getattr(sys, "real_prefix", None) or sys.prefix

    def in_virtualenv(self) -> bool:
        return self.get_base_prefix_compat() != sys.prefix

    def check_venv(self):
        if self.in_virtualenv:
            return
        raise exceptions.virtual_env_not_setup()

    @staticmethod
    def check_python_version():
        python_version = props.python_version
        if python_version.endswith(props.idea_python_version):
            return
        raise exceptions.invalid_python_version()

    @staticmethod
    def update_source_paths(paths: List[str]):
        for path in paths:
            sys.path.insert(0, path)

    @property
    def idea_python(self) -> str:
        self.check_venv()
        return props.which_python

    def get_package_meta(self, c: Context, source_root: str, prop: str) -> str:
        with c.cd(source_root):
            result = c.run(f'{self.idea_python} setup.py --{prop}', hide=True)
            return str(result.stdout).strip()

    @staticmethod
    def get_supported_modules() -> Optional[Set[str]]:
        return {
            'cluster-manager',
            'virtual-desktop-controller'
        }

    @staticmethod
    def get_module_name(token: str) -> Optional[str]:
        if token in ('virtual-desktop', 'virtual-desktop-controller', 'vdc', 'vdi'):
            return 'virtual-desktop-controller'
        if token in ('cluster-manager', 'cm'):
            return 'cluster-manager'
        if token in ('admin', 'administrator'):
            return 'administrator'
        return None


console = SocaDevelopmentConsole()
exceptions = SocaDevelopmentExceptions()
utils = SocaDevelopmentUtils()
