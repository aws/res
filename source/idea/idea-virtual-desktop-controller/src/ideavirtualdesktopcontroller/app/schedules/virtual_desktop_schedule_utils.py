#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

from datetime import date, datetime, time, timedelta

import ideavirtualdesktopcontroller
from ideadatamodel import VirtualDesktopSession, DayOfWeek, VirtualDesktopSchedule, VirtualDesktopScheduleType, VirtualDesktopWeekSchedule
from ideasdk.utils import Utils, DateTimeUtils
from ideavirtualdesktopcontroller.app.events.events_utils import EventsUtils
from ideavirtualdesktopcontroller.app.schedules.virtual_desktop_schedule_db import VirtualDesktopScheduleDB
from res.resources import schedules


class VirtualDesktopScheduleUtils:
    def __init__(self, context: ideavirtualdesktopcontroller.AppContext, db: VirtualDesktopScheduleDB):
        self.context = context
        self._logger = self.context.logger('virtual-desktop-schedule-utils')
        self._schedule_db = db
        self._events_utils = EventsUtils(context=self.context)

    def _get_default_schedule_for_day_of_week(self, day_of_week: DayOfWeek) -> VirtualDesktopSchedule:    
        schedule_type = VirtualDesktopScheduleType(self.context.config().get_string(f'virtual-desktop-controller.dcv_session.schedule.{day_of_week.value}.type', required=True))
        if schedule_type == VirtualDesktopScheduleType.WORKING_HOURS:
            start_up_time = self.context.config().get_string('virtual-desktop-controller.dcv_session.working_hours.start_up_time', required=True)
            shut_down_time = self.context.config().get_string('virtual-desktop-controller.dcv_session.working_hours.shut_down_time', required=True)
        elif schedule_type == VirtualDesktopScheduleType.STOP_ALL_DAY:
            start_up_time = '23:59'
            shut_down_time = '00:00'
        elif schedule_type == VirtualDesktopScheduleType.START_ALL_DAY:
            start_up_time = '00:00'
            shut_down_time = '23:59'
        elif schedule_type == VirtualDesktopScheduleType.CUSTOM_SCHEDULE:
            start_up_time = self.context.config().get_string(f'virtual-desktop-controller.dcv_session.schedule.{day_of_week.value}.start_up_time', required=True)
            shut_down_time = self.context.config().get_string(f'virtual-desktop-controller.dcv_session.schedule.{day_of_week.value}.shut_down_time', required=True)
        else:
            # schedule_type == NO_SCHEDULE
            start_up_time = ''
            shut_down_time = ''

        return VirtualDesktopSchedule(
            day_of_week=day_of_week,
            start_up_time=start_up_time,
            shut_down_time=shut_down_time,
            schedule_type=schedule_type
        )

    def get_default_schedules(self) -> VirtualDesktopWeekSchedule:
        return VirtualDesktopWeekSchedule(
            monday=self._get_default_schedule_for_day_of_week(DayOfWeek.MONDAY),
            tuesday=self._get_default_schedule_for_day_of_week(DayOfWeek.TUESDAY),
            wednesday=self._get_default_schedule_for_day_of_week(DayOfWeek.WEDNESDAY),
            thursday=self._get_default_schedule_for_day_of_week(DayOfWeek.THURSDAY),
            friday=self._get_default_schedule_for_day_of_week(DayOfWeek.FRIDAY),
            saturday=self._get_default_schedule_for_day_of_week(DayOfWeek.SATURDAY),
            sunday=self._get_default_schedule_for_day_of_week(DayOfWeek.SUNDAY),
        )

    def _delete_schedule(self, schedule: VirtualDesktopSchedule):
        if Utils.is_empty(schedule) or schedule.schedule_type == VirtualDesktopScheduleType.NO_SCHEDULE:
            self._logger.debug("No Schedule to delete. Returning")
            return

        if Utils.is_any_empty(getattr(schedule, 'schedule_id', None), getattr(schedule, 'day_of_week', None)):
            return

        self._schedule_db.delete(schedule)

    def _create_schedule_for_day_of_week(self, day_of_week: DayOfWeek, schedule: VirtualDesktopSchedule, idea_session_id: str, idea_session_owner: str) -> VirtualDesktopSchedule:
        if schedule.schedule_type == VirtualDesktopScheduleType.NO_SCHEDULE:
            # THERE IS NO SCHEDULE. DO NOT DO ANYTHING.
            return self._schedule_db.get_empty_schedule(day_of_week)

        schedules_dict = schedules.create_schedule({
            "day_of_week": day_of_week.value,
            "idea_session_id": idea_session_id,
            "idea_session_owner": idea_session_owner,
            "schedule_type": schedule.schedule_type.value,
            "start_up_time": schedule.start_up_time,
            "shut_down_time": schedule.shut_down_time
        })
        return self._schedule_db.convert_db_dict_to_schedule_object(schedules_dict)

    def _create_or_update_schedule_for_session_for_day_of_week(self, day_of_week: DayOfWeek, current_schedule: VirtualDesktopSchedule, new_schedule: VirtualDesktopSchedule, idea_session_id: str, idea_session_owner: str) -> VirtualDesktopSchedule:
        self._logger.debug(f'day_of_week: {day_of_week}, current_schedule: {current_schedule}, new_schedule: {new_schedule}, idea_session_id: {idea_session_id}, idea_session_owner: {idea_session_owner}')

        if Utils.is_empty(current_schedule):
            current_schedule = self._schedule_db.get_empty_schedule(day_of_week)

        if Utils.is_empty(new_schedule):
            return current_schedule
                
        if current_schedule.schedule_type == new_schedule.schedule_type and new_schedule.schedule_type != VirtualDesktopScheduleType.CUSTOM_SCHEDULE:
            self._logger.debug(f'Same schedule type, no need to update schedule')
            return current_schedule
        
        if current_schedule.schedule_type == VirtualDesktopScheduleType.CUSTOM_SCHEDULE and new_schedule.schedule_type == VirtualDesktopScheduleType.CUSTOM_SCHEDULE:
            self._logger.debug(f'Checking for custom schedule changes')
            if current_schedule.start_up_time == new_schedule.start_up_time and current_schedule.shut_down_time == new_schedule.shut_down_time:
                self._logger.debug(f'Same custom schedule, no need to update schedule')
                return current_schedule

        self._delete_schedule(current_schedule)
        new_schedule = self._create_schedule_for_day_of_week(day_of_week, new_schedule, idea_session_id, idea_session_owner)

        return new_schedule

    def update_schedule_for_session(self, new_schedules: VirtualDesktopWeekSchedule, session: VirtualDesktopSession) -> VirtualDesktopSession:
            
        if Utils.is_empty(session.schedule):
            session.schedule = VirtualDesktopWeekSchedule()

        session.schedule.monday = self._create_or_update_schedule_for_session_for_day_of_week(
            day_of_week=DayOfWeek.MONDAY,
            current_schedule=session.schedule.monday,
            new_schedule=new_schedules.monday,
            idea_session_id=session.idea_session_id,
            idea_session_owner=session.owner
        )

        session.schedule.tuesday = self._create_or_update_schedule_for_session_for_day_of_week(
            day_of_week=DayOfWeek.TUESDAY,
            current_schedule=session.schedule.tuesday,
            new_schedule=new_schedules.tuesday,
            idea_session_id=session.idea_session_id,
            idea_session_owner=session.owner
        )

        session.schedule.wednesday = self._create_or_update_schedule_for_session_for_day_of_week(
            day_of_week=DayOfWeek.WEDNESDAY,
            current_schedule=session.schedule.wednesday,
            new_schedule=new_schedules.wednesday,
            idea_session_id=session.idea_session_id,
            idea_session_owner=session.owner
        )

        session.schedule.thursday = self._create_or_update_schedule_for_session_for_day_of_week(
            day_of_week=DayOfWeek.THURSDAY,
            current_schedule=session.schedule.thursday,
            new_schedule=new_schedules.thursday,
            idea_session_id=session.idea_session_id,
            idea_session_owner=session.owner
        )

        session.schedule.friday = self._create_or_update_schedule_for_session_for_day_of_week(
            day_of_week=DayOfWeek.FRIDAY,
            current_schedule=session.schedule.friday,
            new_schedule=new_schedules.friday,
            idea_session_id=session.idea_session_id,
            idea_session_owner=session.owner
        )

        session.schedule.saturday = self._create_or_update_schedule_for_session_for_day_of_week(
            day_of_week=DayOfWeek.SATURDAY,
            current_schedule=session.schedule.saturday,
            new_schedule=new_schedules.saturday,
            idea_session_id=session.idea_session_id,
            idea_session_owner=session.owner
        )

        session.schedule.sunday = self._create_or_update_schedule_for_session_for_day_of_week(
            day_of_week=DayOfWeek.SUNDAY,
            current_schedule=session.schedule.sunday,
            new_schedule=new_schedules.sunday,
            idea_session_id=session.idea_session_id,
            idea_session_owner=session.owner
        )

        return session

    def delete_schedules_for_session(self, session: VirtualDesktopSession):
        if Utils.is_empty(session.schedule):
            return

        self._delete_schedule(schedule=session.schedule.monday)
        self._delete_schedule(schedule=session.schedule.tuesday)
        self._delete_schedule(schedule=session.schedule.wednesday)
        self._delete_schedule(schedule=session.schedule.thursday)
        self._delete_schedule(schedule=session.schedule.friday)
        self._delete_schedule(schedule=session.schedule.saturday)
        self._delete_schedule(schedule=session.schedule.sunday)

    def trigger_schedule(self, event_time: time, schedule: VirtualDesktopSchedule):
        if schedule.schedule_type == VirtualDesktopScheduleType.NO_SCHEDULE:
            pass

        should_resume = False
        should_stop = False

        start_up_time = schedule.start_up_time.split(":")
        shut_down_time = schedule.shut_down_time.split(":")

        start_up_time = DateTimeUtils.to_time_object(hours=int(start_up_time[0]), minutes=int(start_up_time[1]))
        start_up_time_with_delta = (datetime.combine(date.today(), start_up_time) + timedelta(minutes=30)).time()
        shut_down_time = DateTimeUtils.to_time_object(hours=int(shut_down_time[0]), minutes=int(shut_down_time[1]))
        shut_down_time_with_delta = (datetime.combine(date.today(), shut_down_time) + timedelta(minutes=30)).time()

        if (event_time >= start_up_time) and (event_time < shut_down_time) and (event_time < start_up_time_with_delta):
            # Schedule events are expected to be sent every 30 minutes. Only the event that is closest to the start-up time should take effect.
            # This avoids the schedule to resume the VDIs that are stopped manually or automatically.
            # START SESSION
            should_resume = True
        elif (event_time >= shut_down_time) and (event_time < shut_down_time_with_delta):
            # Only the event that is closest to the shut-down time should take effect.
            # This avoids the schedule to stop the VDIs that are started manually.
            # STOP SESSION
            should_stop = True
        else:
            pass

        if not should_resume and not should_stop:
            # No Action to take.
            return

        if should_stop:
            self._events_utils.publish_idea_session_scheduled_stop_event(
                idea_session_id=schedule.idea_session_id,
                idea_session_owner=schedule.idea_session_owner
            )
        elif should_resume:
            self._events_utils.publish_idea_session_scheduled_resume_event(
                idea_session_id=schedule.idea_session_id,
                idea_session_owner=schedule.idea_session_owner
            )