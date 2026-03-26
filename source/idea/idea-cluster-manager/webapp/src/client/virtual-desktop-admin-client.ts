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
    GetModuleInfoRequest,
    GetModuleInfoResult,
    RebootSessionRequest,
    RebootSessionResponse,
    CreateSoftwareStackFromSessionRequest,
    CreateSoftwareStackFromSessionResponse,
    VirtualDesktopSessionConnectionInfo,
    GetSessionConnectionInfoRequest,
    GetSessionConnectionInfoResponse
} from "./data-model";
import IdeaBaseClient, { IdeaBaseClientProps } from "./base-client";
import {
    VirtualDesktopApi,
    CreateSoftwareStackResponseContent,
    CreateSoftwareStackRequestContent,
    DeleteSoftwareStackRequestContent,
    DeleteSoftwareStackResponseContent,
    UpdateSoftwareStackRequestContent,
    UpdateSoftwareStackResponseContent,
    CreatePermissionProfileRequestContent,
    CreatePermissionProfileResponseContent,
    UpdatePermissionProfileRequestContent,
    UpdatePermissionProfileResponseContent,
    UpdateSessionPermissionsRequestContent,
    UpdateSessionPermissionsResponseContent,
    VirtualDesktopApiGetSoftwareStackRequest,
    GetSoftwareStackResponseContent,
    VirtualDesktopApiGetSessionRequest,
    GetSessionResponseContent
} from "./generated/api";
import { Configuration } from "./generated/configuration";

export interface VirtualDesktopAdminClientProps extends IdeaBaseClientProps {}

class VirtualDesktopAdminClient extends IdeaBaseClient<VirtualDesktopAdminClientProps> {

    private generatedClient: VirtualDesktopApi;

    constructor(props: VirtualDesktopAdminClientProps) {
        super(props);

        const config = new Configuration({
            basePath: this.getApiEndpoint(),
            accessToken: async () => await this.getAccessToken(),
        });
        this.generatedClient = new VirtualDesktopApi(config);
    }

    private async getAccessToken(): Promise<string> {
        if (this.props.authContext?.getAccessToken) {
            return await this.props.authContext.getAccessToken();
        }
        return '';
    }

    private getApiEndpoint(): string {
        return this.props.baseUrl;
    }

    async createSoftwareStack(req: CreateSoftwareStackRequestContent): Promise<CreateSoftwareStackResponseContent> {
        const response = await this.generatedClient.createSoftwareStack({
            createSoftwareStackRequestContent: req
        });
        return response.data;
    }

    async deleteSoftwareStack(stackId: string, req: DeleteSoftwareStackRequestContent): Promise<DeleteSoftwareStackResponseContent> {
        const response = await this.generatedClient.deleteSoftwareStack({
            stackId: stackId,
            deleteSoftwareStackRequestContent: req
        });
        return response.data;
    }

    async updateSoftwareStack(stackId: string, req: UpdateSoftwareStackRequestContent): Promise<UpdateSoftwareStackResponseContent> {
        const response = await this.generatedClient.updateSoftwareStack({
            stackId: stackId,
            updateSoftwareStackRequestContent: req
        });
        return response.data;
    }

    async getSoftwareStack(request: VirtualDesktopApiGetSoftwareStackRequest): Promise<GetSoftwareStackResponseContent> {
        try {
            const response = await this.generatedClient.getSoftwareStack({
                stackId: request.stackId,
                baseOs: request.baseOs
            });

            return response.data;
        } catch (error) {
            console.warn('Generated client failed, returning empty response:', error);
            return {};
        }
    }


    async createPermissionProfile(req: CreatePermissionProfileRequestContent): Promise<CreatePermissionProfileResponseContent> {
        const response = await this.generatedClient.createPermissionProfile({
            createPermissionProfileRequestContent: req
        });
        return response.data;
    }

    async updatePermissionProfile(profileId: string, req: UpdatePermissionProfileRequestContent): Promise<UpdatePermissionProfileResponseContent> {
        const response = await this.generatedClient.updatePermissionProfile({
            profileId: profileId,
            updatePermissionProfileRequestContent: req
        });
        return response.data;
    }

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

    getSessionConnectionInfo(req: GetSessionConnectionInfoRequest): Promise<GetSessionConnectionInfoResponse> {
        return this.apiInvoker.invoke_alt<GetSessionConnectionInfoRequest, GetSessionConnectionInfoRequest>("VirtualDesktopAdmin.GetSessionConnectionInfo", req);
    }

    createSoftwareStackFromSession(req: CreateSoftwareStackFromSessionRequest): Promise<CreateSoftwareStackFromSessionResponse> {
        return this.apiInvoker.invoke_alt<CreateSoftwareStackFromSessionRequest, CreateSoftwareStackFromSessionResponse>("VirtualDesktopAdmin.CreateSoftwareStackFromSession", req);
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
