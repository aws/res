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

import { DescribeServersRequest, DescribeServersResponse, DescribeSessionsRequest, DescribeSessionsResponse } from "./data-model";
import IdeaBaseClient, { IdeaBaseClientProps } from "./base-client";

export interface VirtualDesktopDCVClientProps extends IdeaBaseClientProps {}

class VirtualDesktopDCVClient extends IdeaBaseClient<VirtualDesktopDCVClientProps> {
    describeSessions(req: DescribeSessionsRequest): Promise<DescribeSessionsResponse> {
        return this.apiInvoker.invoke_alt<DescribeSessionsRequest, DescribeSessionsResponse>("VirtualDesktopDCV.DescribeSessions", req);
    }

    describeServers(req: DescribeServersRequest): Promise<DescribeServersResponse> {
        return this.apiInvoker.invoke_alt<DescribeServersRequest, DescribeServersResponse>("VirtualDesktopDCV.DescribeServers", req);
    }
}

export default VirtualDesktopDCVClient;
