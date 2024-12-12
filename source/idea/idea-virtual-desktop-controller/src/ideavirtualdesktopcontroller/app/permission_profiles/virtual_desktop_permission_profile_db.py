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
from typing import Dict, Optional, List

import yaml

import ideavirtualdesktopcontroller
from ideadatamodel import exceptions, VirtualDesktopPermissionProfile, ListPermissionProfilesRequest, ListPermissionProfilesResponse, SocaPaginator, VirtualDesktopPermission
from ideasdk.utils import Utils
from ideavirtualdesktopcontroller.app.permission_profiles import constants as permission_profiles_constants
from ideavirtualdesktopcontroller.app.virtual_desktop_notifiable_db import VirtualDesktopNotifiableDB


class VirtualDesktopPermissionProfileDB(VirtualDesktopNotifiableDB):

    def __init__(self, context: ideavirtualdesktopcontroller.AppContext):
        self.context = context
        self._logger = self.context.logger('virtual-desktop-permission-profile-db')
        self._table_obj = None
        self.BASE_PERMISSIONS_CONFIG_FILE = f'{self.context.get_resources_dir()}/permission-config.yaml'
        self.BASE_PERMISSION_PROFILE_CONFIG_FILE = f'{self.context.get_resources_dir()}/base-permission-profile-config.yaml'
        self._permission_types: List[VirtualDesktopPermission] = []
        self._load_permission_types()
        self._ddb_client = self.context.aws().dynamodb_table()
        super().__init__(context, self.table_name, self._logger)

    @property
    def _table(self):
        if Utils.is_empty(self._table_obj):
            self._table_obj = self._ddb_client.Table(self.table_name)
        return self._table_obj

    @property
    def table_name(self) -> str:
        return f'{self.context.cluster_name()}.{self.context.module_id()}.controller.permission-profiles'

    @property
    def permission_types(self) -> List[VirtualDesktopPermission]:
        return self._permission_types

    def _load_permission_types(self):
        with open(self.BASE_PERMISSIONS_CONFIG_FILE, 'r') as f:
            permissions_config = yaml.safe_load(f)

        if Utils.is_empty(permissions_config):
            self._logger.error(f'{self.BASE_PERMISSIONS_CONFIG_FILE} file is empty. Returning')
            return

        for permission_key in permissions_config:
            self._logger.debug(f'Loading {permission_key} from config')
            self._permission_types.append(VirtualDesktopPermission(
                key=permission_key,
                name=permissions_config.get(permission_key).get('name'),
                description=permissions_config.get(permission_key).get('description'),
                enabled=False
            ))

    def convert_permission_profile_object_to_db_dict(self, permission_profile: VirtualDesktopPermissionProfile) -> Dict:
        db_dict = {
            permission_profiles_constants.PERMISSION_PROFILE_DB_HASH_KEY: permission_profile.profile_id,
            permission_profiles_constants.PERMISSION_PROFILE_DB_TITLE_KEY: permission_profile.title,
            permission_profiles_constants.PERMISSION_PROFILE_DB_DESCRIPTION_KEY: permission_profile.description,
            permission_profiles_constants.PERMISSION_PROFILE_DB_CREATED_ON_KEY: Utils.to_milliseconds(permission_profile.created_on),
            permission_profiles_constants.PERMISSION_PROFILE_DB_UPDATED_ON_KEY: Utils.to_milliseconds(permission_profile.updated_on)
        }

        for permission_type in self.permission_types:
            db_dict[permission_type.key] = False
            permission_entry = permission_profile.get_permission(permission_type.key)
            if Utils.is_not_empty(permission_entry):
                db_dict[permission_type.key] = permission_entry.enabled

        return db_dict

    def convert_db_dict_to_permission_profile_object(self, db_dict: Dict) -> Optional[VirtualDesktopPermissionProfile]:
        if Utils.is_empty(db_dict):
            return None

        permission_profile = VirtualDesktopPermissionProfile(
            profile_id=Utils.get_value_as_string(permission_profiles_constants.PERMISSION_PROFILE_DB_HASH_KEY, db_dict, ''),
            title=Utils.get_value_as_string(permission_profiles_constants.PERMISSION_PROFILE_DB_TITLE_KEY, db_dict, ''),
            description=Utils.get_value_as_string(permission_profiles_constants.PERMISSION_PROFILE_DB_DESCRIPTION_KEY, db_dict, ''),
            permissions=[],
            created_on=Utils.to_datetime(Utils.get_value_as_int(permission_profiles_constants.PERMISSION_PROFILE_DB_CREATED_ON_KEY, db_dict, 0)),
            updated_on=Utils.to_datetime(Utils.get_value_as_int(permission_profiles_constants.PERMISSION_PROFILE_DB_UPDATED_ON_KEY, db_dict, 0)),
        )

        for permission_type in self.permission_types:
            permission_profile.permissions.append(VirtualDesktopPermission(
                key=permission_type.key,
                name=permission_type.name,
                description=permission_type.description,
                enabled=Utils.get_value_as_bool(permission_type.key, db_dict, False)
            ))

        return permission_profile

    def update(self, permission_profile: VirtualDesktopPermissionProfile) -> VirtualDesktopPermissionProfile:
        db_entry = self.convert_permission_profile_object_to_db_dict(permission_profile)
        db_entry[permission_profiles_constants.PERMISSION_PROFILE_DB_UPDATED_ON_KEY] = Utils.current_time_ms()
        update_expression_tokens = []
        expression_attr_names = {}
        expression_attr_values = {}

        for key, value in db_entry.items():
            if key in {permission_profiles_constants.PERMISSION_PROFILE_DB_HASH_KEY, permission_profiles_constants.PERMISSION_PROFILE_DB_CREATED_ON_KEY}:
                continue
            update_expression_tokens.append(f'#{key} = :{key}')
            expression_attr_names[f'#{key}'] = key
            expression_attr_values[f':{key}'] = value

        result = self._table.update_item(
            Key={
                permission_profiles_constants.PERMISSION_PROFILE_DB_HASH_KEY: db_entry[permission_profiles_constants.PERMISSION_PROFILE_DB_HASH_KEY],
            },
            UpdateExpression='SET ' + ', '.join(update_expression_tokens),
            ExpressionAttributeNames=expression_attr_names,
            ExpressionAttributeValues=expression_attr_values,
            ReturnValues='ALL_OLD'
        )

        old_db_entry = Utils.get_value_as_dict('Attributes', result, {})
        self.trigger_update_event(db_entry[permission_profiles_constants.PERMISSION_PROFILE_DB_HASH_KEY], '', old_entry=old_db_entry, new_entry=db_entry)
        return self.convert_db_dict_to_permission_profile_object(db_entry)

    def list(self, request: ListPermissionProfilesRequest) -> ListPermissionProfilesResponse:
        list_request = {}
        if Utils.is_not_empty(request.cursor):
            last_evaluated_key = Utils.from_json(Utils.base64_decode(request.cursor))
            if Utils.is_not_empty(last_evaluated_key):
                list_request['ExclusiveStartKey'] = last_evaluated_key

        list_filter = None
        if Utils.is_not_empty(request.filters):
            list_filter = {}
            for filter_ in request.filters:
                if filter_.eq is not None:
                    list_filter[filter_.key] = {'AttributeValueList': [filter_.eq], 'ComparisonOperator': 'EQ'}
                if filter_.like is not None:
                    list_filter[filter_.key] = {'AttributeValueList': [filter_.like], 'ComparisonOperator': 'CONTAINS'}
        if list_filter is not None:
            list_request['ScanFilter'] = list_filter

        list_result = self._table.scan(**list_request)
        profile_entries = Utils.get_value_as_list('Items', list_result, [])
        result = []
        for profile in profile_entries:
            result.append(self.convert_db_dict_to_permission_profile_object(profile))

        response_cursor = None
        last_evaluated_key = Utils.get_any_value('LastEvaluatedKey', list_result)
        if last_evaluated_key is not None:
            response_cursor = Utils.base64_encode(Utils.to_json(last_evaluated_key))

        return ListPermissionProfilesResponse(
            listing=result,
            paginator=SocaPaginator(
                cursor=response_cursor
            )
        )

    def delete(self, profile_name: str):
        if Utils.is_empty(profile_name):
            self._logger.error(f'invalid values for profile_name: {profile_name}. Idempotent delete complete.')
            return

        try:
            result = self._table.delete_item(
                Key={
                    permission_profiles_constants.PERMISSION_PROFILE_DB_HASH_KEY: profile_name
                },
                ReturnValues='ALL_OLD'
            )
            old_db_entry = Utils.get_value_as_dict('Attributes', result, {})
            self.trigger_delete_event(old_db_entry[permission_profiles_constants.PERMISSION_PROFILE_DB_HASH_KEY], '', deleted_entry=old_db_entry)
        except Exception as e:
            self._logger.error(e)
