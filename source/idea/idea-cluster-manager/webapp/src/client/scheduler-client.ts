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

import { GetInstanceTypeOptionsRequest, GetInstanceTypeOptionsResult, GetUserApplicationsRequest, GetUserApplicationsResult, ListJobsRequest, ListJobsResult, SubmitJobRequest, SubmitJobResult, DeleteJobRequest, DeleteJobResult, GetModuleInfoRequest, GetModuleInfoResult } from "./data-model";
import IdeaBaseClient, { IdeaBaseClientProps } from "./base-client";

export interface SchedulerClientProps extends IdeaBaseClientProps {}

class SchedulerClient extends IdeaBaseClient<SchedulerClientProps> {
    getModuleInfo(): Promise<GetModuleInfoRequest> {
        return this.apiInvoker.invoke_alt<GetModuleInfoRequest, GetModuleInfoResult>("App.GetModuleInfo", {});
    }

    listActiveJobs(req: ListJobsRequest): Promise<ListJobsResult> {
        return this.apiInvoker.invoke_alt<ListJobsRequest, ListJobsResult>("Scheduler.ListActiveJobs", req);
    }

    listCompletedJobs(req: ListJobsRequest): Promise<ListJobsResult> {
        return this.apiInvoker.invoke_alt<ListJobsRequest, ListJobsResult>("Scheduler.ListCompletedJobs", req);
    }

    getUserApplications(req: GetUserApplicationsRequest): Promise<GetUserApplicationsResult> {
        return this.apiInvoker.invoke_alt<GetUserApplicationsRequest, GetUserApplicationsResult>("Scheduler.GetUserApplications", req);
    }

    submitJob(req: SubmitJobRequest): Promise<SubmitJobResult> {
        return this.apiInvoker.invoke_alt<SubmitJobRequest, SubmitJobResult>("Scheduler.SubmitJob", req);
    }

    getInstanceTypeOptions(req: GetInstanceTypeOptionsRequest): Promise<GetInstanceTypeOptionsResult> {
        return this.apiInvoker.invoke_alt<GetInstanceTypeOptionsRequest, GetInstanceTypeOptionsResult>("Scheduler.GetInstanceTypeOptions", req);
    }

    deleteJob(req: DeleteJobRequest): Promise<DeleteJobResult> {
        return this.apiInvoker.invoke_alt<DeleteJobRequest, DeleteJobResult>("Scheduler.DeleteJob", req);
    }
}

export default SchedulerClient;
