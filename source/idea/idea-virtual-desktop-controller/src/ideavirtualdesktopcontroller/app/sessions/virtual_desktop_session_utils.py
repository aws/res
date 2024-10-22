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
from typing import List, Dict

import ideavirtualdesktopcontroller
from ideadatamodel import VirtualDesktopSession, VirtualDesktopServer, VirtualDesktopSessionState
from ideasdk.utils import Utils, DateTimeUtils
from ideavirtualdesktopcontroller.app.events.events_utils import EventsUtils
from ideavirtualdesktopcontroller.app.permission_profiles.virtual_desktop_permission_profile_db import VirtualDesktopPermissionProfileDB
from ideavirtualdesktopcontroller.app.schedules.virtual_desktop_schedule_utils import VirtualDesktopScheduleUtils
from ideavirtualdesktopcontroller.app.servers.virtual_desktop_server_utils import VirtualDesktopServerUtils
from ideavirtualdesktopcontroller.app.session_permissions.virtual_desktop_session_permission_db import VirtualDesktopSessionPermissionDB
from ideavirtualdesktopcontroller.app.session_permissions.virtual_desktop_session_permission_utils import VirtualDesktopSessionPermissionUtils
from ideavirtualdesktopcontroller.app.sessions.virtual_desktop_session_db import VirtualDesktopSessionDB
from ideavirtualdesktopcontroller.app.virtual_desktop_controller_utils import VirtualDesktopControllerUtils
from res.resources import vdi_management


class VirtualDesktopSessionUtils:
    def __init__(self, context: ideavirtualdesktopcontroller.AppContext, db: VirtualDesktopSessionDB, session_permission_db: VirtualDesktopSessionPermissionDB, permission_profile_db: VirtualDesktopPermissionProfileDB):
        self.context = context
        self._controller_utils = VirtualDesktopControllerUtils(self.context)
        self.events_utils = EventsUtils(context=self.context)
        self._session_db = db
        self._session_permission_db = session_permission_db
        self._permission_profile_db = permission_profile_db
        self._schedule_utils = VirtualDesktopScheduleUtils(context=self.context, db=self._session_db.schedule_db)
        self._session_permission_utils = VirtualDesktopSessionPermissionUtils(
            context=self.context,
            db=self._session_permission_db,
            permission_profile_db=self._permission_profile_db
        )
        self._server_utils = VirtualDesktopServerUtils(context=self.context, db=self._session_db.server_db)
        self._logger = context.logger('virtual-desktop-session-utils')

    def create_session(self, session: VirtualDesktopSession) -> VirtualDesktopSession:
        # request has been validated and everything.
        try:
            session.server = self._server_utils.provision_host_for_session(session)
        except Exception as e:
            session.failure_reason = f'{e}'
            return session

        session = self._schedule_utils.update_schedule_for_session(self._schedule_utils.get_default_schedules(), session)
        session.state = VirtualDesktopSessionState.PROVISIONING
        return self._session_db.create(session)

    def stop_sessions(self, sessions: List[VirtualDesktopSession]) -> (List[VirtualDesktopSession], List[VirtualDesktopSession]):
        success_response_list: List[VirtualDesktopSession] = []
        fail_response_list: List[VirtualDesktopSession] = []
        session_map: Dict[str: VirtualDesktopSession] = {}
        invalid_dcv_sessions: List[VirtualDesktopSession] = []
        sessions_to_delete: List[VirtualDesktopSession] = []

        for session_orig in sessions:
            session = self._session_db.get_from_db(idea_session_owner=session_orig.owner, idea_session_id=session_orig.idea_session_id)
            if Utils.is_empty(session):
                # Invalid IDEA Session.
                session.failure_reason = f'Invalid RES Session ID: {session.idea_session_id}:{session.name} for user: {session.owner}. Nothing to stop'
                self._logger.error(session.failure_reason)
                fail_response_list.append(session)
                continue

            if session.state not in {VirtualDesktopSessionState.READY}:
                session.failure_reason = f'RES Session ID: {session.idea_session_id}:{session.name} for user: {session.owner} is in {session.state} state. Can\'t stop. Wait for it to be READY.'
                self._logger.error(session.failure_reason)
                fail_response_list.append(session)
                continue

            if Utils.is_empty(session.dcv_session_id):
                # DCV Session doesn't exist. no point deleting.
                self._logger.info("DCV Session doesn't exist. no point deleting.")
                invalid_dcv_sessions.append(session)
                continue

            session.force = session_orig.force
            sessions_to_delete.append(session)
            session_map[session.dcv_session_id] = session

        success_list, error_list = self.context.dcv_broker_client.delete_sessions(sessions_to_delete)

        servers_to_stop: List[VirtualDesktopServer] = []
        servers_to_hibernate: List[VirtualDesktopServer] = []

        for session in success_list:
            session = session_map[session.dcv_session_id]
            session.state = VirtualDesktopSessionState.STOPPING
            session = self._session_db.update(session)
            self.events_utils.publish_validate_dcv_session_deletion_event(
                idea_session_id=session.idea_session_id,
                idea_session_owner=session.owner
            )
            success_response_list.append(session)

        for session in invalid_dcv_sessions:
            session.server.is_idle = session.is_idle if session.is_idle else False
            if session.hibernation_enabled:
                servers_to_hibernate.append(session.server)
            else:
                servers_to_stop.append(session.server)
            session.state = VirtualDesktopSessionState.STOPPING
            session = self._session_db.update(session)
            success_response_list.append(session)

        for session in error_list:
            session_map[session.dcv_session_id].failure_reason = session.failure_reason
            fail_response_list.append(session_map[session.dcv_session_id])

        stop_server_list = [server.dict() for server in servers_to_stop]
        hibernate_server_list = [server.dict() for server in servers_to_hibernate]
        vdi_management.stop_servers(servers=stop_server_list)
        vdi_management.hibernate_servers(servers=hibernate_server_list)
        return success_response_list, fail_response_list

    def resume_sessions(self, sessions: List[VirtualDesktopSession]) -> (List[VirtualDesktopSession], List[VirtualDesktopSession]):
        success_response_list: List[VirtualDesktopSession] = []
        fail_response_list: List[VirtualDesktopSession] = []
        servers_to_start: List[VirtualDesktopServer] = []
        session_server_map: Dict[str: VirtualDesktopSession] = {}

        for session in sessions:
            session = self._session_db.get_from_db(idea_session_owner=session.owner, idea_session_id=session.idea_session_id)
            if Utils.is_empty(session):
                self._logger.error(f'Invalid RES Session ID: {session.idea_session_id}:{session.name} for user: {session.owner}. Nothing to resume')
                session.failure_reason = f'Invalid RES Session ID: {session.idea_session_id}:{session.name} for user: {session.owner}. Nothing to resume'
                fail_response_list.append(session)
                continue

            if session.state not in {VirtualDesktopSessionState.STOPPED, VirtualDesktopSessionState.STOPPED_IDLE}:
                # trying to resume a session that is not stopped. Error.
                session.failure_reason = f'RES Session ID: {session.idea_session_id}:{session.name} for user: {session.owner} is in {session.state} state. Can\'t resume a session not in STOPPED or STOPPED_IDLE state'
                self._logger.error(session.failure_reason)
                fail_response_list.append(session)
                continue

            servers_to_start.append(session.server)
            session_server_map[session.server.instance_id] = session

        response = self._server_utils.start_dcv_hosts(servers_to_start)

        for server in servers_to_start:
            if 'ERROR' in response:
                session_server_map[server.instance_id].failure_reason = Utils.get_value_as_string('ERROR', response, 'There is an error, please check with Admin.')
                fail_response_list.append(session_server_map[server.instance_id])
            else:
                session_server_map[server.instance_id].state = VirtualDesktopSessionState.RESUMING
                session = self._session_db.update(session_server_map[server.instance_id])
                success_response_list.append(session)

        return success_response_list, fail_response_list

    def reboot_sessions(self, sessions: List[VirtualDesktopSession]) -> (List[VirtualDesktopSession], List[VirtualDesktopSession]):
        success_response_list: List[VirtualDesktopSession] = []
        fail_response_list: List[VirtualDesktopSession] = []
        servers_to_reboot: List[VirtualDesktopServer] = []
        sessions_to_reboot: List[VirtualDesktopSession] = []
        sessions_to_reboot_pending_validation: List[VirtualDesktopSession] = []

        for session_orig in sessions:
            session = self._session_db.get_from_db(idea_session_owner=session_orig.owner, idea_session_id=session_orig.idea_session_id)
            if Utils.is_empty(session):
                # Invalid IDEA Session.
                session.failure_reason = f'Invalid RES Session ID: {session.idea_session_id}:{session.name} for user: {session.owner}. Nothing to stop'
                self._logger.error(session.failure_reason)
                fail_response_list.append(session)
                continue

            if session.state not in {VirtualDesktopSessionState.READY, VirtualDesktopSessionState.ERROR}:
                session.failure_reason = f'RES Session ID: {session.idea_session_id}:{session.name} for user: {session.owner} is in {session.state} state. Can\'t reboot. Wait for it to be READY or ERROR.'
                self._logger.error(session.failure_reason)
                fail_response_list.append(session)
                continue

            session.force = session_orig.force
            if Utils.is_not_empty(session.force) and session.force:
                sessions_to_reboot.append(session)
            else:
                sessions_to_reboot_pending_validation.append(session)

        sessions_with_count = self.context.dcv_broker_client.get_active_counts_for_sessions(sessions_to_reboot_pending_validation)

        for session in sessions_with_count:
            if session.connection_count > 0:
                session.failure_reason = f'There exists {session.connection_count} active connection(s) for idea_session_id: {session.idea_session_id}:{session.name}. Please terminate.'
                self._logger.error(session.failure_reason)
                fail_response_list.append(session)
                continue

            sessions_to_reboot.append(session)

        for session in sessions_to_reboot:
            session.state = VirtualDesktopSessionState.RESUMING
            session = self._session_db.update(session)
            servers_to_reboot.append(session.server)
            success_response_list.append(session)

        self._server_utils.reboot_dcv_hosts(servers_to_reboot)
        return success_response_list, fail_response_list

    def terminate_sessions(self, sessions: List[VirtualDesktopSession]) -> (List[VirtualDesktopSession], List[VirtualDesktopSession]):
        success_response_list: List[VirtualDesktopSession] = []
        fail_response_list: List[VirtualDesktopSession] = []
        session_map: Dict[str, VirtualDesktopSession] = {}
        stopped_sessions: List[VirtualDesktopSession] = []
        sessions_to_delete: List[VirtualDesktopSession] = []

        for session_orig in sessions:
            session = self._session_db.get_from_db(idea_session_owner=session_orig.owner, idea_session_id=session_orig.idea_session_id)
            if Utils.is_empty(session):
                session.failure_reason = f'Invalid RES Session ID: {session.idea_session_id}:{session.name} for user: {session.owner}. Nothing to delete'
                self._logger.info(session.failure_reason)
                # Invalid RES Session ID.
                fail_response_list.append(session)
                continue

            self._logger.info(f'Found db entry for {session.idea_session_id}:{session.name} for user: {session.owner}. DCV Session ID: {session.dcv_session_id}')
            if Utils.is_empty(session.dcv_session_id) or session.state in {VirtualDesktopSessionState.STOPPED, VirtualDesktopSessionState.STOPPED_IDLE}:
                self._logger.info(f'dcv session id: {session.dcv_session_id} for user: {session.owner}. Current state: {session.state}. Nothing to delete')
                stopped_sessions.append(session)
                continue

            session_map[session.dcv_session_id] = session
            session.force = session_orig.force
            sessions_to_delete.append(session)

        success_list, error_list = self.context.dcv_broker_client.delete_sessions(sessions_to_delete)

        servers_to_delete = []
        session_db_entries_to_delete = []
        for session in success_list:
            session = session_map[session.dcv_session_id]
            session.state = VirtualDesktopSessionState.DELETING
            session = self._session_db.update(session)
            self.events_utils.publish_validate_dcv_session_deletion_event(
                idea_session_id=session.idea_session_id,
                idea_session_owner=session.owner
            )
            success_response_list.append(session)

        for session in stopped_sessions:
            session_db_entries_to_delete.append(session)
            servers_to_delete.append(session.server)

        self._server_utils.terminate_dcv_hosts(servers_to_delete)
        for session in session_db_entries_to_delete:
            self._schedule_utils.delete_schedules_for_session(session)
            self._session_permission_utils.delete_permissions_for_session(session)
            self._session_db.delete(session)
            session.state = VirtualDesktopSessionState.DELETED
            session.updated_on = DateTimeUtils.current_datetime()
            success_response_list.append(session)

        for session in error_list:
            session_map[session.dcv_session_id].failure_reason = session.failure_reason
            fail_response_list.append(session_map[session.dcv_session_id])

        return success_response_list, fail_response_list