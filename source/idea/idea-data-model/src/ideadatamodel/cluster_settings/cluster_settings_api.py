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
    'ListClusterModulesRequest',
    'ListClusterModulesResult',
    'GetModuleSettingsResult',
    'GetModuleSettingsRequest',
    'UpdateModuleSettingsResult',
    'UpdateModuleSettingsRequest',
    'UpdateQuicConfigRequest',
    'UpdateQuicConfigResult',
    'ListClusterHostsRequest',
    'ListClusterHostsResult',
    'DescribeInstanceTypesRequest',
    'DescribeInstanceTypesResult',
    'GetAllowedSessionsPerUserRequest',
    'GetAllowedSessionsPerUserResult',
    'OPEN_API_SPEC_ENTRIES_CLUSTER_SETTINGS'
)

from ideadatamodel import SocaPayload, SocaListingPayload, IdeaOpenAPISpecEntry

from typing import Optional, List, Any


# ClusterSettings.ListClusterModules

class ListClusterModulesRequest(SocaListingPayload):
    pass


class ListClusterModulesResult(SocaListingPayload):
    listing: Optional[List[Any]]


# ClusterSettings.GetClusterModule

class GetModuleSettingsRequest(SocaPayload):
    module_id: Optional[str]


class GetModuleSettingsResult(SocaPayload):
    settings: Optional[Any]


# ClusterSettings.UpdateModuleSettings
class UpdateModuleSettingsRequest(SocaPayload):
    module_id: Optional[str]
    settings: Optional[Any]


class UpdateModuleSettingsResult(SocaPayload):
    pass


# ClusterSettings.ListClusterHosts
class ListClusterHostsRequest(SocaListingPayload):
    instance_ids: Optional[List[str]]


class ListClusterHostsResult(SocaListingPayload):
    listing: Optional[List[Any]]


# ClusterSettings.DescribeInstanceTypes
class DescribeInstanceTypesRequest(SocaPayload):
    pass


class DescribeInstanceTypesResult(SocaPayload):
    instance_types: List[Any]


class GetAllowedSessionsPerUserRequest(SocaPayload):
    pass


class GetAllowedSessionsPerUserResult(SocaPayload):
    allowed_sessions_per_user: Optional[int]


# ClusterSettings.UpdateQuic
class UpdateQuicConfigRequest(SocaListingPayload):
    enable: Optional[bool]


class UpdateQuicConfigResult(SocaPayload):
    pass


OPEN_API_SPEC_ENTRIES_CLUSTER_SETTINGS = [
    IdeaOpenAPISpecEntry(
        namespace='ClusterSettings.ListClusterModules',
        request=ListClusterModulesRequest,
        result=ListClusterModulesResult,
        is_listing=True,
        is_public=False
    ),
    IdeaOpenAPISpecEntry(
        namespace='ClusterSettings.GetModuleSettings',
        request=GetModuleSettingsRequest,
        result=GetModuleSettingsResult,
        is_listing=False,
        is_public=False
    ),
    IdeaOpenAPISpecEntry(
        namespace='ClusterSettings.UpdateModuleSettings',
        request=UpdateModuleSettingsRequest,
        result=UpdateModuleSettingsResult,
        is_listing=False,
        is_public=False
    ),
    IdeaOpenAPISpecEntry(
        namespace='ClusterSettings.ListClusterHosts',
        request=ListClusterHostsRequest,
        result=ListClusterHostsResult,
        is_listing=True,
        is_public=False
    ),
    IdeaOpenAPISpecEntry(
        namespace='ClusterSettings.DescribeInstanceTypes',
        request=DescribeInstanceTypesRequest,
        result=DescribeInstanceTypesResult,
        is_listing=False,
        is_public=False
    ),
    IdeaOpenAPISpecEntry(
        namespace='ClusterSettings.GetAllowedSessionsPerUser',
        request=GetAllowedSessionsPerUserRequest,
        result=GetAllowedSessionsPerUserResult,
        is_listing=False,
        is_public=False
    ),
    IdeaOpenAPISpecEntry(
        namespace='ClusterSettings.UpdateQuicConfig',
        request=UpdateQuicConfigRequest,
        result=UpdateQuicConfigResult,
        is_listing=False,
        is_public=False
    )
]
