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
import ideavirtualdesktopcontroller
from ideadatamodel import VirtualDesktopArchitecture, exceptions, errorcodes
from ideadatamodel.virtual_desktop import (
    ListSupportedOSResponse,
    ListScheduleTypesResponse,
    ListSupportedGPUResponse,
    ListAllowedInstanceTypesRequest,
    ListAllowedInstanceTypesResponse,
    ListAllowedInstanceTypesForSessionRequest,
    ListAllowedInstanceTypesForSessionResponse,
    ListPermissionProfilesRequest,
    GetPermissionProfileRequest,
    GetPermissionProfileResponse,
    GetBasePermissionsResponse,
    VirtualDesktopSession,
    VirtualDesktopBaseOS,
    VirtualDesktopGPU,
    VirtualDesktopScheduleType
)
from ideasdk.api import ApiInvocationContext
from ideasdk.utils import Utils
from ideavirtualdesktopcontroller.app.api.virtual_desktop_api import VirtualDesktopAPI
from res.exceptions import PermissionProfileNotFound
from res.resources import permission_profiles


class VirtualDesktopUtilsAPI(VirtualDesktopAPI):
    def __init__(self, context: ideavirtualdesktopcontroller.AppContext):
        super().__init__(context)
        self.context = context
        self._logger = context.logger('virtual-desktop-utils-api')
        self.SCOPE_READ = f'{self.context.cluster_name()}-{self.context.module_id()}/read'

        self.acl = {
            'VirtualDesktopUtils.GetBasePermissions': {
                'scope': self.SCOPE_READ,
                'method': self.get_base_permissions,
            },
            'VirtualDesktopUtils.ListPermissionProfiles': {
                'scope': self.SCOPE_READ,
                'method': self.list_permission_profiles,
            },
            'VirtualDesktopUtils.GetPermissionProfile': {
                'scope': self.SCOPE_READ,
                'method': self.get_permission_profile,
            },
        }

    def get_base_permissions(self, context: ApiInvocationContext):
        context.success(GetBasePermissionsResponse(
            permissions=self.permission_profile_db.permission_types
        ))

    def get_permission_profile(self, context: ApiInvocationContext):
        profile_id = context.get_request_payload_as(GetPermissionProfileRequest).profile_id
        if Utils.is_empty(profile_id):
            context.fail(
                message=f'Invalid profile_id: {profile_id}',
                error_code=errorcodes.INVALID_PARAMS
            )
            return
        try:
            profile_dict = permission_profiles.get_permission_profile(profile_id=profile_id)
            profile = self.permission_profile_db.convert_db_dict_to_permission_profile_object(profile_dict)
        except PermissionProfileNotFound:
            context.fail(
                message=f'Invalid profile_id: {profile_id}',
                error_code=errorcodes.INVALID_PARAMS
            )
            return

        context.success(GetPermissionProfileResponse(
            profile=profile
        ))

    def list_permission_profiles(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(ListPermissionProfilesRequest)
        result = self.permission_profile_db.list(request)
        context.success(result)

    def invoke(self, context: ApiInvocationContext):
        namespace = context.namespace

        acl_entry = self.acl.get(namespace)
        if acl_entry is None:
            raise exceptions.unauthorized_access()

        acl_entry_scope = acl_entry.get('scope')
        is_authorized = context.is_authorized(elevated_access=True, scopes=[acl_entry_scope]) if namespace in (
            'VirtualDesktopUtils.ListSupportedOS',
            'VirtualDesktopUtils.ListSupportedGPU',
            'VirtualDesktopUtils.GetPermissionProfile',
        ) else context.is_authorized(elevated_access=False, scopes=[acl_entry_scope])

        if is_authorized:
            acl_entry['method'](context)
        else:
            raise exceptions.unauthorized_access()
