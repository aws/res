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
    ListSupportedOSRequest,
    ListSupportedOSResponse,
    ListAllowedInstanceTypesRequest,
    ListAllowedInstanceTypesResponse,
    ListAllowedInstanceTypesForSessionResponse,
    ListAllowedInstanceTypesForSessionRequest,
    ListPermissionProfilesRequest,
    ListPermissionProfilesResponse,
    GetBasePermissionsRequest,
    GetBasePermissionsResponse,
    ListSupportedGPURequest,
    ListSupportedGPUResponse,
    ListScheduleTypesRequest,
    ListScheduleTypesResponse,
    GetPermissionProfileRequest,
    GetPermissionProfileResponse,
} from "./data-model";
import IdeaBaseClient, { IdeaBaseClientProps } from "./base-client";

export interface VirtualDesktopUtilsClientProps extends IdeaBaseClientProps {}

class VirtualDesktopUtilsClient extends IdeaBaseClient<VirtualDesktopUtilsClientProps> {
    listSupportedOS(req: ListSupportedOSRequest): Promise<ListSupportedOSResponse> {
        return this.apiInvoker.invoke_alt<ListSupportedOSRequest, ListSupportedOSResponse>("VirtualDesktopUtils.ListSupportedOS", req);
    }

    listSupportedGPUs(req: ListSupportedGPURequest): Promise<ListSupportedGPUResponse> {
        return this.apiInvoker.invoke_alt<ListSupportedGPURequest, ListSupportedGPUResponse>("VirtualDesktopUtils.ListSupportedGPU", req);
    }

    listScheduleTypes(req: ListScheduleTypesRequest): Promise<ListScheduleTypesResponse> {
        return this.apiInvoker.invoke_alt<ListScheduleTypesRequest, ListScheduleTypesResponse>("VirtualDesktopUtils.ListScheduleTypes", req);
    }

    listAllowedInstanceTypes(req: ListAllowedInstanceTypesRequest): Promise<ListAllowedInstanceTypesResponse> {
        return this.apiInvoker.invoke_alt<ListAllowedInstanceTypesRequest, ListAllowedInstanceTypesResponse>("VirtualDesktopUtils.ListAllowedInstanceTypes", req);
    }

    listAllowedInstanceTypesForSession(req: ListAllowedInstanceTypesForSessionRequest): Promise<ListAllowedInstanceTypesForSessionResponse> {
        return this.apiInvoker.invoke_alt<ListAllowedInstanceTypesForSessionRequest, ListAllowedInstanceTypesForSessionResponse>("VirtualDesktopUtils.ListAllowedInstanceTypesForSession", req);
    }

    getBasePermissions(req: GetBasePermissionsRequest): Promise<GetBasePermissionsResponse> {
        return this.apiInvoker.invoke_alt<GetBasePermissionsRequest, GetBasePermissionsResponse>("VirtualDesktopUtils.GetBasePermissions", req);
    }

    listPermissionProfiles(req: ListPermissionProfilesRequest): Promise<ListPermissionProfilesResponse> {
        return this.apiInvoker.invoke_alt<ListPermissionProfilesRequest, ListPermissionProfilesResponse>("VirtualDesktopUtils.ListPermissionProfiles", req);
    }

    getPermissionProfile(req: GetPermissionProfileRequest): Promise<GetPermissionProfileResponse> {
        return this.apiInvoker.invoke_alt<GetPermissionProfileRequest, GetPermissionProfileResponse>("VirtualDesktopUtils.GetPermissionProfile", req);
    }
}

export default VirtualDesktopUtilsClient;
