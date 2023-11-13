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
from typing import List, Dict, Optional

import ideavirtualdesktopcontroller
from ideadatamodel import VirtualDesktopSchedule, DayOfWeek, VirtualDesktopScheduleType
from ideasdk.utils import Utils
from ideavirtualdesktopcontroller.app.virtual_desktop_notifiable_db import VirtualDesktopNotifiableDB
from ideavirtualdesktopcontroller.app.schedules import constants as schedules_constants


class VirtualDesktopScheduleDB(VirtualDesktopNotifiableDB):
    def __init__(self, context: ideavirtualdesktopcontroller.AppContext):
        self.context = context
        self._table_obj = None
        self._logger = self.context.logger('virtual-desktop-schedule-db')
        self._ddb_client = self.context.aws().dynamodb_table()
        super().__init__(context, self.table_name, self._logger)

    @property
    def _table(self):
        if Utils.is_empty(self._table_obj):
            self._table_obj = self._ddb_client.Table(self.table_name)
        return self._table_obj

    @property
    def table_name(self) -> str:
        return f'{self.context.cluster_name()}.{self.context.module_id()}.controller.schedules'

    def initialize(self):
        exists = self.context.aws_util().dynamodb_check_table_exists(self.table_name, True)
        if not exists:
            self.context.aws_util().dynamodb_create_table(
                create_table_request={
                    'TableName': self.table_name,
                    'AttributeDefinitions': [
                        {
                            'AttributeName': schedules_constants.SCHEDULE_DB_HASH_KEY,
                            'AttributeType': 'S'
                        },
                        {
                            'AttributeName': schedules_constants.SCHEDULE_DB_RANGE_KEY,
                            'AttributeType': 'S'
                        }
                    ],
                    'KeySchema': [
                        {
                            'AttributeName': schedules_constants.SCHEDULE_DB_HASH_KEY,
                            'KeyType': 'HASH'
                        },
                        {
                            'AttributeName': schedules_constants.SCHEDULE_DB_RANGE_KEY,
                            'KeyType': 'RANGE'
                        }
                    ],
                    'BillingMode': 'PAY_PER_REQUEST'
                },
                wait=True
            )

    @staticmethod
    def get_empty_schedule(day_of_week: Optional[DayOfWeek] = None) -> VirtualDesktopSchedule:
        return VirtualDesktopSchedule(
            schedule_id='',
            day_of_week=day_of_week,
            schedule_type=VirtualDesktopScheduleType.NO_SCHEDULE
        )

    @staticmethod
    def convert_schedule_object_to_db_dict(schedule: VirtualDesktopSchedule) -> Dict:
        schedule_dict = {
            schedules_constants.SCHEDULE_DB_HASH_KEY: f'{schedule.day_of_week}',
            schedules_constants.SCHEDULE_DB_RANGE_KEY: schedule.schedule_id,
            schedules_constants.SCHEDULE_DB_IDEA_SESSION_ID_KEY: schedule.idea_session_id,
            schedules_constants.SCHEDULE_DB_IDEA_SESSION_OWNER_KEY: schedule.idea_session_owner,
            schedules_constants.SCHEDULE_DB_SCHEDULE_TYPE_KEY: schedule.schedule_type,
        }

        if schedule.schedule_type == VirtualDesktopScheduleType.CUSTOM_SCHEDULE:
            schedule_dict[schedules_constants.SCHEDULE_DB_START_UP_TIME_KEY] = schedule.start_up_time
            schedule_dict[schedules_constants.SCHEDULE_DB_SHUT_DOWN_TIME_KEY] = schedule.shut_down_time
        return schedule_dict

    def convert_db_dict_to_schedule_object(self, db_entry: Dict) -> VirtualDesktopSchedule:
        if Utils.is_empty(db_entry):
            return self.get_empty_schedule()

        schedule_id = Utils.get_value_as_string(schedules_constants.SCHEDULE_DB_SCHEDULE_ID_KEY, db_entry, None)
        if Utils.is_empty(schedule_id):
            return self.get_empty_schedule()

        schedule_type = VirtualDesktopScheduleType(Utils.get_value_as_string(schedules_constants.SCHEDULE_DB_SCHEDULE_TYPE_KEY, db_entry))
        start_up_time = Utils.get_value_as_string(schedules_constants.SCHEDULE_DB_START_UP_TIME_KEY, db_entry, None)
        shut_down_time = Utils.get_value_as_string(schedules_constants.SCHEDULE_DB_SHUT_DOWN_TIME_KEY, db_entry, None)

        if schedule_type == VirtualDesktopScheduleType.WORKING_HOURS:
            start_up_time = self.context.config().get_string('virtual-desktop-controller.dcv_session.working_hours.start_up_time', required=True)
            shut_down_time = self.context.config().get_string('virtual-desktop-controller.dcv_session.working_hours.shut_down_time', required=True)
        elif schedule_type == VirtualDesktopScheduleType.STOP_ALL_DAY:
            start_up_time = '23:59'
            shut_down_time = '00:00'
        elif schedule_type == VirtualDesktopScheduleType.START_ALL_DAY:
            start_up_time = '00:00'
            shut_down_time = '23:59'

        return VirtualDesktopSchedule(
            schedule_id=schedule_id,
            start_up_time=start_up_time,
            shut_down_time=shut_down_time,
            schedule_type=schedule_type,
            idea_session_owner=Utils.get_value_as_string(schedules_constants.SCHEDULE_DB_IDEA_SESSION_OWNER_KEY, db_entry),
            idea_session_id=Utils.get_value_as_string(schedules_constants.SCHEDULE_DB_IDEA_SESSION_ID_KEY, db_entry),
            day_of_week=Utils.get_value_as_string(schedules_constants.SCHEDULE_DB_HASH_KEY, db_entry),
        )

    def create(self, schedule: VirtualDesktopSchedule) -> VirtualDesktopSchedule:
        db_entry = self.convert_schedule_object_to_db_dict(schedule)
        db_entry[schedules_constants.SCHEDULE_DB_RANGE_KEY] = Utils.uuid()
        self._table.put_item(
            Item=db_entry
        )
        super().trigger_create_event(db_entry[schedules_constants.SCHEDULE_DB_HASH_KEY], db_entry[schedules_constants.SCHEDULE_DB_RANGE_KEY], new_entry=db_entry)
        return self.convert_db_dict_to_schedule_object(db_entry)

    def get(self, day_of_week: DayOfWeek, schedule_id: str) -> VirtualDesktopSchedule:
        if Utils.is_empty(day_of_week) or Utils.is_empty(schedule_id):
            self._logger.error(f'invalid {day_of_week} {schedule_id} combination. DB entry does\'nt exist, returning No Schedule')
            return self.get_empty_schedule(day_of_week)
        try:
            result = self._table.get_item(
                Key={
                    schedules_constants.SCHEDULE_DB_HASH_KEY: day_of_week,
                    schedules_constants.SCHEDULE_DB_RANGE_KEY: schedule_id
                }
            )
            schedule = Utils.get_value_as_dict('Item', result)
        except self._ddb_client.exceptions.ResourceNotFoundException as _:
            # in this case we simply need to return None since the resource was not found
            return self.get_empty_schedule(day_of_week)
        except Exception as e:
            self._logger.exception(e)
            raise e

        return self.convert_db_dict_to_schedule_object(schedule)

    def update(self, schedule: VirtualDesktopSchedule) -> VirtualDesktopSchedule:
        db_entry = self.convert_schedule_object_to_db_dict(schedule)
        update_expression_tokens = []
        expression_attr_names = {}
        expression_attr_values = {}

        for key, value in db_entry.items():
            if key in {schedules_constants.SCHEDULE_DB_HASH_KEY, schedules_constants.SCHEDULE_DB_RANGE_KEY}:
                continue

            update_expression_tokens.append(f'#{key} = :{key}')
            expression_attr_names[f'#{key}'] = key
            expression_attr_values[f':{key}'] = value

        result = self._table.update_item(
            Key={
                schedules_constants.SCHEDULE_DB_HASH_KEY: db_entry[schedules_constants.SCHEDULE_DB_HASH_KEY],
                schedules_constants.SCHEDULE_DB_RANGE_KEY: db_entry[schedules_constants.SCHEDULE_DB_RANGE_KEY]
            },
            UpdateExpression='SET ' + ', '.join(update_expression_tokens),
            ExpressionAttributeNames=expression_attr_names,
            ExpressionAttributeValues=expression_attr_values,
            ReturnValues='ALL_OLD'
        )

        old_db_entry = Utils.get_value_as_dict('Attributes', result, {})
        super().trigger_update_event(db_entry[schedules_constants.SCHEDULE_DB_HASH_KEY], db_entry[schedules_constants.SCHEDULE_DB_RANGE_KEY], old_entry=old_db_entry, new_entry=db_entry)
        return self.convert_db_dict_to_schedule_object(db_entry)

    def get_schedules_for_day_of_week(self, day_of_week: DayOfWeek) -> List[VirtualDesktopSchedule]:
        query_request = {
            'KeyConditions': {
                schedules_constants.SCHEDULE_DB_HASH_KEY: {
                    'AttributeValueList': [
                        day_of_week
                    ],
                    'ComparisonOperator': 'EQ'
                },
            }
        }
        query_result = self._table.query(**query_request)
        schedule_entries = Utils.get_value_as_list('Items', query_result, [])
        result: List[VirtualDesktopSchedule] = []
        for schedule in schedule_entries:
            result.append(self.convert_db_dict_to_schedule_object(schedule))

        return result

    def delete(self, schedule: VirtualDesktopSchedule):
        if Utils.is_empty(schedule):
            self._logger.info('Empty schedule object. Returning.')
            return

        result = self._table.delete_item(
            Key={
                schedules_constants.SCHEDULE_DB_HASH_KEY: f'{schedule.day_of_week}',
                schedules_constants.SCHEDULE_DB_RANGE_KEY: schedule.schedule_id
            },
            ReturnValues='ALL_OLD'
        )
        old_db_entry = Utils.get_value_as_dict('Attributes', result, {})
        super().trigger_delete_event(old_db_entry[schedules_constants.SCHEDULE_DB_HASH_KEY], old_db_entry[schedules_constants.SCHEDULE_DB_RANGE_KEY], deleted_entry=old_db_entry)
