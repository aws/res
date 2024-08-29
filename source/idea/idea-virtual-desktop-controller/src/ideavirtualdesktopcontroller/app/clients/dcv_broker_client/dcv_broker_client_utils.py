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
from threading import RLock
from typing import List

import ideavirtualdesktopcontroller
from ideadatamodel.virtual_desktop import (
    VirtualDesktopSession,
    VirtualDesktopBaseOS,
    VirtualDesktopSessionState,
    VirtualDesktopServer,
    VirtualDesktopSessionType
)
from ideasdk.utils import Utils
from ideavirtualdesktopcontroller.app.session_permissions.virtual_desktop_session_permission_utils import VirtualDesktopSessionPermissionUtils


class DCVBrokerClientUtils:

    def __init__(self, context: ideavirtualdesktopcontroller.AppContext, session_permission_utils: VirtualDesktopSessionPermissionUtils):
        self.context = context
        self._logger = context.logger('dcv-broker-client-utils')
        self._session_permission_utils = session_permission_utils
        self.BROKER_TABLE_NAMES = 'dcv-broker.table-names-list'
        self.broker_table_names_lock = RLock()

    def get_broker_dynamodb_table_names(self) -> List[str]:
        broker_table_names = self.context.cache().long_term().get(self.BROKER_TABLE_NAMES)
        if Utils.is_empty(broker_table_names):
            broker_table_names = []
            with self.broker_table_names_lock:
                last_evaluated_table_name = None
                while True:
                    if Utils.is_empty(last_evaluated_table_name):
                        response = self.context.aws().dynamodb().list_tables()
                    else:
                        response = self.context.aws().dynamodb().list_tables(
                            ExclusiveStartTableName=last_evaluated_table_name
                        )
                    table_names = Utils.get_value_as_list('TableNames', response, [])
                    for table_name in table_names:
                        if f'{self.context.cluster_name()}.{self.context.module_id()}.dcv-broker.' in table_name:
                            broker_table_names.append(table_name)

                    last_evaluated_table_name = Utils.get_value_as_string('LastEvaluatedTableName', response, None)
                    if Utils.is_empty(last_evaluated_table_name):
                        break

                self.context.cache().long_term().set(self.BROKER_TABLE_NAMES, broker_table_names)
        return broker_table_names

    @staticmethod
    def get_server_object_from_success_result(server_json) -> VirtualDesktopServer:
        server = VirtualDesktopServer(
            server_id=Utils.get_value_as_string("id", server_json, None),
            private_ip=Utils.get_value_as_string("ip", server_json, None),
            private_dns_name=Utils.get_value_as_string("hostname", server_json, None),
            public_ip=None,
            public_dns_name=None,
            availability=Utils.get_value_as_string("availability", server_json, None),
            unavailability_reason=Utils.get_value_as_string("unavailabilityreason", server_json, None),
            console_session_count=Utils.get_value_as_int("consolesessioncount", server_json, None),
            virtual_session_count=Utils.get_value_as_int("virtualsessioncount", server_json, None)
        )

        tags = Utils.get_value_as_list('tags', server_json, [])
        for tag in tags:
            if Utils.get_value_as_string("key", tag, None) == 'dcv:os-family':
                server.os_family = Utils.get_value_as_string("value", tag, None)
            elif Utils.get_value_as_string("key", tag, None) == 'dcv:max-concurrent-sessions-per-user':
                server.max_concurrent_sessions_per_user = Utils.get_value_as_string("value", tag, None)
            elif Utils.get_value_as_string("key", tag, None) == 'dcv:max-virtual-sessions':
                server.max_virtual_sessions = Utils.get_value_as_string("value", tag, None)

        return server

    @staticmethod
    def get_session_object_from_success_result(session_json) -> VirtualDesktopSession:
        return VirtualDesktopSession(
            dcv_session_id=Utils.get_value_as_string("id", session_json, None),
            owner=Utils.get_value_as_string("owner", session_json, None),
            type=VirtualDesktopSessionType[Utils.get_value_as_string("type", session_json, "VIRTUAL")],
            name=Utils.get_value_as_string("name", session_json, None),
            state=VirtualDesktopSessionState[Utils.get_value_as_string("state", session_json, "READY")],
            server=DCVBrokerClientUtils.get_server_object_from_success_result(Utils.get_value_as_dict("server", session_json, {}))
        )

    @staticmethod
    def get_session_object_from_error_result(session_json) -> VirtualDesktopSession:
        session_request_data = Utils.get_value_as_dict('create_session_request_data', session_json, {})

        return VirtualDesktopSession(
            dcv_session_id=Utils.get_value_as_string("id", session_request_data, None),
            owner=Utils.get_value_as_string("owner", session_request_data, None),
            type=VirtualDesktopSessionType[Utils.get_value_as_string("type", session_request_data, "VIRTUAL")],
            name=Utils.get_value_as_string("name", session_request_data, None),
            failure_reason=Utils.get_value_as_string("failure_reason", session_json, None)
        )

    @staticmethod
    def get_storage_root_for_base_os(base_os: VirtualDesktopBaseOS, owner) -> str:
        if base_os in (VirtualDesktopBaseOS.AMAZON_LINUX2, VirtualDesktopBaseOS.RHEL8, VirtualDesktopBaseOS.RHEL9):
            return f'/home/{owner}/storage-root'

        return f'C:\\session-storage\\{owner}'

    def get_commands_to_execute_for_resuming_session(self, session: VirtualDesktopSession) -> List[str]:
        storage_root = DCVBrokerClientUtils.get_storage_root_for_base_os(session.software_stack.base_os, session.owner)
        command_list = []
        permissions_content = self._session_permission_utils.generate_permissions_for_session(session, False)

        if session.software_stack.base_os == VirtualDesktopBaseOS.WINDOWS:
            dcv_command = f'cmd.exe /c "`"C:\\Program Files\\NICE\\DCV\\Server\\bin\\dcv.exe`" create-session ' \
                          f'--type {session.type.lower()} --name `"{session.name}`" --user {session.owner} ' \
                          f'--owner {session.owner} --storage-root `"{storage_root}`" '
            if Utils.is_not_empty(permissions_content):
                permissions_folder = f'C:\\Program Files\\NICE\\DCV\\{session.dcv_session_id}\\'
                command_list.append(f'Remove-Item -Recurse -Force "{permissions_folder}"')
                command_list.append(f'New-Item -Path "{permissions_folder}" -ItemType Directory')
                command_list.append(f'New-Item -Path "{permissions_folder}" -Name "idea.perm" -ItemType File -Force -Value "{permissions_content}"')
                permissions_file_path = f'{permissions_folder}idea.perm'
                dcv_command += f'--permissions-file `"{permissions_file_path}`" '
        else:
            dcv_command = f'dcv create-session --type {session.type.lower()} --name "{session.name}" ' \
                          f'--user {session.owner} --owner {session.owner} --storage-root "{storage_root}" '

            if Utils.is_not_empty(permissions_content):
                command_list.append(f"mkdir -p /etc/dcv/{session.dcv_session_id}/")
                command_list.append(f"echo \"{permissions_content}\" > /etc/dcv/{session.dcv_session_id}/idea.perm")
                permissions_file_path = f"/etc/dcv/{session.dcv_session_id}/idea.perm"
                dcv_command += f'--permissions-file "{permissions_file_path}" '

        dcv_command += f'{session.dcv_session_id}'
        if session.software_stack.base_os == VirtualDesktopBaseOS.WINDOWS:
            dcv_command += '"'

        command_list.append(dcv_command)
        return command_list

    def get_active_counts_for_sessions(self, sessions: List[VirtualDesktopSession]) -> List[VirtualDesktopSession]:
        if Utils.is_empty(sessions):
            return []

        dcv_session_id_map = {}
        for session in sessions:
            dcv_session_id_map[session.dcv_session_id] = session
            session.connection_count = 0

        response = self.context.dcv_broker_client.describe_sessions(sessions)

        session_response = Utils.get_value_as_dict('sessions', response, {})
        for dcv_session_id in session_response.keys():
            dcv_session_id_map[dcv_session_id].connection_count = Utils.get_value_as_int('num_of_connections',
                                                                                         session_response.get(dcv_session_id), 0)
        return sessions
