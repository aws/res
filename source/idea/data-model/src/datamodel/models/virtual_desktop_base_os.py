#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from enum import Enum


class VirtualDesktopBaseOs(str, Enum):
    """Enumeration values for VirtualDesktopBaseOs"""

    AMAZONLINUX2 = 'amazonlinux2'
    AMZN2023 = 'amzn2023'
    RHEL8 = 'rhel8'
    RHEL9 = 'rhel9'
    UBUNTU2204 = 'ubuntu2204'
    UBUNTU2404 = 'ubuntu2404'
    ROCKY9 = 'rocky9'
    WINDOWS = 'windows'
