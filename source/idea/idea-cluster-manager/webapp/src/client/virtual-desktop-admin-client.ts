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
    VirtualDesktopApiGetSoftwareStackRequest,
    GetSoftwareStackResponseContent,
    GetSessionConnectionRequestContent,
    GetSessionConnectionResponseContent,
    CreateSoftwareStackFromSessionRequestContent,
    CreateSoftwareStackFromSessionResponseContent,
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

    async getSessionConnection(req: GetSessionConnectionRequestContent): Promise<GetSessionConnectionResponseContent> {
        const response = await this.generatedClient.getSessionConnection({
            getSessionConnectionRequestContent: req
        });
        return response.data;
    }

    async createSoftwareStackFromSession(req: CreateSoftwareStackFromSessionRequestContent): Promise<CreateSoftwareStackFromSessionResponseContent> {
        const response = await this.generatedClient.createSoftwareStackFromSession({
            createSoftwareStackFromSessionRequestContent: req
        });
        return response.data;
    }

    joinSession(idea_session_id: string, idea_session_owner: string): Promise<boolean> {
        return new Promise<boolean>(() => {
            this.getSessionConnection({
                connection: {
                    idea_session_id: idea_session_id,
                    idea_session_owner: idea_session_owner,
                },
            })
                .then((result) => {
                    return `${result.connection?.endpoint}${result.connection?.['web_url_path']}?authToken=${result.connection?.['access_token']}#${result.connection?.['idea_session_id']}`;
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
