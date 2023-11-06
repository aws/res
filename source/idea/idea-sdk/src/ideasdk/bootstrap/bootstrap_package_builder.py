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
import shutil
from threading import RLock

from ideasdk.context import BootstrapContext
from ideasdk.utils import Utils, Jinja2Utils
from ideadatamodel import exceptions

from typing import List
import os
import tempfile

_BOOTSTRAP_BUILDER_LOCK = RLock()


class BootstrapPackageBuilder:
    """
    Renders the bootstrap module and returns the path to the rendered bootstrap tar.gz file.
    The final packaged tar.gz will be returned as string path by the build method
    The caller is responsible to clean up the temporary package after uploading to S3.
    """

    def __init__(self, bootstrap_context: BootstrapContext,
                 source_directory: str,
                 target_package_basename: str,
                 components: List[str],
                 tmp_dir: str = None,
                 force_build: bool = False,
                 base_os: str = None,
                 logger=None):
        """
        :param bootstrap_context: template rendering context.

        :param source_directory: path to the top level idea-bootstrap directory.

        :param target_package_basename: the base name of the target package where the rendered templates will be created.
        eg. idea-bootstrap-scheduler-1654785667888

        :param components: a list of components that are needed to be included in the rendered bootstrap package

        :param force_build: if force_build is True and the bootstrap package directory already exists, the existing directory will be deleted.
        if force_build is False, building bootstrap package will be skipped if the directory exists. this is to enable customizations
        to bootstrap package out of sources.
        """

        if Utils.is_empty(components):
            raise exceptions.invalid_params('components[] is required.')

        if 'common' not in components:
            if Utils.is_not_empty(base_os):
                if base_os.lower() != 'windows':
                    components.insert(0, 'common')
            else:
                components.insert(0, 'common')

        self.bootstrap_context = bootstrap_context
        self.source_directory = source_directory
        self.target_package_basename = target_package_basename
        self.force_build = force_build
        self.components = components
        self.logger = logger
        self.tmp_dir = tmp_dir

    def log(self, message: str):
        if self.logger is not None:
            self.logger.info(message)
        else:
            print(message)

    def build(self) -> str:
        with _BOOTSTRAP_BUILDER_LOCK:
            tmp_dir = self.tmp_dir
            if Utils.is_empty(tmp_dir):
                tmp_dir = tempfile.mkdtemp()
            else:
                os.makedirs(tmp_dir, exist_ok=True)

            target_dir = os.path.join(tmp_dir, self.target_package_basename)
            if Utils.is_dir(target_dir):
                if self.force_build:
                    self.log(f'deleting existing directory: {target_dir} ...')
                    shutil.rmtree(target_dir)
                else:
                    self.log(f'found existing bootstrap directory: {target_dir}. use force_build=True to '
                             f'rebuild the bootstrap package.')
                    target_archive = os.path.join(tmp_dir, f'{self.target_package_basename}.tar.gz')
                    if Utils.is_file(target_archive):
                        os.remove(target_archive)
                    shutil.make_archive(target_dir, 'gztar', target_dir)
                    return target_archive

            env = Jinja2Utils.env_using_file_system_loader(self.source_directory)

            components = os.listdir(self.source_directory)
            for component in components:
                if component == '_templates':
                    continue
                if component not in self.components:
                    continue
                source_component_dir = os.path.join(self.source_directory, component)
                files = os.listdir(source_component_dir)

                target_component_dir = os.path.join(target_dir, component)
                os.makedirs(target_component_dir, exist_ok=True)
                for file in files:
                    if file == '_templates':
                        continue
                    if file.endswith('.jinja2'):
                        template = env.get_template(f'{component}/{file}')
                        content = template.render(context=self.bootstrap_context)
                        target_file = os.path.join(target_component_dir, file.replace('.jinja2', ''))
                        self.log(f'rendered template: {target_file}')
                        with open(target_file, 'w') as f:
                            f.write(content)
                    else:
                        source_file = os.path.join(source_component_dir, file)
                        target_file = os.path.join(target_component_dir, file)
                        if os.path.isdir(source_file):
                            self.log(f'copied directory: {target_file}')
                            shutil.copytree(source_file, target_file)
                        else:
                            self.log(f'copied file: {target_file}')
                            shutil.copy2(source_file, target_file)

            shutil.make_archive(target_dir, 'gztar', target_dir)
            return os.path.join(tmp_dir, f'{self.target_package_basename}.tar.gz')
