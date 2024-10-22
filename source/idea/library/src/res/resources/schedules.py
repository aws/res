#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import logging
from typing import Any, Dict, Optional

import res.exceptions as exceptions
from res.utils import table_utils, time_utils

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)

SCHEDULE_DB_HASH_KEY = "day_of_week"
SCHEDULE_DB_RANGE_KEY = "schedule_id"
SCHEDULE_DB_SCHEDULE_TYPE_KEY = "schedule_type"
SCHEDULE_DB_TABLE_NAME = "vdc.controller.schedules"
SCHEDULE_DAYS = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]


def delete_schedule(schedule: Dict[str, Any]) -> None:
    """
    Delete schedule from DDB
    :param schedule: scheduke to be deleted
    """
    if (
        not schedule.get(SCHEDULE_DB_SCHEDULE_TYPE_KEY)
        or schedule.get(SCHEDULE_DB_SCHEDULE_TYPE_KEY) == "NO_SCHEDULE"
    ):
        logger.info("No schedule to delete")
        return

    if not schedule.get(SCHEDULE_DB_HASH_KEY):
        raise Exception(f"{SCHEDULE_DB_HASH_KEY} not provided")

    if not schedule.get(SCHEDULE_DB_RANGE_KEY):
        raise Exception(f"{SCHEDULE_DB_RANGE_KEY} not provided")
    table_utils.delete_item(
        SCHEDULE_DB_TABLE_NAME,
        key={
            SCHEDULE_DB_HASH_KEY: schedule.get(SCHEDULE_DB_HASH_KEY),
            SCHEDULE_DB_RANGE_KEY: schedule.get(SCHEDULE_DB_RANGE_KEY),
        },
    )
