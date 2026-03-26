#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from enum import Enum


class VirtualDesktopScheduleType(str, Enum):
    """Enumeration values for VirtualDesktopScheduleType"""

    WORKING_HOURS = 'WORKING_HOURS'
    STOP_ALL_DAY = 'STOP_ALL_DAY'
    START_ALL_DAY = 'START_ALL_DAY'
    CUSTOM_SCHEDULE = 'CUSTOM_SCHEDULE'
    NO_SCHEDULE = 'NO_SCHEDULE'
