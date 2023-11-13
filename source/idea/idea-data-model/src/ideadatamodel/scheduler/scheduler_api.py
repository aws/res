#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

__all__ = (
    'ListNodesRequest',
    'ListNodesResult',
    'ListJobsRequest',
    'ListJobsResult',
    'GetJobRequest',
    'GetJobResult',
    'SubmitJobRequest',
    'SubmitJobResult',
    'DeleteJobRequest',
    'DeleteJobResult',
    'GetInstanceTypeOptionsRequest',
    'GetInstanceTypeOptionsResult',
    'CreateQueueProfileRequest',
    'CreateQueueProfileResult',
    'GetQueueProfileRequest',
    'GetQueueProfileResult',
    'UpdateQueueProfileRequest',
    'UpdateQueueProfileResult',
    'EnableQueueProfileRequest',
    'EnableQueueProfileResult',
    'DisableQueueProfileRequest',
    'DisableQueueProfileResult',
    'DeleteQueueProfileRequest',
    'DeleteQueueProfileResult',
    'CreateQueuesRequest',
    'CreateQueuesResult',
    'DeleteQueuesRequest',
    'DeleteQueuesResult',
    'ListQueueProfilesRequest',
    'ListQueueProfilesResult',
    'CreateHpcApplicationRequest',
    'CreateHpcApplicationResult',
    'UpdateHpcApplicationRequest',
    'UpdateHpcApplicationResult',
    'GetHpcApplicationRequest',
    'GetHpcApplicationResult',
    'DeleteHpcApplicationRequest',
    'DeleteHpcApplicationResult',
    'ListHpcApplicationsRequest',
    'ListHpcApplicationsResult',
    'GetUserApplicationsRequest',
    'GetUserApplicationsResult',
    'ProvisionAlwaysOnNodesRequest',
    'ProvisionAlwaysOnNodesResult',
    'CreateHpcLicenseResourceRequest',
    'CreateHpcLicenseResourceResult',
    'GetHpcLicenseResourceRequest',
    'GetHpcLicenseResourceResult',
    'UpdateHpcLicenseResourceRequest',
    'UpdateHpcLicenseResourceResult',
    'DeleteHpcLicenseResourceRequest',
    'DeleteHpcLicenseResourceResult',
    'ListHpcLicenseResourcesRequest',
    'ListHpcLicenseResourcesResult',
    'CheckHpcLicenseResourceAvailabilityRequest',
    'CheckHpcLicenseResourceAvailabilityResult',
    'OPEN_API_SPEC_ENTRIES_SCHEDULER'
)

from ideadatamodel import SocaPayload, SocaListingPayload, IdeaOpenAPISpecEntry
from ideadatamodel.aws import ServiceQuota
from ideadatamodel.scheduler.scheduler_model import *

from typing import Optional, Set, List


class ListNodesRequest(SocaListingPayload):
    instance_ids: Optional[List[str]]
    instance_types: Optional[List[str]]
    job_id: Optional[str]
    job_group: Optional[str]
    compute_stack: Optional[str]
    queue_type: Optional[str]
    states: Optional[Set[SocaComputeNodeState]]


class ListNodesResult(SocaListingPayload):
    listing: Optional[List[SocaComputeNode]]


class ListJobsRequest(SocaListingPayload):
    queue_type: Optional[str]
    queue: Optional[str]
    states: Optional[Set[SocaJobState]]


class ListJobsResult(SocaListingPayload):
    listing: Optional[List[SocaJob]]


# SchedulerAdmin.CreateQueueProfile

class CreateQueueProfileRequest(SocaPayload):
    queue_profile: Optional[HpcQueueProfile]


class CreateQueueProfileResult(SocaPayload):
    queue_profile: Optional[HpcQueueProfile]
    validation_errors: Optional[JobValidationResult]


# SchedulerAdmin.GetQueueProfile

class GetQueueProfileRequest(SocaPayload):
    queue_profile_name: Optional[str]
    queue_profile_id: Optional[str]
    queue_name: Optional[str]


class GetQueueProfileResult(SocaPayload):
    queue_profile: Optional[HpcQueueProfile]


# SchedulerAdmin.UpdateQueueProfile

class UpdateQueueProfileRequest(SocaPayload):
    queue_profile: Optional[HpcQueueProfile]


class UpdateQueueProfileResult(SocaPayload):
    queue_profile: Optional[HpcQueueProfile]


# SchedulerAdmin.EnableQueueProfile

class EnableQueueProfileRequest(SocaPayload):
    queue_profile_id: Optional[str]
    queue_profile_name: Optional[str]


class EnableQueueProfileResult(SocaPayload):
    pass


# SchedulerAdmin.DisableQueueProfile

class DisableQueueProfileRequest(SocaPayload):
    queue_profile_id: Optional[str]
    queue_profile_name: Optional[str]


class DisableQueueProfileResult(SocaPayload):
    pass


# SchedulerAdmin.DeleteQueueProfile

class DeleteQueueProfileRequest(SocaPayload):
    queue_profile_id: Optional[str]
    queue_profile_name: Optional[str]
    delete_queues: Optional[bool]


class DeleteQueueProfileResult(SocaPayload):
    pass


# SchedulerAdmin.CreateQueues

class CreateQueuesRequest(SocaPayload):
    queue_profile_id: Optional[str]
    queue_profile_name: Optional[str]
    queue_names: Optional[str]


class CreateQueuesResult(SocaPayload):
    pass


# SchedulerAdmin.DeleteQueues

class DeleteQueuesRequest(SocaPayload):
    queue_profile_id: Optional[str]
    queue_profile_name: Optional[str]
    queue_names: Optional[str]


class DeleteQueuesResult(SocaPayload):
    pass


# SchedulerAdmin.ListQueueProfiles

class ListQueueProfilesRequest(SocaListingPayload):
    lite: Optional[bool]


class ListQueueProfilesResult(SocaListingPayload):
    listing: Optional[List[HpcQueueProfile]]


# Scheduler.GetInstanceTypeOptions
class GetInstanceTypeOptionsRequest(SocaPayload):
    enable_ht_support: Optional[bool]
    instance_types: Optional[List[str]]
    queue_name: Optional[str]
    queue_profile_name: Optional[str]


class GetInstanceTypeOptionsResult(SocaPayload):
    instance_types: Optional[List[SocaInstanceTypeOptions]]


# Scheduler.SubmitJob

class SubmitJobRequest(SocaPayload):
    job_owner: Optional[str]
    project: Optional[str]
    dry_run: Optional[bool]
    job_script_interpreter: Optional[str]
    job_script: Optional[str]  # base64 encoded job data shell script


class SubmitJobResult(SocaPayload):
    dry_run: Optional[DryRunOption]
    accepted: Optional[bool]
    job: Optional[SocaJob]
    validations: Optional[JobValidationResult]
    incidentals: Optional[JobValidationResult]
    service_quotas: Optional[List[ServiceQuota]]
    reserved_instances_unavailable: Optional[bool]
    service_quota_unavailable: Optional[bool]
    estimated_bom_cost: Optional[SocaJobEstimatedBOMCost]
    budget_usage: Optional[SocaJobEstimatedBudgetUsage]

    @property
    def job_uid(self) -> Optional[str]:
        if self.job is None:
            return None
        return self.job.job_uid


# Scheduler.DeleteJob
class DeleteJobRequest(SocaPayload):
    job_id: Optional[str]


class DeleteJobResult(SocaPayload):
    pass


# Scheduler.GetActiveJob, Scheduler.GetCompletedJob
class GetJobRequest(SocaPayload):
    job_id: Optional[str]


class GetJobResult(SocaPayload):
    job: Optional[SocaJob]


# SchedulerAdmin.CreateHpcApplication

class CreateHpcApplicationRequest(SocaPayload):
    application: Optional[HpcApplication]


class CreateHpcApplicationResult(SocaPayload):
    application: Optional[HpcApplication]


# SchedulerAdmin.GetHpcApplication

class GetHpcApplicationRequest(SocaPayload):
    application_id: Optional[str]


class GetHpcApplicationResult(SocaPayload):
    application: Optional[HpcApplication]


# SchedulerAdmin.UpdateHpcApplication


class UpdateHpcApplicationRequest(SocaPayload):
    application: Optional[HpcApplication]


class UpdateHpcApplicationResult(SocaPayload):
    application: Optional[HpcApplication]


# SchedulerAdmin.DeleteHpcApplication

class DeleteHpcApplicationRequest(SocaPayload):
    application_id: Optional[str]


class DeleteHpcApplicationResult(SocaPayload):
    pass


# SchedulerAdmin.ListHpcApplications

class ListHpcApplicationsRequest(SocaListingPayload):
    lite: Optional[bool]


class ListHpcApplicationsResult(SocaListingPayload):
    listing: Optional[List[HpcApplication]]


# SchedulerAdmin.ProvisionAlwaysOnNodes
class ProvisionAlwaysOnNodesRequest(SocaPayload):
    project_name: Optional[str]
    queue_profile_name: Optional[str]
    queue_name: Optional[str]
    owner: Optional[str]
    params: Optional[SocaJobParams]


class ProvisionAlwaysOnNodesResult(SocaPayload):
    stack_name: Optional[str]
    stack_id: Optional[str]


# SchedulerAdmin.GetUserApplications

class GetUserApplicationsRequest(SocaPayload):
    username: Optional[str]
    application_ids: Optional[List[str]]


class GetUserApplicationsResult(SocaPayload):
    applications: List[HpcApplication]


# SchedulerAdmin.CreateHpcLicenseResource

class CreateHpcLicenseResourceRequest(SocaPayload):
    license_resource: Optional[HpcLicenseResource]
    dry_run: Optional[bool]


class CreateHpcLicenseResourceResult(SocaPayload):
    license_resource: Optional[HpcLicenseResource]


# SchedulerAdmin.GetHpcLicenseResource
class GetHpcLicenseResourceRequest(SocaPayload):
    name: Optional[str]


class GetHpcLicenseResourceResult(SocaPayload):
    license_resource: Optional[HpcLicenseResource]


# SchedulerAdmin.UpdateHpcLicenseResource
class UpdateHpcLicenseResourceRequest(SocaPayload):
    license_resource: Optional[HpcLicenseResource]
    dry_run: Optional[bool]


class UpdateHpcLicenseResourceResult(SocaPayload):
    license_resource: Optional[HpcLicenseResource]


# SchedulerAdmin.DeleteHpcLicenseResource
class DeleteHpcLicenseResourceRequest(SocaPayload):
    name: Optional[str]


class DeleteHpcLicenseResourceResult(SocaPayload):
    pass


# SchedulerAdmin.ListHpcLicenseResources
class ListHpcLicenseResourcesRequest(SocaListingPayload):
    pass


class ListHpcLicenseResourcesResult(SocaListingPayload):
    listing: Optional[List[HpcLicenseResource]]


# SchedulerAdmin.CheckHpcLicenseResourceAvailability
class CheckHpcLicenseResourceAvailabilityRequest(SocaPayload):
    name: Optional[str]


class CheckHpcLicenseResourceAvailabilityResult(SocaPayload):
    available_count: Optional[int]


OPEN_API_SPEC_ENTRIES_SCHEDULER = [
    IdeaOpenAPISpecEntry(
        namespace='Scheduler.ListActiveJobs',
        request=ListJobsRequest,
        result=ListJobsResult,
        is_listing=True,
        is_public=False
    ),
    IdeaOpenAPISpecEntry(
        namespace='Scheduler.ListCompletedJobs',
        request=ListJobsRequest,
        result=ListJobsResult,
        is_listing=True,
        is_public=False
    ),
    IdeaOpenAPISpecEntry(
        namespace='Scheduler.GetUserApplications',
        request=GetUserApplicationsRequest,
        result=GetUserApplicationsResult,
        is_listing=False,
        is_public=False
    ),
    IdeaOpenAPISpecEntry(
        namespace='Scheduler.SubmitJob',
        request=SubmitJobRequest,
        result=SubmitJobResult,
        is_listing=False,
        is_public=False
    ),
    IdeaOpenAPISpecEntry(
        namespace='Scheduler.DeleteJob',
        request=DeleteJobRequest,
        result=DeleteJobResult,
        is_listing=False,
        is_public=False
    ),
    IdeaOpenAPISpecEntry(
        namespace='Scheduler.GetActiveJob',
        request=GetJobRequest,
        result=GetJobResult,
        is_listing=False,
        is_public=False
    ),
    IdeaOpenAPISpecEntry(
        namespace='Scheduler.GetCompletedJob',
        request=GetJobRequest,
        result=GetJobResult,
        is_listing=False,
        is_public=False
    ),
    IdeaOpenAPISpecEntry(
        namespace='Scheduler.GetInstanceTypeOptions',
        request=GetInstanceTypeOptionsRequest,
        result=GetInstanceTypeOptionsResult,
        is_listing=False,
        is_public=False
    ),
    IdeaOpenAPISpecEntry(
        namespace='SchedulerAdmin.ListActiveJobs',
        request=ListJobsRequest,
        result=ListJobsResult,
        is_listing=True,
        is_public=False
    ),
    IdeaOpenAPISpecEntry(
        namespace='SchedulerAdmin.ListCompletedJobs',
        request=ListJobsRequest,
        result=ListJobsResult,
        is_listing=True,
        is_public=False
    ),
    IdeaOpenAPISpecEntry(
        namespace='SchedulerAdmin.ListNodes',
        request=ListNodesRequest,
        result=ListNodesResult,
        is_listing=True,
        is_public=False
    ),
    IdeaOpenAPISpecEntry(
        namespace='SchedulerAdmin.CreateQueueProfile',
        request=CreateQueueProfileRequest,
        result=CreateQueueProfileResult,
        is_listing=False,
        is_public=False
    ),
    IdeaOpenAPISpecEntry(
        namespace='SchedulerAdmin.GetQueueProfile',
        request=GetQueueProfileRequest,
        result=GetQueueProfileResult,
        is_listing=False,
        is_public=False
    ),
    IdeaOpenAPISpecEntry(
        namespace='SchedulerAdmin.UpdateQueueProfile',
        request=UpdateQueueProfileRequest,
        result=UpdateQueueProfileResult,
        is_listing=False,
        is_public=False
    ),
    IdeaOpenAPISpecEntry(
        namespace='SchedulerAdmin.EnableQueueProfile',
        request=EnableQueueProfileRequest,
        result=EnableQueueProfileResult,
        is_listing=False,
        is_public=False
    ),
    IdeaOpenAPISpecEntry(
        namespace='SchedulerAdmin.DisableQueueProfile',
        request=DisableQueueProfileRequest,
        result=DisableQueueProfileResult,
        is_listing=False,
        is_public=False
    ),
    IdeaOpenAPISpecEntry(
        namespace='SchedulerAdmin.DeleteQueueProfile',
        request=DeleteQueueProfileRequest,
        result=DeleteQueueProfileResult,
        is_listing=False,
        is_public=False
    ),
    IdeaOpenAPISpecEntry(
        namespace='SchedulerAdmin.ListQueueProfiles',
        request=ListQueueProfilesRequest,
        result=ListQueueProfilesResult,
        is_listing=True,
        is_public=False
    ),
    IdeaOpenAPISpecEntry(
        namespace='SchedulerAdmin.CreateHpcApplication',
        request=CreateHpcApplicationRequest,
        result=CreateHpcApplicationResult,
        is_listing=False,
        is_public=False
    ),
    IdeaOpenAPISpecEntry(
        namespace='SchedulerAdmin.GetHpcApplication',
        request=GetHpcApplicationRequest,
        result=GetHpcApplicationResult,
        is_listing=False,
        is_public=False
    ),
    IdeaOpenAPISpecEntry(
        namespace='SchedulerAdmin.UpdateHpcApplication',
        request=UpdateHpcApplicationRequest,
        result=UpdateHpcApplicationResult,
        is_listing=False,
        is_public=False
    ),
    IdeaOpenAPISpecEntry(
        namespace='SchedulerAdmin.DeleteHpcApplication',
        request=DeleteHpcApplicationRequest,
        result=DeleteHpcApplicationResult,
        is_listing=False,
        is_public=False
    ),
    IdeaOpenAPISpecEntry(
        namespace='SchedulerAdmin.ListHpcApplications',
        request=ListHpcApplicationsRequest,
        result=ListHpcApplicationsResult,
        is_listing=True,
        is_public=False
    ),
    IdeaOpenAPISpecEntry(
        namespace='SchedulerAdmin.GetUserApplications',
        request=GetUserApplicationsRequest,
        result=GetUserApplicationsResult,
        is_listing=False,
        is_public=False
    ),
    IdeaOpenAPISpecEntry(
        namespace='SchedulerAdmin.ProvisionAlwaysOnNodes',
        request=ProvisionAlwaysOnNodesRequest,
        result=ProvisionAlwaysOnNodesResult,
        is_listing=False,
        is_public=False
    ),
    IdeaOpenAPISpecEntry(
        namespace='SchedulerAdmin.CreateHpcLicenseResource',
        request=CreateHpcLicenseResourceRequest,
        result=CreateHpcLicenseResourceResult,
        is_listing=False,
        is_public=False
    ),
    IdeaOpenAPISpecEntry(
        namespace='SchedulerAdmin.GetHpcLicenseResource',
        request=GetHpcLicenseResourceRequest,
        result=GetHpcLicenseResourceResult,
        is_listing=False,
        is_public=False
    ),
    IdeaOpenAPISpecEntry(
        namespace='SchedulerAdmin.UpdateHpcLicenseResource',
        request=UpdateHpcLicenseResourceRequest,
        result=UpdateHpcLicenseResourceResult,
        is_listing=False,
        is_public=False
    ),
    IdeaOpenAPISpecEntry(
        namespace='SchedulerAdmin.DeleteHpcLicenseResource',
        request=DeleteHpcLicenseResourceRequest,
        result=DeleteHpcLicenseResourceResult,
        is_listing=False,
        is_public=False
    ),
    IdeaOpenAPISpecEntry(
        namespace='SchedulerAdmin.ListHpcLicenseResources',
        request=ListHpcLicenseResourcesRequest,
        result=ListHpcLicenseResourcesResult,
        is_listing=True,
        is_public=False
    ),
    IdeaOpenAPISpecEntry(
        namespace='SchedulerAdmin.CheckHpcLicenseResourceAvailability',
        request=CheckHpcLicenseResourceAvailabilityRequest,
        result=CheckHpcLicenseResourceAvailabilityResult,
        is_listing=False,
        is_public=False
    )
]
