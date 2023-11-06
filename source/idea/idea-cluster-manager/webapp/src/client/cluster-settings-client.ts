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
    ListClusterModulesRequest,
    ListClusterModulesResult,
    GetModuleSettingsRequest,
    GetModuleSettingsResult,
    UpdateModuleSettingsRequest,
    UpdateModuleSettingsResult,
    ListClusterHostsRequest,
    ListClusterHostsResult,
    DescribeInstanceTypesRequest,
    DescribeInstanceTypesResult,
    GetModuleInfoRequest,
    GetModuleInfoResult
} from "./data-model";
import IdeaBaseClient, { IdeaBaseClientProps } from "./base-client";

export interface ClusterSettingsClientProps extends IdeaBaseClientProps {}

class ClusterSettingsClient extends IdeaBaseClient<ClusterSettingsClientProps> {
    getModuleInfo(): Promise<GetModuleInfoRequest> {
        return this.apiInvoker.invoke_alt<GetModuleInfoRequest, GetModuleInfoResult>("App.GetModuleInfo", {});
    }

    listClusterModules(req: ListClusterModulesRequest): Promise<ListClusterModulesResult> {
        return this.apiInvoker.invoke_alt<ListClusterModulesRequest, ListClusterModulesResult>("ClusterSettings.ListClusterModules", req);
    }

    getModuleSettings(req: GetModuleSettingsRequest): Promise<GetModuleSettingsResult> {
        return this.apiInvoker.invoke_alt<GetModuleSettingsRequest, GetModuleSettingsResult>("ClusterSettings.GetModuleSettings", req);
    }

    updateModuleSettings(req: UpdateModuleSettingsRequest): Promise<UpdateModuleSettingsResult> {
        return this.apiInvoker.invoke_alt<UpdateModuleSettingsRequest, UpdateModuleSettingsResult>("ClusterSettings.UpdateModuleSettings", req);
    }

    listClusterHosts(req: ListClusterHostsRequest): Promise<ListClusterHostsResult> {
        return this.apiInvoker.invoke_alt<ListClusterHostsRequest, ListClusterHostsResult>("ClusterSettings.ListClusterHosts", req);
    }

    describeInstanceTypes(req: DescribeInstanceTypesRequest): Promise<DescribeInstanceTypesResult> {
        return this.apiInvoker.invoke_alt<DescribeInstanceTypesRequest, DescribeInstanceTypesResult>("ClusterSettings.DescribeInstanceTypes", req);
    }
}

export default ClusterSettingsClient;
