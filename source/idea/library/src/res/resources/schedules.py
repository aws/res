#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from datamodel.models.day_of_week import DayOfWeek
from datamodel.models.virtual_desktop_schedule_type import VirtualDesktopScheduleType
from res.clients.events import events_client
from res.resources import cluster_settings
from res.utils import logging_utils, table_utils

SCHEDULE_DB_HASH_KEY = "day_of_week"
SCHEDULE_DB_RANGE_KEY = "schedule_id"
SCHEDULE_DB_SESSION_ID_KEY = "idea_session_id"
SCHEDULE_DB_SCHEDULE_TYPE_KEY = "schedule_type"
SCHEDULE_DB_TABLE_NAME = "vdc.controller.schedules"

logger = logging_utils.get_logger(SCHEDULE_DB_TABLE_NAME)


class VirtualDesktopSchedule:
    def __init__(
        self,
        schedule_id=None,
        idea_session_id=None,
        idea_session_owner=None,
        day_of_week=None,
        start_up_time=None,
        shut_down_time=None,
        schedule_type=None,
    ):
        self.schedule_id: Optional[str] = schedule_id
        self.idea_session_id: Optional[str] = idea_session_id
        self.idea_session_owner: Optional[str] = idea_session_owner
        self.day_of_week: Optional[DayOfWeek] = day_of_week
        self.start_up_time: Optional[str] = start_up_time
        self.shut_down_time: Optional[str] = shut_down_time
        self.schedule_type: Optional[VirtualDesktopScheduleType] = schedule_type

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schedule_id": self.schedule_id,
            "idea_session_id": self.idea_session_id,
            "idea_session_owner": self.idea_session_owner,
            "day_of_week": (
                self.day_of_week.value
                if isinstance(self.day_of_week, DayOfWeek)
                else self.day_of_week
            ),
            "start_up_time": self.start_up_time,
            "shut_down_time": self.shut_down_time,
            "schedule_type": (
                self.schedule_type.value
                if isinstance(self.schedule_type, VirtualDesktopScheduleType)
                else self.schedule_type
            ),
        }


class VirtualDesktopWeekSchedule:
    def __init__(
        self,
        monday=None,
        tuesday=None,
        wednesday=None,
        thursday=None,
        friday=None,
        saturday=None,
        sunday=None,
    ):
        self.monday: Optional[VirtualDesktopSchedule] = monday
        self.tuesday: Optional[VirtualDesktopSchedule] = tuesday
        self.wednesday: Optional[VirtualDesktopSchedule] = wednesday
        self.thursday: Optional[VirtualDesktopSchedule] = thursday
        self.friday: Optional[VirtualDesktopSchedule] = friday
        self.saturday: Optional[VirtualDesktopSchedule] = saturday
        self.sunday: Optional[VirtualDesktopSchedule] = sunday

    def to_dict(self) -> Dict[str, Any]:
        return {
            day.value: (
                getattr(self, day.value).to_dict() if getattr(self, day.value) else None
            )
            for day in DayOfWeek
        }


def create_schedule(schedule: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create schedule in DDB
    :param schedule: scheduke to be created
    """
    if not schedule:
        raise Exception("schedule is required")
    schedule[SCHEDULE_DB_RANGE_KEY] = str(uuid.uuid4())
    created_schedule = table_utils.create_item(
        table_name=SCHEDULE_DB_TABLE_NAME, item=schedule
    )
    events_client.publish_create_event(
        created_schedule[SCHEDULE_DB_HASH_KEY],
        created_schedule[SCHEDULE_DB_RANGE_KEY],
        new_entry=created_schedule,
        table_name=SCHEDULE_DB_TABLE_NAME,
    )
    return created_schedule


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


def get_default_schedules() -> Dict[str, Any]:
    return {day.value: _get_default_schedule_for_day_of_week(day) for day in DayOfWeek}


def _get_default_schedule_for_day_of_week(day_of_week: DayOfWeek) -> Dict[str, Any]:
    schedule_type = VirtualDesktopScheduleType(
        cluster_settings.get_setting(
            f"vdc.dcv_session.schedule.{day_of_week.value}.type"
        )
    )
    if schedule_type == VirtualDesktopScheduleType.WORKING_HOURS:
        start_up_time = cluster_settings.get_setting(
            "vdc.dcv_session.working_hours.start_up_time"
        )
        shut_down_time = cluster_settings.get_setting(
            "vdc.dcv_session.working_hours.shut_down_time"
        )
    elif schedule_type == VirtualDesktopScheduleType.STOP_ALL_DAY:
        start_up_time = "23:59"
        shut_down_time = "00:00"
    elif schedule_type == VirtualDesktopScheduleType.START_ALL_DAY:
        start_up_time = "00:00"
        shut_down_time = "23:59"
    elif schedule_type == VirtualDesktopScheduleType.CUSTOM_SCHEDULE:
        start_up_time = cluster_settings.get_setting(
            f"vdc.dcv_session.schedule.{day_of_week.value}.start_up_time"
        )
        shut_down_time = cluster_settings.get_setting(
            f"vdc.dcv_session.schedule.{day_of_week.value}.shut_down_time"
        )
    else:
        # schedule_type == NO_SCHEDULE
        start_up_time = ""
        shut_down_time = ""

    return {
        "day_of_week": (
            day_of_week.value if isinstance(day_of_week, DayOfWeek) else day_of_week
        ),
        "start_up_time": start_up_time,
        "shut_down_time": shut_down_time,
        "schedule_type": (
            schedule_type.value
            if isinstance(schedule_type, VirtualDesktopScheduleType)
            else schedule_type
        ),
    }


def update_schedule_for_session(
    new_session: Dict[str, Any], session_to_update: Dict[str, Any]
) -> Dict[str, Any]:
    for day in DayOfWeek:
        session_to_update[f"{day.value}_schedule"] = (
            _create_or_update_schedule_for_session_for_day_of_week(
                day,
                session_to_update.get(f"{day.value}_schedule"),
                new_session.get(f"{day.value}_schedule"),
                session_to_update[SCHEDULE_DB_SESSION_ID_KEY],
                session_to_update["owner"],
            )
        )

    return session_to_update


def _create_or_update_schedule_for_session_for_day_of_week(
    day_of_week: DayOfWeek,
    current_schedule: Dict[str, Any],
    new_schedule: Dict[str, Any],
    idea_session_id: str,
    idea_session_owner: str,
) -> Dict[str, Any]:
    logger.debug(
        f"day_of_week: {day_of_week}, current_schedule: {current_schedule}, new_schedule: {new_schedule}, idea_session_id: {idea_session_id}, idea_session_owner: {idea_session_owner}"
    )

    if not current_schedule:
        current_schedule = get_empty_schedule(day_of_week)

    if not new_schedule:
        return current_schedule

    if (
        current_schedule.get("schedule_type") == new_schedule.get("schedule_type")
        and new_schedule.get("schedule_type")
        != VirtualDesktopScheduleType.CUSTOM_SCHEDULE.value
    ):
        logger.debug(f"Same schedule type, no need to update schedule")
        return current_schedule

    if (
        current_schedule.get("schedule_type")
        == VirtualDesktopScheduleType.CUSTOM_SCHEDULE.value
        and new_schedule.get("schedule_type")
        == VirtualDesktopScheduleType.CUSTOM_SCHEDULE.value
    ):
        logger.debug(f"Checking for custom schedule changes")
        if current_schedule.get("start_up_time") == new_schedule.get(
            "start_up_time"
        ) and current_schedule.get("shut_down_time") == new_schedule.get(
            "shut_down_time"
        ):
            logger.debug(f"Same custom schedule, no need to update schedule")
            return current_schedule

    _delete_schedule(current_schedule)
    new_schedule = _create_schedule_for_day_of_week(
        day_of_week, new_schedule, idea_session_id, idea_session_owner
    )

    return new_schedule


def _delete_schedule(schedule: Dict[str, Any]):
    if (
        not schedule
        or schedule.get("schedule_type") == VirtualDesktopScheduleType.NO_SCHEDULE.value
    ):
        logger.debug("No Schedule to delete. Returning")
        return

    if not schedule.get("schedule_id") or not schedule.get("day_of_week"):
        logger.warning(
            f"Schedule missing schedule_id or day_of_week, skipping delete: "
            f"schedule_id={schedule.get('schedule_id')}, "
            f"day_of_week={schedule.get('day_of_week')}"
        )
        return

    delete_schedule(schedule)


def _create_schedule_for_day_of_week(
    day_of_week: DayOfWeek,
    schedule: Dict[str, Any],
    idea_session_id: str,
    idea_session_owner: str,
) -> Dict[str, Any]:
    if schedule.get("schedule_type") == VirtualDesktopScheduleType.NO_SCHEDULE.value:
        return get_empty_schedule(day_of_week)

    schedules_dict = create_schedule(
        {
            "day_of_week": DayOfWeek(day_of_week),
            "idea_session_id": idea_session_id,
            "idea_session_owner": idea_session_owner,
            "schedule_type": schedule.get("schedule_type"),
            "start_up_time": schedule.get("start_up_time"),
            "shut_down_time": schedule.get("shut_down_time"),
        }
    )
    return schedules_dict


def get_empty_schedule(day_of_week: Optional[DayOfWeek] = None) -> Dict[str, Any]:
    return {
        "schedule_id": "",
        "day_of_week": (
            day_of_week.value if isinstance(day_of_week, DayOfWeek) else day_of_week
        ),
        "schedule_type": VirtualDesktopScheduleType.NO_SCHEDULE.value,
    }
