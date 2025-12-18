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

import IdeaBaseClient, { IdeaBaseClientProps } from "./base-client";
import { BatchGetDCVSessionsRequestContent, BatchGetDCVSessionsResponseContent, ListDCVServersResponseContent, VirtualDesktopDcvApi, VirtualDesktopDcvApiListDCVServersRequest } from "./generated/api";
import { Configuration } from "./generated/configuration";

export interface VirtualDesktopDCVClientProps extends IdeaBaseClientProps { }

class VirtualDesktopDCVClient extends IdeaBaseClient<VirtualDesktopDCVClientProps> {
    private generatedClient: VirtualDesktopDcvApi;

    constructor(props: VirtualDesktopDCVClientProps) {
        super(props);

        const config = new Configuration({
            basePath: this.getApiEndpoint(),
            accessToken: async () => await this.getAccessToken(),
        });
        this.generatedClient = new VirtualDesktopDcvApi(config);
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

    async listDCVServers(req?: VirtualDesktopDcvApiListDCVServersRequest): Promise<ListDCVServersResponseContent> {
        try {
            const response = await this.generatedClient.listDCVServers({
                nextToken: req?.nextToken
            });
            return response.data;
        } catch (error) {
            console.warn('Generated client failed, returning empty response:', error);
            return {
                response: {}
            }
        }
    }

    async batchGetDCVSessions(req?: BatchGetDCVSessionsRequestContent): Promise<BatchGetDCVSessionsResponseContent> {
        try {
            const response = await this.generatedClient.batchGetDCVSessions({
                batchGetDCVSessionsRequestContent: req
            });
            return response.data;
        } catch (error) {
            console.warn('Generated client failed, returning empty response:', error);
            return {
                response: {}
            }
        }
    }
}

export default VirtualDesktopDCVClient;
