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
from logging import Logger

import ideavirtualdesktopcontroller
from ideavirtualdesktopcontroller.app.app_protocols import VirtualDesktopNotifiableDBProtocol
from ideavirtualdesktopcontroller.app.clients.events_client.events_client import VirtualDesktopEvent, VirtualDesktopEventType


class VirtualDesktopNotifiableDB(VirtualDesktopNotifiableDBProtocol):
    def __init__(self, context: ideavirtualdesktopcontroller.AppContext, table_name: str, logger: Logger):
        self.context = context
        self._logger = logger
        self._table_name = table_name
        self.sqs_client = self.context.aws().sqs()

    def trigger_delete_event(self, hash_key: str, range_key: str, deleted_entry: dict):
        self.context.events_client.publish_event(
            event=VirtualDesktopEvent(
                event_group_id=f'{hash_key}-{range_key}',
                event_type=VirtualDesktopEventType.DB_ENTRY_DELETED_EVENT,
                detail={
                    'hash_key': hash_key,
                    'range_key': range_key,
                    'deleted_value': deleted_entry,
                    'table_name': self._table_name
                }
            )
        )

    def trigger_create_event(self, hash_key: str, range_key: str, new_entry: dict):
        self.context.events_client.publish_event(
            event=VirtualDesktopEvent(
                event_group_id=f'{hash_key}-{range_key}',
                event_type=VirtualDesktopEventType.DB_ENTRY_CREATED_EVENT,
                detail={
                    'hash_key': hash_key,
                    'range_key': range_key,
                    'new_value': new_entry,
                    'table_name': self._table_name
                }
            )
        )

    def trigger_update_event(self, hash_key: str, range_key: str, old_entry: dict, new_entry: dict):
        self.context.events_client.publish_event(
            event=VirtualDesktopEvent(
                event_group_id=f'{hash_key}-{range_key}',
                event_type=VirtualDesktopEventType.DB_ENTRY_UPDATED_EVENT,
                detail={
                    'hash_key': hash_key,
                    'range_key': range_key,
                    'old_value': old_entry,
                    'new_value': new_entry,
                    'table_name': self._table_name
                }
            )
        )
