#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import unittest
from typing import Dict, Optional

import res as res
from res.resources import schedules
from res.utils import table_utils, time_utils

TEST_SCHEDULE_ID = "test_schedule_id"
TEST_DAY_OF_WEEK = "test_day_of_week"
TEST_SCHEDULE_TYPE = "test_schedule_type"


class SchedulesTestContext:
    schedule: Optional[Dict]


class TestSchedules(unittest.TestCase):

    def setUp(self):
        self.context: SchedulesTestContext = SchedulesTestContext()
        self.context.schedule = {
            schedules.SCHEDULE_DB_HASH_KEY: TEST_DAY_OF_WEEK,
            schedules.SCHEDULE_DB_RANGE_KEY: TEST_SCHEDULE_ID,
            "schedule_type": TEST_SCHEDULE_TYPE,
        }
        table_utils.create_item(
            schedules.SCHEDULE_DB_TABLE_NAME, item=self.context.schedule
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
