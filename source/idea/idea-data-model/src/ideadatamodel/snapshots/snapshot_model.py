#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

__all__ = (
    'Snapshot',
    'SnapshotStatus'
)

from ideadatamodel import SocaBaseModel
from datetime import datetime
from enum import Enum
from typing import Optional


class SnapshotStatus(str, Enum):
    IN_PROGRESS = 'IN_PROGRESS'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'

class Snapshot(SocaBaseModel):
    s3_bucket_name: Optional[str]
    snapshot_path: Optional[str]
    status: Optional[SnapshotStatus]
    created_on: Optional[datetime]
