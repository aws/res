#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import unittest
from unittest.mock import MagicMock

import pytest
import res as res
from res import exceptions
from res.clients.dcv_broker import dcv_broker_client
from res.clients.events import events_client
from res.resources import (
    schedules,
    servers,
    session_permissions,
    sessions,
    vdi_management,
)
from res.utils import table_utils

TEST_STRING = "test"
TEST_OWNER = "test_owner"
TEST_USER = "test_user"
TEST_INSTANCE_ID = "test_instance_id"
TEST_DCV_SESSION_ID = "test_dcv_session_id"
TEST_SESSION_ID = "test_session_id"
TEST_SCHEDULE_ID = "test_schedule_id"
TEST_SCHEDULE_DAY = schedules.SCHEDULE_DAYS[0]
TEST_SCHEDULE_TYPE = "test_schedule_type"
SESSION = {
    "idea_session_id": TEST_SESSION_ID,
    "name": TEST_STRING,
    "dcv_session_id": TEST_DCV_SESSION_ID,
}
READY_STATE = "READY"
STOPPED_STATE = "STOPPED"
STOPPING_STATE = "STOPPING"


@pytest.fixture(scope="class")
def monkeypatch_for_class(request):
    request.cls.monkeypatch = pytest.MonkeyPatch()


@pytest.mark.usefixtures("monkeypatch_for_class")
class TestVDIManagement(unittest.TestCase):

    def setUp(self):
        self.SERVER = {
            servers.SERVER_DB_HASH_KEY: TEST_INSTANCE_ID,
            servers.SERVER_DB_STATE_KEY: READY_STATE,
            servers.SERVER_DB_SESSION_ID_KEY: TEST_SESSION_ID,
        }
        self.SCHEDULES = {
            schedules.SCHEDULE_DB_HASH_KEY: TEST_SCHEDULE_DAY,
            schedules.SCHEDULE_DB_RANGE_KEY: TEST_SCHEDULE_ID,
            schedules.SCHEDULE_DB_SCHEDULE_TYPE_KEY: TEST_SCHEDULE_TYPE,
        }
        self.SESSION = {
            sessions.SESSION_DB_HASH_KEY: TEST_OWNER,
            sessions.SESSION_DB_RANGE_KEY: TEST_SESSION_ID,
            sessions.SESSION_DB_STATE_KEY: READY_STATE,
            sessions.SESSION_DB_DCV_SESSION_ID_KEY: TEST_DCV_SESSION_ID,
            "name": TEST_STRING,
            "server": self.SERVER,
            "force": True,
            f"{TEST_SCHEDULE_DAY}{sessions.SESSION_DB_SCHEDULE_SUFFIX}": self.SCHEDULES,
        }
        self.SESSION_PERMISSION = {
            session_permissions.SESSION_PERMISSION_DB_HASH_KEY: TEST_SESSION_ID,
            session_permissions.SESSION_PERMISSION_DB_RANGE_KEY: TEST_USER,
        }
        table_utils.create_item(servers.SERVER_TABLE_NAME, item=self.SERVER)
        table_utils.create_item(sessions.SESSIONS_TABLE_NAME, item=self.SESSION)
        table_utils.create_item(schedules.SCHEDULE_DB_TABLE_NAME, item=self.SCHEDULES)
        table_utils.create_item(
            session_permissions.SESSION_PERMISSION_TABLE_NAME,
            item=self.SESSION_PERMISSION,
        )

    def test_stop_or_hibernate_servers_pass(self):
        mocked_stop_hosts = MagicMock()
        self.monkeypatch.setattr(vdi_management, "_stop_hosts", mocked_stop_hosts)

        mocked_stop_hosts.return_value = {
            "StoppingInstances": [{"InstanceId": TEST_INSTANCE_ID}]
        }

        servers_to_stop = [{"instance_id": TEST_INSTANCE_ID}]

        current_session = sessions.get_session(
            owner=TEST_OWNER, session_id=TEST_SESSION_ID
        )
        assert current_session.get(sessions.SESSION_DB_STATE_KEY) == READY_STATE

        current_server = servers.get_server(instance_id=TEST_INSTANCE_ID)
        assert current_server.get(servers.SERVER_DB_STATE_KEY) == READY_STATE

        vdi_management._stop_or_hibernate_servers(servers=servers_to_stop)

        current_server = servers.get_server(instance_id=TEST_INSTANCE_ID)
        assert current_server.get(servers.SERVER_DB_STATE_KEY) == STOPPED_STATE

        current_session = sessions.get_session(
            owner=TEST_OWNER, session_id=TEST_SESSION_ID
        )
        assert current_session.get(sessions.SESSION_DB_STATE_KEY) == READY_STATE

    def test_stop_vdi_sessions_with_dcv_session_pass(self):
        self.monkeypatch.setattr(
            dcv_broker_client, "delete_sessions", self.delete_dcv_session_response()
        )

        self.monkeypatch.setattr(
            events_client, "publish_validate_dcv_session_deletion_event", MagicMock()
        )

        current_session = sessions.get_session(
            owner=TEST_OWNER, session_id=TEST_SESSION_ID
        )

        assert current_session.get(sessions.SESSION_DB_STATE_KEY) == READY_STATE

        current_server = servers.get_server(instance_id=TEST_INSTANCE_ID)
        assert current_server.get(servers.SERVER_DB_STATE_KEY) == READY_STATE

        success, _ = vdi_management.stop_sessions([self.SESSION])

        current_server = servers.get_server(instance_id=TEST_INSTANCE_ID)
        assert current_server.get(servers.SERVER_DB_STATE_KEY) == READY_STATE

        current_session = sessions.get_session(
            owner=TEST_OWNER, session_id=TEST_SESSION_ID
        )
        assert current_session.get(sessions.SESSION_DB_STATE_KEY) == STOPPING_STATE

        assert len(success) == 1
        assert success[0] == current_session

    def test_stop_vdi_sessions_with_no_dcv_session_pass(self):
        self.monkeypatch.setattr(
            dcv_broker_client, "delete_sessions", self.delete_dcv_session_response()
        )

        current_session = sessions.get_session(
            owner=TEST_OWNER, session_id=TEST_SESSION_ID
        )
        current_session[sessions.SESSION_DB_DCV_SESSION_ID_KEY] = ""
        sessions.update_session(current_session)

        assert current_session.get(sessions.SESSION_DB_STATE_KEY) == READY_STATE

        current_server = servers.get_server(instance_id=TEST_INSTANCE_ID)
        assert current_server.get(servers.SERVER_DB_STATE_KEY) == READY_STATE

        success, _ = vdi_management.stop_sessions([self.SESSION])

        current_server = servers.get_server(instance_id=TEST_INSTANCE_ID)
        assert current_server.get(servers.SERVER_DB_STATE_KEY) == STOPPED_STATE

        current_session = sessions.get_session(
            owner=TEST_OWNER, session_id=TEST_SESSION_ID
        )
        assert current_session.get(sessions.SESSION_DB_STATE_KEY) == STOPPING_STATE

        assert len(success) == 1
        assert success[0] == current_session

    def test_stop_sessions_not_in_ready_fail(self):
        self.monkeypatch.setattr(
            dcv_broker_client, "delete_sessions", self.delete_dcv_session_response()
        )

        current_session = self.SESSION
        current_session[sessions.SESSION_DB_STATE_KEY] = STOPPED_STATE
        sessions.update_session(current_session)

        _, fail = vdi_management.stop_sessions([current_session])

        assert len(fail) == 1
        assert fail[0].get(sessions.SESSION_DB_HASH_KEY) == TEST_OWNER
        # Check if current_Session is a subset of fail[0] since fail[0] has an extra failure_reason field
        assert fail[0].items() > current_session.items()
        assert fail[0].get("failure_reason")

    def delete_dcv_session_response(self):
        def delete_session_response(curr_sessions):
            if curr_sessions and curr_sessions[0].get(
                sessions.SESSION_DB_DCV_SESSION_ID_KEY
            ):
                return [{"dcv_session_id": TEST_DCV_SESSION_ID}], []
            else:
                return [], []

        return delete_session_response

    def test_delete_schedule_for_session_pass(self):
        item = table_utils.get_item(
            schedules.SCHEDULE_DB_TABLE_NAME,
            key={
                schedules.SCHEDULE_DB_HASH_KEY: TEST_SCHEDULE_DAY,
                schedules.SCHEDULE_DB_RANGE_KEY: TEST_SCHEDULE_ID,
            },
        )
        assert item is not None
        assert item == self.SCHEDULES

        vdi_management.delete_schedule_for_session(session=self.SESSION)

        item = table_utils.get_item(
            schedules.SCHEDULE_DB_TABLE_NAME,
            key={
                schedules.SCHEDULE_DB_HASH_KEY: TEST_SCHEDULE_DAY,
                schedules.SCHEDULE_DB_RANGE_KEY: TEST_SCHEDULE_ID,
            },
        )
        assert item is None

    def test_terminate_sessions_with_no_dcv_session_pass(self):
        self.monkeypatch.setattr(
            dcv_broker_client, "delete_sessions", self.delete_dcv_session_response()
        )
        self.monkeypatch.setattr(
            vdi_management,
            "_terminate_hosts",
            lambda server: {"TerminatingInstances": [{"InstanceId": TEST_INSTANCE_ID}]},
        )

        current_session = self.SESSION
        current_session[sessions.SESSION_DB_DCV_SESSION_ID_KEY] = ""
        sessions.update_session(current_session)
        assert servers.get_server(instance_id=TEST_INSTANCE_ID) is not None
        assert (
            session_permissions.get_session_permission(
                session_id=TEST_SESSION_ID, user=TEST_USER
            )
            is not None
        )

        success, _ = vdi_management.terminate_sessions([self.SESSION])

        with pytest.raises(exceptions.ServerNotFound) as exc_info:
            servers.get_server(instance_id=TEST_INSTANCE_ID)
        assert f"Server not found: {TEST_INSTANCE_ID}" == exc_info.value.args[0]

        with pytest.raises(exceptions.UserSessionNotFound) as exc_info:
            sessions.get_session(owner=TEST_OWNER, session_id=TEST_SESSION_ID)
        assert f"Session not found: {TEST_SESSION_ID}" == exc_info.value.args[0]

        with pytest.raises(exceptions.SessionPermissionsNotFound) as exc_info:
            session_permissions.get_session_permission(
                session_id=TEST_SESSION_ID, user=TEST_USER
            )
        assert (
            f"Session permission not found for {session_permissions.SESSION_PERMISSION_DB_HASH_KEY}: {TEST_SESSION_ID} for {session_permissions.SESSION_PERMISSION_DB_RANGE_KEY} : {TEST_USER}"
            == exc_info.value.args[0]
        )

        assert len(success) == 1
