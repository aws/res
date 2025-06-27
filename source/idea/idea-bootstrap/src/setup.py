#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from setuptools import setup, find_packages
import ideabootstrap_meta

setup(
    name=ideabootstrap_meta.__name__,
    version=ideabootstrap_meta.__version__,
    description='Bootstrap',
    url='https://aws.amazon.com/hpc/res/',
    author='Amazon',
    license='Apache License, Version 2.0',
    packages=find_packages(),
    package_dir={
        'ideabootstrap': 'ideabootstrap'
    },
)
