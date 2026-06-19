#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import unittest
from typing import Dict, Optional
from unittest.mock import MagicMock, patch

import pytest
import res as res
from res.clients.events import events_client
from res.resources import cluster_settings, schedules
from res.utils import table_utils, time_utils

TEST_SCHEDULE_ID = "test_schedule_id"
TEST_DAY_OF_WEEK = "test_day_of_week"
TEST_SCHEDULE_TYPE = "test_schedule_type"
TEST_DAY_OF_WEEK_2 = "test_day_of_week_2"
TEST_SCHEDULE_TYPE_2 = "test_schedule_type_2"
TEST_QUEUE_URL = "test_queue_url"


@pytest.fixture(scope="class")
def monkeypatch_for_class(request):
    request.cls.monkeypatch = pytest.MonkeyPatch()


class SchedulesTestContext:
    schedule: Optional[Dict]


@pytest.mark.usefixtures("monkeypatch_for_class")
class TestSchedules(unittest.TestCase):

    @patch("res.utils.table_utils.create_item")
    def setUp(self, mock_create_item):
        self.context: SchedulesTestContext = SchedulesTestContext()
        self.context.schedule = {
            schedules.SCHEDULE_DB_HASH_KEY: TEST_DAY_OF_WEEK,
            schedules.SCHEDULE_DB_RANGE_KEY: TEST_SCHEDULE_ID,
            schedules.SCHEDULE_DB_SCHEDULE_TYPE_KEY: TEST_SCHEDULE_TYPE,
        }

    @patch("res.utils.table_utils.delete_item")
    def test_delete_schedule_pass(self, mock_delete_item):
        """delete schedule happy path"""
        schedules.delete_schedule(self.context.schedule)

        mock_delete_item.assert_called_once_with(
            schedules.SCHEDULE_DB_TABLE_NAME,
            key={
                schedules.SCHEDULE_DB_HASH_KEY: TEST_DAY_OF_WEEK,
                schedules.SCHEDULE_DB_RANGE_KEY: TEST_SCHEDULE_ID,
            },
        )

    @patch("res.resources.schedules.events_client.publish_create_event")
    @patch("res.utils.table_utils.create_item")
    def test_create_schedule_pass(self, mock_create_item, mock_publish_event):
        """create schedule should pass"""
        schedule = {
            schedules.SCHEDULE_DB_HASH_KEY: TEST_DAY_OF_WEEK_2,
            schedules.SCHEDULE_DB_SCHEDULE_TYPE_KEY: TEST_SCHEDULE_TYPE_2,
        }
        mock_create_item.return_value = schedule

        returned_schedule = schedules.create_schedule(schedule)

        mock_create_item.assert_called_once()
        mock_publish_event.assert_called_once()
        assert returned_schedule[schedules.SCHEDULE_DB_HASH_KEY] == TEST_DAY_OF_WEEK_2
        assert (
            returned_schedule[schedules.SCHEDULE_DB_SCHEDULE_TYPE_KEY]
            == TEST_SCHEDULE_TYPE_2
        )
        assert schedules.SCHEDULE_DB_RANGE_KEY in schedule  # verify UUID was generated

    def test_create_schedule_fail_empty_schedule(self):
        """
        create schedule should fail
        """
        with pytest.raises(Exception) as exc_info:
            schedules.create_schedule(None)
        assert "schedule is required" in exc_info.value.args[0]

    @patch(
        "res.resources.schedules._create_or_update_schedule_for_session_for_day_of_week"
    )
    def test_update_schedule_for_session(self, mock_create_or_update):
        """Test update_schedule_for_session calls helper function for each day of week."""
        from res.resources.schedules import SCHEDULE_DB_SESSION_ID_KEY, DayOfWeek

        old_session = {
            SCHEDULE_DB_SESSION_ID_KEY: "session-123",
            "owner": "user1",
            "monday_schedule": {"schedule_type": "NO_SCHEDULE"},
            "tuesday_schedule": {"schedule_type": "WORKING_HOURS"},
        }
        new_session = {
            "monday_schedule": {"schedule_type": "WORKING_HOURS"},
            "tuesday_schedule": {"schedule_type": "CUSTOM_SCHEDULE"},
        }

        mock_create_or_update.return_value = {"schedule_type": "updated"}

        result = schedules.update_schedule_for_session(new_session, old_session)

        # Should be called once for each day of the week (7 times)
        assert mock_create_or_update.call_count == len(DayOfWeek)
        # Should return the old_session with updated schedules
        assert result == old_session
        # All day schedules should be updated
        for day in DayOfWeek:
            assert result[f"{day.value}_schedule"] == {"schedule_type": "updated"}
