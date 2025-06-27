#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import ideadcvconnectiongateway_meta
from setuptools import find_packages, setup

setup(
    name=ideadcvconnectiongateway_meta.__name__,
    version=ideadcvconnectiongateway_meta.__version__,
    description='RES DCV Connection Gateway',
    url='https://aws.amazon.com/hpc/res/',
    author='Amazon',
    license='Apache License, Version 2.0',
    packages=find_packages(),
    package_dir={
        'ideadcvconnectiongateway': 'ideadcvconnectiongateway'
    },
    entry_points='''
        [console_scripts]
        resserver=ideadcvconnectiongateway.app.app_main:main
    '''
)
