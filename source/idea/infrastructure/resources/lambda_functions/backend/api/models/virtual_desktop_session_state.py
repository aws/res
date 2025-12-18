#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from enum import Enum


class VirtualDesktopSessionState(str, Enum):
    """Enumeration values for VirtualDesktopSessionState"""

    PROVISIONING = 'PROVISIONING'
    CREATING = 'CREATING'
    INITIALIZING = 'INITIALIZING'
    READY = 'READY'
    RESUMING = 'RESUMING'
    STOPPING = 'STOPPING'
    STOPPED = 'STOPPED'
    STOPPED_IDLE = 'STOPPED_IDLE'
    ERROR = 'ERROR'
    DELETING = 'DELETING'
    DELETED = 'DELETED'
