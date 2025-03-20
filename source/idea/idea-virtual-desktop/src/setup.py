#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import ideavirtualdesktop_meta
from setuptools import find_packages, setup

setup(
    name=ideavirtualdesktop_meta.__name__,
    version=ideavirtualdesktop_meta.__version__,
    description='RES Virtual Desktop',
    url='https://aws.amazon.com/hpc/res/',
    author='Amazon',
    license='Apache License, Version 2.0',
    packages=find_packages(),
    package_dir={
        'ideavirtualdesktop_meta': 'ideavirtualdesktop_meta'
    },
    entry_points='''
        [console_scripts]
        resserver=ideavirtualdesktop.app.app_main:main
    '''
)
