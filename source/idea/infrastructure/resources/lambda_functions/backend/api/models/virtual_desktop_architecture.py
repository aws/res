#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from enum import Enum


class VirtualDesktopArchitecture(str, Enum):
    """Enumeration values for VirtualDesktopArchitecture"""

    X86_64 = 'x86_64'
    ARM64 = 'arm64'
