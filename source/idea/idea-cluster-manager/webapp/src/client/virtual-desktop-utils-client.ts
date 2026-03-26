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

import {
    ListAllowedInstanceTypesResponseContent,
    ListAllowedInstanceTypesForSessionResponseContent,
    VirtualDesktopUtilsApi,
    VirtualDesktopUtilsApiListAllowedInstanceTypesRequest,
    VirtualDesktopUtilsApiListAllowedInstanceTypesForSessionRequest,
    VirtualDesktopUtilsApiListPermissionProfilesRequest,
    ListPermissionProfilesResponseContent,
    VirtualDesktopUtilsApiGetPermissionProfileRequest,
    GetPermissionProfileResponseContent,
    VirtualDesktopPermissionProfile
} from "./generated/api";
import { Configuration } from "./generated/configuration";

export interface VirtualDesktopUtilsClientProps extends IdeaBaseClientProps { }

class VirtualDesktopUtilsClient extends IdeaBaseClient<VirtualDesktopUtilsClientProps> {
    private generatedClient: VirtualDesktopUtilsApi;

    constructor(props: VirtualDesktopUtilsClientProps) {
        super(props);

        const config = new Configuration({
            basePath: this.getApiEndpoint(),
            accessToken: async () => await this.getAccessToken(),
        });

        this.generatedClient = new VirtualDesktopUtilsApi(config);
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

    async listPermissionProfiles(request: VirtualDesktopUtilsApiListPermissionProfilesRequest): Promise<ListPermissionProfilesResponseContent> {
        try {
            let allProfiles: VirtualDesktopPermissionProfile[] = [];
            let nextToken = request.nextToken;
            let lastResponse;

            do {
                const response = await this.generatedClient.listPermissionProfiles({
                    profileId: request.profileId,
                    nextToken: nextToken
                });
                
                lastResponse = response;
                allProfiles.push(...(response.data.listing || []));
                nextToken = response.data.nextToken;
            } while (nextToken);

            return {
                ...lastResponse.data,
                listing: allProfiles,
                nextToken: undefined
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

    async getPermissionProfile(request: VirtualDesktopUtilsApiGetPermissionProfileRequest): Promise<GetPermissionProfileResponseContent> {
        try {
            const response = await this.generatedClient.getPermissionProfile({
                profileId: request.profileId
            });

            return response.data;
        } catch (error) {
            console.warn('Generated client failed, returning empty response:', error);
            return {
                profile: {
                    profile_id: "",
                    title: "",
                    description: "",
                    permissions: [],
                    created_on: undefined,
                    updated_on: undefined
                }
            };
        }
    }

    async listAllowedInstanceTypes(request: VirtualDesktopUtilsApiListAllowedInstanceTypesRequest): Promise<ListAllowedInstanceTypesResponseContent> {
        try {
            const response = await this.generatedClient.listAllowedInstanceTypes(request);

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

    async listAllowedInstanceTypesForSession(request: VirtualDesktopUtilsApiListAllowedInstanceTypesForSessionRequest): Promise<ListAllowedInstanceTypesForSessionResponseContent> {
        try {
            const response = await this.generatedClient.listAllowedInstanceTypesForSession(request);

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
}

export default VirtualDesktopUtilsClient;
