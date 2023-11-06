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
    ListNodesRequest,
    ListNodesResult,
    ListJobsRequest,
    ListJobsResult,
    ListQueueProfilesRequest,
    ListQueueProfilesResult,
    EnableQueueProfileRequest,
    EnableQueueProfileResult,
    DisableQueueProfileRequest,
    DisableQueueProfileResult,
    CreateQueueProfileRequest,
    CreateQueueProfileResult,
    GetQueueProfileRequest,
    GetQueueProfileResult,
    UpdateQueueProfileRequest,
    UpdateQueueProfileResult,
    DeleteQueueProfileRequest,
    DeleteQueueProfileResult,
    CreateQueuesRequest,
    CreateQueuesResult,
    DeleteQueuesRequest,
    DeleteQueuesResult,
    ListHpcApplicationsRequest,
    ListHpcApplicationsResult,
    CreateHpcApplicationRequest,
    CreateHpcApplicationResult,
    GetHpcApplicationRequest,
    GetHpcApplicationResult,
    UpdateHpcApplicationRequest,
    UpdateHpcApplicationResult,
    DeleteHpcApplicationRequest,
    DeleteHpcApplicationResult,
    GetModuleInfoRequest,
    GetModuleInfoResult,
    GetUserApplicationsRequest,
    GetUserApplicationsResult,
    CreateHpcLicenseResourceRequest,
    CreateHpcLicenseResourceResult,
    GetHpcLicenseResourceRequest,
    GetHpcLicenseResourceResult,
    UpdateHpcLicenseResourceRequest,
    UpdateHpcLicenseResourceResult,
    DeleteHpcLicenseResourceRequest,
    DeleteHpcLicenseResourceResult,
    ListHpcLicenseResourcesRequest,
    ListHpcLicenseResourcesResult,
    CheckHpcLicenseResourceAvailabilityRequest,
    CheckHpcLicenseResourceAvailabilityResult,
    DeleteJobRequest,
    DeleteJobResult,
} from "./data-model";
import IdeaBaseClient, { IdeaBaseClientProps } from "./base-client";

export interface SchedulerAdminClientProps extends IdeaBaseClientProps {}

class SchedulerAdminClient extends IdeaBaseClient<SchedulerAdminClientProps> {
    getModuleInfo(): Promise<GetModuleInfoRequest> {
        return this.apiInvoker.invoke_alt<GetModuleInfoRequest, GetModuleInfoResult>("App.GetModuleInfo", {});
    }

    listActiveJobs(req: ListJobsRequest): Promise<ListJobsResult> {
        return this.apiInvoker.invoke_alt<ListJobsRequest, ListJobsResult>("SchedulerAdmin.ListActiveJobs", req);
    }

    listCompletedJobs(req: ListJobsRequest): Promise<ListJobsResult> {
        return this.apiInvoker.invoke_alt<ListJobsRequest, ListJobsResult>("SchedulerAdmin.ListCompletedJobs", req);
    }

    listNodes(req: ListNodesRequest): Promise<ListNodesResult> {
        return this.apiInvoker.invoke_alt<ListNodesRequest, ListNodesResult>("SchedulerAdmin.ListNodes", req);
    }

    createQueueProfile(req: CreateQueueProfileRequest): Promise<CreateQueueProfileResult> {
        return this.apiInvoker.invoke_alt<CreateQueueProfileRequest, CreateQueueProfileResult>("SchedulerAdmin.CreateQueueProfile", req);
    }

    getQueueProfile(req: GetQueueProfileRequest): Promise<GetQueueProfileResult> {
        return this.apiInvoker.invoke_alt<GetQueueProfileRequest, GetQueueProfileResult>("SchedulerAdmin.GetQueueProfile", req);
    }

    updateQueueProfile(req: UpdateQueueProfileRequest): Promise<UpdateQueueProfileResult> {
        return this.apiInvoker.invoke_alt<UpdateQueueProfileRequest, UpdateQueueProfileResult>("SchedulerAdmin.UpdateQueueProfile", req);
    }

    deleteQueueProfile(req: DeleteQueueProfileRequest): Promise<DeleteQueueProfileResult> {
        return this.apiInvoker.invoke_alt<DeleteQueueProfileRequest, DeleteQueueProfileResult>("SchedulerAdmin.DeleteQueueProfile", req);
    }

    enableQueueProfile(req: EnableQueueProfileRequest): Promise<EnableQueueProfileResult> {
        return this.apiInvoker.invoke_alt<EnableQueueProfileRequest, EnableQueueProfileResult>("SchedulerAdmin.EnableQueueProfile", req);
    }

    disableQueueProfile(req: DisableQueueProfileRequest): Promise<DisableQueueProfileResult> {
        return this.apiInvoker.invoke_alt<DisableQueueProfileRequest, DisableQueueProfileResult>("SchedulerAdmin.DisableQueueProfile", req);
    }

    listQueueProfiles(req: ListQueueProfilesRequest): Promise<ListQueueProfilesResult> {
        return this.apiInvoker.invoke_alt<ListQueueProfilesRequest, ListQueueProfilesResult>("SchedulerAdmin.ListQueueProfiles", req);
    }

    createQueues(req: CreateQueuesRequest): Promise<CreateQueuesResult> {
        return this.apiInvoker.invoke_alt<CreateQueuesRequest, CreateQueuesResult>("SchedulerAdmin.CreateQueues", req);
    }

    deleteQueues(req: DeleteQueuesRequest): Promise<DeleteQueuesResult> {
        return this.apiInvoker.invoke_alt<DeleteQueuesRequest, DeleteQueuesResult>("SchedulerAdmin.DeleteQueues", req);
    }

    createHpcApplication(req: CreateHpcApplicationRequest): Promise<CreateHpcApplicationResult> {
        return this.apiInvoker.invoke_alt<CreateHpcApplicationRequest, CreateHpcApplicationResult>("SchedulerAdmin.CreateHpcApplication", req);
    }

    getHpcApplication(req: GetHpcApplicationRequest): Promise<GetHpcApplicationResult> {
        return this.apiInvoker.invoke_alt<GetHpcApplicationRequest, GetHpcApplicationResult>("SchedulerAdmin.GetHpcApplication", req);
    }

    updateHpcApplication(req: UpdateHpcApplicationRequest): Promise<UpdateHpcApplicationResult> {
        return this.apiInvoker.invoke_alt<UpdateHpcApplicationRequest, UpdateHpcApplicationResult>("SchedulerAdmin.UpdateHpcApplication", req);
    }

    deleteHpcApplication(req: DeleteHpcApplicationRequest): Promise<DeleteHpcApplicationResult> {
        return this.apiInvoker.invoke_alt<DeleteHpcApplicationRequest, DeleteHpcApplicationResult>("SchedulerAdmin.DeleteHpcApplication", req);
    }

    listHpcApplications(req: ListHpcApplicationsRequest): Promise<ListHpcApplicationsResult> {
        return this.apiInvoker.invoke_alt<ListHpcApplicationsRequest, ListHpcApplicationsResult>("SchedulerAdmin.ListHpcApplications", req);
    }

    getUserApplications(req: GetUserApplicationsRequest): Promise<GetUserApplicationsResult> {
        return this.apiInvoker.invoke_alt<GetUserApplicationsRequest, GetUserApplicationsResult>("SchedulerAdmin.GetUserApplications", req);
    }

    createHpcLicenseResource(req: CreateHpcLicenseResourceRequest): Promise<CreateHpcLicenseResourceResult> {
        return this.apiInvoker.invoke_alt<CreateHpcLicenseResourceRequest, CreateHpcLicenseResourceResult>("SchedulerAdmin.CreateHpcLicenseResource", req);
    }

    getHpcLicenseResource(req: GetHpcLicenseResourceRequest): Promise<GetHpcLicenseResourceResult> {
        return this.apiInvoker.invoke_alt<GetHpcLicenseResourceRequest, GetHpcLicenseResourceResult>("SchedulerAdmin.GetHpcLicenseResource", req);
    }

    updateHpcLicenseResource(req: UpdateHpcLicenseResourceRequest): Promise<UpdateHpcLicenseResourceResult> {
        return this.apiInvoker.invoke_alt<UpdateHpcLicenseResourceRequest, UpdateHpcLicenseResourceResult>("SchedulerAdmin.UpdateHpcLicenseResource", req);
    }

    deleteHpcLicenseResource(req: DeleteHpcLicenseResourceRequest): Promise<DeleteHpcLicenseResourceResult> {
        return this.apiInvoker.invoke_alt<DeleteHpcLicenseResourceRequest, DeleteHpcLicenseResourceResult>("SchedulerAdmin.DeleteHpcLicenseResource", req);
    }

    listHpcLicenseResources(req: ListHpcLicenseResourcesRequest): Promise<ListHpcLicenseResourcesResult> {
        return this.apiInvoker.invoke_alt<ListHpcLicenseResourcesRequest, ListHpcLicenseResourcesResult>("SchedulerAdmin.ListHpcLicenseResources", req);
    }

    checkHpcLicenseResourceAvailability(req: CheckHpcLicenseResourceAvailabilityRequest): Promise<CheckHpcLicenseResourceAvailabilityResult> {
        return this.apiInvoker.invoke_alt<CheckHpcLicenseResourceAvailabilityRequest, CheckHpcLicenseResourceAvailabilityResult>("SchedulerAdmin.CheckHpcLicenseResourceAvailability", req);
    }

    deleteJob(req: DeleteJobRequest): Promise<DeleteJobResult> {
        return this.apiInvoker.invoke_alt<DeleteJobRequest, DeleteJobResult>("SchedulerAdmin.DeleteJob", req);
    }
}

export default SchedulerAdminClient;
