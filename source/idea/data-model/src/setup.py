#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import datamodel_meta
from setuptools import find_packages, setup

setup(
    name=datamodel_meta.__name__,
    version=datamodel_meta.__version__,
    description="RES data model",
    url="https://aws.amazon.com/hpc/res/",
    author="Amazon",
    license="Apache License, Version 2.0",
    packages=find_packages(exclude=['tests']),
    package_dir={
        'datamodel': 'datamodel'
    },
    package_data={
        'datamodel': ['config/*.yaml']
    }
)
