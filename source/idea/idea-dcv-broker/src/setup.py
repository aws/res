#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import ideadcvbroker_meta
from setuptools import find_packages, setup

setup(
    name=ideadcvbroker_meta.__name__,
    version=ideadcvbroker_meta.__version__,
    description='RES DCV Broker',
    url='https://aws.amazon.com/hpc/res/',
    author='Amazon',
    license='Apache License, Version 2.0',
    packages=find_packages(),
    package_dir={
        'ideadcvbroker': 'ideadcvbroker'
    },
    entry_points='''
        [console_scripts]
        resserver=ideadcvbroker.app.app_main:main
    '''
)
