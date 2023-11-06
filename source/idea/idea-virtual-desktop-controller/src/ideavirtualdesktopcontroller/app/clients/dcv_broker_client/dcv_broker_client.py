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

from typing import Dict, List

import ideavirtualdesktopcontroller
import ideavirtualdesktopcontroller.app.clients.dcvssmswaggerclient as dcvssmswaggerclient
from botocore.exceptions import ClientError
from ideadatamodel.virtual_desktop import (
    VirtualDesktopSession,
    VirtualDesktopBaseOS,
    VirtualDesktopSessionState,
    VirtualDesktopSessionScreenshot,
    VirtualDesktopSessionConnectionInfo
)
from ideasdk.utils import Utils
from ideavirtualdesktopcontroller.app.clients.dcv_broker_client.dcv_broker_client_utils import DCVBrokerClientUtils
from ideavirtualdesktopcontroller.app.clients.dcvssmswaggerclient import UpdateSessionPermissionsRequestData
from ideavirtualdesktopcontroller.app.clients.dcvssmswaggerclient.models.create_session_request_data import CreateSessionRequestData
from ideavirtualdesktopcontroller.app.clients.dcvssmswaggerclient.models.delete_session_request_data import DeleteSessionRequestData
from ideavirtualdesktopcontroller.app.clients.dcvssmswaggerclient.models.describe_servers_request_data import DescribeServersRequestData
from ideavirtualdesktopcontroller.app.clients.dcvssmswaggerclient.models.describe_sessions_request_data import DescribeSessionsRequestData
from ideavirtualdesktopcontroller.app.clients.dcvssmswaggerclient.models.get_session_screenshot_request_data import \
    GetSessionScreenshotRequestData
from ideavirtualdesktopcontroller.app.clients.dcvssmswaggerclient.models.key_value_pair import KeyValuePair
from ideavirtualdesktopcontroller.app.app_protocols import DCVClientProtocol
import urllib3.exceptions

from ideavirtualdesktopcontroller.app.permission_profiles.virtual_desktop_permission_profile_db import VirtualDesktopPermissionProfileDB
from ideavirtualdesktopcontroller.app.session_permissions.virtual_desktop_session_permission_utils import VirtualDesktopSessionPermissionUtils
from ideavirtualdesktopcontroller.app.ssm_commands.virtual_desktop_ssm_commands_db import VirtualDesktopSSMCommandsDB
from ideavirtualdesktopcontroller.app.ssm_commands.virtual_desktop_ssm_commands_utils import VirtualDesktopSSMCommandsUtils
from ideavirtualdesktopcontroller.app.session_permissions.virtual_desktop_session_permission_db import VirtualDesktopSessionPermissionDB

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class DCVBrokerClient(DCVClientProtocol):
    def __init__(self, context: ideavirtualdesktopcontroller.AppContext):
        self.context = context

        self._ssm_commands_db = VirtualDesktopSSMCommandsDB(self.context)
        self._ssm_commands_utils = VirtualDesktopSSMCommandsUtils(self.context, db=self._ssm_commands_db)
        self._session_permission_db = VirtualDesktopSessionPermissionDB(self.context)
        self._permission_profile_db = VirtualDesktopPermissionProfileDB(self.context)
        self._session_permission_utils = VirtualDesktopSessionPermissionUtils(
            self.context,
            db=self._session_permission_db,
            permission_profile_db=self._permission_profile_db)
        self._dcv_broker_client_utils = DCVBrokerClientUtils(
            context=self.context,
            session_permission_utils=self._session_permission_utils)
        self.__INTERNAL_ALB_ENDPOINT = self.context.config().get_cluster_internal_endpoint()
        self.__BROKER_CLIENT_COMMUNICATION_PORT = self.context.config().get_int('virtual-desktop-controller.dcv_broker.client_communication_port', required=True)
        # self.__CERT_FILE_LOCATION = ''
        self._logger = context.logger('dcv-broker-client')
        self.DCV_SESSION_DELETE_ERROR_SESSION_DOESNT_EXIST = "The requested dcvSession does not exist"

    def _get_client_configuration(self):
        configuration = dcvssmswaggerclient.Configuration()
        configuration.host = f'{self.__INTERNAL_ALB_ENDPOINT}:{self.__BROKER_CLIENT_COMMUNICATION_PORT}'

        # this is made false because we have not yet installed these certificates on the machine.
        configuration.verify_ssl = False
        # configuration.ssl_ca_cert = self.__CERT_FILE_LOCATION
        return configuration

    def _set_request_headers(self, api_client):
        api_client.set_default_header(header_name='Authorization',
                                      header_value='Bearer {}'.format(self.context.token_service.get_access_token()))

    def _get_servers_api(self):
        api_instance = dcvssmswaggerclient.ServersApi(dcvssmswaggerclient.ApiClient(self._get_client_configuration()))
        self._set_request_headers(api_instance.api_client)
        return api_instance

    def _get_sessions_api(self):
        api_instance = dcvssmswaggerclient.SessionsApi(dcvssmswaggerclient.ApiClient(self._get_client_configuration()))
        self._set_request_headers(api_instance.api_client)
        return api_instance

    def _get_sessions_connections_api(self):
        api_instance = dcvssmswaggerclient.GetSessionConnectionDataApi(dcvssmswaggerclient.ApiClient(self._get_client_configuration()))
        self._set_request_headers(api_instance.api_client)
        return api_instance

    def _get_session_permissions_api(self):
        api_instance = dcvssmswaggerclient.SessionPermissionsApi(dcvssmswaggerclient.ApiClient(self._get_client_configuration()))
        self._set_request_headers(api_instance.api_client)
        return api_instance

    def enforce_session_permissions(self, session: VirtualDesktopSession):
        permissions_content = self._session_permission_utils.generate_permissions_for_session(session, True)
        permissions_content_base_64 = None if Utils.is_empty(permissions_content) else Utils.base64_encode(permissions_content)
        request = UpdateSessionPermissionsRequestData(
            session_id=session.dcv_session_id,
            owner=session.owner,
            permissions_file=permissions_content_base_64
        )
        _ = self._get_session_permissions_api().update_session_permissions([request])

    def _delete_sessions(self, sessions: List[VirtualDesktopSession], force=False) -> Dict:
        if Utils.is_empty(sessions):
            self._logger.info('sessions is empty.. returning')
            return {}

        delete_sessions_request = list()
        for session in sessions:
            delete_sessions_request.append(DeleteSessionRequestData(session_id=session.dcv_session_id, owner=session.owner, force=force))

        api_response = self._get_sessions_api().delete_sessions(body=delete_sessions_request)
        return api_response.to_dict()

    def get_active_counts_for_sessions(self, sessions: List[VirtualDesktopSession]) -> List[VirtualDesktopSession]:
        return self._dcv_broker_client_utils.get_active_counts_for_sessions(sessions)

    def describe_sessions(self, sessions: List[VirtualDesktopSession]) -> Dict:
        session_ids = []

        if Utils.is_empty(sessions):
            sessions = []

        for session in sessions:
            session_ids.append(session.dcv_session_id)

        if Utils.is_empty(session_ids):
            session_ids = None

        response = self._describe_sessions(session_ids=session_ids)
        sessions = {}
        for session in Utils.get_value_as_list("sessions", response, []):
            sessions[session["id"]] = session
        response["sessions"] = sessions
        return response

    def _describe_sessions(self, session_ids=None, next_token=None, tags=None, owner=None) -> Dict:
        filters = list()
        if tags:
            for tag in tags:
                filter_key_value_pair = KeyValuePair(key='tag:' + tag['Key'], value=tag['Value'])
                filters.append(filter_key_value_pair)
        if owner:
            filter_key_value_pair = KeyValuePair(key='owner', value=owner)
            filters.append(filter_key_value_pair)

        request = DescribeSessionsRequestData(session_ids=session_ids, filters=filters, next_token=next_token)
        api_response = self._get_sessions_api().describe_sessions(body=request)
        return api_response.to_dict()

    def resume_session(self, session: VirtualDesktopSession) -> VirtualDesktopSession:
        try:
            _ = self._ssm_commands_utils.submit_ssm_command_to_resume_session(
                instance_id=session.server.instance_id,
                idea_session_id=session.idea_session_id,
                idea_session_owner=session.owner,
                commands=self._dcv_broker_client_utils.get_commands_to_execute_for_resuming_session(session),
                document_name="AWS-RunPowerShellScript" if session.software_stack.base_os == VirtualDesktopBaseOS.WINDOWS else "AWS-RunShellScript"
            )
            session.state = VirtualDesktopSessionState.RESUMING
        except ClientError as e:
            self._logger.error(e)
            # Most probably this instance is not yet ready to run ssm commands.
            session.failure_reason = f'Instance {session.server.instance_id} is not yet ready to run ssm commands, because {str(e)}'
        return session

    def _create_session(self, session: VirtualDesktopSession) -> Dict:

        request_data = CreateSessionRequestData(
            name=session.name,
            owner=session.owner,
            type=session.type.name,
            init_file_path=None,
            autorun_file=None,
            autorun_file_arguments=None,
            max_concurrent_clients=None,
            dcv_gl_enabled=None,
            requirements=f"tag:idea_session_id='{session.idea_session_id}'",
        )

        permissions_content = self._session_permission_utils.generate_permissions_for_session(session, True)
        request_data.permissions_file = None if Utils.is_empty(permissions_content) else Utils.base64_encode(permissions_content)
        request_data.storage_root = self._dcv_broker_client_utils.get_storage_root_for_base_os(session.software_stack.base_os, session.owner)
        return self._get_sessions_api().create_sessions(body=[request_data]).to_dict()

    def create_session(self, session: VirtualDesktopSession) -> VirtualDesktopSession:
        create_session_response = self._create_session(session)
        # self._logger.info(create_session_response)

        # WE KNOW THERE IS GOING TO BE EXACTLY ONE SESSION EITHER IN SUCCESSFUL LIST OR UNSUCCESSFUL LIST
        for entry in Utils.get_value_as_list("successful_list", create_session_response, []):
            session = self._dcv_broker_client_utils.get_session_object_from_success_result(entry)

        for entry in Utils.get_value_as_list("unsuccessful_list", create_session_response, []):
            session = self._dcv_broker_client_utils.get_session_object_from_error_result(entry)

        return session

    def delete_sessions(self, sessions: List[VirtualDesktopSession]) -> (List[VirtualDesktopSession], List[VirtualDesktopSession]):
        if Utils.is_empty(sessions):
            self._logger.error('sessions to delete list is empty. Returning.')
            return [], []

        can_delete_sessions = []
        sessions_to_check = []
        for session in sessions:
            if Utils.is_not_empty(session.force) and session.force:
                can_delete_sessions.append(session)
            else:
                sessions_to_check.append(session)

        sessions_with_count = self.get_active_counts_for_sessions(sessions_to_check)
        unsuccessful_list = []
        delete_fail_session_ids = []

        for session in sessions_with_count:
            if session.connection_count > 0:
                session.failure_reason = f'There exists {session.connection_count} active connection(s) for idea_session_id: {session.idea_session_id}:{session.name}. Please terminate.'
                self._logger.error(session.failure_reason)
                delete_fail_session_ids.append(session.dcv_session_id)
                unsuccessful_list.append(session)
            else:
                can_delete_sessions.append(session)

        api_response = self._delete_sessions(can_delete_sessions, True)

        successful_list = []
        delete_success_session_ids = []
        for entry in Utils.get_value_as_list('successful_list', api_response, []):
            dcv_session_id = Utils.get_value_as_string('session_id', entry, None)
            successful_list.append(VirtualDesktopSession(dcv_session_id=dcv_session_id))
            delete_success_session_ids.append(dcv_session_id)

        for entry in Utils.get_value_as_list('unsuccessful_list', api_response, []):
            dcv_session_id = Utils.get_value_as_string('session_id', entry, None)
            failure_reason = Utils.get_value_as_string('failure_reason', entry, None)

            if failure_reason == self.DCV_SESSION_DELETE_ERROR_SESSION_DOESNT_EXIST:
                # the session doesn't exist anyway. No need to delete, we can categorize this as success.
                successful_list.append(VirtualDesktopSession(dcv_session_id=dcv_session_id))
                delete_success_session_ids.append(dcv_session_id)
            else:
                unsuccessful_list.append(VirtualDesktopSession(
                    dcv_session_id=dcv_session_id,
                    failure_reason=failure_reason,
                ))
                delete_fail_session_ids.append(dcv_session_id)
                self._logger.info(f'Delete session request failed for dcv_session_id: {dcv_session_id} because {failure_reason}')

        self._logger.info(f'Delete session request complete... success dcv_session_ids: {delete_success_session_ids}')
        return successful_list, unsuccessful_list

    def describe_servers(self) -> Dict:
        request_data = DescribeServersRequestData()
        return self._get_servers_api().describe_servers(body=request_data).to_dict()

    def _get_session_screenshots(self, screenshots: List[VirtualDesktopSessionScreenshot]) -> Dict:
        if Utils.is_empty(screenshots):
            self._logger.error('Zero valid screenshots requests sent. Returning Empty Dict... ')
            return {}

        request_data = []
        for screenshot in screenshots:
            request_data.append(GetSessionScreenshotRequestData(session_id=screenshot.dcv_session_id))
        return self._get_sessions_api().get_session_screenshots(body=request_data).to_dict()

    def get_session_screenshots(self, screenshots: List[VirtualDesktopSessionScreenshot]) -> (List[VirtualDesktopSessionScreenshot], List[VirtualDesktopSessionScreenshot]):
        successful_list = []
        unsuccessful_list = []
        while len(screenshots) > 0:
            successful, unsuccessful = self._get_session_screenshots_impl(screenshots[:5])
            successful_list.extend(successful)
            unsuccessful_list.extend(unsuccessful)
            screenshots = screenshots[5:]

        return successful_list, unsuccessful_list

    def _get_session_screenshots_impl(self, screenshots: List[VirtualDesktopSessionScreenshot]) -> (List[VirtualDesktopSessionScreenshot], List[VirtualDesktopSessionScreenshot]):
        api_response = self._get_session_screenshots(screenshots)

        successful_list = []
        for entry in Utils.get_value_as_list('successful_list', api_response, []):
            screenshot_entry = Utils.get_value_as_dict('session_screenshot', entry, {})
            image_list = Utils.get_value_as_list('images', screenshot_entry, [])
            for image in image_list:
                if not Utils.get_value_as_bool("primary", image, False):
                    continue

                successful_list.append(VirtualDesktopSessionScreenshot(
                    image_data=Utils.get_value_as_string('data', image, None),
                    image_type=Utils.get_value_as_string('format', image, 'png'),
                    create_time=Utils.get_value_as_string('creation_time', image, None),
                    dcv_session_id=Utils.get_value_as_string('session_id', screenshot_entry, None)
                ))
                break

        unsuccessful_list = []
        for entry in Utils.get_value_as_list('unsuccessful_list', api_response, []):
            unsuccessful_list.append(VirtualDesktopSessionScreenshot(
                dcv_session_id=Utils.get_value_as_string('session_id',
                                                         Utils.get_value_as_dict('get_session_screenshot_request_data', entry, {}), None),
                failure_reason=Utils.get_value_as_string('failure_reason', entry, None)
            ))

        return successful_list, unsuccessful_list

    def _get_session_connection_data(self, dcv_session_id: str, username: str) -> Dict:
        api_response = self._get_sessions_connections_api().get_session_connection_data(session_id=dcv_session_id, user=username)
        return api_response.to_dict()

    def get_session_connection_data(self, dcv_session_id: str, username: str) -> VirtualDesktopSessionConnectionInfo:
        try:
            api_response = self._get_session_connection_data(dcv_session_id, username)
        except Exception as e:
            self._logger.error(e)
            failure_reason = f'Error in retrieving session connection data for DCV Session ID: {dcv_session_id} for username: {username}'
            self._logger.error(failure_reason)
            return VirtualDesktopSessionConnectionInfo(
                failure_reason=failure_reason
            )

        session = Utils.get_value_as_dict('session', api_response, {})
        server = Utils.get_value_as_dict('server', session, {})

        return VirtualDesktopSessionConnectionInfo(
            dcv_session_id=Utils.get_value_as_string('id', session, None),
            idea_session_owner=Utils.get_value_as_string('owner', session, None),
            username=username,
            web_url_path=Utils.get_value_as_string('web_url_path', server, None),
            access_token=Utils.get_value_as_string('connection_token', api_response, None)
        )
