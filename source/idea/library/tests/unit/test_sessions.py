#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import unittest
from typing import Dict, Optional

import pytest
import res as res
import res.exceptions as exceptions
from res.resources import sessions
from res.utils import table_utils, time_utils

TEST_OWNER = "test_owner"
TEST_SESSION_ID = "test_session_id"
RANDOM_OWNER = "random_owner"
RANDOM_SESSION_ID = "random_session_id"
TEST_STATE = "test_state"
UPDATED_STATE = "updates_state"


class SessionsTestContext:
    session: Optional[Dict]


class TestSessions(unittest.TestCase):

    def setUp(self):
        self.context: SessionsTestContext = SessionsTestContext()
        self.context.session = {
            sessions.SESSION_DB_HASH_KEY: TEST_OWNER,
            sessions.SESSION_DB_RANGE_KEY: TEST_SESSION_ID,
            sessions.SESSION_DB_STATE_KEY: TEST_STATE,
        }
        table_utils.create_item(sessions.SESSIONS_TABLE_NAME, item=self.context.session)

    def test_sessions_get_sessions_invalid_request_should_fail(self):
        """
        get session failure
        """
        # invalid owner
        with pytest.raises(exceptions.UserSessionNotFound) as exc_info:
            sessions.get_session(owner=RANDOM_OWNER, session_id=TEST_SESSION_ID)
        assert f"Session not found: {TEST_SESSION_ID}" == exc_info.value.args[0]

        # invalid session id
        with pytest.raises(exceptions.UserSessionNotFound) as exc_info:
            sessions.get_session(owner=TEST_OWNER, session_id=RANDOM_SESSION_ID)
        assert f"Session not found: {RANDOM_SESSION_ID}" == exc_info.value.args[0]

    def test_sessions_get_sessions_valid_request_should_pass(self):
        """
        get session happy path
        """
        result = sessions.get_session(owner=TEST_OWNER, session_id=TEST_SESSION_ID)
        assert result is not None
        assert result.get(sessions.SESSION_DB_HASH_KEY) == TEST_OWNER
        assert result.get(sessions.SESSION_DB_RANGE_KEY) == TEST_SESSION_ID

    def test_sessions_update_session_should_pass(self):
        """
        update session happy path
        """
        assert self.context.session is not None
        updated_session = self.context.session
        updated_session["state"] = UPDATED_STATE
        sessions.update_session(updated_session)
        session = sessions.get_session(owner=TEST_OWNER, session_id=TEST_SESSION_ID)
        assert session is not None
        assert session.get(sessions.SESSION_DB_HASH_KEY) == TEST_OWNER
        assert session.get(sessions.SESSION_DB_RANGE_KEY) == TEST_SESSION_ID
        assert session.get(sessions.SESSION_DB_STATE_KEY) == UPDATED_STATE

        curr_time = time_utils.current_time_ms()
        assert session.get(sessions.SESSION_DB_UPDATED_ON_KEY) is not None
        assert session.get(sessions.SESSION_DB_UPDATED_ON_KEY) <= curr_time
