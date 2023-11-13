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
from enum import Enum
from typing import Union, Optional, Dict

import ideavirtualdesktopcontroller
from ideadatamodel import exceptions
from ideasdk.utils import Utils
from ideavirtualdesktopcontroller.app.sessions import constants as sessions_constants


class VirtualDesktopSessionCounterType(str, Enum):
    DCV_SESSION_CREATION_REQUEST_ACCPETED_COUNTER = 'DCV_SESSION_CREATION_REQUEST_ACCPETED_COUNTER'
    DCV_SESSION_RESUMED_COUNTER = 'DCV_SESSION_RESUMED_COUNTER'
    VALIDATE_DCV_SESSION_CREATED_COUNTER = 'VALIDATE_DCV_SESSION_CREATED_COUNTER'


class VirtualDesktopSessionCounterDBModel:
    idea_session_id: Optional[str]
    counter_type: Optional[VirtualDesktopSessionCounterType]
    counter: Optional[int]

    def __init__(self, idea_session_id: Optional[str], counter_type: Optional[str], counter: Optional[int] = None):
        self.idea_session_id = idea_session_id
        self.counter_type = counter_type
        self.counter = counter


class VirtualDesktopSessionCounterDB:
    def __init__(self, context: ideavirtualdesktopcontroller.AppContext):
        self.context = context
        self._logger = self.context.logger('virtual-desktop-session-counter-db')
        self._table_obj = None
        self._ddb_client = self.context.aws().dynamodb_table()

    @property
    def _table(self):
        if Utils.is_empty(self._table_obj):
            self._table_obj = self._ddb_client.Table(self.table_name)
        return self._table_obj

    @property
    def table_name(self) -> str:
        return f'{self.context.cluster_name()}.{self.context.module_id()}.controller.user-sessions-counter'

    def initialize(self):
        exists = self.context.aws_util().dynamodb_check_table_exists(self.table_name, True)
        if not exists:
            self.context.aws_util().dynamodb_create_table(
                create_table_request={
                    'TableName': self.table_name,
                    'AttributeDefinitions': [
                        {
                            'AttributeName': sessions_constants.USER_SESSION_COUNTER_DB_HASH_KEY,
                            'AttributeType': 'S'
                        },
                        {
                            'AttributeName': sessions_constants.USER_SESSION_COUNTER_DB_RANGE_KEY,
                            'AttributeType': 'S'
                        },
                    ],
                    'KeySchema': [
                        {
                            'AttributeName': sessions_constants.USER_SESSION_COUNTER_DB_HASH_KEY,
                            'KeyType': 'HASH'
                        },
                        {
                            'AttributeName': sessions_constants.USER_SESSION_COUNTER_DB_RANGE_KEY,
                            'KeyType': 'RANGE'
                        }
                    ],
                    'BillingMode': 'PAY_PER_REQUEST'
                },
                wait=True
            )

    @staticmethod
    def _convert_session_counter_db_model_to_dict(db_model: VirtualDesktopSessionCounterDBModel) -> Dict:
        return {
            sessions_constants.USER_SESSION_COUNTER_DB_HASH_KEY: db_model.idea_session_id,
            sessions_constants.USER_SESSION_COUNTER_DB_RANGE_KEY: db_model.counter_type.name,
            sessions_constants.USER_SESSION_COUNTER_DB_COUNTER_KEY: db_model.counter
        }

    @staticmethod
    def _convert_session_counter_dict_to_db_model(db_entry: Dict) -> VirtualDesktopSessionCounterDBModel:
        return VirtualDesktopSessionCounterDBModel(
            idea_session_id=Utils.get_value_as_string(sessions_constants.USER_SESSION_COUNTER_DB_HASH_KEY, db_entry, ''),
            counter_type=VirtualDesktopSessionCounterType(Utils.get_value_as_string(sessions_constants.USER_SESSION_COUNTER_DB_RANGE_KEY, db_entry, '')),
            counter=Utils.get_value_as_int(sessions_constants.USER_SESSION_COUNTER_DB_COUNTER_KEY, db_entry, 0)
        )

    def create(self, db_model: VirtualDesktopSessionCounterDBModel) -> VirtualDesktopSessionCounterDBModel:
        db_entry = self._convert_session_counter_db_model_to_dict(db_model)
        self._table.put_item(
            Item=db_entry
        )
        return self._convert_session_counter_dict_to_db_model(db_entry)

    def get(self, idea_session_id: str, counter_type: VirtualDesktopSessionCounterType) -> Union[VirtualDesktopSessionCounterDBModel, None]:
        if Utils.is_empty(idea_session_id) or Utils.is_empty(counter_type):
            raise exceptions.invalid_params('idea_session_id and counter_type are required')

        try:
            result = self._table.get_item(
                Key={
                    sessions_constants.USER_SESSION_COUNTER_DB_HASH_KEY: idea_session_id,
                    sessions_constants.USER_SESSION_COUNTER_DB_RANGE_KEY: counter_type
                }
            )
            db_entry = Utils.get_value_as_dict('Item', result)
        except self._ddb_client.exceptions.ResourceNotFoundException as _:
            # in this case we simply need to return None since the resource was not found
            db_entry = None
        except Exception as e:
            self._logger.exception(e)
            raise e

        if Utils.is_empty(db_entry):
            db_entry = {
                sessions_constants.USER_SESSION_COUNTER_DB_HASH_KEY: idea_session_id,
                sessions_constants.USER_SESSION_COUNTER_DB_RANGE_KEY: counter_type.value
            }

        return self._convert_session_counter_dict_to_db_model(db_entry)

    def create_or_update(self, db_model: VirtualDesktopSessionCounterDBModel) -> VirtualDesktopSessionCounterDBModel:
        db_entry = self._convert_session_counter_db_model_to_dict(db_model)
        update_expression_tokens = []
        expression_attr_names = {}
        expression_attr_values = {}

        for key, value in db_entry.items():
            if key in {sessions_constants.USER_SESSION_COUNTER_DB_HASH_KEY, sessions_constants.USER_SESSION_COUNTER_DB_RANGE_KEY}:
                continue
            update_expression_tokens.append(f'#{key} = :{key}')
            expression_attr_names[f'#{key}'] = key
            expression_attr_values[f':{key}'] = value

        result = self._table.update_item(
            Key={
                sessions_constants.USER_SESSION_COUNTER_DB_HASH_KEY: db_entry[sessions_constants.USER_SESSION_COUNTER_DB_HASH_KEY],
                sessions_constants.USER_SESSION_COUNTER_DB_RANGE_KEY: db_entry[sessions_constants.USER_SESSION_COUNTER_DB_RANGE_KEY],
            },
            UpdateExpression='SET ' + ', '.join(update_expression_tokens),
            ExpressionAttributeNames=expression_attr_names,
            ExpressionAttributeValues=expression_attr_values,
            ReturnValues='ALL_NEW'
        )
        return self._convert_session_counter_dict_to_db_model(result['Attributes'])

    def delete(self, db_model: VirtualDesktopSessionCounterDBModel):
        self._table.delete_item(
            Key={
                sessions_constants.USER_SESSION_COUNTER_DB_HASH_KEY: db_model.idea_session_id,
                sessions_constants.USER_SESSION_COUNTER_DB_RANGE_KEY: db_model.counter_type.value,
            }
        )
