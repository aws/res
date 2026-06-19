#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import unittest
from unittest.mock import MagicMock

import pytest
import res as res
from res import exceptions
from res.clients.dcv_session_manager import dcv_session_manager_client
from res.clients.events import events_client
from res.resources import (
    cluster_settings,
    schedules,
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
TEST_SCHEDULE_DAY = schedules.DayOfWeek.MONDAY.value
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
            "server": {"instance_id": TEST_INSTANCE_ID, "state": READY_STATE},
            "force": True,
            f"{TEST_SCHEDULE_DAY}{sessions.SESSION_DB_SCHEDULE_SUFFIX}": self.SCHEDULES,
        }
        self.SESSION_PERMISSION = {
            session_permissions.SESSION_PERMISSION_DB_HASH_KEY: TEST_SESSION_ID,
            session_permissions.SESSION_PERMISSION_DB_RANGE_KEY: TEST_USER,
        }
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

        vdi_management._stop_or_hibernate_servers(servers=servers_to_stop)

        mocked_stop_hosts.assert_called_once()

    def test_stop_vdi_sessions_with_dcv_session_pass(self):
        mocked_stop_hosts = MagicMock()
        self.monkeypatch.setattr(vdi_management, "_stop_hosts", mocked_stop_hosts)

        mocked_stop_hosts.return_value = {
            "StoppingInstances": [{"InstanceId": TEST_INSTANCE_ID}]
        }

        current_session = sessions.get_session(
            owner=TEST_OWNER, session_id=TEST_SESSION_ID
        )

        assert current_session.get(sessions.SESSION_DB_STATE_KEY) == READY_STATE

        success, _ = vdi_management.stop_sessions([self.SESSION])

        current_session = sessions.get_session(
            owner=TEST_OWNER, session_id=TEST_SESSION_ID
        )
        assert current_session.get(sessions.SESSION_DB_STATE_KEY) == STOPPING_STATE

        assert len(success) == 1
        assert success[0] == current_session

    def test_stop_vdi_sessions_with_no_dcv_session_pass(self):
        mocked_stop_hosts = MagicMock()
        self.monkeypatch.setattr(vdi_management, "_stop_hosts", mocked_stop_hosts)

        mocked_stop_hosts.return_value = {
            "StoppingInstances": [{"InstanceId": TEST_INSTANCE_ID}]
        }

        current_session = sessions.get_session(
            owner=TEST_OWNER, session_id=TEST_SESSION_ID
        )
        current_session[sessions.SESSION_DB_DCV_SESSION_ID_KEY] = ""
        sessions.update_session(current_session)

        assert current_session.get(sessions.SESSION_DB_STATE_KEY) == READY_STATE

        success, _ = vdi_management.stop_sessions([self.SESSION])

        current_session = sessions.get_session(
            owner=TEST_OWNER, session_id=TEST_SESSION_ID
        )
        assert current_session.get(sessions.SESSION_DB_STATE_KEY) == STOPPING_STATE

        assert len(success) == 1
        assert success[0] == current_session

    def test_stop_sessions_not_in_ready_fail(self):
        current_session = self.SESSION
        current_session[sessions.SESSION_DB_STATE_KEY] = STOPPED_STATE
        sessions.update_session(current_session)

        _, fail = vdi_management.stop_sessions([current_session])

        assert len(fail) == 1
        assert fail[0].get(sessions.SESSION_DB_HASH_KEY) == TEST_OWNER
        # Check if current_Session is a subset of fail[0] since fail[0] has an extra failure_reason field
        assert fail[0].items() > current_session.items()
        assert fail[0].get("failure_reason")

    def test_validate_sessions_to_delete_blocks_on_active_connections(self):
        """When force=False and the session has active connections, mark as conflict."""
        session = {**self.SESSION, "force": False}

        self.monkeypatch.setattr(
            dcv_session_manager_client,
            "describe_sessions",
            lambda req: {
                "successful_list": [
                    {"session_id": TEST_SESSION_ID, "num_of_connections": 2}
                ],
                "unsuccessful_list": [],
            },
        )

        sessions_to_validate = [session]
        vdi_management.validate_sessions_to_delete(sessions_to_validate)

        assert sessions_to_validate[0].get("failure_reason") is not None
        assert "active connection" in sessions_to_validate[0]["failure_reason"]
        assert (
            sessions_to_validate[0].get("failure_code")
            == exceptions.FAILURE_CODE_CONFLICT
        )

    def test_validate_sessions_to_delete_zero_connections_passes(self):
        """When force=False and the session has zero active connections, no failure set."""
        session = {**self.SESSION, "force": False}

        self.monkeypatch.setattr(
            dcv_session_manager_client,
            "describe_sessions",
            lambda req: {
                "successful_list": [
                    {"session_id": TEST_SESSION_ID, "num_of_connections": 0}
                ],
                "unsuccessful_list": [],
            },
        )

        sessions_to_validate = [session]
        vdi_management.validate_sessions_to_delete(sessions_to_validate)

        assert sessions_to_validate[0].get("failure_reason") is None

    def test_validate_sessions_to_delete_treats_unsuccessful_as_zero(self):
        """Failed describe is treated as 0 connections (matches legacy broker behavior)."""
        session = {**self.SESSION, "force": False}

        self.monkeypatch.setattr(
            dcv_session_manager_client,
            "describe_sessions",
            lambda req: {
                "successful_list": [],
                "unsuccessful_list": [
                    {
                        "session_id": TEST_SESSION_ID,
                        "failure_reason": "host unreachable",
                    }
                ],
            },
        )

        sessions_to_validate = [session]
        vdi_management.validate_sessions_to_delete(sessions_to_validate)

        assert sessions_to_validate[0].get("failure_reason") is None

    def test_get_active_counts_for_sessions_empty_input(self):
        """Empty input returns empty list and skips the network call."""
        called = []
        self.monkeypatch.setattr(
            dcv_session_manager_client,
            "describe_sessions",
            lambda req: called.append(req) or {},
        )

        result = vdi_management.get_active_counts_for_sessions([])

        assert result == []
        assert called == []

    def test_get_active_counts_for_sessions_populates_counts(self):
        """Successful entries populate connection_count on the matching session."""
        session1 = {
            sessions.SESSION_DB_HASH_KEY: TEST_OWNER,
            sessions.SESSION_DB_RANGE_KEY: TEST_SESSION_ID,
            "owner": TEST_OWNER,
        }
        session2 = {
            sessions.SESSION_DB_HASH_KEY: "owner-2",
            sessions.SESSION_DB_RANGE_KEY: "session-2",
            "owner": "owner-2",
        }

        captured = {}

        def fake_describe(req):
            captured["req"] = req
            return {
                "successful_list": [
                    {"session_id": TEST_SESSION_ID, "num_of_connections": 3},
                    {"session_id": "session-2", "num_of_connections": 0},
                ],
                "unsuccessful_list": [],
            }

        self.monkeypatch.setattr(
            dcv_session_manager_client, "describe_sessions", fake_describe
        )

        result = vdi_management.get_active_counts_for_sessions([session1, session2])

        assert result is not None and len(result) == 2
        assert result[0]["connection_count"] == 3
        assert result[1]["connection_count"] == 0
        # Helper sends (session_id, owner) per session.
        assert captured["req"] == [
            {"session_id": TEST_SESSION_ID, "owner": TEST_OWNER},
            {"session_id": "session-2", "owner": "owner-2"},
        ]

    def test_get_active_counts_for_sessions_unsuccessful_defaults_to_zero(self):
        """Sessions in unsuccessful_list keep connection_count=0 (no failure_reason set)."""
        session = {
            sessions.SESSION_DB_HASH_KEY: TEST_OWNER,
            sessions.SESSION_DB_RANGE_KEY: TEST_SESSION_ID,
            "owner": TEST_OWNER,
        }

        self.monkeypatch.setattr(
            dcv_session_manager_client,
            "describe_sessions",
            lambda req: {
                "successful_list": [],
                "unsuccessful_list": [
                    {"session_id": TEST_SESSION_ID, "failure_reason": "unreachable"}
                ],
            },
        )

        result = vdi_management.get_active_counts_for_sessions([session])

        assert result[0]["connection_count"] == 0
        # Helper does not propagate the failure onto the session — caller decides.
        assert "failure_reason" not in result[0]

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

    def test_terminate_sessions_with_dcv_session_pass(self):
        self.monkeypatch.setattr(
            vdi_management,
            "_terminate_hosts",
            lambda server: {"TerminatingInstances": [{"InstanceId": TEST_INSTANCE_ID}]},
        )
        self.monkeypatch.setattr(
            cluster_settings, "get_setting", lambda setting: "test_url"
        )

        current_session = self.SESSION
        assert (
            current_session.get(sessions.SESSION_DB_DCV_SESSION_ID_KEY)
            == TEST_DCV_SESSION_ID
        )
        assert current_session.get(sessions.SESSION_DB_STATE_KEY) == READY_STATE

        success, _ = vdi_management.terminate_sessions([self.SESSION])

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

    def test_terminate_sessions_with_no_dcv_session_pass(self):
        self.monkeypatch.setattr(
            vdi_management,
            "_terminate_hosts",
            lambda server: {"TerminatingInstances": [{"InstanceId": TEST_INSTANCE_ID}]},
        )
        self.monkeypatch.setattr(
            cluster_settings, "get_setting", lambda setting: "test_url"
        )
        current_session = self.SESSION
        current_session[sessions.SESSION_DB_DCV_SESSION_ID_KEY] = ""
        sessions.update_session(current_session)
        assert (
            session_permissions.get_session_permission(
                session_id=TEST_SESSION_ID, user=TEST_USER
            )
            is not None
        )

        success, _ = vdi_management.terminate_sessions([self.SESSION])

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

    def test_start_sessions_updates_state_and_starts_hosts(self):
        mocked_start_hosts = MagicMock()
        self.monkeypatch.setattr(vdi_management, "_start_hosts", mocked_start_hosts)
        mocked_start_hosts.return_value = {
            "StartingInstances": [
                {"InstanceId": TEST_INSTANCE_ID, "CurrentState": {"Name": "pending"}}
            ]
        }

        current_session = self.SESSION.copy()
        current_session[sessions.SESSION_DB_STATE_KEY] = "STOPPED"
        sessions.update_session(current_session)

        success, fail = vdi_management.start_sessions([current_session])

        assert len(success) == 1
        assert len(fail) == 0

        updated_session = sessions.get_session(
            owner=TEST_OWNER, session_id=TEST_SESSION_ID
        )
        assert updated_session.get(sessions.SESSION_DB_STATE_KEY) == "RESUMING"
        mocked_start_hosts.assert_called_once()

    def test_start_sessions_multiple_sessions(self):
        mocked_start_hosts = MagicMock()
        self.monkeypatch.setattr(vdi_management, "_start_hosts", mocked_start_hosts)
        mocked_start_hosts.return_value = {
            "StartingInstances": [
                {"InstanceId": TEST_INSTANCE_ID, "CurrentState": {"Name": "pending"}},
                {"InstanceId": "i-second", "CurrentState": {"Name": "pending"}},
            ]
        }

        session1 = self.SESSION.copy()
        session1[sessions.SESSION_DB_STATE_KEY] = "STOPPED"
        sessions.update_session(session1)

        session2 = self.SESSION.copy()
        session2[sessions.SESSION_DB_HASH_KEY] = "other_owner"
        session2[sessions.SESSION_DB_RANGE_KEY] = "other-session-id"
        session2[sessions.SESSION_DB_STATE_KEY] = "STOPPED"
        session2["name"] = "Session 2"
        session2["server"] = {"instance_id": "i-second"}
        table_utils.create_item(sessions.SESSIONS_TABLE_NAME, item=session2)

        success, fail = vdi_management.start_sessions([session1, session2])

        assert len(success) == 2
        assert len(fail) == 0
        mocked_start_hosts.assert_called_once()
        current_session = sessions.get_session(
            owner=TEST_OWNER, session_id=TEST_SESSION_ID
        )
        assert current_session.get(sessions.SESSION_DB_STATE_KEY) == "RESUMING"

    def test_reboot_sessions_success(self):
        mocked_ec2 = MagicMock()
        self.monkeypatch.setattr(
            vdi_management,
            "AwsClientProvider",
            MagicMock(return_value=MagicMock(ec2=MagicMock(return_value=mocked_ec2))),
        )

        current_session = sessions.get_session(
            owner=TEST_OWNER, session_id=TEST_SESSION_ID
        )
        assert current_session.get(sessions.SESSION_DB_STATE_KEY) == READY_STATE

        success, fail = vdi_management.reboot_sessions([self.SESSION])

        assert len(success) == 1
        assert len(fail) == 0

        updated_session = sessions.get_session(
            owner=TEST_OWNER, session_id=TEST_SESSION_ID
        )
        assert updated_session.get(sessions.SESSION_DB_STATE_KEY) == "RESUMING"
        mocked_ec2.reboot_instances.assert_called_once()

    def test_reboot_sessions_ec2_failure_raises(self):
        mocked_ec2 = MagicMock()
        mocked_ec2.reboot_instances.side_effect = Exception("EC2 throttled")
        self.monkeypatch.setattr(
            vdi_management,
            "AwsClientProvider",
            MagicMock(return_value=MagicMock(ec2=MagicMock(return_value=mocked_ec2))),
        )

        with pytest.raises(Exception, match="EC2 throttled"):
            vdi_management.reboot_sessions([self.SESSION])
