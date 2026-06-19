#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from enum import Enum


class VirtualDesktopSessionType(str, Enum):
    """Enumeration values for VirtualDesktopSessionType"""

    CONSOLE = 'CONSOLE'
    VIRTUAL = 'VIRTUAL'
