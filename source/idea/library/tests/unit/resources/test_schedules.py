#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import unittest
from typing import Dict, Optional
from unittest.mock import MagicMock

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

    def setUp(self):
        self.context: SchedulesTestContext = SchedulesTestContext()
        self.context.schedule = {
            schedules.SCHEDULE_DB_HASH_KEY: TEST_DAY_OF_WEEK,
            schedules.SCHEDULE_DB_RANGE_KEY: TEST_SCHEDULE_ID,
            schedules.SCHEDULE_DB_SCHEDULE_TYPE_KEY: TEST_SCHEDULE_TYPE,
        }
        table_utils.create_item(
            schedules.SCHEDULE_DB_TABLE_NAME, item=self.context.schedule
        )
        table_utils.create_item(
            cluster_settings.CLUSTER_SETTINGS_TABLE_NAME,
            item={"key": "vdc.events_sqs_queue_url", "value": "queuevalue"},
        )

    def test_delete_schedule_pass(self):
        """
        delete schedule happy path
        """
        item = table_utils.get_item(
            schedules.SCHEDULE_DB_TABLE_NAME,
            key={
                schedules.SCHEDULE_DB_HASH_KEY: TEST_DAY_OF_WEEK,
                schedules.SCHEDULE_DB_RANGE_KEY: TEST_SCHEDULE_ID,
            },
        )
        assert item is not None

        schedules.delete_schedule(self.context.schedule)

        item = table_utils.get_item(
            schedules.SCHEDULE_DB_TABLE_NAME,
            key={
                schedules.SCHEDULE_DB_HASH_KEY: TEST_DAY_OF_WEEK,
                schedules.SCHEDULE_DB_RANGE_KEY: TEST_SCHEDULE_ID,
            },
        )
        assert item is None

    def test_create_schedule_pass(self):
        """
        create schedule should pass
        """
        schedule = {
            schedules.SCHEDULE_DB_HASH_KEY: TEST_DAY_OF_WEEK_2,
            schedules.SCHEDULE_DB_SCHEDULE_TYPE_KEY: TEST_SCHEDULE_TYPE_2,
        }
        self.monkeypatch.setattr(events_client, "publish_create_event", MagicMock())

        returned_schedule = schedules.create_schedule(schedule)

        assert returned_schedule[schedules.SCHEDULE_DB_HASH_KEY] == TEST_DAY_OF_WEEK_2
        assert (
            returned_schedule[schedules.SCHEDULE_DB_SCHEDULE_TYPE_KEY]
            == TEST_SCHEDULE_TYPE_2
        )

    def test_create_schedule_fail_empty_schedule(self):
        """
        create schedule should fail
        """
        with pytest.raises(Exception) as exc_info:
            schedules.create_schedule(None)
        assert "schedule is required" in exc_info.value.args[0]
