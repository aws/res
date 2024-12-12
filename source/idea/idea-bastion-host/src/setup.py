#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import ideabastionhost_meta
from setuptools import find_packages, setup

setup(
    name=ideabastionhost_meta.__name__,
    version=ideabastionhost_meta.__version__,
    description='RES bastion host',
    url='https://aws.amazon.com/hpc/res/',
    author='Amazon',
    license='Apache License, Version 2.0',
    packages=find_packages(),
    package_dir={
        'ideabastionhost_meta': 'ideabastionhost_meta'
    },
    entry_points='''
        [console_scripts]
        resserver=ideabastionhost.app.app_main:main
    '''
)
