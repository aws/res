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


import ideavirtualdesktopcontroller
from ideadatamodel import (
    exceptions,
    VirtualDesktopServer
)
from ideasdk.utils import Utils
from ideavirtualdesktopcontroller.app.virtual_desktop_notifiable_db import VirtualDesktopNotifiableDB
from ideavirtualdesktopcontroller.app.servers import constants as servers_constants

from typing import Dict, Optional


class VirtualDesktopServerDB(VirtualDesktopNotifiableDB):
    def __init__(self, context: ideavirtualdesktopcontroller.AppContext):
        self.context = context
        self._logger = self.context.logger('virtual-desktop-server-db')
        self._table_obj = None
        self._ddb_client = self.context.aws().dynamodb_table()
        super().__init__(context, self.table_name, self._logger)

    @property
    def _table(self):
        if Utils.is_empty(self._table_obj):
            self._table_obj = self._ddb_client.Table(self.table_name)
        return self._table_obj

    @property
    def table_name(self) -> str:
        return f'{self.context.cluster_name()}.{self.context.module_id()}.controller.servers'

    def initialize(self):
        exists = self.context.aws_util().dynamodb_check_table_exists(self.table_name, True)
        if not exists:
            self.context.aws_util().dynamodb_create_table(
                create_table_request={
                    'TableName': self.table_name,
                    'AttributeDefinitions': [
                        {
                            'AttributeName': servers_constants.DCV_HOST_DB_HASH_KEY,
                            'AttributeType': 'S'
                        }
                    ],
                    'KeySchema': [
                        {
                            'AttributeName': servers_constants.DCV_HOST_DB_HASH_KEY,
                            'KeyType': 'HASH'
                        }
                    ],
                    'BillingMode': 'PAY_PER_REQUEST'
                },
                wait=True
            )

    @staticmethod
    def convert_server_object_to_db_dict(server: VirtualDesktopServer) -> Dict:
        if Utils.is_empty(server):
            return {}

        return {
            servers_constants.DCV_HOST_DB_HASH_KEY: server.instance_id,
            servers_constants.DCV_HOST_DB_INSTANCE_TYPE_KEY: server.instance_type,
            servers_constants.DCV_HOST_DB_IDEA_SESSION_ID_KEY: server.idea_sesssion_id,
            servers_constants.DCV_HOST_DB_IDEA_SESSION_OWNER_KEY: server.idea_session_owner,
            servers_constants.DCV_HOST_DB_STATE_KEY: server.state,
            servers_constants.DCV_HOST_DB_LOCKED_KEY: False if Utils.is_empty(server.locked) else server.locked
        }

    @staticmethod
    def convert_db_entry_to_server_object(db_entry: dict) -> Optional[VirtualDesktopServer]:
        if Utils.is_empty(db_entry):
            return None

        return VirtualDesktopServer(
            instance_id=Utils.get_value_as_string(servers_constants.DCV_HOST_DB_HASH_KEY, db_entry),
            instance_type=Utils.get_value_as_string(servers_constants.DCV_HOST_DB_INSTANCE_TYPE_KEY, db_entry),
            idea_sesssion_id=Utils.get_value_as_string(servers_constants.DCV_HOST_DB_IDEA_SESSION_ID_KEY, db_entry),
            idea_session_owner=Utils.get_value_as_string(servers_constants.DCV_HOST_DB_IDEA_SESSION_OWNER_KEY, db_entry),
            locked=Utils.get_value_as_bool(servers_constants.DCV_HOST_DB_LOCKED_KEY, db_entry, False)
        )

    def create(self, server: VirtualDesktopServer, idea_session_id: str, idea_session_owner: str) -> VirtualDesktopServer:
        db_entry = self.convert_server_object_to_db_dict(server)
        db_entry[servers_constants.DCV_HOST_DB_IDEA_SESSION_ID_KEY] = idea_session_id
        db_entry[servers_constants.DCV_HOST_DB_IDEA_SESSION_OWNER_KEY] = idea_session_owner
        db_entry[servers_constants.DCV_HOST_DB_CREATED_ON_KEY] = Utils.current_time_ms()
        db_entry[servers_constants.DCV_HOST_DB_UPDATED_ON_KEY] = Utils.current_time_ms()
        db_entry[servers_constants.DCV_HOST_DB_STATE_KEY] = 'CREATED'
        self._table.put_item(
            Item=db_entry
        )
        self.trigger_create_event(db_entry[servers_constants.DCV_HOST_DB_HASH_KEY], '', new_entry=db_entry)
        return self.convert_db_entry_to_server_object(db_entry)

    def get(self, instance_id: str) -> Optional[VirtualDesktopServer]:
        if Utils.is_empty(instance_id):
            raise exceptions.invalid_params('instance_id is required')

        try:
            result = self._table.get_item(
                Key={
                    servers_constants.DCV_HOST_DB_HASH_KEY: instance_id
                }
            )
            db_dict = Utils.get_value_as_dict('Item', result)
        except self._ddb_client.exceptions.ResourceNotFoundException as _:
            # in this case we simply need to return None since the resource was not found
            return None
        except Exception as e:
            self._logger.exception(e)
            raise e

        return self.convert_db_entry_to_server_object(db_dict)

    def update(self, server: VirtualDesktopServer) -> VirtualDesktopServer:
        db_entry = self.convert_server_object_to_db_dict(server)
        db_entry[servers_constants.DCV_HOST_DB_UPDATED_ON_KEY] = Utils.current_time_ms()
        update_expression_tokens = []
        expression_attr_names = {}
        expression_attr_values = {}

        for key, value in db_entry.items():
            if key in {servers_constants.DCV_HOST_DB_HASH_KEY, servers_constants.DCV_HOST_DB_CREATED_ON_KEY}:
                continue
            update_expression_tokens.append(f'#{key} = :{key}')
            expression_attr_names[f'#{key}'] = key
            expression_attr_values[f':{key}'] = value

        result = self._table.update_item(
            Key={
                servers_constants.DCV_HOST_DB_HASH_KEY: db_entry[servers_constants.DCV_HOST_DB_HASH_KEY]
            },
            UpdateExpression='SET ' + ', '.join(update_expression_tokens),
            ExpressionAttributeNames=expression_attr_names,
            ExpressionAttributeValues=expression_attr_values,
            ReturnValues='ALL_OLD'
        )

        old_db_entry = Utils.get_value_as_dict('Attributes', result, {})
        self.trigger_update_event(db_entry[servers_constants.DCV_HOST_DB_HASH_KEY], '', old_entry=old_db_entry, new_entry=db_entry)
        return self.convert_db_entry_to_server_object(db_entry)

    def delete(self, dcv_host: VirtualDesktopServer):
        if Utils.is_empty(dcv_host.instance_id):
            raise exceptions.invalid_params('instance_id is required')

        result = self._table.delete_item(
            Key={
                servers_constants.DCV_HOST_DB_HASH_KEY: dcv_host.instance_id
            },
            ReturnValues='ALL_OLD'
        )
        old_db_entry = Utils.get_value_as_dict('Attributes', result, {})
        self.trigger_delete_event(old_db_entry[servers_constants.DCV_HOST_DB_HASH_KEY], '', deleted_entry=old_db_entry)
