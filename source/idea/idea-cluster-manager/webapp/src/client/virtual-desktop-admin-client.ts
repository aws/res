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
    BatchCreateSessionRequest,
    BatchCreateSessionResponse,
    StopSessionRequest,
    StopSessionResponse,
    ResumeSessionsRequest,
    ResumeSessionsResponse,
    ListSoftwareStackRequest,
    ListSoftwareStackResponse,
    CreateSoftwareStackRequest,
    CreateSoftwareStackResponse,
    UpdateSoftwareStackRequest,
    UpdateSoftwareStackResponse,
    DeleteSoftwareStackRequest,
    DeleteSoftwareStackResponse,
    GetModuleInfoRequest,
    GetModuleInfoResult,
    RebootSessionRequest,
    RebootSessionResponse,
    CreateSoftwareStackFromSessionRequest,
    CreateSoftwareStackFromSessionResponse,
    VirtualDesktopSessionConnectionInfo,
    GetSessionConnectionInfoRequest,
    CreatePermissionProfileResponse,
    CreatePermissionProfileRequest,
    ListPermissionsRequest,
    ListPermissionsResponse,
    GetSoftwareStackInfoResponse,
    GetSoftwareStackInfoRequest,
    UpdatePermissionProfileResponse,
    UpdatePermissionProfileRequest,
    UpdateSessionPermissionRequest,
    UpdateSessionPermissionResponse,
} from "./data-model";
import IdeaBaseClient, { IdeaBaseClientProps } from "./base-client";

export interface VirtualDesktopAdminClientProps extends IdeaBaseClientProps {}

class VirtualDesktopAdminClient extends IdeaBaseClient<VirtualDesktopAdminClientProps> {
    getModuleInfo(): Promise<GetModuleInfoRequest> {
        return this.apiInvoker.invoke_alt<GetModuleInfoRequest, GetModuleInfoResult>("App.GetModuleInfo", {});
    }

    createSession(req: CreateSessionRequest): Promise<CreateSessionResponse> {
        return this.apiInvoker.invoke_alt<CreateSessionRequest, CreateSessionResponse>("VirtualDesktopAdmin.CreateSession", req);
    }

    batchCreateSessions(req: BatchCreateSessionRequest): Promise<BatchCreateSessionResponse> {
        return this.apiInvoker.invoke_alt<BatchCreateSessionRequest, BatchCreateSessionResponse>("VirtualDesktopAdmin.BatchCreateSessions", req);
    }

    updateSession(req: UpdateSessionRequest): Promise<UpdateSessionResponse> {
        return this.apiInvoker.invoke_alt<UpdateSessionRequest, UpdateSessionResponse>("VirtualDesktopAdmin.UpdateSession", req);
    }

    deleteSessions(req: DeleteSessionRequest): Promise<DeleteSessionResponse> {
        return this.apiInvoker.invoke_alt<DeleteSessionRequest, DeleteSessionResponse>("VirtualDesktopAdmin.DeleteSessions", req);
    }

    getSessionInfo(req: GetSessionInfoRequest): Promise<GetSessionInfoResponse> {
        return this.apiInvoker.invoke_alt<GetSessionInfoRequest, GetSessionInfoResponse>("VirtualDesktopAdmin.GetSessionInfo", req);
    }

    listSessions(req: ListSessionsRequest): Promise<ListSessionsResponse> {
        return this.apiInvoker.invoke_alt<ListSessionsRequest, ListSessionsResponse>("VirtualDesktopAdmin.ListSessions", req);
    }

    stopSessions(req: StopSessionRequest): Promise<StopSessionResponse> {
        return this.apiInvoker.invoke_alt<StopSessionRequest, StopSessionResponse>("VirtualDesktopAdmin.StopSessions", req);
    }

    rebootSessions(req: RebootSessionRequest): Promise<RebootSessionResponse> {
        return this.apiInvoker.invoke_alt<RebootSessionRequest, RebootSessionResponse>("VirtualDesktopAdmin.RebootSessions", req);
    }

    resumeSessions(req: ResumeSessionsRequest): Promise<ResumeSessionsResponse> {
        return this.apiInvoker.invoke_alt<ResumeSessionsRequest, ResumeSessionsResponse>("VirtualDesktopAdmin.ResumeSessions", req);
    }

    getSessionScreenshot(req: GetSessionScreenshotRequest): Promise<GetSessionScreenshotResponse> {
        return this.apiInvoker.invoke_alt<GetSessionScreenshotRequest, GetSessionScreenshotResponse>("VirtualDesktopAdmin.GetSessionScreenshot", req);
    }

    getSessionConnectionInfo(req: GetSessionConnectionInfoRequest): Promise<GetSessionConnectionInfoRequest> {
        return this.apiInvoker.invoke_alt<GetSessionConnectionInfoRequest, GetSessionConnectionInfoRequest>("VirtualDesktopAdmin.GetSessionConnectionInfo", req);
    }

    createSoftwareStack(req: CreateSoftwareStackRequest): Promise<CreateSoftwareStackResponse> {
        return this.apiInvoker.invoke_alt<CreateSoftwareStackRequest, CreateSoftwareStackResponse>("VirtualDesktopAdmin.CreateSoftwareStack", req);
    }

    updateSoftwareStack(req: UpdateSoftwareStackRequest): Promise<UpdateSoftwareStackResponse> {
        return this.apiInvoker.invoke_alt<UpdateSoftwareStackRequest, UpdateSoftwareStackResponse>("VirtualDesktopAdmin.UpdateSoftwareStack", req);
    }

    deleteSoftwareStack(req: DeleteSoftwareStackRequest): Promise<DeleteSoftwareStackResponse> {
        return this.apiInvoker.invoke_alt<DeleteSoftwareStackRequest, DeleteSoftwareStackResponse>("VirtualDesktopAdmin.DeleteSoftwareStack", req);
    }

    getSoftwareStackInfo(req: GetSoftwareStackInfoRequest): Promise<GetSoftwareStackInfoResponse> {
        return this.apiInvoker.invoke_alt<GetSoftwareStackInfoRequest, GetSoftwareStackInfoResponse>("VirtualDesktopAdmin.GetSoftwareStackInfo", req);
    }

    listSoftwareStacks(req: ListSoftwareStackRequest): Promise<ListSoftwareStackResponse> {
        return this.apiInvoker.invoke_alt<ListSoftwareStackRequest, ListSoftwareStackResponse>("VirtualDesktopAdmin.ListSoftwareStacks", req);
    }

    createSoftwareStackFromSession(req: CreateSoftwareStackFromSessionRequest): Promise<CreateSoftwareStackFromSessionResponse> {
        return this.apiInvoker.invoke_alt<CreateSoftwareStackFromSessionRequest, CreateSoftwareStackFromSessionResponse>("VirtualDesktopAdmin.CreateSoftwareStackFromSession", req);
    }

    createPermissionProfile(req: CreatePermissionProfileRequest): Promise<CreatePermissionProfileResponse> {
        return this.apiInvoker.invoke_alt<CreatePermissionProfileRequest, CreatePermissionProfileResponse>("VirtualDesktopAdmin.CreatePermissionProfile", req);
    }

    updatePermissionProfile(req: UpdatePermissionProfileRequest): Promise<UpdatePermissionProfileResponse> {
        return this.apiInvoker.invoke_alt<UpdatePermissionProfileRequest, UpdatePermissionProfileResponse>("VirtualDesktopAdmin.UpdatePermissionProfile", req);
    }

    listSessionPermissions(req: ListPermissionsRequest): Promise<ListPermissionsResponse> {
        return this.apiInvoker.invoke_alt<ListPermissionsRequest, ListPermissionsResponse>("VirtualDesktopAdmin.ListSessionPermissions", req);
    }

    listSharedPermissions(req: ListPermissionsRequest): Promise<ListPermissionsResponse> {
        return this.apiInvoker.invoke_alt<ListPermissionsRequest, ListPermissionsResponse>("VirtualDesktopAdmin.ListSharedPermissions", req);
    }

    updateSessionPermission(req: UpdateSessionPermissionRequest): Promise<UpdateSessionPermissionResponse> {
        return this.apiInvoker.invoke_alt<UpdateSessionPermissionRequest, UpdateSessionPermissionResponse>("VirtualDesktopAdmin.UpdateSessionPermissions", req);
    }

    joinSession(idea_session_id: string, idea_session_owner: string, username?: string): Promise<boolean> {
        return new Promise<boolean>(() => {
            let connection_info: VirtualDesktopSessionConnectionInfo = {
                idea_session_id: idea_session_id,
                idea_session_owner: idea_session_owner,
            };

            if (username) {
                connection_info.username = username;
            }

            this.getSessionConnectionInfo({
                connection_info: connection_info,
            })
                .then((result) => {
                    return `${result.connection_info?.endpoint}${result.connection_info?.web_url_path}?authToken=${result.connection_info?.access_token}#${result.connection_info?.dcv_session_id}`;
                })
                .then((url) => {
                    window.open(url);
                    return true;
                })
                .catch((error) => {
                    console.error(error);
                    return false;
                });
        });
    }
}

export default VirtualDesktopAdminClient;
