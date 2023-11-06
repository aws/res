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
    CreateSessionRequest,
    CreateSessionResponse,
    GetSessionInfoRequest,
    GetSessionInfoResponse,
    UpdateSessionRequest,
    UpdateSessionResponse,
    DeleteSessionRequest,
    DeleteSessionResponse,
    ListSessionsRequest,
    ListSessionsResponse,
    GetSessionScreenshotRequest,
    GetSessionScreenshotResponse,
    StopSessionRequest,
    StopSessionResponse,
    ResumeSessionsRequest,
    ResumeSessionsResponse,
    GetSessionConnectionInfoRequest,
    GetSessionConnectionInfoResponse,
    ListSoftwareStackRequest,
    ListSoftwareStackResponse,
    GetModuleInfoRequest,
    GetModuleInfoResult,
    RebootSessionResponse,
    RebootSessionRequest,
    UpdateSessionPermissionRequest,
    UpdateSessionPermissionResponse,
    ListPermissionsRequest,
    ListPermissionsResponse,
    VirtualDesktopSessionConnectionInfo,
} from "./data-model";
import IdeaBaseClient, { IdeaBaseClientProps } from "./base-client";

export interface VirtualDesktopClientProps extends IdeaBaseClientProps {}

class VirtualDesktopClient extends IdeaBaseClient<VirtualDesktopClientProps> {
    getModuleInfo(): Promise<GetModuleInfoRequest> {
        return this.apiInvoker.invoke_alt<GetModuleInfoRequest, GetModuleInfoResult>("App.GetModuleInfo", {});
    }

    createSession(req: CreateSessionRequest): Promise<CreateSessionResponse> {
        return this.apiInvoker.invoke_alt<CreateSessionRequest, CreateSessionResponse>("VirtualDesktop.CreateSession", req);
    }

    updateSession(req: UpdateSessionRequest): Promise<UpdateSessionResponse> {
        return this.apiInvoker.invoke_alt<UpdateSessionRequest, UpdateSessionResponse>("VirtualDesktop.UpdateSession", req);
    }

    deleteSessions(req: DeleteSessionRequest): Promise<DeleteSessionResponse> {
        return this.apiInvoker.invoke_alt<DeleteSessionRequest, DeleteSessionResponse>("VirtualDesktop.DeleteSessions", req);
    }

    getSessionInfo(req: GetSessionInfoRequest): Promise<GetSessionInfoResponse> {
        return this.apiInvoker.invoke_alt<GetSessionInfoRequest, GetSessionInfoResponse>("VirtualDesktop.GetSessionInfo", req);
    }

    getSessionScreenshot(req: GetSessionScreenshotRequest): Promise<GetSessionScreenshotResponse> {
        return this.apiInvoker.invoke_alt<GetSessionScreenshotRequest, GetSessionScreenshotResponse>("VirtualDesktop.GetSessionScreenshot", req);
    }

    getSessionConnectionInfo(req: GetSessionConnectionInfoRequest): Promise<GetSessionConnectionInfoResponse> {
        return this.apiInvoker.invoke_alt<GetSessionConnectionInfoRequest, GetSessionConnectionInfoResponse>("VirtualDesktop.GetSessionConnectionInfo", req);
    }

    listSessions(req: ListSessionsRequest): Promise<ListSessionsResponse> {
        return this.apiInvoker.invoke_alt<ListSessionsRequest, ListSessionsResponse>("VirtualDesktop.ListSessions", req);
    }

    stopSessions(req: StopSessionRequest): Promise<StopSessionResponse> {
        return this.apiInvoker.invoke_alt<StopSessionRequest, StopSessionResponse>("VirtualDesktop.StopSessions", req);
    }

    resumeSessions(req: ResumeSessionsRequest): Promise<ResumeSessionsResponse> {
        return this.apiInvoker.invoke_alt<ResumeSessionsRequest, ResumeSessionsResponse>("VirtualDesktop.ResumeSessions", req);
    }

    rebootSessions(req: RebootSessionRequest): Promise<RebootSessionResponse> {
        return this.apiInvoker.invoke_alt<RebootSessionRequest, RebootSessionResponse>("VirtualDesktop.RebootSessions", req);
    }

    listSoftwareStacks(req: ListSoftwareStackRequest): Promise<ListSoftwareStackResponse> {
        return this.apiInvoker.invoke_alt<ListSoftwareStackRequest, ListSoftwareStackResponse>("VirtualDesktop.ListSoftwareStacks", req);
    }

    listSharedPermissions(req: ListPermissionsRequest): Promise<ListPermissionsResponse> {
        return this.apiInvoker.invoke_alt<ListPermissionsRequest, ListPermissionsResponse>("VirtualDesktop.ListSharedPermissions", req);
    }

    listSessionPermissions(req: ListPermissionsRequest): Promise<ListPermissionsResponse> {
        return this.apiInvoker.invoke_alt<ListPermissionsRequest, ListPermissionsResponse>("VirtualDesktop.ListSessionPermissions", req);
    }

    updateSessionPermissions(req: UpdateSessionPermissionRequest): Promise<UpdateSessionPermissionResponse> {
        return this.apiInvoker.invoke_alt<UpdateSessionPermissionRequest, UpdateSessionPermissionResponse>("VirtualDesktop.UpdateSessionPermissions", req);
    }
}

export default VirtualDesktopClient;
