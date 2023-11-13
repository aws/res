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
from typing import Optional, Union, Dict

import ideavirtualdesktopcontroller
from ideadatamodel import exceptions
from ideasdk.utils import Utils
from ideavirtualdesktopcontroller.app.ssm_commands import constants as ssm_commands_constants


class VirtualDesktopSSMCommandType(str, Enum):
    RESUME_SESSION = 'RESUME_SESSION'
    CPU_UTILIZATION_CHECK_STOP_SCHEDULED_SESSION = 'CPU_UTILIZATION_CHECK_STOP_SCHEDULED_SESSION'
    WINDOWS_ENABLE_USERDATA_EXECUTION = 'WINDOWS_ENABLE_USERDATA_EXECUTION'
    WINDOWS_DISABLE_USERDATA_EXECUTION = 'WINDOWS_DISABLE_USERDATA_EXECUTION'


class VirtualDesktopSSMCommand:
    command_id: Optional[str]
    command_type: Optional[VirtualDesktopSSMCommandType]
    additional_payload: Optional[Dict]

    def __init__(self, command_id: Optional[str], command_type: Optional[VirtualDesktopSSMCommandType], additional_payload: Optional[Dict]):
        self.command_id = command_id
        self.command_type = command_type
        self.additional_payload = additional_payload


class VirtualDesktopSSMCommandsDB:
    def __init__(self, context: ideavirtualdesktopcontroller.AppContext):
        self.context = context
        self._logger = self.context.logger('virtual-desktop-ssm-commands-db')
        self._table_obj = None
        self._ddb_client = self.context.aws().dynamodb_table()

    def initialize(self):
        exists = self.context.aws_util().dynamodb_check_table_exists(self.table_name, True)
        if not exists:
            self.context.aws_util().dynamodb_create_table(
                create_table_request={
                    'TableName': self.table_name,
                    'AttributeDefinitions': [
                        {
                            'AttributeName': ssm_commands_constants.SSM_COMMANDS_DB_HASH_KEY,
                            'AttributeType': 'S'
                        }
                    ],
                    'KeySchema': [
                        {
                            'AttributeName': ssm_commands_constants.SSM_COMMANDS_DB_HASH_KEY,
                            'KeyType': 'HASH'
                        }
                    ],
                    'BillingMode': 'PAY_PER_REQUEST'
                },
                wait=True
            )

    @property
    def _table(self):
        if Utils.is_empty(self._table_obj):
            self._table_obj = self._ddb_client.Table(self.table_name)
        return self._table_obj

    @property
    def table_name(self) -> str:
        return f'{self.context.cluster_name()}.{self.context.module_id()}.controller.ssm-commands'

    @staticmethod
    def _convert_db_model_to_db_dict(db_model: VirtualDesktopSSMCommand) -> dict:
        return {
            ssm_commands_constants.SSM_COMMANDS_DB_HASH_KEY: db_model.command_id,
            ssm_commands_constants.SSM_COMMANDS_DB_COMMAND_TYPE_KEY: db_model.command_type,
            ssm_commands_constants.SSM_COMMANDS_DB_COMMAND_ADDITIONAL_PAYLOAD_KEY: db_model.additional_payload
        }

    @staticmethod
    def _convert_db_dict_to_db_model(db_entry: dict) -> Optional[VirtualDesktopSSMCommand]:
        if Utils.is_empty(db_entry):
            return None

        return VirtualDesktopSSMCommand(
            command_id=Utils.get_value_as_int(ssm_commands_constants.SSM_COMMANDS_DB_HASH_KEY, db_entry, 0),
            command_type=VirtualDesktopSSMCommandType(Utils.get_value_as_string(ssm_commands_constants.SSM_COMMANDS_DB_COMMAND_TYPE_KEY, db_entry, None)),
            additional_payload=Utils.get_value_as_dict(ssm_commands_constants.SSM_COMMANDS_DB_COMMAND_ADDITIONAL_PAYLOAD_KEY, db_entry, {}),
        )

    def create(self, db_model: VirtualDesktopSSMCommand) -> VirtualDesktopSSMCommand:
        db_entry = self._convert_db_model_to_db_dict(db_model)
        self._table.put_item(
            Item=db_entry
        )
        return self._convert_db_dict_to_db_model(db_entry)

    def get(self, command_id: str) -> Union[VirtualDesktopSSMCommand, None]:
        if Utils.is_empty(command_id):
            raise exceptions.invalid_params('command_id required')

        try:
            result = self._table.get_item(
                Key={
                    ssm_commands_constants.SSM_COMMANDS_DB_HASH_KEY: command_id
                }
            )
            db_entry = Utils.get_value_as_dict('Item', result)
        except self._ddb_client.exceptions.ResourceNotFoundException as _:
            # in this case we simply need to return None since the resource was not found
            db_entry = None
        except Exception as e:
            self._logger.exception(e)
            raise e

        return self._convert_db_dict_to_db_model(db_entry)

    def delete(self, command_id: Optional[str]):
        self._table.delete_item(
            Key={
                ssm_commands_constants.SSM_COMMANDS_DB_HASH_KEY: command_id,
            }
        )
