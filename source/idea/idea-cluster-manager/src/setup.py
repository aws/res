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

from setuptools import setup, find_packages
import ideaclustermanager_meta

setup(
    name=ideaclustermanager_meta.__name__,
    version=ideaclustermanager_meta.__version__,
    description='Cluster Manager',
    url='https://awslabs.github.io/scale-out-computing-on-aws/',
    author='Amazon',
    license='Apache License, Version 2.0',
    packages=find_packages(),
    package_dir={
        'ideaclustermanager': 'ideaclustermanager'
    },
    entry_points='''
        [console_scripts]
        resctl=ideaclustermanager.cli.cli_main:main
        resserver=ideaclustermanager.app.app_main:main
    '''
)
