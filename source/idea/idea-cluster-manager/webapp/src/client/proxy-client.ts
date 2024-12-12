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
    DescribeMountTargetRequest, DescribeMountTargetResult,
    ListBudgetsRequest, ListEFSRequest, ListFSxRequest, ListFSxSVMRequest, ListFSxVolumeRequest,
    ListBudgetsResult, ListEFSResult, ListFSxResult, ListFSxSVMResult, ListFSxVolumeResult,
    ListClusterHostsResult,
} from "./data-model";
import IdeaBaseClient, { IdeaBaseClientProps } from "./base-client";
import { Constants } from "../common/constants";

export interface ProxyClientProps extends IdeaBaseClientProps {
}

class ProxyClient extends IdeaBaseClient<ProxyClientProps> {
    listBudgets(req: ListBudgetsRequest): Promise<ListBudgetsResult> {
        return this.apiInvoker.invoke_alt<ListBudgetsRequest, ListBudgetsResult>("budgets", req, false, true, {"X-Amz-Target": "AWSBudgetServiceGateway.DescribeBudgets"});
    }

    listEFS(req: ListEFSRequest): Promise<ListEFSResult> {
        return this.apiInvoker.invoke_alt(`${req.AWSRegion}/elasticfilesystem/2015-02-01/file-systems?MaxItems=${Constants.EFS_NUMBER_OF_FS_QUOTA * 10}`, undefined, false, true, {}, "GET");
    }

    describeEFSMountTarget(req: DescribeMountTargetRequest): Promise<DescribeMountTargetResult> {
        return this.apiInvoker.invoke_alt(`${req.AWSRegion}/elasticfilesystem/2015-02-01/mount-targets?FileSystemId=${req.FileSystemId}`, req, false, true, {}, "GET");
    }

    listFSx(req: ListFSxRequest): Promise<ListFSxResult> {
        return this.apiInvoker.invoke_alt(`${req.AWSRegion}/fsx`, undefined, false, true, {"X-Amz-Target": "AWSSimbaAPIService_v20180301.DescribeFileSystems"});
    }

    listFSxSVM(req: ListFSxSVMRequest): Promise<ListFSxSVMResult> {
        return this.apiInvoker.invoke_alt(`${req.AWSRegion}/fsx`, {"Filters": [{"Name": "file-system-id", "Values": req.FileSystemIds}]}, false, true, {"X-Amz-Target": "AWSSimbaAPIService_v20180301.DescribeStorageVirtualMachines"});
    }

    listFSxVolumes(req: ListFSxVolumeRequest): Promise<ListFSxVolumeResult> {
        return this.apiInvoker.invoke_alt(`${req.AWSRegion}/fsx`, {"Filters": [{"Name": "file-system-id", "Values": req.FileSystemIds}]}, false, true, {"X-Amz-Target": "AWSSimbaAPIService_v20180301.DescribeVolumes"});
    }

    listClusterHosts(req: any): Promise<ListClusterHostsResult> {
        return this.apiInvoker.invoke_alt<any, ListClusterHostsResult>(`${req.AWSRegion}/ec2`, req.QueryStringParameters, false, true, {"Content-Type": "text/plain"});
    }
}

export default ProxyClient;
