#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from enum import Enum


class VirtualDesktopGpu(str, Enum):
    """Enumeration values for VirtualDesktopGpu"""

    NO_GPU = 'NO_GPU'
    NVIDIA = 'NVIDIA'
    AMD = 'AMD'
