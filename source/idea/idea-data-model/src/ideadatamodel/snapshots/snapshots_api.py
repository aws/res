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
    'CreateSnapshotRequest',
    'CreateSnapshotResult',
    'ListSnapshotsRequest',
    'ListSnapshotsResult',
    'OPEN_API_SPEC_ENTRIES_SNAPSHOTS'
)

from ideadatamodel.api import SocaPayload, IdeaOpenAPISpecEntry, SocaListingPayload
from ideadatamodel.snapshots.snapshot_model import Snapshot

from typing import List, Optional


class CreateSnapshotRequest(SocaPayload):
    snapshot: Optional[Snapshot]


class CreateSnapshotResult(SocaPayload):
    snapshot: Optional[Snapshot]

class ListSnapshotsRequest(SocaListingPayload):
    pass


class ListSnapshotsResult(SocaListingPayload):
    listing: Optional[List[Snapshot]]


OPEN_API_SPEC_ENTRIES_SNAPSHOTS = [
    IdeaOpenAPISpecEntry(
        namespace='Snapshots.CreateSnapshot',
        request=CreateSnapshotRequest,
        result=CreateSnapshotResult,
        is_listing=False,
        is_public=False
    ),
    IdeaOpenAPISpecEntry(
        namespace='Snapshots.ListSnapshots',
        request=ListSnapshotsRequest,
        result=ListSnapshotsResult,
        is_listing=True,
        is_public=False
    ),
]
