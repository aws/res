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

from ideasdk.api import BaseAPI, ApiInvocationContext
from ideadatamodel.snapshots import (
    CreateSnapshotRequest,
    CreateSnapshotResult,
    ListSnapshotsRequest
)
from ideadatamodel import exceptions
from ideasdk.utils import Utils

import ideaclustermanager


class SnapshotsAPI(BaseAPI):

    def __init__(self, context: ideaclustermanager.AppContext):
        self.context = context

        self.SCOPE_WRITE = f'{self.context.module_id()}/write'
        self.SCOPE_READ = f'{self.context.module_id()}/read'

        self.acl = {
            'Snapshots.CreateSnapshot': {
                'scope': self.SCOPE_WRITE,
                'method': self.create_snapshot
            },
            'Snapshots.ListSnapshots': {
                'scope': self.SCOPE_READ,
                'method': self.list_snapshots
            }
        }

    def create_snapshot(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(CreateSnapshotRequest)
        if Utils.is_empty(request.snapshot):
            raise exceptions.invalid_params('Snapshot is empty.')

        self.context.snapshots.create_snapshot(request.snapshot)
        context.success(CreateSnapshotResult(
            result='Successfully created Snapshot.'
        ))

    def list_snapshots(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(ListSnapshotsRequest)
        result = self.context.snapshots.list_snapshots(request)
        context.success(result)

    def invoke(self, context: ApiInvocationContext):
        namespace = context.namespace

        acl_entry = Utils.get_value_as_dict(namespace, self.acl)
        if acl_entry is None:
            raise exceptions.unauthorized_access()

        acl_entry_scope = Utils.get_value_as_string('scope', acl_entry)
        is_authorized = context.is_authorized(elevated_access=True, scopes=[acl_entry_scope])

        if is_authorized:
            acl_entry['method'](context)
        else:
            raise exceptions.unauthorized_access()
