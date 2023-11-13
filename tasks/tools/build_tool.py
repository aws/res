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
from typing import Optional
import shutil
import os
from abc import abstractmethod, ABC


class BaseMetadataUpdater(ABC):

    @abstractmethod
    def update(self):
        ...


class PythonAppMetaFileUpdater(BaseMetadataUpdater):
    """
    Update SOCA Release Version in Python App: <packagename>_meta/__init__ file
    This enables applications to find SOCA Release version and current version without relying on Environment Variables
    """

    def __init__(self, meta_file: str):
        if not os.path.isfile(meta_file):
            raise idea.exceptions.invalid_params(f'meta_file: {meta_file} does not exist of not found')
        self.meta_file = meta_file

    def update(self):
        version_var_name = '__version__'
        release_version = idea.props.idea_release_version
        with open(self.meta_file, 'r') as f:
            lines = f.readlines()

        result = []
        found = False
        for line in lines:
            if len(line.strip()) == 0:
                result.append(line)
                continue
            if not line.strip().startswith(version_var_name):
                result.append(line)
                continue
            result.append(f"{version_var_name} = '{release_version}'")
            found = True
            break

        if not found:
            result.append(f"{version_var_name} = '{release_version}'")

        result.append(os.linesep)

        with open(self.meta_file, 'w') as f:
            f.write(''.join(result))


class InstallScriptsFileUpdater(BaseMetadataUpdater):

    def update(self):
        pass


class WebAppEnvFileUpdater(BaseMetadataUpdater):

    def __init__(self, webapp_env_file: str, app_name: str, app_version: str, release_version: str):
        if not os.path.isfile(webapp_env_file):
            raise idea.exceptions.invalid_params(f'webapp .env file: {webapp_env_file} does not exist of not found')
        self.webapp_env_file = webapp_env_file
        self.app_name = app_name
        self.app_version = app_version
        self.release_version = release_version

    def update(self):
        var_release_version = 'REACT_APP_IDEA_RELEASE_VERSION'

        release_version = f'{var_release_version}="{self.release_version}"{os.linesep}'
        release_version_updated = False

        with open(self.webapp_env_file, 'r') as f:
            lines = f.readlines()

        updates = []
        for line in lines:
            updated = line
            if updated.startswith(var_release_version):
                updated = release_version
                release_version_updated = True
            updates.append(updated)

        # takes care of scenarios when the env var does not exist in the file or a new env is added in future.
        if not release_version_updated:
            updates.append(release_version)

        webapp_env_file_contents = ''.join(updates)

        with open(self.webapp_env_file, 'w') as f:
            f.write(webapp_env_file_contents)


class NpmPackageJsonFileUpdater(BaseMetadataUpdater):
    """
    Update the package.json name and version using setup.py name and version
    Helps keep python app and web app name and versions in-sync
    should be called everytime during build
    """

    def __init__(self, package_json_file: str, app_name: str, app_version: str, release_version: str):
        if not os.path.isfile(package_json_file):
            raise idea.exceptions.invalid_params(f'package.json file: {package_json_file} does not exist of not found')
        self.package_json_file = package_json_file
        self.app_name = app_name
        self.app_version = app_version
        self.release_version = release_version

    def update(self):
        with open(self.package_json_file, 'r') as f:
            lines = f.readlines()
        updates = []

        for line in lines:
            updated = line
            token = updated.strip()
            if token.startswith('"name"'):
                updated = f'  "name": "web-portal", {os.linesep}'
            elif token.startswith('"version"'):
                updated = f'  "version": "{self.app_version}", {os.linesep}'
            updates.append(updated)
        package_json_contents = ''.join(updates)

        with open(self.package_json_file, 'w') as f:
            f.write(package_json_contents)


class BuildTool:
    """
    IDEA Project Build Tool
    Handles building of individual projects under <PROJECT_ROOT>/source/idea/*

    Works based on standard idea directory structure:
    <PROJECT_ROOT>/
    + source/
      + idea/
        + <project-name>/
          + src/
            + <projectname>/
            + <projectname>_meta/
              + __init__.py
            + setup.py
          + resources/
          + config/
          + webapp?/
          + scripts/

    Build outputs will be available under:
    <PROJECT_ROOT>/
    + build/
      + <project-name>/
    """

    def __init__(self, c: Context, app_name: str):
        self.c = c

        if app_name is None:
            raise idea.exceptions.invalid_params('app_name is required')

        app_dir = os.path.join(idea.props.project_source_dir, app_name)
        if not os.path.isdir(app_dir):
            raise idea.exceptions.invalid_params(f'project_dir: {app_dir} not found or does not exist')

        self.app_dir = app_dir
        self.release_version = idea.props.idea_release_version
        self._given_app_name = app_name
        self._app_name: Optional[str] = None

    @property
    def app_name(self) -> str:
        if self._app_name is not None:
            return self._app_name
        if self.has_src():
            self._app_name = idea.utils.get_package_meta(self.c, self.src_dir, 'name')
            return self._app_name
        else:
            return self._given_app_name

    @property
    def app_version(self) -> str:
        return idea.props.idea_release_version

    @property
    def output_dir(self) -> str:
        return os.path.join(idea.props.project_build_dir, self.output_archive_basename)

    @property
    def output_archive_basename(self) -> str:
        return self.app_name

    @property
    def output_archive_name(self) -> str:
        return f'{self.output_archive_basename}.tar.gz'

    @property
    def output_archive_file(self) -> str:
        return os.path.join(idea.props.project_build_dir, self.output_archive_name)

    @property
    def src_dir(self) -> str:
        return os.path.join(self.app_dir, 'src')

    def has_src(self) -> bool:
        return os.path.isdir(self.src_dir)

    @property
    def webapp_dir(self) -> str:
        return os.path.join(self.app_dir, 'webapp')

    @property
    def webapp_build_dir(self) -> str:
        return os.path.join(self.webapp_dir, 'build')

    def has_webapp(self) -> bool:
        return os.path.isdir(self.webapp_dir)

    @property
    def node_modules_dir(self) -> str:
        return os.path.join(self.webapp_dir, 'node_modules')

    def are_node_modules_installed(self) -> bool:
        return os.path.isdir(self.node_modules_dir)

    @property
    def resources_dir(self) -> str:
        return os.path.join(self.app_dir, 'resources')

    def has_resources(self) -> bool:
        return os.path.isdir(self.resources_dir)

    @property
    def install_dir(self) -> str:
        return os.path.join(self.app_dir, 'install')

    def has_install(self) -> bool:
        return os.path.isdir(self.install_dir)

    @property
    def config_dir(self) -> str:
        return os.path.join(self.app_dir, 'config')

    def has_config(self) -> bool:
        return os.path.isdir(self.config_dir)

    @property
    def bootstrap_dir(self) -> str:
        return os.path.join(idea.props.project_source_dir, 'idea-bootstrap')

    def find_app_meta_file(self) -> str:
        src_dir = self.src_dir
        files = os.listdir(src_dir)
        for file in files:
            if file.endswith('_meta'):
                return os.path.join(src_dir, file, '__init__.py')
        raise idea.exceptions.build_failed(f'could not find app meta file (__init__.py) in: {src_dir}')

    def clean(self):
        if self.has_src():
            src_dist = os.path.join(self.src_dir, 'dist')
            if os.path.isdir(src_dist):
                idea.console.print(f'deleting {src_dist} ...')
                shutil.rmtree(src_dist, ignore_errors=True)

            egg_name = self.app_name.replace('-', '_')
            egg_info_name = f'{egg_name}.egg-info'
            src_egg = os.path.join(self.src_dir, egg_info_name)
            if os.path.isdir(src_egg):
                idea.console.print(f'deleting {src_egg} ...')
                shutil.rmtree(os.path.join(self.src_dir, egg_info_name), ignore_errors=True)

        if self.has_webapp():
            skip_web = os.environ.get('IDEA_SKIP_WEB_BUILD', '0')
            if skip_web == '0':
                if os.path.isdir(self.webapp_build_dir):
                    idea.console.print(f'deleting {self.webapp_build_dir} ...')
                    shutil.rmtree(self.webapp_build_dir, ignore_errors=True)

        if os.path.isdir(self.output_dir):
            idea.console.print(f'deleting {self.output_dir} ...')
            shutil.rmtree(self.output_dir)

        if os.path.isfile(self.output_archive_file):
            idea.console.print(f'deleting {self.output_archive_file} ...')
            os.remove(self.output_archive_file)

        if self.app_name == 'idea-administrator':
            files = os.listdir(idea.props.deployment_administrator_dir)
            for file in files:
                if file == 'Dockerfile' or file == 'cfn_params_2_values.sh':
                    continue
                file_path = os.path.join(idea.props.deployment_administrator_dir, file)
                if os.path.isfile(file_path):
                    idea.console.print(f'deleting {file_path} ...')
                    os.remove(os.path.join(idea.props.deployment_administrator_dir, file))
                elif os.path.isdir(file_path):
                    idea.console.print(f'deleting {file_path} ...')
                    shutil.rmtree(file_path)

    def pre_build_src(self):
        if not self.has_src():
            return
        PythonAppMetaFileUpdater(meta_file=self.find_app_meta_file()).update()

    def build_src(self):
        if not self.has_src():
            return
        with self.c.cd(self.src_dir):
            self.c.run(f'{idea.utils.idea_python} setup.py sdist')

    def pre_build_webapp(self):
        if not self.has_webapp():
            return
        webapp_dir = self.webapp_dir

        app_name = self.app_name
        app_version = self.app_version
        release_version = self.release_version

        NpmPackageJsonFileUpdater(
            package_json_file=os.path.join(webapp_dir, 'package.json'),
            app_name=app_name,
            app_version=app_version,
            release_version=release_version
        ).update()

        WebAppEnvFileUpdater(
            webapp_env_file=os.path.join(webapp_dir, '.env'),
            app_name=app_name,
            app_version=app_version,
            release_version=release_version
        ).update()

    def build_webapp(self):

        skip_web = os.environ.get('IDEA_SKIP_WEB_BUILD', '0')
        if skip_web == '1':
            return

        if not self.has_webapp():
            return

        with self.c.cd(self.webapp_dir):
            self.c.run('yarn install && yarn build')

    def copy_build_outputs(self):

        output_dir = self.output_dir
        shutil.rmtree(output_dir, ignore_errors=True)
        os.makedirs(output_dir, exist_ok=True)

        # src (sdist)
        if self.has_src():
            app_name = self.app_name
            # python does not accept server and does some funky normalization on the semver.
            # this is only applicable for pre-releases or dev branches. e.g. 3.0.0-dev.1 gets converted to 3.0.0.dev1
            normalized_python_app_version = idea.utils.get_package_meta(self.c, self.src_dir, 'version')
            sdist_name = f'{app_name}-{normalized_python_app_version}.tar.gz'
            sdist = os.path.join(self.src_dir, 'dist', sdist_name)
            shutil.copy(sdist, os.path.join(output_dir, f'{app_name}-lib.tar.gz'))

        # webapp
        if self.has_webapp():
            shutil.copytree(self.webapp_build_dir, os.path.join(output_dir, 'webapp'))

        # config
        if self.has_config():
            shutil.copytree(self.config_dir, os.path.join(output_dir, 'config'))

        # resources
        if self.has_resources():
            shutil.copytree(self.resources_dir, os.path.join(output_dir, 'resources'))
            shutil.copytree(self.bootstrap_dir, os.path.join(output_dir, 'resources', 'bootstrap'))

    def build(self):

        idea.console.print_header_block(f'build {self.app_name}')

        self.pre_build_src()
        self.build_src()
        self.pre_build_webapp()
        self.build_webapp()

        # copy build outputs to project build dir
        self.copy_build_outputs()
