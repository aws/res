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
    GetSessionScreenshotRequest,
    GetSessionScreenshotResponse,
    GetModuleInfoRequest,
    GetModuleInfoResult,
} from "./data-model";
import IdeaBaseClient, { IdeaBaseClientProps } from "./base-client";

import {
    VirtualDesktopApi,
    ListSoftwareStacksResponseContent,
    VirtualDesktopApiListSoftwareStacksRequest,
    ListSessionPermissionsResponseContent,
    VirtualDesktopApiListSessionPermissionsRequest,
    UpdateSessionPermissionsRequestContent,
    UpdateSessionPermissionsResponseContent,
    ListSharedPermissionsResponseContent,
    VirtualDesktopApiListSharedPermissionsRequest,
    VirtualDesktopSessionPermission,
    VirtualDesktopSession,
    VirtualDesktopApiListSessionsRequest,
    ListSessionsResponseContent,
    VirtualDesktopApiGetSessionRequest,
    GetSessionResponseContent,
    CreateSessionRequestContent,
    CreateSessionResponseContent,
    UpdateSessionResponseContent,
	UpdateSessionRequestContent,
    BatchStopSessionRequestContent,
    BatchStopSessionResponseContent,
    BatchDeleteSessionRequestContent,
    BatchDeleteSessionResponseContent,
    BatchRebootSessionRequestContent,
    BatchRebootSessionResponseContent,
    BatchStartSessionRequestContent,
    BatchStartSessionResponseContent,
    GetSessionConnectionRequestContent,
    GetSessionConnectionResponseContent,
} from "./generated/api";
import { Configuration } from "./generated/configuration";

export interface VirtualDesktopClientProps extends IdeaBaseClientProps {}

class VirtualDesktopClient extends IdeaBaseClient<VirtualDesktopClientProps> {

    private generatedClient: VirtualDesktopApi;

    constructor(props: VirtualDesktopClientProps) {
        super(props);

        const config = new Configuration({
            basePath: this.getApiEndpoint(),
            accessToken: async () => await this.getAccessToken(),
        });

        this.generatedClient = new VirtualDesktopApi(config);
    }

    private getApiEndpoint(): string {
        return this.props.baseUrl;
    }

    private async getAccessToken(): Promise<string> {
        if (this.props.authContext?.getAccessToken) {
            return await this.props.authContext.getAccessToken();
        }
        return '';
    }

    async listSoftwareStacks(request: VirtualDesktopApiListSoftwareStacksRequest): Promise<ListSoftwareStacksResponseContent> {
        try {
            const response = await this.generatedClient.listSoftwareStacks({
                baseOs: request.baseOs,
                projectId: request.projectId,
                softwareStackName: request.softwareStackName,
                nextToken: request.nextToken,
            });

            return response.data;
        } catch (error) {
            console.warn('Generated client failed, returning empty response:', error);
            return {
                paginator: undefined,
                sort_by: undefined,
                data_range: undefined,
                listing: [],
                filters: []
            };
        }
    }

    async updateSessionPermissions(req: UpdateSessionPermissionsRequestContent): Promise<UpdateSessionPermissionsResponseContent> {
        const response = await this.generatedClient.updateSessionPermissions({
            updateSessionPermissionsRequestContent: req
        });
        return response.data;
    }

    async listSessionPermissions(request: VirtualDesktopApiListSessionPermissionsRequest): Promise<ListSessionPermissionsResponseContent> {
        try {

            let allPermissions: VirtualDesktopSessionPermission[] = [];
            let nextToken = request.nextToken;
            let lastResponse;

            do {
                const response = await this.generatedClient.listSessionPermissions({
                    resSessionId: request.resSessionId,
                    nextToken: nextToken,
                });

                lastResponse = response;
                allPermissions.push(...(response.data.listing || []));
                nextToken = response.data.nextToken;
            } while (nextToken);

            return {
                ...lastResponse.data,
                listing: allPermissions,
                nextToken: undefined
            };
        } catch (error) {
            console.warn('Failed to list session permissions, returning empty response:', error);
            return {
                paginator: undefined,
                sort_by: undefined,
                data_range: undefined,
                listing: [],
                filters: []
            };
        }
    }

    async listSharedPermissions(request: VirtualDesktopApiListSharedPermissionsRequest): Promise<ListSharedPermissionsResponseContent> {
        try {

            let allPermissions: VirtualDesktopSessionPermission[] = [];
            let nextToken = request.nextToken;
            let lastResponse;

            do {
                const response = await this.generatedClient.listSharedPermissions({
                    username: request.username,
                    sessionName: request.sessionName,
                    state: request.state,
                    baseOs: request.baseOs,
                    dateRangeKey: request.dateRangeKey,
                    after: request.after,
                    before: request.before,
                    nextToken: nextToken,
                });

                lastResponse = response;
                allPermissions.push(...(response.data.listing || []));
                nextToken = response.data.nextToken;
            } while (nextToken);

            return {
                ...lastResponse.data,
                listing: allPermissions,
                nextToken: undefined
            };
        } catch (error) {
            console.warn('Failed to list shared permissions, returning empty response:', error);
            return {
                paginator: undefined,
                sort_by: undefined,
                data_range: undefined,
                listing: [],
                filters: []
            };
        }
    }

    async listSessions(request: VirtualDesktopApiListSessionsRequest): Promise<ListSessionsResponseContent> {
        try {

            let allSessions: VirtualDesktopSession[] = [];
            let nextToken = request.nextToken;
            let lastResponse;

            do {
                const response = await this.generatedClient.listSessions({
                    baseOs: request.baseOs,
                    state: request.state,
                    sessionName: request.sessionName,
                    stackId: request.stackId,
                    dateRangeKey: request.dateRangeKey,
                    after: request.after,
                    before: request.before,
                    nextToken: nextToken,
                    owner: request.owner,
                });

                lastResponse = response;
                allSessions.push(...(response.data.listing || []));
                nextToken = response.data.nextToken;
            } while (nextToken);

            return {
                ...lastResponse.data,
                listing: allSessions
            };
        } catch (error) {
            console.warn('Generated client failed, returning empty response:', error);
            return {
                paginator: undefined,
                sort_by: undefined,
                data_range: undefined,
                listing: [],
                filters: []
            };
        }
    }

    async getSession(request: VirtualDesktopApiGetSessionRequest): Promise<GetSessionResponseContent> {
        const response = await this.generatedClient.getSession({
            resSessionId: request.resSessionId,
            owner: request.owner
        });
        return response.data;
    }

    async createSession(request: CreateSessionRequestContent): Promise<CreateSessionResponseContent> {
        try {
            const response = await this.generatedClient.createSession({
                createSessionRequestContent: request
            });

            return response.data;
        } catch (error) {
            console.warn('Generated client failed:', error);
            throw error;
        }
    }

    async updateSession(resSessionId: string, req: UpdateSessionRequestContent): Promise<UpdateSessionResponseContent> {
        const response = await this.generatedClient.updateSession({
            resSessionId: resSessionId,
            updateSessionRequestContent: req
        });
        return response.data;
    }

    async batchStopSession(req: BatchStopSessionRequestContent): Promise<BatchStopSessionResponseContent> {
        const response = await this.generatedClient.batchStopSession({
            batchStopSessionRequestContent: req
        });
        return response.data;
    }

    async batchDeleteSession(req: BatchDeleteSessionRequestContent): Promise<BatchDeleteSessionResponseContent> {
        const response = await this.generatedClient.batchDeleteSession({
            batchDeleteSessionRequestContent: req
        });
        return response.data;
    }

    async batchRebootSession(req: BatchRebootSessionRequestContent): Promise<BatchRebootSessionResponseContent> {
        const response = await this.generatedClient.batchRebootSession({
            batchRebootSessionRequestContent: req
        });
        return response.data;
    }
    async batchStartSession(req: BatchStartSessionRequestContent): Promise<BatchStartSessionResponseContent> {
        const response = await this.generatedClient.batchStartSession({
            batchStartSessionRequestContent: req
        });
        return response.data;
    }

    getModuleInfo(): Promise<GetModuleInfoRequest> {
        return this.apiInvoker.invoke_alt<GetModuleInfoRequest, GetModuleInfoResult>("App.GetModuleInfo", {});
    }

    getSessionScreenshot(req: GetSessionScreenshotRequest): Promise<GetSessionScreenshotResponse> {
        return this.apiInvoker.invoke_alt<GetSessionScreenshotRequest, GetSessionScreenshotResponse>("VirtualDesktop.GetSessionScreenshot", req);
    }

    async getSessionConnection(req: GetSessionConnectionRequestContent): Promise<GetSessionConnectionResponseContent> {
        const response = await this.generatedClient.getSessionConnection({
            getSessionConnectionRequestContent: req
        });
        return response.data;
    }
}

export default VirtualDesktopClient;
