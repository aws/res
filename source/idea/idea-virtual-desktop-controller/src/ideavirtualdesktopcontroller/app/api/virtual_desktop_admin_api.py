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
from typing import Dict

import ideavirtualdesktopcontroller
from ideadatamodel import (
    ListUsersInGroupRequest,
    GetProjectRequest,
    CreateSessionRequest,
    CreateSessionResponse,
    DeleteSoftwareStackRequest,
    DeleteSoftwareStackResponse,
    BatchCreateSessionRequest,
    BatchCreateSessionResponse,
    GetSessionConnectionInfoRequest,
    GetSessionConnectionInfoResponse,
    GetSessionScreenshotRequest,
    GetSessionScreenshotResponse,
    UpdateSessionRequest,
    UpdateSessionResponse,
    GetSessionInfoRequest,
    GetSessionInfoResponse,
    DeleteSessionRequest,
    DeleteSessionResponse,
    StopSessionRequest,
    StopSessionResponse,
    RebootSessionRequest,
    RebootSessionResponse,
    ResumeSessionsRequest,
    ResumeSessionsResponse,
    ListSessionsRequest,
    CreateSoftwareStackRequest,
    CreateSoftwareStackResponse,
    UpdateSoftwareStackRequest,
    UpdateSoftwareStackResponse,
    GetSoftwareStackInfoRequest,
    GetSoftwareStackInfoResponse,
    ListSoftwareStackRequest,
    ListPermissionsRequest,
    CreateSoftwareStackFromSessionRequest,
    CreateSoftwareStackFromSessionResponse,
    CreatePermissionProfileResponse,
    CreatePermissionProfileRequest,
    UpdatePermissionProfileRequest,
    UpdatePermissionProfileResponse,
    DeletePermissionProfileRequest,
    DeletePermissionProfileResponse,
    UpdateSessionPermissionRequest,
    UpdateSessionPermissionResponse,
    VirtualDesktopSession,
    VirtualDesktopArchitecture,
    VirtualDesktopSoftwareStack
)
from ideadatamodel import errorcodes, exceptions, constants
from ideasdk.api import ApiInvocationContext
from ideasdk.utils import Utils, ApiUtils
from ideavirtualdesktopcontroller.app.api.virtual_desktop_api import VirtualDesktopAPI

class VirtualDesktopAdminAPI(VirtualDesktopAPI):

    def __init__(self, context: ideavirtualdesktopcontroller.AppContext):
        super().__init__(context)
        self.context = context
        self._logger = context.logger('virtual-desktop-admin-api')
        self.SCOPE_WRITE = f'{self.context.module_id()}/write'
        self.SCOPE_READ = f'{self.context.module_id()}/read'

        self.acl = {
            'VirtualDesktopAdmin.CreateSession': {
                'scope': self.SCOPE_WRITE,
                'method': self.create_session,
            },
            'VirtualDesktopAdmin.BatchCreateSessions':  {
                'scope': self.SCOPE_WRITE,
                'method': self.batch_create_sessions,
            },
            'VirtualDesktopAdmin.UpdateSession': {
                'scope': self.SCOPE_WRITE,
                'method': self.update_session,
            },
            'VirtualDesktopAdmin.DeleteSessions': {
                'scope': self.SCOPE_WRITE,
                'method': self.delete_sessions,
            },
            'VirtualDesktopAdmin.GetSessionInfo': {
                'scope': self.SCOPE_READ,
                'method': self.get_session_info,
            },
            'VirtualDesktopAdmin.ListSessions': {
                'scope': self.SCOPE_READ,
                'method': self.list_sessions,
            },
            'VirtualDesktopAdmin.StopSessions': {
                'scope': self.SCOPE_WRITE,
                'method': self.stop_sessions,
            },
            'VirtualDesktopAdmin.RebootSessions': {
                'scope': self.SCOPE_WRITE,
                'method': self.reboot_sessions,
            },
            'VirtualDesktopAdmin.ResumeSessions': {
                'scope': self.SCOPE_WRITE,
                'method': self.resume_sessions,
            },
            'VirtualDesktopAdmin.GetSessionScreenshot': {
                'scope': self.SCOPE_READ,
                'method': self.get_session_screenshots,
            },
            'VirtualDesktopAdmin.GetSessionConnectionInfo': {
                'scope': self.SCOPE_READ,
                'method': self.get_session_connection_info,
            },
            'VirtualDesktopAdmin.CreateSoftwareStack': {
                'scope': self.SCOPE_WRITE,
                'method': self.create_software_stack,
            },
            'VirtualDesktopAdmin.UpdateSoftwareStack': {
                'scope': self.SCOPE_WRITE,
                'method': self.update_software_stack,
            },
            'VirtualDesktopAdmin.GetSoftwareStackInfo': {
                'scope': self.SCOPE_READ,
                'method': self.get_software_stack_info,
            },
            'VirtualDesktopAdmin.ListSoftwareStacks': {
                'scope': self.SCOPE_READ,
                'method': self.list_software_stacks,
            },
            'VirtualDesktopAdmin.CreateSoftwareStackFromSession': {
                'scope': self.SCOPE_WRITE,
                'method': self.create_software_stack_from_session,
            },
            'VirtualDesktopAdmin.DeleteSoftwareStack': {
                'scope': self.SCOPE_WRITE,
                'method': self.delete_software_stack,
            },
            'VirtualDesktopAdmin.CreatePermissionProfile': {
                'scope': self.SCOPE_WRITE,
                'method': self.create_permission_profile,
            },
            'VirtualDesktopAdmin.UpdatePermissionProfile': {
                'scope': self.SCOPE_WRITE,
                'method': self.update_permission_profile,
            },
            'VirtualDesktopAdmin.DeletePermissionProfile': {
                'scope': self.SCOPE_WRITE,
                'method': self.delete_permission_profile,
            },
            'VirtualDesktopAdmin.ListSessionPermissions': {
                'scope': self.SCOPE_READ,
                'method': self.list_session_permissions,
            },
            'VirtualDesktopAdmin.ListSharedPermissions': {
                'scope': self.SCOPE_READ,
                'method': self.list_shared_permissions,
            },
            'VirtualDesktopAdmin.UpdateSessionPermissions': {
                'scope': self.SCOPE_WRITE,
                'method': self.update_session_permission,
            },
        }

    def _validate_resume_session_request(self, session: VirtualDesktopSession) -> (VirtualDesktopSession, bool):
        return self.validate_resume_session_request(session)

    def _validate_reboot_session_request(self, session: VirtualDesktopSession) -> bool:
        return self.validate_stop_session_request(session)

    def _validate_stop_session_request(self, session: VirtualDesktopSession) -> bool:
        return self.validate_stop_session_request(session)

    def _validate_delete_session_request(self, session: VirtualDesktopSession) -> (VirtualDesktopSession, bool):
        return self.validate_delete_session_request(session)

    def _validate_create_session_request(self, session: VirtualDesktopSession) -> (VirtualDesktopSession, bool):
        # Validate Session Object
        if Utils.is_empty(session):
            session = VirtualDesktopSession()
            session.failure_reason = 'Missing Create Session Info'
            return session, False

        return self.validate_create_session_request(session)

    @staticmethod
    def _validate_update_software_stack_request(software_stack: VirtualDesktopSoftwareStack) -> (VirtualDesktopSoftwareStack, bool):
        if Utils.is_empty(software_stack):
            software_stack = VirtualDesktopSoftwareStack()
            software_stack.failure_reason = 'software_stack request missing'
            return software_stack, False

        if Utils.is_any_empty(software_stack.name):
            software_stack.failure_reason = 'software_stack.name missing'
            return software_stack, False

        if Utils.is_any_empty(software_stack.description):
            software_stack.failure_reason = 'software_stack.description missing'
            return software_stack, False

        if Utils.is_empty(software_stack.base_os):
            software_stack.failure_reason = 'software_stack.base_os missing'
            return software_stack, False

        for project in software_stack.projects:
            if Utils.is_empty(project.project_id):
                software_stack.failure_reason = 'software_stack.project.project_id missing'
                return software_stack, False

        return software_stack, True

    def _validate_create_software_stack_request(self, software_stack: VirtualDesktopSoftwareStack) -> (VirtualDesktopSoftwareStack, bool):
        software_stack, is_valid = self.validate_create_software_stack_request(software_stack)
        if not is_valid:
            self._logger.error(software_stack.failure_reason)
            return software_stack, False

        if Utils.is_empty(software_stack.min_ram):
            software_stack.failure_reason = 'software_stack.min_ram missing'
            return software_stack, False

        if Utils.is_empty(software_stack.min_storage):
            software_stack.failure_reason = 'software_stack.min_storage missing'
            return software_stack, False

        if Utils.is_empty(software_stack.gpu):
            software_stack.failure_reason = 'software_stack.gpu missing'
            return software_stack, False

        if Utils.is_empty(software_stack.ami_id):
            software_stack.failure_reason = 'software_stack.ami_id'
            return software_stack, False

        image_description = self.controller_utils.describe_image_id(software_stack.ami_id)
        if Utils.is_empty(image_description) or Utils.get_value_as_string('ImageId', image_description, None) != software_stack.ami_id:
            software_stack.failure_reason = f'Invalid software_stack.ami_id: {software_stack.ami_id}'
            return software_stack, False

        if Utils.is_not_empty(software_stack.architecture) and Utils.get_value_as_string('Architecture', image_description, None) != software_stack.architecture.value:
            software_stack.failure_reason = f'Invalid software_stack.ami_id: {software_stack.ami_id} with architecture: {software_stack.architecture.value}'
            return software_stack, False

        if Utils.is_empty(software_stack.architecture):
            software_stack.architecture = VirtualDesktopArchitecture(Utils.get_value_as_string('Architecture', image_description, None))

        return software_stack, True

    def create_session(self, context: ApiInvocationContext):
        session = context.get_request_payload_as(CreateSessionRequest).session
        if session.name:
            ApiUtils.validate_input(session.name,
                                    constants.SESSION_NAME_REGEX,
                                    constants.SESSION_NAME_ERROR_MESSAGE)

        session, is_valid = self._validate_create_session_request(session)
        if not is_valid:
            context.fail(
                message=session.failure_reason,
                payload=CreateSessionResponse(
                    session=session
                ),
                error_code=errorcodes.INVALID_PARAMS
            )
            return

        session = self.complete_create_session_request(session, context)
        session.is_launched_by_admin = True
        session = self.session_utils.create_session(session)
        if Utils.is_empty(session.failure_reason):
            context.success(CreateSessionResponse(
                session=session
            ))
        else:
            context.fail(
                message=session.failure_reason,
                payload=CreateSessionResponse(
                    session=session
                ),
                error_code=errorcodes.CREATE_SESSION_FAILED
            )

    def batch_create_sessions(self, context: ApiInvocationContext):
        """
        Creates a multiple sessions.
        """
        sessions = context.get_request_payload_as(BatchCreateSessionRequest).sessions
        valid_sessions = []
        failed_sessions = []

        for session in sessions:
            session, is_valid = self._validate_create_session_request(session)
            if not is_valid:
                failed_sessions.append(session)
            else:
                session = self.complete_create_session_request(session, context)
                session = self.session_utils.create_session(session)
                if Utils.is_empty(session.failure_reason):
                    valid_sessions.append(session)
                else:
                    failed_sessions.append(session)

        context.success(BatchCreateSessionResponse(
            success=valid_sessions,
            failed=failed_sessions
        ))

    def get_session_screenshots(self, context: ApiInvocationContext):
        screenshots = context.get_request_payload_as(GetSessionScreenshotRequest).screenshots
        valid_screenshots = []
        fail_list = []

        for screenshot in screenshots:
            screenshot, is_valid = self.validate_get_session_screenshot_request(screenshot)
            if is_valid:
                valid_screenshots.append(screenshot)
            else:
                fail_list.append(screenshot)

        valid_screenshots = self.complete_get_session_screenshots_request(valid_screenshots, context)
        success_list, fail_list_response = self._get_session_screenshots(valid_screenshots)
        fail_list.extend(fail_list_response)

        context.success(GetSessionScreenshotResponse(
            success=success_list,
            failed=fail_list
        ))

    def get_software_stack_info(self, context: ApiInvocationContext):
        stack_id = context.get_request_payload_as(GetSoftwareStackInfoRequest).stack_id
        base_os = context.get_request_payload_as(GetSoftwareStackInfoRequest).base_os
        if Utils.is_empty(stack_id):
            context.fail(
                error_code=errorcodes.INVALID_PARAMS,
                message='stack_id is missing'
            )
            return

        context.success(GetSoftwareStackInfoResponse(
            software_stack=self._get_software_stack_info(stack_id, base_os)
        ))

    def get_session_info(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(GetSessionInfoRequest)
        session = request.session
        self.validate_get_session_info_request(session)
        session = self.complete_get_session_info_request(session, context)
        session = self.session_db.get_from_db(session.owner, session.idea_session_id)
        if Utils.is_empty(session.failure_reason):
            context.success(GetSessionInfoResponse(
                session=session
            ))
        else:
            context.fail(
                error_code=errorcodes.INVALID_PARAMS,
                message=session.failure_reason,
                payload=GetSessionInfoResponse(
                    session=session
                ))

    def delete_sessions(self, context: ApiInvocationContext):
        """
        Deletes multiple sessions (session ids provided)
        """
        sessions = context.get_request_payload_as(DeleteSessionRequest).sessions
        valid_sessions = []
        failed_sessions = []
        for session in sessions:
            session, is_valid = self._validate_delete_session_request(session)
            if is_valid:
                self.complete_delete_session_request(session, context)
                valid_sessions.append(session)
            else:
                failed_sessions.append(session)

        success_list, failed_list = self.session_utils.terminate_sessions(valid_sessions)
        failed_list.extend(failed_sessions)
        context.success(DeleteSessionResponse(
            success=success_list,
            failed=failed_list
        ))

    def reboot_sessions(self, context: ApiInvocationContext):
        sessions = context.get_request_payload_as(RebootSessionRequest).sessions
        failed_sessions = []
        sessions_to_reboot = []

        for session in sessions:
            is_valid = self._validate_reboot_session_request(session)
            if not is_valid:
                failed_sessions.append(session)
                continue

            self.complete_reboot_session_request(session, context)
            sessions_to_reboot.append(session)

        success, failed = self._reboot_sessions(sessions_to_reboot)
        failed.extend(failed_sessions)
        context.success(RebootSessionResponse(
            success=success,
            failed=failed
        ))

    def stop_sessions(self, context: ApiInvocationContext):
        sessions = context.get_request_payload_as(StopSessionRequest).sessions
        failed_sessions = []
        sessions_to_stop = []

        for session in sessions:
            is_valid = self._validate_stop_session_request(session)
            if not is_valid:
                failed_sessions.append(session)
                continue

            self.complete_stop_session_request(session, context)
            sessions_to_stop.append(session)

        success, failed = self._stop_sessions(sessions_to_stop)
        failed.extend(failed_sessions)
        context.success(StopSessionResponse(
            success=success,
            failed=failed
        ))

    def resume_sessions(self, context: ApiInvocationContext):
        sessions = context.get_request_payload_as(ResumeSessionsRequest).sessions
        failed_sessions = []
        sessions_to_resume = []
        for session in sessions:
            session, is_valid = self._validate_resume_session_request(session)
            if not is_valid:
                failed_sessions.append(session)
                continue

            self.complete_resume_session_request(session, context)
            sessions_to_resume.append(session)

        success_list, fail_list = self._resume_sessions(sessions_to_resume)
        fail_list.extend(failed_sessions)
        context.success(ResumeSessionsResponse(
            success=success_list,
            failed=fail_list
        ))

    def list_software_stacks(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(ListSoftwareStackRequest)
        result = self._list_software_stacks(request)
        context.success(result)

    def list_sessions(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(ListSessionsRequest)
        result = self.session_db.list_all_from_db(request)
        context.success(result)

    def update_session(self, context: ApiInvocationContext):
        session = context.get_request_payload_as(UpdateSessionRequest).session
        self.complete_update_session_request(session, context)

        session = self._update_session(session)
        if Utils.is_not_empty(session.failure_reason):
            context.fail(
                message=session.failure_reason,
                error_code=errorcodes.UPDATE_SESSION_FAILED,
                payload=UpdateSessionResponse(
                    session=session
                ))
        else:
            context.success(UpdateSessionResponse(
                session=session
            ))

    def update_session_permission(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(UpdateSessionPermissionRequest)
        is_valid_request, request = self.validate_update_session_permission_request(request)

        if not is_valid_request:
            context.fail(
                error_code=errorcodes.INVALID_PARAMS,
                payload=UpdateSessionPermissionResponse(
                    permissions=[] + request.create + request.update + request.delete
                ),
                message='Invalid request. Rejecting all permissions'
            )
        else:
            response = self.session_permissions_utils.update_permission_for_sessions(request)
            context.success(response)

    def update_software_stack(self, context: ApiInvocationContext):
        new_software_stack = context.get_request_payload_as(UpdateSoftwareStackRequest).software_stack
        new_software_stack, is_valid = self._validate_update_software_stack_request(new_software_stack)
        if not is_valid:
            context.fail(
                message=new_software_stack.failure_reason,
                error_code=errorcodes.INVALID_PARAMS,
                payload=UpdateSoftwareStackResponse(
                    software_stack=new_software_stack
                ))
            return

        if Utils.is_any_empty(new_software_stack.stack_id):
            new_software_stack.failure_reason = 'software_stack.stack_id missing'
            context.fail(
                message=new_software_stack.failure_reason,
                error_code=errorcodes.INVALID_PARAMS,
                payload=UpdateSoftwareStackResponse(
                    software_stack=new_software_stack
                ))
            return

        old_software_stack = self.software_stack_db.get(stack_id=new_software_stack.stack_id, base_os=new_software_stack.base_os)
        if old_software_stack is None:
            new_software_stack.failure_reason = f'Invalid id {new_software_stack.stack_id} with base os {new_software_stack.base_os}'
            context.fail(
                message=new_software_stack.failure_reason,
                error_code=errorcodes.INVALID_PARAMS,
                payload=UpdateSoftwareStackResponse(
                    software_stack=new_software_stack
                ))
            return

        if Utils.is_not_empty(new_software_stack.description):
            old_software_stack.description = new_software_stack.description
        if Utils.is_not_empty(new_software_stack.name):
            old_software_stack.name = new_software_stack.name
        if Utils.is_not_empty(new_software_stack.enabled):
            old_software_stack.enabled = new_software_stack.enabled
        old_software_stack.projects = new_software_stack.projects

        new_software_stack = self.software_stack_db.update(old_software_stack)
        ss_projects = []
        for project in new_software_stack.projects:
            ss_projects.append(self.context.projects_client.get_project(GetProjectRequest(project_id=project.project_id)).project)
        new_software_stack.projects = ss_projects
        context.success(UpdateSoftwareStackResponse(
            software_stack=new_software_stack
        ))

    def create_software_stack(self, context: ApiInvocationContext):
        software_stack = context.get_request_payload_as(CreateSoftwareStackRequest).software_stack

        if software_stack.name:
            ApiUtils.validate_input(software_stack.name,
                                    constants.SOFTWARE_STACK_NAME_REGEX,
                                    constants.SOFTWARE_STACK_NAME_ERROR_MESSAGE)

        software_stack, is_valid = self._validate_create_software_stack_request(software_stack)
        if not is_valid:
            context.fail(
                message=software_stack.failure_reason,
                error_code=errorcodes.INVALID_PARAMS,
                payload=CreateSoftwareStackResponse(
                    software_stack=software_stack
                ))
            return

        software_stack = self._create_software_stack(software_stack)
        context.success(CreateSoftwareStackResponse(
            software_stack=software_stack
        ))

    def create_software_stack_from_session(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(CreateSoftwareStackFromSessionRequest)
        session = request.session
        if Utils.is_empty(session.owner):
            context.fail(
                message='session.owner missing',
                payload=None,
                error_code=errorcodes.INVALID_PARAMS
            )
            return

        new_software_stack = request.new_software_stack
        new_software_stack, is_valid = self.validate_create_software_stack_request(new_software_stack)
        if not is_valid:
            context.fail(
                message=new_software_stack.failure_reason,
                payload=None,
                error_code=errorcodes.INVALID_PARAMS
            )
            return

        new_software_stack = self._create_software_stack_from_session(session, new_software_stack)
        if Utils.is_empty(new_software_stack.failure_reason):
            context.success(CreateSoftwareStackFromSessionResponse(software_stack=new_software_stack))
        else:
            context.fail(
                message=new_software_stack.failure_reason,
                payload=CreateSoftwareStackFromSessionResponse(software_stack=new_software_stack),
                error_code=errorcodes.CREATED_SOFTWARE_STACK_FROM_SESSION_FAILED
            )

    def delete_software_stack(self, context: ApiInvocationContext):
        software_stack = context.get_request_payload_as(DeleteSoftwareStackRequest).software_stack
        if Utils.is_empty(software_stack.stack_id) or Utils.is_empty(software_stack.base_os):
            context.fail(
                error_code=errorcodes.INVALID_PARAMS,
                message=f'Stack ID and base OS are required'
            )

            return

        self._delete_software_stack(software_stack)
        context.success(DeleteSoftwareStackResponse())

    def update_permission_profile(self, context: ApiInvocationContext):
        permission_profile = context.get_request_payload_as(UpdatePermissionProfileRequest).profile
        existing_profile = self.permission_profile_db.get(profile_id=permission_profile.profile_id)
        if Utils.is_empty(existing_profile):
            context.fail(
                error_code=errorcodes.INVALID_PARAMS,
                message=f'Profile ID: {permission_profile.profile_id} does not exist'
            )
            return
        permission_profile = self.permission_profile_db.update(permission_profile)
        context.success(UpdatePermissionProfileResponse(
            profile=permission_profile
        ))

    def create_permission_profile(self, context: ApiInvocationContext):
        permission_profile = context.get_request_payload_as(CreatePermissionProfileRequest).profile
        existing_profile = self.permission_profile_db.get(profile_id=permission_profile.profile_id)
        if Utils.is_not_empty(existing_profile):
            context.fail(
                error_code=errorcodes.INVALID_PARAMS,
                message=f'Profile ID: {permission_profile.profile_id} is not unique. Use a unique name'
            )
            return

        permission_profile = self.permission_profile_db.create(permission_profile)
        context.success(CreatePermissionProfileResponse(
            profile=permission_profile
        ))

    def delete_permission_profile(self, context: ApiInvocationContext):
        profile_id = context.get_request_payload_as(DeletePermissionProfileRequest).profile_id
        if not profile_id:
            context.fail(
                message="permission profile ID is required",
                error_code=errorcodes.INVALID_PARAMS,
                payload=DeletePermissionProfileResponse(
                ))
            return
        existing_profile = self.permission_profile_db.get(profile_id=profile_id)
        if not existing_profile:
            context.success(DeletePermissionProfileResponse())
            return

        self.permission_profile_db.delete(profile_id)
        context.success(DeletePermissionProfileResponse())

    def get_session_connection_info(self, context: ApiInvocationContext):
        self._logger.info(f'received get session connection info request from user: {context.get_username()}')
        connection_info_request = context.get_request_payload_as(GetSessionConnectionInfoRequest).connection_info
        message, is_valid = self.validate_get_connection_info_request(connection_info_request)
        if not is_valid:
            context.fail(
                message=message,
                error_code=errorcodes.INVALID_PARAMS,
                payload=GetSessionConnectionInfoResponse(
                    connection_info=connection_info_request
                ))
            return

        if Utils.is_empty(connection_info_request.username):
            connection_info_request.username = context.get_username()

        connection_info = self._get_session_connection_info(connection_info_request, context)

        if Utils.is_empty(connection_info.failure_reason):
            context.success(GetSessionConnectionInfoResponse(
                connection_info=connection_info
            ))
        else:
            context.fail(
                message=connection_info.failure_reason,
                error_code=errorcodes.SESSION_CONNECTION_ERROR,
                payload=GetSessionConnectionInfoResponse(
                    connection_info=connection_info
                ))

    def list_shared_permissions(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(ListPermissionsRequest)

        username = request.username
        if Utils.is_empty(username):
            context.fail(
                error_code=errorcodes.INVALID_PARAMS,
                message='username missing',
                payload=request
            )
            return

        response = self._list_shared_permissions(username=username, request=request)
        context.success(response)

    def list_session_permissions(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(ListPermissionsRequest)
        idea_session_id = request.idea_session_id
        if Utils.is_empty(idea_session_id):
            context.fail(
                error_code=errorcodes.INVALID_PARAMS,
                message='RES Session ID missing',
                payload=request
            )
            return

        response = self._list_session_permissions(idea_session_id=idea_session_id, request=request)
        context.success(response)

    def invoke(self, context: ApiInvocationContext):
        namespace = context.namespace

        acl_entry = self.acl.get(namespace)
        if acl_entry is None:
            raise exceptions.unauthorized_access()

        acl_entry_scope = acl_entry.get('scope')
        is_authorized = context.is_authorized(elevated_access=True, scopes=[acl_entry_scope])

        if is_authorized:
            acl_entry['method'](context)
        else:
            raise exceptions.unauthorized_access()
