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
    CreateSessionRequest,
    CreateSessionResponse,
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
    ListSoftwareStackRequest,
    ListPermissionsRequest,
    UpdateSessionPermissionRequest,
    UpdateSessionPermissionResponse,
    VirtualDesktopSession,
    VirtualDesktopSessionScreenshot,
    VirtualDesktopSessionConnectionInfo,
    SocaFilter
)
from ideadatamodel import errorcodes, exceptions
from ideasdk.api import ApiInvocationContext
from ideasdk.utils import Utils
from ideavirtualdesktopcontroller.app.api.virtual_desktop_api import VirtualDesktopAPI
from ideavirtualdesktopcontroller.app.software_stacks.constants import SOFTWARE_STACK_DB_FILTER_PROJECT_ID_KEY, SOFTWARE_STACK_DB_PROJECTS_KEY


class VirtualDesktopUserAPI(VirtualDesktopAPI):

    def __init__(self, context: ideavirtualdesktopcontroller.AppContext):
        super().__init__(context)
        self.context = context
        self._logger = context.logger('virtual-desktop-user-api')
        self.SCOPE_WRITE = f'{self.context.module_id()}/write'
        self.SCOPE_READ = f'{self.context.module_id()}/read'

        self.acl = {
            'VirtualDesktop.CreateSession': {
                'scope': self.SCOPE_WRITE,
                'method': self.create_session,
            },
            'VirtualDesktop.UpdateSession': {
                'scope': self.SCOPE_WRITE,
                'method': self.update_session,
            },
            'VirtualDesktop.DeleteSessions': {
                'scope': self.SCOPE_WRITE,
                'method': self.delete_sessions,
            },
            'VirtualDesktop.GetSessionInfo': {
                'scope': self.SCOPE_READ,
                'method': self.get_session_info,
            },
            'VirtualDesktop.GetSessionScreenshot': {
                'scope': self.SCOPE_READ,
                'method': self.get_session_screenshots,
            },
            'VirtualDesktop.GetSessionConnectionInfo': {
                'scope': self.SCOPE_READ,
                'method': self.get_session_connection_info,
            },
            'VirtualDesktop.ListSessions': {
                'scope': self.SCOPE_READ,
                'method': self.list_sessions,
            },
            'VirtualDesktop.StopSessions': {
                'scope': self.SCOPE_WRITE,
                'method': self.stop_sessions,
            },
            'VirtualDesktop.ResumeSessions': {
                'scope': self.SCOPE_WRITE,
                'method': self.resume_sessions,
            },
            'VirtualDesktop.RebootSessions': {
                'scope': self.SCOPE_WRITE,
                'method': self.reboot_sessions,
            },
            'VirtualDesktop.ListSoftwareStacks': {
                'scope': self.SCOPE_READ,
                'method': self.list_software_stacks,
            },
            'VirtualDesktop.ListSharedPermissions': {
                'scope': self.SCOPE_READ,
                'method': self.list_shared_permissions,
            },
            'VirtualDesktop.ListSessionPermissions': {
                'scope': self.SCOPE_READ,
                'method': self.list_session_permissions,
            },
            'VirtualDesktop.UpdateSessionPermissions': {
                'scope': self.SCOPE_WRITE,
                'method': self.update_session_permission
            },
        }

    @staticmethod
    def _validate_owner(owner: str, context: ApiInvocationContext) -> (str, bool):
        if not Utils.is_empty(owner) and owner != context.get_username():
            return "Invalid owner provided. Non Admin users can submit requests for themselves only", False
        return "", True
    
    def _validate_owner_for_create(self, session: VirtualDesktopSession, context: ApiInvocationContext) -> (str, bool):
        '''
        User should be able to create session for themself if they have vdis.create_sessions for this project.
        User should be able to create session for others if they have vdis.create_terminate_others_sessions permission for this project.
        '''
        if Utils.is_empty(session.project) or Utils.is_empty(session.project.project_id):
            session.failure_reason = 'missing session.project.project_id'
            return session, False
        if Utils.is_empty(session.owner):
            session.failure_reason = 'missing session.owner'
            return session, False
        
        self._logger.info(f'Session creation requested by {context.get_username()} in project ID: {session.project.project_id} to be owned by {session.owner}')
        
        if session.owner == context.get_username():
            if not context.is_authorized(elevated_access=False, scopes=[self.acl.get(context.namespace).get('scope')], 
                                         role_assignment_resource_key=f'{session.project.project_id}:project', permission="vdis.create_sessions"):
                session.failure_reason = "You're not authorized to create sessions for yourself in this project."
                return session, False
        elif not context.is_authorized(elevated_access=False, scopes=[self.acl.get(context.namespace).get('scope')], 
                                       role_assignment_resource_key=f'{session.project.project_id}:project', permission="vdis.create_terminate_others_sessions"):
            session.failure_reason = "You're not authorized to create sessions for others in this project."
            return session, False

        return "", True
    
    def _validate_owner_for_delete(self, session: VirtualDesktopSession, context: ApiInvocationContext) -> (str, bool):
        '''
        User should always be able to terminate their own sessions.
        User should be able to terminate session for others if they have vdis.create_terminate_others_sessions permission for this project.
        '''
        if Utils.is_empty(session.project) or Utils.is_empty(session.project.project_id):
            session.failure_reason = 'missing session.project.project_id'
            return session, False
        if Utils.is_empty(session.owner):
            session.failure_reason = 'missing session.owner'
            return session, False
        
        if session.owner != context.get_username() and not context.is_authorized(elevated_access=False, scopes=[self.acl.get(context.namespace).get('scope')], 
                                                                                 role_assignment_resource_key=f'{session.project.project_id}:project', permission='vdis.create_terminate_others_sessions'):
            session.failure_reason = "You're not authorized to terminate others' sessions in this project."
            return session, False
        
        self._logger.info(f'Session termination requested by {context.get_username()} for session ID: {session.idea_session_id} owned by {session.owner}')

        return "", True

    def _validate_reboot_session_request(self, session: VirtualDesktopSession, context: ApiInvocationContext) -> (VirtualDesktopSession, bool):
        self.validate_reboot_session_request(session)
        message, is_valid = self._validate_owner(session.owner, context)
        if not is_valid:
            session.failure_reason = message

        return session, is_valid

    def _validate_stop_session_request(self, session: VirtualDesktopSession, context: ApiInvocationContext) -> (VirtualDesktopSession, bool):
        self.validate_stop_session_request(session)
        message, is_valid = self._validate_owner(session.owner, context)
        if not is_valid:
            session.failure_reason = message

        return session, is_valid

    def _validate_delete_session_request(self, session: VirtualDesktopSession, context: ApiInvocationContext) -> (VirtualDesktopSession, bool):
        valid_response = True
        session, is_valid = self.validate_delete_session_request(session)
        if not is_valid:
            valid_response = False

        error_message, is_valid = self._validate_owner_for_delete(session, context)
        if not is_valid:
            session.failure_reason = Utils.get_as_string(value=session.failure_reason, default='') + str(error_message)
            valid_response = False
        return session, valid_response

    def _validate_get_session_info_request(self, session: VirtualDesktopSession, context: ApiInvocationContext) -> (VirtualDesktopSession, bool):
        self.validate_get_session_info_request(session)
        message, is_valid = self._validate_owner(session.owner, context)
        if not is_valid:
            session.failure_reason = message

        return session, is_valid

    def _validate_get_connection_info_request(self, connection_info: VirtualDesktopSessionConnectionInfo, context: ApiInvocationContext) -> (VirtualDesktopSessionConnectionInfo, bool):
        message, is_valid = self.validate_get_connection_info_request(connection_info)
        if not is_valid:
            connection_info.failure_reason = message
            return connection_info, False

        message, is_valid = self._validate_owner(connection_info.username, context)
        if not is_valid:
            connection_info.failure_reason = message

        return connection_info, is_valid

    @staticmethod
    def _validate_update_session_permission_request(request: UpdateSessionPermissionRequest, context: ApiInvocationContext) -> (str, bool):
        for permission in request.create + request.delete + request.update:
            if permission.idea_session_owner != context.get_username():
                return 'Can update permission for session owned by user only', False
        return '', True

    def _validate_update_session_request(self, session: VirtualDesktopSession, context: ApiInvocationContext) -> (VirtualDesktopSession, bool):
        message, is_valid = self._validate_owner(session.owner, context)
        if not is_valid:
            session.failure_reason = message

        return session, is_valid

    def _validate_create_session_request(self, session: VirtualDesktopSession, context: ApiInvocationContext) -> (VirtualDesktopSession, bool):
        # Validate Session Object
        if Utils.is_empty(session):
            session = VirtualDesktopSession()
            session.failure_reason = 'Missing Create Session Info'
            return session, False

        # If session.owner is empty, assume owner is self
        if Utils.is_empty(session.owner): session.owner = context.get_username()
        message, is_valid = self._validate_owner_for_create(session, context)
        if not is_valid:
            session.failure_reason = Utils.get_as_string(value=session.failure_reason, default='') + str(message)
            self._logger.error(session.failure_reason)
            return session, False

        session_count_for_user = self.session_db.get_session_count_for_user(session.owner)
        if session_count_for_user >= self.context.config().get_int('virtual-desktop-controller.dcv_session.allowed_sessions_per_user', required=True):
            session.failure_reason = f'User {session.owner} has exceeded the allowed number of sessions: {session_count_for_user}. Please contact the System Administrators if you need to create more sessions.'
            return session, False

        return self.validate_create_session_request(session)

    def _validate_get_session_screenshot_request(self, screenshot: VirtualDesktopSessionScreenshot, context: ApiInvocationContext) -> (VirtualDesktopSessionScreenshot, bool):
        screenshot, is_valid = self.validate_get_session_screenshot_request(screenshot)
        validation_response = True
        if not is_valid:
            validation_response = False

        error_message, is_valid = self._validate_owner(screenshot.idea_session_owner, context)
        if not is_valid:
            screenshot.failure_reason = Utils.get_as_string(value=screenshot.failure_reason, default='') + str(error_message)
            self._logger.info(f'{screenshot.failure_reason}')
            validation_response = False
        return screenshot, validation_response

    def _validate_resume_session_request(self, session: VirtualDesktopSession, context: ApiInvocationContext) -> (VirtualDesktopSession, bool):
        session, is_valid = self.validate_resume_session_request(session)
        if not is_valid:
            return session, is_valid

        message, is_valid = self._validate_owner(session.owner, context)
        if not is_valid:
            session.failure_reason = message

        return session, is_valid

    def create_session(self, context: ApiInvocationContext):
        """
        Creates a single session.
        The username is retrieved from the token to ensure that the session created is in the user's name only.
        """
        self._logger.debug(f'received create session request from user: {context.get_username()}')
        session = context.get_request_payload_as(CreateSessionRequest).session
        session, is_valid = self._validate_create_session_request(session, context)
        if not is_valid:
            self._logger.error(session.failure_reason)
            context.fail(
                error_code=errorcodes.INVALID_PARAMS,
                message=session.failure_reason,
                payload=CreateSessionResponse(
                    session=session
                )
            )
            return

        session = self.complete_create_session_request(session, context)
        session.is_launched_by_admin = False
        session = self.session_utils.create_session(session)

        if Utils.is_empty(session.failure_reason):
            self._logger.info(f'session request created for user: {session.owner} with session name: {session.name} and idea_session_id: {session.idea_session_id}:{session.name}' + '' if session.owner == context.get_username() else f' by: {context.get_username()}')
            context.success(CreateSessionResponse(
                session=session
            ))
        else:
            context.fail(
                message=session.failure_reason,
                error_code=errorcodes.CREATE_SESSION_FAILED,
                payload=CreateSessionResponse(
                    session=session
                ))

    def get_session_connection_info(self, context: ApiInvocationContext):
        self._logger.info(f'received get session connection info request from user: {context.get_username()}')
        connection_info_request = context.get_request_payload_as(GetSessionConnectionInfoRequest).connection_info
        connection_info_request, is_valid_idea_session = self._validate_get_connection_info_request(connection_info_request, context)
        if not is_valid_idea_session:
            context.fail(
                message=connection_info_request.failure_reason,
                error_code=errorcodes.INVALID_PARAMS,
                payload=GetSessionConnectionInfoResponse(
                    connection_info=connection_info_request
                ))
            return

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

    def get_session_screenshots(self, context: ApiInvocationContext):
        screenshots = context.get_request_payload_as(GetSessionScreenshotRequest).screenshots
        valid_screenshots = []
        fail_list = []

        for screenshot in screenshots:
            screenshot, is_valid = self._validate_get_session_screenshot_request(screenshot, context)
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

    def get_session_info(self, context: ApiInvocationContext):
        session = context.get_request_payload_as(GetSessionInfoRequest).session
        session, is_valid = self._validate_get_session_info_request(session, context)
        if not is_valid:
            self._logger.error(session.failure_reason)
            context.fail(
                error_code=errorcodes.INVALID_PARAMS,
                message=session.failure_reason,
                payload=CreateSessionResponse(
                    session=session
                )
            )
            return

        session = self.complete_get_session_info_request(session, context)
        session = self.session_db.get_from_db(session.owner, session.idea_session_id)

        if Utils.is_empty(session.failure_reason):
            context.success(GetSessionInfoResponse(
                session=session))
        else:
            context.fail(
                error_code=errorcodes.INVALID_PARAMS,
                message=session.failure_reason,
                payload=GetSessionInfoResponse(
                    session=session
                )
            )

    def delete_sessions(self, context: ApiInvocationContext):
        """
        Deletes multiple sessions (session ids provided)
        """
        sessions = context.get_request_payload_as(DeleteSessionRequest).sessions
        valid_sessions = []
        failed_sessions = []
        for session in sessions:
            session, is_valid = self._validate_delete_session_request(session, context)
            if is_valid:
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
            session, is_valid = self._validate_reboot_session_request(session, context)
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
            session, is_valid = self._validate_stop_session_request(session, context)
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
            session, is_valid = self._validate_resume_session_request(session, context)
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

    def update_session(self, context: ApiInvocationContext):
        session = context.get_request_payload_as(UpdateSessionRequest).session
        session, is_valid = self._validate_update_session_request(session, context)
        if not is_valid:
            self._logger.error(session.failure_reason)
            context.fail(
                error_code=errorcodes.INVALID_PARAMS,
                message=session.failure_reason,
                payload=CreateSessionResponse(
                    session=session
                )
            )
            return

        self.complete_update_session_request(session, context)
        session = self._update_session(session)
        if Utils.is_not_empty(session.failure_reason):
            self._logger.error(session.failure_reason)
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

    def list_sessions(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(ListSessionsRequest)
        result = None
        username = context.get_username()

        # Get a list of projects where the current user has permission to manage other user sessions
        user_projects = self.get_user_projects(username=username)
        projects_to_manage_sessions = [project.project_id for project in user_projects if 
                                       context.is_authorized(elevated_access=False, scopes=[self.acl.get(context.namespace).get('scope')], 
                                                             role_assignment_resource_key=f'{project.project_id}:project', permission='vdis.create_terminate_others_sessions')]

        if not projects_to_manage_sessions:
            result = self.session_db.list_all_for_user(request, username)
        else:
            result = self.session_db.list_all_for_user_and_managed_sessions(request, username, projects_to_manage_sessions)
        context.success(result)

    def list_software_stacks(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(ListSoftwareStackRequest)
        project_id = request.project_id
        if Utils.is_empty(project_id):
            context.fail(
                error_code=errorcodes.INVALID_PARAMS,
                message='missing project_id',
                payload=request
            )
            return

        project_filter_found = False
        if Utils.is_not_empty(request.filters):
            for listing_filter in request.filters:
                if listing_filter.key == SOFTWARE_STACK_DB_FILTER_PROJECT_ID_KEY:
                    listing_filter.value = project_id
                    break

        if not project_filter_found:
            request.add_filter(SocaFilter(
                key=SOFTWARE_STACK_DB_PROJECTS_KEY,
                value=project_id
            ))

        result = self._list_software_stacks(request)
        context.success(result)

    def list_shared_permissions(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(ListPermissionsRequest)
        response = self._list_shared_permissions(username=context.get_username(), request=request)
        context.success(response)

    def list_session_permissions(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(ListPermissionsRequest)
        idea_session_id = request.idea_session_id
        if Utils.is_empty(idea_session_id):
            context.fail(
                error_code=errorcodes.INVALID_PARAMS,
                message='missing RES Session ID',
                payload=request
            )
            return

        session = self.get_session_if_owner(username=context.get_username(), idea_session_id=idea_session_id)
        if Utils.is_empty(session):
            context.fail(
                error_code=errorcodes.INVALID_PARAMS,
                message=f'Only session owner can request to list_session_permissions for session {idea_session_id}',
                payload=request
            )
            return

        response = self._list_session_permissions(idea_session_id=idea_session_id, request=request)
        context.success(response)

    def update_session_permission(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(UpdateSessionPermissionRequest)
        message, is_valid = self._validate_update_session_permission_request(request, context)
        if not is_valid:
            context.fail(
                error_code=errorcodes.INVALID_PARAMS,
                payload=UpdateSessionPermissionResponse(
                    permissions=[] + request.create + request.update + request.delete
                ),
                message=message
            )
        else:
            is_valid, request = self.validate_update_session_permission_request(request)

        if not is_valid:
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

    def invoke(self, context: ApiInvocationContext):
        namespace = context.namespace
        
        acl_entry = self.acl.get(namespace)
        if acl_entry is None:
            raise exceptions.unauthorized_access()

        acl_entry_scope = acl_entry.get('scope')
        is_authorized = context.is_authorized(elevated_access=False, scopes=[acl_entry_scope])
        self._logger.info(f'Is authorized: {is_authorized}')
        if is_authorized:
            acl_entry['method'](context)
        else:
            raise exceptions.unauthorized_access()
