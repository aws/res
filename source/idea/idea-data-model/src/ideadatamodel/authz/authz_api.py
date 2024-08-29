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
    'BatchPutRoleAssignmentRequest',
    'BatchPutRoleAssignmentResponse',
    'BatchDeleteRoleAssignmentRequest',
    'BatchDeleteRoleAssignmentResponse',
    'PutRoleAssignmentRequest',
    'PutRoleAssignmentSuccessResponse',
    'PutRoleAssignmentErrorResponse',
    'DeleteRoleAssignmentRequest',
    'DeleteRoleAssignmentSuccessResponse',
    'DeleteRoleAssignmentErrorResponse',
    'ListRoleAssignmentsRequest',
    'ListRolesResponse',
    'ListRolesRequest',
    'GetRoleResponse',
    'GetRoleRequest',
    'CreateRoleRequest',
    'CreateRoleResponse',
    'DeleteRoleRequest',
    'DeleteRoleResponse',
    'UpdateRoleRequest',
    'UpdateRoleResponse',
    'ListRoleAssignmentsResponse',
    'OPEN_API_SPEC_ENTRIES_AUTHZ'
)

from ideadatamodel import SocaPayload, SocaListingPayload, SocaPaginator, IdeaOpenAPISpecEntry
from ideadatamodel.authz.role_assignments_model import RoleAssignment
from ideadatamodel.authz.roles_model import Role
from typing import Optional, List

# Authz.BatchPutRoleAssignment

class PutRoleAssignmentRequest(SocaPayload):
    request_id: str
    resource_id: str
    actor_id: str
    resource_type: str
    actor_type: str
    role_id: str

class PutRoleAssignmentSuccessResponse(SocaPayload):
    request_id: str
    status_code: str

class PutRoleAssignmentErrorResponse(SocaPayload):
    request_id: str
    error_code: str
    message: Optional[str] = None

class BatchPutRoleAssignmentRequest(SocaPayload):
    items: List[PutRoleAssignmentRequest]

class BatchPutRoleAssignmentResponse(SocaPayload):
    items: List[PutRoleAssignmentSuccessResponse]
    errors: List[PutRoleAssignmentErrorResponse]

# Authz.BatchDeleteRoleAssignment

class DeleteRoleAssignmentRequest(SocaPayload):
    request_id: str
    resource_id: str
    actor_id: str
    resource_type: str
    actor_type: str

class DeleteRoleAssignmentSuccessResponse(SocaPayload):
    request_id: str
    status_code: str

class DeleteRoleAssignmentErrorResponse(SocaPayload):
    request_id: str
    error_code: str
    message: Optional[str] = None

class BatchDeleteRoleAssignmentRequest(SocaPayload):
    items: List[DeleteRoleAssignmentRequest]

class BatchDeleteRoleAssignmentResponse(SocaPayload):
    items: List[DeleteRoleAssignmentSuccessResponse]
    errors: List[DeleteRoleAssignmentErrorResponse]

# Authz.ListRoleAssignments

class ListRoleAssignmentsRequest(SocaListingPayload):
    paginator: Optional[SocaPaginator] = None
    resource_key: Optional[str] = None
    actor_key: Optional[str] = None
    max_results: Optional[int] = None

class ListRoleAssignmentsResponse(SocaListingPayload):
    items: List[RoleAssignment]

# Authz.ListRoles

class ListRolesRequest(SocaListingPayload):
    paginator: Optional[SocaPaginator] = None
    include_permissions: Optional[bool] = False

class ListRolesResponse(SocaListingPayload):
    items: List[Role]

# Authz.GetRole

class GetRoleRequest(SocaPayload):
    role_id: Optional[str]

class GetRoleResponse(SocaPayload):
    role: Role

# Authz.CreateRole

class CreateRoleRequest(SocaPayload):
    role: Role

class CreateRoleResponse(SocaPayload):
    role: Role

# Authz.DeleteRole

class DeleteRoleRequest(SocaPayload):
    role_id: Optional[str]

class DeleteRoleResponse(SocaPayload):
    pass

# Authz.UpdateRole

class UpdateRoleRequest(SocaPayload):
    role: Role

class UpdateRoleResponse(SocaPayload):
    role: Role

OPEN_API_SPEC_ENTRIES_AUTHZ = [
    IdeaOpenAPISpecEntry(
        namespace='Authz.BatchPutRoleAssignment',
        request=BatchPutRoleAssignmentRequest,
        result=BatchPutRoleAssignmentResponse,
        is_listing=False,
        is_public=False
    ),
    IdeaOpenAPISpecEntry(
        namespace='Authz.ListRoleAssignments',
        request=ListRoleAssignmentsRequest,
        result=ListRoleAssignmentsResponse,
        is_listing=True,
        is_public=False
    ),
    IdeaOpenAPISpecEntry(
        namespace='Authz.BatchDeleteRoleAssignment',
        request=BatchDeleteRoleAssignmentRequest,
        result=BatchDeleteRoleAssignmentResponse,
        is_listing=False,
        is_public=False
    ),
    IdeaOpenAPISpecEntry(
        namespace='Authz.ListRoles',
        request=ListRolesRequest,
        result=ListRolesResponse,
        is_listing=True,
        is_public=False
    ),
    IdeaOpenAPISpecEntry(
        namespace='Authz.GetRole',
        request=GetRoleRequest,
        result=GetRoleResponse,
        is_listing=False,
        is_public=False
    ),
    IdeaOpenAPISpecEntry(
        namespace='Authz.CreateRole',
        request=CreateRoleRequest,
        result=CreateRoleResponse,
        is_listing=False,
        is_public=False
    ),
    IdeaOpenAPISpecEntry(
        namespace='Authz.DeleteRole',
        request=DeleteRoleRequest,
        result=DeleteRoleResponse,
        is_listing=False,
        is_public=False
    ),
    IdeaOpenAPISpecEntry(
        namespace='Authz.UpdateRole',
        request=UpdateRoleRequest,
        result=UpdateRoleResponse,
        is_listing=False,
        is_public=False
    ),
]
