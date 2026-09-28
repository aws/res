#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import random
import unittest
from unittest.mock import MagicMock

import botocore.exceptions
import pytest
import res as res
from res import constants, exceptions
from res.clients.dcv_session_manager import dcv_session_manager_client
from res.resources import (
    cluster_settings,
    schedules,
    session_permissions,
    sessions,
    software_stacks,
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

    def test_terminate_hosts_with_no_servers_returns_empty_response(self):
        mocked_aws_provider = MagicMock()
        mocked_ec2 = MagicMock()
        mocked_aws_provider.return_value.ec2.return_value = mocked_ec2
        self.monkeypatch.setattr(
            vdi_management, "AwsClientProvider", mocked_aws_provider
        )

        response = vdi_management._terminate_hosts([])

        assert response == []
        mocked_ec2.delete_fleets.assert_not_called()
        mocked_ec2.terminate_instances.assert_not_called()

    def test_terminate_hosts_deletes_fleets(self):
        mocked_aws_provider = MagicMock()
        mocked_ec2 = MagicMock()
        mocked_ec2.delete_fleets.return_value = {
            "SuccessfulFleetDeletions": [{"FleetId": "fleet-1"}]
        }
        mocked_aws_provider.return_value.ec2.return_value = mocked_ec2
        self.monkeypatch.setattr(
            vdi_management, "AwsClientProvider", mocked_aws_provider
        )

        servers = [{"instance_id": TEST_INSTANCE_ID, "fleet_id": "fleet-1"}]
        response = vdi_management._terminate_hosts(servers)

        mocked_ec2.delete_fleets.assert_called_once_with(
            FleetIds=["fleet-1"], TerminateInstances=True
        )
        assert response == [{"SuccessfulFleetDeletions": [{"FleetId": "fleet-1"}]}]

    def test_terminate_hosts_batches_fleet_ids_over_delete_fleets_cap(self):
        mocked_aws_provider = MagicMock()
        mocked_ec2 = MagicMock()
        mocked_ec2.delete_fleets.return_value = {"SuccessfulFleetDeletions": []}
        mocked_aws_provider.return_value.ec2.return_value = mocked_ec2
        self.monkeypatch.setattr(
            vdi_management, "AwsClientProvider", mocked_aws_provider
        )

        # 60 fleets → three batches of 25, 25, 10.
        servers = [
            {"instance_id": f"i-{i}", "fleet_id": f"fleet-{i}"} for i in range(60)
        ]
        vdi_management._terminate_hosts(servers)

        call_batch_sizes = [
            len(call.kwargs["FleetIds"])
            for call in mocked_ec2.delete_fleets.call_args_list
        ]
        assert call_batch_sizes == [25, 25, 10]

    def test_terminate_hosts_logs_unsuccessful_fleet_deletions(self):
        mocked_aws_provider = MagicMock()
        mocked_ec2 = MagicMock()
        mocked_ec2.delete_fleets.return_value = {
            "SuccessfulFleetDeletions": [],
            "UnsuccessfulFleetDeletions": [
                {"FleetId": "fleet-1", "Error": {"Code": "fleetIdDoesNotExist"}}
            ],
        }
        mocked_aws_provider.return_value.ec2.return_value = mocked_ec2
        self.monkeypatch.setattr(
            vdi_management, "AwsClientProvider", mocked_aws_provider
        )
        mocked_logger = MagicMock()
        self.monkeypatch.setattr(vdi_management, "logger", mocked_logger)

        servers = [{"instance_id": TEST_INSTANCE_ID, "fleet_id": "fleet-1"}]
        vdi_management._terminate_hosts(servers)

        assert any(
            "Failed to delete fleets" in call.args[0]
            for call in mocked_logger.warning.call_args_list
        )

    def test_terminate_hosts_terminates_instances_without_fleet_id(self):
        mocked_aws_provider = MagicMock()
        mocked_ec2 = MagicMock()
        mocked_ec2.terminate_instances.return_value = {
            "TerminatingInstances": [{"InstanceId": TEST_INSTANCE_ID}]
        }
        mocked_aws_provider.return_value.ec2.return_value = mocked_ec2
        self.monkeypatch.setattr(
            vdi_management, "AwsClientProvider", mocked_aws_provider
        )

        servers = [{"instance_id": TEST_INSTANCE_ID}]
        response = vdi_management._terminate_hosts(servers)

        mocked_ec2.delete_fleets.assert_not_called()
        mocked_ec2.terminate_instances.assert_called_once_with(
            InstanceIds=[TEST_INSTANCE_ID]
        )
        assert response == [
            {"TerminatingInstances": [{"InstanceId": TEST_INSTANCE_ID}]}
        ]

    def test_terminate_hosts_handles_mixed_fleet_and_no_fleet_servers(self):
        mocked_aws_provider = MagicMock()
        mocked_ec2 = MagicMock()
        mocked_ec2.delete_fleets.return_value = {
            "SuccessfulFleetDeletions": [{"FleetId": "fleet-1"}]
        }
        mocked_ec2.terminate_instances.return_value = {
            "TerminatingInstances": [{"InstanceId": "i-no-fleet"}]
        }
        mocked_aws_provider.return_value.ec2.return_value = mocked_ec2
        self.monkeypatch.setattr(
            vdi_management, "AwsClientProvider", mocked_aws_provider
        )

        servers = [
            {"instance_id": "i-new", "fleet_id": "fleet-1"},
            {"instance_id": "i-no-fleet"},
        ]
        vdi_management._terminate_hosts(servers)

        mocked_ec2.delete_fleets.assert_called_once_with(
            FleetIds=["fleet-1"], TerminateInstances=True
        )
        mocked_ec2.terminate_instances.assert_called_once_with(
            InstanceIds=["i-no-fleet"]
        )

    def test_terminate_hosts_skips_servers_without_fleet_id_or_instance_id(self):
        mocked_aws_provider = MagicMock()
        mocked_ec2 = MagicMock()
        mocked_aws_provider.return_value.ec2.return_value = mocked_ec2
        self.monkeypatch.setattr(
            vdi_management, "AwsClientProvider", mocked_aws_provider
        )

        response = vdi_management._terminate_hosts([{}])

        assert response == []
        mocked_ec2.delete_fleets.assert_not_called()
        mocked_ec2.terminate_instances.assert_not_called()

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


class TestValidateAttemptSubnets:
    """Tests for validate_attempt_subnets."""

    @pytest.fixture(autouse=True)
    def setup(self, monkeypatch, context):
        self._settings = {}
        monkeypatch.setattr(
            cluster_settings, "get_setting", lambda key: self._settings.get(key)
        )

    def test_uses_session_subnet_id_when_provided(self):
        self._settings = {
            "vdc.dcv_session.network.private_subnets": ["subnet-abc"],
            "cluster.network.private_subnets": [],
        }
        session = {"server": {"subnet_id": "subnet-abc"}}
        result, is_valid = vdi_management.validate_attempt_subnets(session)
        assert is_valid
        assert result["attempt_subnets"] == ["subnet-abc"]

    def test_uses_configured_vdi_subnets(self):
        self._settings = {
            "vdc.dcv_session.network.private_subnets": ["subnet-1", "subnet-2"]
        }
        session = {"server": {}}
        result, is_valid = vdi_management.validate_attempt_subnets(session)
        assert is_valid
        assert result["attempt_subnets"] == ["subnet-1", "subnet-2"]

    def test_falls_back_to_cluster_subnets(self):
        self._settings = {
            "vdc.dcv_session.network.private_subnets": None,
            "cluster.network.private_subnets": ["subnet-cluster"],
        }
        session = {"server": {}}
        result, is_valid = vdi_management.validate_attempt_subnets(session)
        assert is_valid
        assert result["attempt_subnets"] == ["subnet-cluster"]

    def test_returns_false_when_no_subnets(self):
        self._settings = {
            "vdc.dcv_session.network.private_subnets": None,
            "cluster.network.private_subnets": None,
        }
        session = {"server": {}}
        result, is_valid = vdi_management.validate_attempt_subnets(session)
        assert not is_valid
        assert result["failure_reason"] == "No subnets available for deployment"

    def test_valid_subnet_in_vdi_subnets_accepted(self):
        """Test that a user-provided subnet_id in configured VDI subnets is accepted."""
        self._settings = {
            "vdc.dcv_session.network.private_subnets": ["subnet-aaa", "subnet-bbb"],
            "cluster.network.private_subnets": ["subnet-ccc"],
        }
        session = {"server": {"subnet_id": "subnet-aaa"}}
        result, is_valid = vdi_management.validate_attempt_subnets(session)
        assert is_valid
        assert result["attempt_subnets"] == ["subnet-aaa"]

    def test_valid_subnet_in_cluster_subnets_accepted(self):
        """Test that a user-provided subnet_id in cluster private subnets is accepted."""
        self._settings = {
            "vdc.dcv_session.network.private_subnets": ["subnet-aaa"],
            "cluster.network.private_subnets": ["subnet-ccc", "subnet-ddd"],
        }
        session = {"server": {"subnet_id": "subnet-ccc"}}
        result, is_valid = vdi_management.validate_attempt_subnets(session)
        assert is_valid
        assert result["attempt_subnets"] == ["subnet-ccc"]

    def test_invalid_subnet_rejected(self):
        """Test that a user-provided subnet_id NOT in allowed subnets is rejected."""
        self._settings = {
            "vdc.dcv_session.network.private_subnets": ["subnet-aaa", "subnet-bbb"],
            "cluster.network.private_subnets": ["subnet-ccc"],
        }
        session = {"server": {"subnet_id": "subnet-unauthorized"}}
        result, is_valid = vdi_management.validate_attempt_subnets(session)
        assert not is_valid
        assert "subnet-unauthorized" in result["failure_reason"]
        assert "not authorized for this environment" in result["failure_reason"]

    def test_invalid_subnet_rejected_when_no_subnets_configured(self):
        """Test that a user-provided subnet_id is rejected when no subnets are configured."""
        self._settings = {
            "vdc.dcv_session.network.private_subnets": None,
            "cluster.network.private_subnets": None,
        }
        session = {"server": {"subnet_id": "subnet-xyz"}}
        result, is_valid = vdi_management.validate_attempt_subnets(session)
        assert not is_valid
        assert "subnet-xyz" in result["failure_reason"]
        assert "not authorized for this environment" in result["failure_reason"]


class TestCreateVirtualDesktop:
    """Tests for create_virtual_desktop."""

    @pytest.fixture(autouse=True)
    def setup(self, monkeypatch, context):
        monkeypatch.setattr(
            vdi_management.ec2_utils, "get_gpu_manufacturer", lambda x: "NO_GPU"
        )
        monkeypatch.setattr(cluster_settings, "get_setting", lambda k: "test-value")

    def test_success_sets_state_provisioning(self, monkeypatch):
        monkeypatch.setattr(
            vdi_management.schedules, "get_default_schedules", lambda: None
        )
        monkeypatch.setattr(
            vdi_management,
            "_build_user_data_and_provision",
            lambda s: {
                "Instances": [{"InstanceId": "i-abc123"}],
                "FleetId": "fleet-abc",
            },
        )
        monkeypatch.setattr(vdi_management.user_sessions, "create_session", lambda s: s)

        session = {"idea_session_id": "s1", "owner": "user1", "server": {}}
        result = vdi_management.create_virtual_desktop(session)

        assert result["state"] == "PROVISIONING"
        assert result["server"]["instance_id"] == "i-abc123"
        assert result["server"]["fleet_id"] == "fleet-abc"

    def test_stores_ami_id_on_server(self, monkeypatch):
        monkeypatch.setattr(
            vdi_management.schedules, "get_default_schedules", lambda: None
        )
        monkeypatch.setattr(
            vdi_management,
            "_build_user_data_and_provision",
            lambda s: {
                "Instances": [{"InstanceId": "i-abc123"}],
                "FleetId": "fleet-abc",
                "ami_id": "ami-12345678",
            },
        )
        monkeypatch.setattr(vdi_management.user_sessions, "create_session", lambda s: s)

        session = {"idea_session_id": "s1", "owner": "user1", "server": {}}
        result = vdi_management.create_virtual_desktop(session)

        assert result["server"]["ami_id"] == "ami-12345678"

    def test_attaches_default_schedule(self, monkeypatch):
        schedule = {"monday": {"start": "09:00", "end": "17:00"}}
        monkeypatch.setattr(
            vdi_management.schedules, "get_default_schedules", lambda: schedule
        )
        monkeypatch.setattr(
            vdi_management,
            "_build_user_data_and_provision",
            lambda s: {"Instances": [{"InstanceId": "i-123"}]},
        )
        monkeypatch.setattr(vdi_management.user_sessions, "create_session", lambda s: s)

        session = {"idea_session_id": "s1", "owner": "user1", "server": {}}
        result = vdi_management.create_virtual_desktop(session)

        assert result["monday_schedule"]["idea_session_id"] == "s1"
        assert result["monday_schedule"]["idea_session_owner"] == "user1"

    def test_provisioning_failure_sets_failure_reason(self, monkeypatch):
        monkeypatch.setattr(
            vdi_management.schedules, "get_default_schedules", lambda: None
        )
        monkeypatch.setattr(
            vdi_management,
            "_build_user_data_and_provision",
            MagicMock(side_effect=Exception("EC2 capacity error")),
        )

        session = {"idea_session_id": "s1", "owner": "user1", "server": {}}
        result = vdi_management.create_virtual_desktop(session)

        assert result["failure_reason"] == "Internal error: EC2 capacity error"
        assert result["failure_code"] == exceptions.FAILURE_CODE_INTERNAL_SERVICE
        assert "state" not in result

    def test_client_error_sets_client_failure_type(self, monkeypatch):
        monkeypatch.setattr(
            vdi_management.schedules, "get_default_schedules", lambda: None
        )
        monkeypatch.setattr(
            vdi_management,
            "_build_user_data_and_provision",
            MagicMock(
                side_effect=vdi_management.exceptions.InvalidParams(
                    "EC2 launch failed due to invalid parameters: InvalidParameterValue"
                )
            ),
        )

        session = {"idea_session_id": "s1", "owner": "user1", "server": {}}
        result = vdi_management.create_virtual_desktop(session)

        assert "invalid parameters" in result["failure_reason"].lower()
        assert result["failure_code"] == exceptions.FAILURE_CODE_BAD_REQUEST
        assert "state" not in result

    def test_botocore_client_error_sets_server_failure_type(self, monkeypatch):

        monkeypatch.setattr(
            vdi_management.schedules, "get_default_schedules", lambda: None
        )
        error_response = {
            "Error": {"Code": "InsufficientInstanceCapacity", "Message": "No capacity"}
        }
        monkeypatch.setattr(
            vdi_management,
            "_build_user_data_and_provision",
            MagicMock(
                side_effect=botocore.exceptions.ClientError(
                    error_response, "RunInstances"
                )
            ),
        )

        session = {"idea_session_id": "s1", "owner": "user1", "server": {}}
        result = vdi_management.create_virtual_desktop(session)

        assert "InsufficientInstanceCapacity" in result["failure_reason"]
        assert result["failure_code"] == exceptions.FAILURE_CODE_INTERNAL_SERVICE
        assert "state" not in result

    def test_custom_schedule_preserved_when_provided(self, monkeypatch):
        """When session already has a schedule, default is not applied."""
        monkeypatch.setattr(
            vdi_management,
            "_build_user_data_and_provision",
            lambda s: {"Instances": [{"InstanceId": "i-123"}]},
        )
        monkeypatch.setattr(vdi_management.user_sessions, "create_session", lambda s: s)

        custom_schedule = {
            "monday": {"start_up_time": "06:00", "shut_down_time": "22:00"}
        }
        session = {
            "idea_session_id": "s2",
            "owner": "user2",
            "server": {},
            "schedule": custom_schedule,
        }
        result = vdi_management.create_virtual_desktop(session)

        assert result["monday_schedule"]["start_up_time"] == "06:00"
        assert result["monday_schedule"]["shut_down_time"] == "22:00"
        assert result["monday_schedule"]["idea_session_id"] == "s2"

    def test_create_session_persists_schedule_records(self, monkeypatch):
        """On normal flow, schedule records are created from default schedules."""
        default_schedule = {
            "monday": {"schedule_type": "WORKING_HOURS"},
            "tuesday": {"schedule_type": "NO_SCHEDULE"},
            "wednesday": {
                "schedule_type": "CUSTOM_SCHEDULE",
                "start_up_time": "06:00",
                "shut_down_time": "22:00",
            },
        }
        monkeypatch.setattr(
            vdi_management.schedules, "get_default_schedules", lambda: default_schedule
        )
        monkeypatch.setattr(
            vdi_management,
            "_build_user_data_and_provision",
            lambda s: {"Instances": [{"InstanceId": "i-123"}]},
        )
        monkeypatch.setattr(vdi_management.user_sessions, "create_session", lambda s: s)
        mock_create = MagicMock(
            side_effect=lambda **kwargs: {
                "schedule_type": kwargs["schedule"].get("schedule_type"),
                "start_up_time": kwargs["schedule"].get("start_up_time", "09:00"),
                "shut_down_time": kwargs["schedule"].get("shut_down_time", "17:00"),
                "idea_session_id": kwargs["idea_session_id"],
                "idea_session_owner": kwargs["idea_session_owner"],
            }
        )
        monkeypatch.setattr(
            vdi_management.schedules,
            "create_schedule_for_day_of_week",
            mock_create,
        )

        session = {"idea_session_id": "s1", "owner": "user1", "server": {}}
        result = vdi_management.create_virtual_desktop(session)

        # Called for monday (WORKING_HOURS) and wednesday (CUSTOM_SCHEDULE), not tuesday (NO_SCHEDULE)
        assert mock_create.call_count == 2
        mock_create.assert_any_call(
            day_of_week=vdi_management.schedules.DayOfWeek("monday"),
            schedule={
                "schedule_type": "WORKING_HOURS",
                "idea_session_id": "s1",
                "idea_session_owner": "user1",
            },
            idea_session_id="s1",
            idea_session_owner="user1",
        )
        mock_create.assert_any_call(
            day_of_week=vdi_management.schedules.DayOfWeek("wednesday"),
            schedule={
                "schedule_type": "CUSTOM_SCHEDULE",
                "start_up_time": "06:00",
                "shut_down_time": "22:00",
                "idea_session_id": "s1",
                "idea_session_owner": "user1",
            },
            idea_session_id="s1",
            idea_session_owner="user1",
        )

        # Verify schedule records are flattened into session record
        assert result["monday_schedule"]["schedule_type"] == "WORKING_HOURS"
        assert result["monday_schedule"]["start_up_time"] == "09:00"
        assert result["monday_schedule"]["shut_down_time"] == "17:00"
        assert result["monday_schedule"]["idea_session_id"] == "s1"
        assert result["monday_schedule"]["idea_session_owner"] == "user1"

        assert result["wednesday_schedule"]["schedule_type"] == "CUSTOM_SCHEDULE"
        assert result["wednesday_schedule"]["start_up_time"] == "06:00"
        assert result["wednesday_schedule"]["shut_down_time"] == "22:00"
        assert result["wednesday_schedule"]["idea_session_id"] == "s1"
        assert result["wednesday_schedule"]["idea_session_owner"] == "user1"

        # NO_SCHEDULE day is not persisted via create_schedule_for_day_of_week
        assert result["tuesday_schedule"]["schedule_type"] == "NO_SCHEDULE"

        assert result["state"] == "PROVISIONING"

    def test_schedule_write_failure_does_not_block_session_creation(self, monkeypatch):
        """When create_schedule_for_day_of_week raises, session is still created."""
        monkeypatch.setattr(
            vdi_management.schedules, "get_default_schedules", lambda: None
        )
        monkeypatch.setattr(
            vdi_management,
            "_build_user_data_and_provision",
            lambda s: {"Instances": [{"InstanceId": "i-123"}]},
        )
        monkeypatch.setattr(vdi_management.user_sessions, "create_session", lambda s: s)
        monkeypatch.setattr(
            vdi_management.schedules,
            "create_schedule_for_day_of_week",
            MagicMock(side_effect=Exception("DynamoDB write failed")),
        )

        session = {
            "idea_session_id": "s1",
            "owner": "user1",
            "server": {},
            "schedule": {
                "monday": {"schedule_type": "WORKING_HOURS"},
            },
        }
        result = vdi_management.create_virtual_desktop(session)

        assert result["state"] == "PROVISIONING"
        assert "failure_reason" not in result


class TestBuildUserDataAndProvision:
    """Tests for _build_user_data_and_provision."""

    @pytest.fixture(autouse=True)
    def setup(self, monkeypatch, context):
        monkeypatch.setattr(
            cluster_settings,
            "get_setting",
            lambda k: {
                "cluster.cluster_name": "my-cluster",
                "global-settings.custom_tags": [],
                "vdc.dcv_session.metadata_http_tokens": "required",
                "cluster.ebs.kms_key_id": "alias/aws/ebs",
                "vdc.dcv_session.network.subnet_autoretry": False,
                "vdc.dcv_session.network.randomize_subnets": False,
            }.get(k, ""),
        )
        monkeypatch.setattr(
            vdi_management.res_tags,
            "convert_custom_tags_to_key_value_pairs",
            lambda t: {},
        )
        monkeypatch.setattr(
            vdi_management.res_tags,
            "convert_tags_list_of_dict_to_tags_dict",
            lambda t: {},
        )

    def test_calls_provision_ec2_instance(self, monkeypatch):
        mock_provision = MagicMock(
            return_value={"Instances": [{"InstanceId": "i-123"}]}
        )
        monkeypatch.setattr(vdi_management, "_provision_ec2_instance", mock_provision)

        session = {
            "name": "s1",
            "owner": "user1",
            "project": {"name": "proj1"},
            "attempt_subnets": ["subnet-1"],
            "tags": [],
        }
        result = vdi_management._build_user_data_and_provision(session)

        mock_provision.assert_called_once()
        # No software stack resolved for this session, so ami_id is absent/None.
        assert result == {"Instances": [{"InstanceId": "i-123"}], "ami_id": None}

    def test_includes_software_stack_ami_in_response(self, monkeypatch):
        mock_provision = MagicMock(
            return_value={"Instances": [{"InstanceId": "i-123"}]}
        )
        monkeypatch.setattr(vdi_management, "_provision_ec2_instance", mock_provision)
        monkeypatch.setattr(
            vdi_management.software_stacks,
            "get_software_stack",
            lambda base_os, stack_id: {"ami_id": "ami-12345678"},
        )

        session = {
            "name": "s1",
            "owner": "user1",
            "project": {"name": "proj1"},
            "attempt_subnets": ["subnet-1"],
            "tags": [],
            "base_os": "amazonlinux2",
            "software_stack_id": "stack-1",
        }
        result = vdi_management._build_user_data_and_provision(session)

        assert result["ami_id"] == "ami-12345678"

    def test_project_tags_included_in_instance_tags(self, monkeypatch):
        mock_provision = MagicMock(
            return_value={"Instances": [{"InstanceId": "i-456"}]}
        )
        monkeypatch.setattr(vdi_management, "_provision_ec2_instance", mock_provision)

        session = {
            "name": "s1",
            "owner": "user1",
            "project": {
                "name": "proj1",
                "tags": {"env": "dev", "team": "res"},
            },
            "attempt_subnets": ["subnet-1"],
            "tags": [],
        }
        vdi_management._build_user_data_and_provision(session)

        # aws_tags is the 3rd positional arg to _provision_ec2_instance
        aws_tags = mock_provision.call_args[0][2]
        tag_dict = {t["Key"]: t["Value"] for t in aws_tags}
        assert tag_dict["env"] == "dev"
        assert tag_dict["team"] == "res"

    def test_shuffles_subnets_when_randomize_enabled(self, monkeypatch):
        monkeypatch.setattr(
            cluster_settings,
            "get_setting",
            lambda k: {
                "cluster.cluster_name": "c",
                "global-settings.custom_tags": [],
                "vdc.dcv_session.metadata_http_tokens": "required",
                "cluster.ebs.kms_key_id": "",
                "vdc.dcv_session.network.subnet_autoretry": False,
                "vdc.dcv_session.network.randomize_subnets": True,
            }.get(k, ""),
        )
        mock_shuffle = MagicMock()
        monkeypatch.setattr(random, "shuffle", mock_shuffle)
        monkeypatch.setattr(
            vdi_management,
            "_provision_ec2_instance",
            lambda *a, **kw: {"Instances": [{"InstanceId": "i-1"}]},
        )

        session = {
            "name": "s",
            "owner": "o",
            "project": {},
            "attempt_subnets": ["a", "b"],
            "tags": [],
        }
        vdi_management._build_user_data_and_provision(session)

        mock_shuffle.assert_called_once()


class TestProvisionEc2Instance:
    """Tests for _provision_ec2_instance (orchestration only)."""

    @pytest.fixture(autouse=True)
    def setup(self, monkeypatch, context):
        monkeypatch.setattr(
            vdi_management, "_build_userdata", lambda s, stack: "#!/bin/bash\necho hi"
        )
        monkeypatch.setattr(
            vdi_management.launch_templates,
            "create_for_session",
            lambda **kw: ("lt-test", 1),
        )
        self.mock_delete_launch_template = MagicMock()
        monkeypatch.setattr(
            vdi_management.launch_templates,
            "delete_for_session",
            self.mock_delete_launch_template,
        )
        monkeypatch.setattr(
            vdi_management.ec2_utils,
            "get_valid_instance_types_by_allowed_list",
            lambda hibernation_support, allowed_instance_types: {
                instance_type: {}
                for entry in allowed_instance_types
                for instance_type in (
                    [entry] if "." in entry else [f"{entry}.medium", f"{entry}.large"]
                )
            },
        )
        monkeypatch.setattr(
            cluster_settings,
            "get_setting",
            lambda k: {
                "cluster.cluster_name": "my-cluster",
                "vdc.dcv_session.smart_retry.enabled": False,
            }.get(k),
        )
        self.mock_create_fleet = MagicMock(
            return_value={
                "Instances": [
                    {
                        "InstanceId": "i-new",
                        "InstanceType": "t3.medium",
                        "SubnetId": "subnet-1",
                    }
                ],
                "FleetId": "fleet-abc",
            }
        )
        monkeypatch.setattr(
            vdi_management,
            "_create_fleet",
            self.mock_create_fleet,
        )

    def _session(self, instance_type="t3.medium", hibernation_enabled=False):
        return {
            "base_os": "amzn2023",
            "idea_session_id": "s1",
            "software_stack_id": "ss-test",
            "hibernation_enabled": hibernation_enabled,
            "server": {
                "instance_type": instance_type,
                "security_groups": ["sg-1"],
                "instance_profile_arn": "arn:test",
                "root_volume_size": {"value": 50},
            },
        }

    def _software_stack(self, allowed=("t3.medium", "t3.large")):
        return {
            "ami_id": "ami-123",
            "base_os": "amzn2023",
            "allowed_instance_types": list(allowed),
        }

    def test_returns_result_from_create_fleet(self):
        result = vdi_management._provision_ec2_instance(
            self._session(),
            ["subnet-1"],
            [],
            "required",
            "alias/aws/ebs",
            {"Tenancy": "default"},
            self._software_stack(),
        )

        assert result == self.mock_create_fleet.return_value
        self.mock_create_fleet.assert_called_once()
        self.mock_delete_launch_template.assert_called_once_with("lt-test")

    def test_launch_template_deleted_when_create_fleet_raises(self):
        self.mock_create_fleet.side_effect = exceptions.InvalidParams("boom")

        with pytest.raises(exceptions.InvalidParams):
            vdi_management._provision_ec2_instance(
                self._session(),
                ["subnet-1"],
                [],
                "required",
                "kms",
                {"Tenancy": "default"},
                self._software_stack(),
            )

        self.mock_delete_launch_template.assert_called_once_with("lt-test")

    def test_launch_template_deleted_when_create_for_session_raises(self, monkeypatch):
        def raise_on_create(**kw):
            raise exceptions.InvalidParams("bad ami")

        monkeypatch.setattr(
            vdi_management.launch_templates, "create_for_session", raise_on_create
        )

        with pytest.raises(exceptions.InvalidParams):
            vdi_management._provision_ec2_instance(
                self._session(),
                ["subnet-1"],
                [],
                "required",
                "kms",
                {"Tenancy": "default"},
                self._software_stack(),
            )

        self.mock_delete_launch_template.assert_called_once_with(None)


class TestCreateFleet:
    """Tests for _create_fleet (single-call CreateFleet wrapper)."""

    def _patch_ec2(self, monkeypatch, mock_ec2):
        monkeypatch.setattr(
            vdi_management,
            "AwsClientProvider",
            MagicMock(return_value=MagicMock(ec2=MagicMock(return_value=mock_ec2))),
        )

    def _call(self, overrides=None):
        return vdi_management._create_fleet(
            idea_session_id="s1",
            launch_template_id="lt-test",
            launch_template_version=1,
            overrides=overrides
            or [{"InstanceType": "t3.medium", "SubnetId": "subnet-1"}],
            fleet_tags=[{"Key": "res:EnvironmentName", "Value": "my-cluster"}],
        )

    def test_success_returns_picked_instance(self, monkeypatch):
        mock_ec2 = MagicMock()
        mock_ec2.create_fleet.return_value = {
            "FleetId": "fleet-abc",
            "Instances": [
                {
                    "InstanceIds": ["i-new"],
                    "InstanceType": "t3.medium",
                    "LaunchTemplateAndOverrides": {
                        "Overrides": {"SubnetId": "subnet-1"}
                    },
                }
            ],
            "Errors": [],
        }
        self._patch_ec2(monkeypatch, mock_ec2)

        result = self._call()

        assert result == {
            "Instances": [
                {
                    "InstanceId": "i-new",
                    "InstanceType": "t3.medium",
                    "SubnetId": "subnet-1",
                }
            ],
            "FleetId": "fleet-abc",
        }
        mock_ec2.create_fleet.assert_called_once()

    def test_client_error_propagates(self, monkeypatch):
        mock_ec2 = MagicMock()
        mock_ec2.create_fleet.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "InvalidParameterValue", "Message": "bad ami"}},
            "CreateFleet",
        )
        self._patch_ec2(monkeypatch, mock_ec2)

        with pytest.raises(botocore.exceptions.ClientError):
            self._call()

        assert mock_ec2.create_fleet.call_count == 1

    def test_zero_instances_raises_invalid_params(self, monkeypatch):
        mock_ec2 = MagicMock()
        mock_ec2.create_fleet.return_value = {
            "FleetId": "f",
            "Instances": [],
            "Errors": [
                {"ErrorCode": "InsufficientInstanceCapacity", "ErrorMessage": "ICE"}
            ],
        }
        self._patch_ec2(monkeypatch, mock_ec2)

        with pytest.raises(exceptions.InvalidParams, match="ICE"):
            self._call()

        assert mock_ec2.create_fleet.call_count == 1

    def test_fleet_tagged_from_input(self, monkeypatch):
        mock_ec2 = MagicMock()
        mock_ec2.create_fleet.return_value = {
            "FleetId": "f",
            "Instances": [{"InstanceIds": ["i-1"]}],
        }
        self._patch_ec2(monkeypatch, mock_ec2)

        self._call()

        tag_specs = mock_ec2.create_fleet.call_args[1]["TagSpecifications"]
        assert tag_specs == [
            {
                "ResourceType": "fleet",
                "Tags": [{"Key": "res:EnvironmentName", "Value": "my-cluster"}],
            }
        ]


class TestBuildFleetOverrides:
    """Tests for _build_fleet_overrides."""

    @pytest.fixture(autouse=True)
    def setup(self, monkeypatch):
        monkeypatch.setattr(
            vdi_management.ec2_utils,
            "get_valid_instance_types_by_allowed_list",
            lambda hibernation_support, allowed_instance_types: {
                instance_type: {}
                for entry in allowed_instance_types
                for instance_type in (
                    [entry] if "." in entry else [f"{entry}.medium", f"{entry}.large"]
                )
            },
        )

    def _virtual_desktop(self, instance_type="t3.medium", hibernation_enabled=False):
        return {
            "idea_session_id": "s1",
            "hibernation_enabled": hibernation_enabled,
            "server": {"instance_type": instance_type},
        }

    def _software_stack(
        self, allowed=("t3.medium", "t3.large"), min_ram_value=None, min_ram_unit=None
    ):
        return {
            "allowed_instance_types": list(allowed),
            "min_ram_value": min_ram_value,
            "min_ram_unit": min_ram_unit,
        }

    def test_smart_retry_off_single_user_subnet(self):
        overrides = vdi_management._build_fleet_overrides(
            self._virtual_desktop(),
            self._software_stack(),
            ["subnet-1"],
            smart_retry_enabled=False,
        )
        assert overrides == [{"InstanceType": "t3.medium", "SubnetId": "subnet-1"}]

    def test_smart_retry_off_multiple_subnets(self):
        overrides = vdi_management._build_fleet_overrides(
            self._virtual_desktop(),
            self._software_stack(),
            ["subnet-1", "subnet-2"],
            smart_retry_enabled=False,
        )
        assert [o["SubnetId"] for o in overrides] == ["subnet-1", "subnet-2"]
        assert all(o["InstanceType"] == "t3.medium" for o in overrides)

    def test_smart_retry_on_cross_product(self):
        overrides = vdi_management._build_fleet_overrides(
            self._virtual_desktop(),
            self._software_stack(allowed=("t3.medium", "t3.large")),
            ["subnet-1", "subnet-2"],
            smart_retry_enabled=True,
        )
        pairs = {(o["InstanceType"], o["SubnetId"]) for o in overrides}
        assert pairs == {
            ("t3.medium", "subnet-1"),
            ("t3.medium", "subnet-2"),
            ("t3.large", "subnet-1"),
            ("t3.large", "subnet-2"),
        }
        assert all("Placement" not in o for o in overrides)

    def test_smart_retry_on_expands_families(self):
        overrides = vdi_management._build_fleet_overrides(
            self._virtual_desktop(),
            self._software_stack(allowed=("t3",)),
            ["subnet-1"],
            smart_retry_enabled=True,
        )
        assert {o["InstanceType"] for o in overrides} == {"t3.medium", "t3.large"}

    def test_raises_when_no_valid_instance_types(self, monkeypatch):
        monkeypatch.setattr(
            vdi_management.ec2_utils,
            "get_valid_instance_types_by_allowed_list",
            lambda hibernation_support, allowed_instance_types: {},
        )

        with pytest.raises(exceptions.InvalidParams, match="No valid instance types"):
            vdi_management._build_fleet_overrides(
                self._virtual_desktop(hibernation_enabled=True),
                self._software_stack(allowed=("g4dn",)),
                ["subnet-1"],
                smart_retry_enabled=True,
            )

    def test_smart_retry_filters_by_min_ram(self, monkeypatch):
        """Instance types that don't meet the software stack min RAM are excluded."""
        monkeypatch.setattr(
            vdi_management.software_stacks,
            "validate_min_ram",
            lambda instance_type_name, software_stack: instance_type_name
            != "t3.medium",
        )
        overrides = vdi_management._build_fleet_overrides(
            self._virtual_desktop(),
            self._software_stack(
                allowed=("t3.medium", "t3.large"),
                min_ram_value=50,
                min_ram_unit="GiB",
            ),
            ["subnet-1"],
            smart_retry_enabled=True,
        )
        assert {o["InstanceType"] for o in overrides} == {"t3.large"}


class TestBuildUserdata:
    """Tests for _build_userdata."""

    @pytest.fixture(autouse=True)
    def setup(self, monkeypatch, context):
        monkeypatch.setattr(vdi_management.gpu_utils, "is_nvidia_gpu", lambda x: False)
        monkeypatch.setattr(vdi_management.gpu_utils, "is_amd_gpu", lambda x: False)
        monkeypatch.setattr(
            vdi_management.script_utils, "_retrieve_rerun_on_reboot", lambda *a: False
        )
        monkeypatch.setattr(
            vdi_management.script_utils, "_retrieve_scripts_as_commands", lambda *a: []
        )
        monkeypatch.setattr(
            vdi_management.script_utils,
            "_store_commands_as_linux_script",
            lambda *a: [],
        )
        monkeypatch.setattr(cluster_settings, "get_setting", lambda k: "test-value")
        monkeypatch.setattr(cluster_settings, "get_secret", lambda k: "my-secret-key")
        monkeypatch.setattr(
            vdi_management, "_has_fsx_lustre_file_systems", lambda: False
        )
        mock_builder = MagicMock()
        mock_builder.build.return_value = "#!/bin/bash\nbootstrap"
        monkeypatch.setattr(
            vdi_management, "BootstrapUserDataBuilder", lambda **kw: mock_builder
        )

    def test_returns_userdata_string(self):
        session = {
            "base_os": "amzn2023",
            "owner": "user1",
            "idea_session_id": "s1",
            "session_type": "CONSOLE",
            "hibernation_enabled": False,
            "project": {"project_id": "p1", "name": "proj"},
            "server": {"instance_type": "t3.medium"},
        }
        result = vdi_management._build_userdata(session, {"gpu": "NO_GPU"})
        assert result == "#!/bin/bash\nbootstrap"

    def test_windows_calls_build_windows_commands(self, monkeypatch):
        mock_win_commands = MagicMock(return_value=["powershell cmd"])
        monkeypatch.setattr(
            vdi_management, "_build_windows_install_commands", mock_win_commands
        )
        mock_builder = MagicMock()
        mock_builder.build.return_value = "windows-userdata"
        monkeypatch.setattr(
            vdi_management, "BootstrapUserDataBuilder", lambda **kw: mock_builder
        )

        session = {
            "base_os": "windows",
            "owner": "user1",
            "idea_session_id": "s1",
            "session_type": "CONSOLE",
            "hibernation_enabled": False,
            "project": {"project_id": "p1", "name": "proj"},
            "server": {"instance_type": "t3.medium"},
        }
        result = vdi_management._build_userdata(session, {"gpu": "NO_GPU"})

        mock_win_commands.assert_called_once()
        assert result == "windows-userdata"


class TestBuildWindowsInstallCommands:
    """Tests for _build_windows_install_commands."""

    @pytest.fixture(autouse=True)
    def setup(self, monkeypatch, context):
        monkeypatch.setattr(cluster_settings, "get_setting", lambda k: "test-value")
        monkeypatch.setattr(
            vdi_management.script_utils, "_retrieve_scripts_as_commands", lambda *a: []
        )
        monkeypatch.setattr(
            vdi_management.script_utils,
            "_store_commands_as_windows_script",
            lambda *a: [],
        )

    def test_returns_list_of_commands(self):
        session = {"owner": "user1", "idea_session_id": "s1"}
        project = {"project_id": "p1", "name": "proj"}
        result = vdi_management._build_windows_install_commands(
            session, project, "jwt-token", "https://broker.api"
        )

        assert isinstance(result, list)
        assert any("Install-WindowsEC2Instance" in cmd for cmd in result)
        assert any("jwt-token" in cmd for cmd in result)


class TestHasFsxLustreFileSystems:
    """Tests for _has_fsx_lustre_file_systems."""

    @pytest.fixture(autouse=True)
    def setup(self, context):
        pass

    def test_returns_true_when_entries_exist(self, monkeypatch):
        monkeypatch.setattr(
            vdi_management.cluster_settings_utils,
            "get_config_entries",
            lambda query: [{"key": "shared-storage.lustre.fsx_lustre.id"}],
        )
        assert vdi_management._has_fsx_lustre_file_systems() is True

    def test_returns_false_when_no_entries(self, monkeypatch):
        monkeypatch.setattr(
            vdi_management.cluster_settings_utils,
            "get_config_entries",
            lambda query: [],
        )
        assert vdi_management._has_fsx_lustre_file_systems() is False
