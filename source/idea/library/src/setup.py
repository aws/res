#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import res_meta
from setuptools import find_packages, setup

setup(
    name=res_meta.__name__,
    version=res_meta.__version__,
    description="RES library",
    url="https://aws.amazon.com/hpc/res/",
    author="Amazon",
    license="Apache License, Version 2.0",
    packages=find_packages(),
    package_dir={"res": "res"},
    entry_points="""
        [console_scripts]
        res=res.app_main:main
    """,
)
