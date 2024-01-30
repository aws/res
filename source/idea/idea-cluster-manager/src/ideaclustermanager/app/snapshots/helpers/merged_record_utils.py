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

from enum import Enum
from pydantic import BaseModel
from typing import Dict, Optional


class MergedRecordActionType(Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


class MergedRecordDelta(BaseModel):
    """
    Class for storing the delta after merging a table record:
    original_record: Existing record under the RES environment before applying snapshot
    snapshot_record: Record from the snapshot to apply
    resolved_record: Record being merged after resolving the conflict between original_record and snapshot_record
    action_performed: Action performed for applying snapshot
    """
    original_record: Optional[Dict] = None
    snapshot_record: Dict
    resolved_record: Optional[Dict] = None
    action_performed: Optional[MergedRecordActionType] = None
