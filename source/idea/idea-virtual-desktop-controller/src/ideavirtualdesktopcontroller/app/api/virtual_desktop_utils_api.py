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
from ideadatamodel import exceptions, errorcodes
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


class VirtualDesktopUtilsAPI(VirtualDesktopAPI):
    def __init__(self, context: ideavirtualdesktopcontroller.AppContext):
        super().__init__(context)
        self.context = context
        self._logger = context.logger('virtual-desktop-utils-api')

        self.namespace_handler_map = {
            'VirtualDesktopUtils.ListSupportedOS': self.list_supported_os,
            'VirtualDesktopUtils.ListSupportedGPU': self.list_supported_gpu,
            'VirtualDesktopUtils.ListScheduleTypes': self.list_schedule_types,
            'VirtualDesktopUtils.ListAllowedInstanceTypes': self.list_allowed_instance_types,
            'VirtualDesktopUtils.ListAllowedInstanceTypesForSession': self.list_allowed_instance_types_for_session,
            'VirtualDesktopUtils.GetBasePermissions': self.get_base_permissions,
            'VirtualDesktopUtils.ListPermissionProfiles': self.list_permission_profiles,
            'VirtualDesktopUtils.GetPermissionProfile': self.get_permission_profile
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
        profile = self.permission_profile_db.get(profile_id=profile_id)
        if Utils.is_empty(profile):
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

    def _validate_list_allowed_instance_types_for_session(self, session: VirtualDesktopSession) -> (VirtualDesktopSession, bool):
        if Utils.is_empty(session):
            session.failure_reason = 'Invalid session object'
            self._logger.error(session.failure_reason)
            return session, False

        if Utils.is_empty(session.hibernation_enabled):
            session.failure_reason = 'Missing session.hibernation_enabled'
            self._logger.error(session.failure_reason)
            return session, False

        if Utils.is_empty(session.software_stack):
            session.failure_reason = 'Missing session.new_software_stack'
            self._logger.error(session.failure_reason)
            return session, False

        if Utils.is_empty(session.software_stack.architecture):
            session.failure_reason = 'Missing session.new_software_stack.architecture'
            self._logger.error(session.failure_reason)
            return session, False

        if Utils.is_empty(session.server):
            session.failure_reason = 'Missing session.server'
            self._logger.error(session.failure_reason)
            return session, False

        if Utils.is_empty(session.server.instance_type):
            session.failure_reason = 'Missing session.server.instance_type'
            self._logger.error(session.failure_reason)
            return session, False

        return session, True

    def list_allowed_instance_types_for_session(self, context: ApiInvocationContext):
        session = context.get_request_payload_as(ListAllowedInstanceTypesForSessionRequest).session
        session, is_valid = self._validate_list_allowed_instance_types_for_session(session)

        if not is_valid:
            context.fail(
                message=session.failure_reason,
                payload=ListAllowedInstanceTypesForSessionResponse(listing=[]),
                error_code=errorcodes.GENERAL_ERROR
            )
            return

        allowed_instance_types = self.controller_utils.get_valid_instance_types(session.hibernation_enabled, session.software_stack, self.controller_utils.get_gpu_manufacturer(session.server.instance_type))
        context.success(ListAllowedInstanceTypesResponse(
            listing=allowed_instance_types
        ))

    def list_allowed_instance_types(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(ListAllowedInstanceTypesRequest)

        hibernation_enabled = False if Utils.is_empty(request.hibernation_support) else request.hibernation_support
        allowed_instance_types = self.controller_utils.get_valid_instance_types(hibernation_enabled, request.software_stack)
        context.success(ListAllowedInstanceTypesResponse(
            listing=allowed_instance_types
        ))

    @staticmethod
    def list_schedule_types(context: ApiInvocationContext):
        schedule_types = []
        for schedule_type in VirtualDesktopScheduleType:
            schedule_types.append(schedule_type)
        context.success(ListScheduleTypesResponse(
            listing=schedule_types
        ))

    @staticmethod
    def list_supported_gpu(context: ApiInvocationContext):
        supported_gpu = []
        for gpu in VirtualDesktopGPU:
            supported_gpu.append(gpu)
        context.success(ListSupportedGPUResponse(
            listing=supported_gpu
        ))

    @staticmethod
    def list_supported_os(context: ApiInvocationContext):
        supported_os = []
        for os in VirtualDesktopBaseOS:
            supported_os.append(os)
        context.success(ListSupportedOSResponse(
            listing=supported_os
        ))

    def invoke(self, context: ApiInvocationContext):

        if not context.is_authorized_user():
            raise exceptions.unauthorized_access()

        namespace = context.namespace
        if namespace in self.namespace_handler_map:
            self.namespace_handler_map[namespace](context)
