/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 *
 * Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
 * with the License. A copy of the License is located at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
 * OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
 * and limitations under the License.
 */

import {
    GetModuleInfoRequest,
    GetModuleInfoResult,
    CreateSnapshotRequest,
    CreateSnapshotResult,
    ListSnapshotsRequest,
    ListSnapshotsResult
} from "./data-model";
import IdeaBaseClient, { IdeaBaseClientProps } from "./base-client";

export interface SnapshotsClientProps extends IdeaBaseClientProps {}

class SnapshotsClient extends IdeaBaseClient<SnapshotsClientProps> {
    getModuleInfo(): Promise<GetModuleInfoRequest> {
        return this.apiInvoker.invoke_alt<GetModuleInfoRequest, GetModuleInfoResult>("App.GetModuleInfo", {});
    }
    createSnapshot(req: CreateSnapshotRequest): Promise<CreateSnapshotResult> {
        return this.apiInvoker.invoke_alt<CreateSnapshotRequest, CreateSnapshotResult>("Snapshots.CreateSnapshot", req);
    }

    listSnapshots(req?: ListSnapshotsRequest): Promise<ListSnapshotsResult> {
        return this.apiInvoker.invoke_alt<ListSnapshotsRequest, ListSnapshotsResult>("Snapshots.ListSnapshots", req);
    }
}

export default SnapshotsClient;
