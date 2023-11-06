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

from datetime import time

import ideavirtualdesktopcontroller
from ideadatamodel import VirtualDesktopSession, DayOfWeek, VirtualDesktopSchedule, VirtualDesktopScheduleType, VirtualDesktopWeekSchedule
from ideasdk.utils import Utils, DateTimeUtils
from ideavirtualdesktopcontroller.app.events.events_utils import EventsUtils
from ideavirtualdesktopcontroller.app.schedules.virtual_desktop_schedule_db import VirtualDesktopScheduleDB


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

    def _is_same_schedule(self, schedule_a: VirtualDesktopSchedule, schedule_b: VirtualDesktopSchedule) -> bool:
        if Utils.is_empty(schedule_a) and Utils.is_empty(schedule_b):
            self._logger.debug('Both the schedules are emtpy and hence equivalent...')
            # both are empty.
            return True

        if (Utils.is_not_empty(schedule_a) and Utils.is_empty(schedule_b)) or (Utils.is_not_empty(schedule_b) and Utils.is_empty(schedule_a)):
            # exactly one is not empty.
            self._logger.debug('Exactly one schedule is empty and hence different...')
            return False

        # both are not empty
        if (schedule_a.schedule_type == schedule_b.schedule_type) and (
            schedule_a.schedule_type == VirtualDesktopScheduleType.STOP_ALL_DAY or schedule_a.schedule_type == VirtualDesktopScheduleType.START_ALL_DAY or schedule_a.schedule_type == VirtualDesktopScheduleType.NO_SCHEDULE or schedule_a.schedule_type == VirtualDesktopScheduleType.WORKING_HOURS):
            self._logger.debug('Both are not empty but are the same static schedule type...')
            return True

        if schedule_a.schedule_type == VirtualDesktopScheduleType.NO_SCHEDULE or schedule_b.schedule_type == VirtualDesktopScheduleType.NO_SCHEDULE:
            # at this point both do not have the same schedule type, but one is NO SCHEDULE for sure. They are different
            self._logger.debug('At least one of the schedules is NO_SCHEDULE and hence different...')
            return False

        return False

    def _delete_schedule(self, schedule: VirtualDesktopSchedule):
        if Utils.is_empty(schedule) or schedule.schedule_type == VirtualDesktopScheduleType.NO_SCHEDULE:
            self._logger.debug("No Schedule to delete. Returning")
            return

        if Utils.is_any_empty(schedule.schedule_id, schedule.day_of_week):
            return

        self._schedule_db.delete(schedule)

    def _create_schedule_for_day_of_week(self, day_of_week: DayOfWeek, schedule: VirtualDesktopSchedule, idea_session_id: str, idea_session_owner: str) -> VirtualDesktopSchedule:
        if schedule.schedule_type == VirtualDesktopScheduleType.NO_SCHEDULE:
            # THERE IS NO SCHEDULE. DO NOT DO ANYTHING.
            return self._schedule_db.get_empty_schedule(day_of_week)

        return self._schedule_db.create(
            VirtualDesktopSchedule(
                day_of_week=DayOfWeek(day_of_week),
                idea_session_id=idea_session_id,
                idea_session_owner=idea_session_owner,
                schedule_type=schedule.schedule_type,
                start_up_time=schedule.start_up_time,
                shut_down_time=schedule.shut_down_time,
            ))

    def _create_or_update_schedule_for_session_for_day_of_week(self, day_of_week: DayOfWeek, current_schedule: VirtualDesktopSchedule, new_schedule: VirtualDesktopSchedule, idea_session_id: str, idea_session_owner: str) -> VirtualDesktopSchedule:
        self._logger.debug(f'day_of_week: {day_of_week}, current_schedule: {current_schedule}, new_schedule: {new_schedule}, idea_session_id: {idea_session_id}, idea_session_owner: {idea_session_owner}')

        if Utils.is_empty(current_schedule):
            current_schedule = self._schedule_db.get_empty_schedule(day_of_week)

        if Utils.is_empty(new_schedule):
            self._logger.debug(f'No schedule provided for {day_of_week}, will leave it as is.')
            return current_schedule

        if self._is_same_schedule(new_schedule, current_schedule):
            self._logger.debug(f'Both schedules for {day_of_week} are the same. NO OP. Returning')
            return current_schedule

        create_new = False

        if new_schedule.schedule_type == VirtualDesktopScheduleType.NO_SCHEDULE:
            self._logger.info(f'no new schedule for {day_of_week}')
            create_new = False
            new_schedule = self._schedule_db.get_empty_schedule(day_of_week)
        elif Utils.is_empty(current_schedule) or current_schedule.schedule_type != new_schedule.schedule_type:
            self._logger.info(f'schedule types mismatch. Delete old, create new for {day_of_week}')
            create_new = True

        if Utils.is_not_empty(current_schedule) and (current_schedule.schedule_type != VirtualDesktopScheduleType.NO_SCHEDULE or Utils.is_not_empty(current_schedule.schedule_id)):
            self._delete_schedule(current_schedule)

        if create_new:
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
        should_resume = False
        should_stop = False
        working_hours_start_up_time = self.context.config().get_string('virtual-desktop-controller.dcv_session.working_hours.start_up_time', required=True)
        working_hours_shut_down_time = self.context.config().get_string('virtual-desktop-controller.dcv_session.working_hours.shut_down_time', required=True)

        if VirtualDesktopScheduleType[schedule.schedule_type] == VirtualDesktopScheduleType.STOP_ALL_DAY:
            should_stop = True
        elif VirtualDesktopScheduleType[schedule.schedule_type] == VirtualDesktopScheduleType.START_ALL_DAY:
            should_resume = True
        else:
            # CUSTOM OR WORKING HOURS
            if VirtualDesktopScheduleType[schedule.schedule_type] == VirtualDesktopScheduleType.WORKING_HOURS:
                start_up_time = working_hours_start_up_time.split(":")
                shut_down_time = working_hours_shut_down_time.split(":")
            else:
                # CUSTOM
                start_up_time = schedule.start_up_time.split(":")
                shut_down_time = schedule.shut_down_time.split(":")

            start_up_time = DateTimeUtils.to_time_object(hours=int(start_up_time[0]), minutes=int(shut_down_time[1]))
            shut_down_time = DateTimeUtils.to_time_object(hours=int(shut_down_time[0]), minutes=int(shut_down_time[1]))
            if event_time < start_up_time:
                # should we shut down a running session ?? or leave as is.
                pass
            elif (event_time >= start_up_time) and (event_time < shut_down_time):
                # START SESSION
                should_resume = True
            else:
                # event_time >= shut_down_time:
                # STOP SESSION
                should_stop = True

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
