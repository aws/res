#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import unittest
from unittest.mock import MagicMock

import pytest
import res as res
from res.clients.dcv_broker import dcv_broker_client

TEST_STRING = "test"
TEST_SESSION_ID = "test_session_id"
POS_NUM_CONNECTIONS = 1
ZERO_NUM_CONNECTIONS = 0
SESSION = {
    "idea_session_id": TEST_SESSION_ID,
    "name": TEST_STRING,
    "dcv_session_id": TEST_SESSION_ID,
}


@pytest.fixture(scope="class")
def monkeypatch_for_class(request):
    request.cls.monkeypatch = pytest.MonkeyPatch()


@pytest.mark.usefixtures("monkeypatch_for_class")
class TestDcvBroker(unittest.TestCase):

    def test_dcv_broker_describe_sessions_pass(self):
        """
        describe dcv session
        """
        session_response = {
            "sessions": [
                {
                    "id": TEST_SESSION_ID,
                }
            ]
        }

        self.monkeypatch.setattr(
            dcv_broker_client,
            "_describe_sessions",
            lambda session_ids: session_response,
        )

        result = dcv_broker_client.describe_sessions([SESSION])
        assert len(result) == 1
        assert result.get("sessions").get(TEST_SESSION_ID) == {"id": TEST_SESSION_ID}

    def test_get_active_counts_for_sessions_pass(self):
        """
        get active_connection_count for dcv session
        """
        describe_session_response = {
            "sessions": {
                TEST_SESSION_ID: {
                    "id": TEST_SESSION_ID,
                    "num_of_connections": POS_NUM_CONNECTIONS,
                }
            }
        }
        mock_describe_session = MagicMock(return_value=describe_session_response)
        self.monkeypatch.setattr(
            dcv_broker_client, "describe_sessions", mock_describe_session
        )

        result = dcv_broker_client.get_active_counts_for_sessions(sessions=[SESSION])
        mock_describe_session.assert_called_once()
        assert len(result) == 1
        assert result[0].get("connection_count") == POS_NUM_CONNECTIONS

    def delete_session_response(self):
        def _delete_session_response(sessions):
            if sessions and sessions[0]:
                return {
                    "successful_list": [
                        {
                            "session_id": TEST_SESSION_ID,
                        }
                    ],
                }
            else:
                return {}

        return _delete_session_response

    def test_delete_sessions_unsuccessful(self):
        """
        delete dcv session unsuccessful
        """
        describe_session_response = {
            "sessions": {
                TEST_SESSION_ID: {
                    "id": TEST_SESSION_ID,
                    "num_of_connections": POS_NUM_CONNECTIONS,
                }
            }
        }
        mock_describe_session = MagicMock(return_value=describe_session_response)
        self.monkeypatch.setattr(
            dcv_broker_client, "describe_sessions", mock_describe_session
        )
        self.monkeypatch.setattr(
            dcv_broker_client, "_delete_sessions", self.delete_session_response()
        )
        success, fail = dcv_broker_client.delete_sessions([SESSION])
        assert len(success) == 0
        assert len(fail) == 1
        assert fail[0].get("connection_count") == POS_NUM_CONNECTIONS
        assert fail[0].get("dcv_session_id") == TEST_SESSION_ID
        assert fail[0].get("failure_reason")

    def test_delete_sessions_successful(self):
        """
        delete dcv session successful
        """
        describe_session_response = {
            "sessions": {
                TEST_SESSION_ID: {
                    "id": TEST_SESSION_ID,
                    "num_of_connections": ZERO_NUM_CONNECTIONS,
                }
            }
        }
        mock_describe_session = MagicMock(return_value=describe_session_response)
        self.monkeypatch.setattr(
            dcv_broker_client, "describe_sessions", mock_describe_session
        )
        self.monkeypatch.setattr(
            dcv_broker_client, "_delete_sessions", self.delete_session_response()
        )
        success, fail = dcv_broker_client.delete_sessions([SESSION])
        assert len(success) == 1
        assert len(fail) == 0
        assert success[0].get("dcv_session_id") == TEST_SESSION_ID
        assert not success[0].get("failure_reason")
