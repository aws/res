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
from typing import Optional

import ideavirtualdesktopcontroller
from ideadatamodel import DayOfWeek

from ideasdk.utils import DateTimeUtils, Utils
from ideavirtualdesktopcontroller.app.clients.events_client.events_client import VirtualDesktopEvent
from ideavirtualdesktopcontroller.app.events.handlers.base_event_handler import BaseVirtualDesktopControllerEventHandler


class ScheduledEventHandler(BaseVirtualDesktopControllerEventHandler):

    def __init__(self, context: ideavirtualdesktopcontroller.AppContext):
        super().__init__(context, 'scheduled-event-handler')
        self.DAY_OF_WEEKS = [DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY, DayOfWeek.THURSDAY, DayOfWeek.FRIDAY, DayOfWeek.SATURDAY, DayOfWeek.SUNDAY]

    def handle_event(self, message_id: str, sender_id: str, event: VirtualDesktopEvent):
        if not self.is_sender_scheduled_event_lambda_role(sender_id):
            raise self.message_source_validation_failed(f'Corrupted sender_id: {sender_id}. Ignoring message')

        event_time = Utils.get_value_as_string('time', event.detail, '')
        if Utils.is_empty(event_time):
            self.log_error(message_id=message_id, message=f'event time is {event_time}. Invalid message. Returning.')
            return

        # The time in the event is UTC because AWS always sends events in UTC Time zone,
        # hence we need to convert it to cluster time zone.
        event_time = DateTimeUtils.to_datetime_in_timezone(event_time, self.context.cluster_timezone())
        self.log_info(message_id=message_id, message=f'Handling scheduled event at time {event_time} in {self.context.cluster_timezone()}')
        day_of_week = self.DAY_OF_WEEKS[event_time.weekday()]
        schedule_db_entries = self.schedule_db.get_schedules_for_day_of_week(day_of_week)
        for schedule_db_entry in schedule_db_entries:
            self.log_info(message_id=message_id, message=f'Triggering schedule {schedule_db_entry.schedule_id}')
            self.schedule_utils.trigger_schedule(event_time.time(), schedule_db_entry)

        cursor: Optional[str] = None
        loop_break = False
        sessions_info = set()
        while not loop_break:
            permissions, cursor = self.session_permissions_db.list_all_from_db(cursor)
            for permission in permissions:
                if event_time >= permission.expiry_date:
                    self.log_info(message_id=message_id, message=f'Session Permission for session {permission.idea_session_id} has expired. Expiry Date {permission.expiry_date}. Deleting Permission')
                    sessions_info.add((permission.idea_session_id, permission.idea_session_owner))
                    self.session_permissions_db.delete(permission)

            loop_break = Utils.is_empty(cursor)

        for session_info in sessions_info:
            self.events_utils.publish_enforce_session_permissions_event(
                idea_session_id=session_info[0],
                idea_session_owner=session_info[1],
            )
