#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import adsync_meta  # type: ignore
from setuptools import find_packages, setup  # type: ignore

setup(
    name=adsync_meta.__name__,
    version=adsync_meta.__version__,
    description="AD Sync",
    url="https://github.com/aws/res",
    author="Amazon",
    license="Apache License, Version 2.0",
    packages=find_packages(),
    package_dir={"adsync": "adsync"},
    entry_points="""
        [console_scripts]
        res-ad-sync=adsync.main:main
    """,
)
