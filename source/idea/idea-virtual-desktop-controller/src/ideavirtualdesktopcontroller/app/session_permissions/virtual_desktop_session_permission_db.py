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

from typing import Dict, List, Optional
from boto3.dynamodb.conditions import Key

import ideavirtualdesktopcontroller
from ideadatamodel import (
    exceptions,
    SocaSortBy,
    VirtualDesktopSessionPermission,
    VirtualDesktopBaseOS,
    VirtualDesktopSessionState,
    VirtualDesktopSessionType,
    VirtualDesktopPermissionProfile,
    VirtualDesktopSessionPermissionActorType,
    ListPermissionsRequest,
    ListPermissionsResponse,
    SocaPaginator
)
from ideadatamodel.common.common_model import SocaSortOrder
from ideasdk.aws.opensearch.opensearchable_db import OpenSearchableDB

from ideasdk.utils import Utils
from ideavirtualdesktopcontroller.app.session_permissions import constants as session_permissions_constants
from ideavirtualdesktopcontroller.app.virtual_desktop_notifiable_db import VirtualDesktopNotifiableDB


class VirtualDesktopSessionPermissionDB(VirtualDesktopNotifiableDB, OpenSearchableDB):
    DEFAULT_PAGE_SIZE = 10

    def __init__(self, context: ideavirtualdesktopcontroller.AppContext):
        self.context = context
        self._logger = self.context.logger('virtual-desktop-session-permissions-db')
        self._table_obj = None
        self._ddb_client = self.context.aws().dynamodb_table()
        VirtualDesktopNotifiableDB.__init__(self, context=context, table_name=self.table_name, logger=self._logger)
        OpenSearchableDB.__init__(
            self, context=context, logger=self._logger,
            term_filter_map={
                session_permissions_constants.SESSION_PERMISSIONS_FILTER_ACTOR_KEY: 'actor_name.raw',
                session_permissions_constants.SESSION_PERMISSIONS_FILTER_SESSION_ID_KEY: 'idea_session_id.raw',
                session_permissions_constants.SESSION_PERMISSIONS_FILTER_SESSION_NAME_KEY: 'idea_session_name.raw',
                session_permissions_constants.SESSION_PERMISSIONS_FILTER_SESSION_BASE_OS_KEY: 'idea_session_base_os.raw',
                session_permissions_constants.SESSION_PERMISSIONS_FILTER_SESSION_INSTANCE_TYPE_KEY: 'idea_session_instance_type.raw',
                session_permissions_constants.SESSION_PERMISSIONS_FILTER_SESSION_STATE_KEY: 'idea_session_state.raw',
                session_permissions_constants.SESSION_PERMISSIONS_FILTER_SESSION_TYPE_KEY: 'idea_session_type.raw',
                session_permissions_constants.SESSION_PERMISSIONS_FILTER_PERMISSION_PROFILE_ID_KEY: 'permission_profile_id.raw'
            },
            date_range_filter_map={
                session_permissions_constants.SESSION_PERMISSIONS_DB_IDEA_SESSION_CREATED_ON_KEY: 'idea_session_created_on'
            },
            default_page_size=self.DEFAULT_PAGE_SIZE
        )

    @property
    def _table(self):
        if Utils.is_empty(self._table_obj):
            self._table_obj = self._ddb_client.Table(self.table_name)
        return self._table_obj

    @property
    def table_name(self) -> str:
        return f'{self.context.cluster_name()}.{self.context.module_id()}.controller.session-permissions'

    def initialize(self):
        exists = self.context.aws_util().dynamodb_check_table_exists(self.table_name, True)
        if not exists:
            self.context.aws_util().dynamodb_create_table(
                create_table_request={
                    'TableName': self.table_name,
                    'AttributeDefinitions': [
                        {
                            'AttributeName': session_permissions_constants.SESSION_PERMISSIONS_DB_HASH_KEY,
                            'AttributeType': 'S'
                        },
                        {
                            'AttributeName': session_permissions_constants.SESSION_PERMISSIONS_DB_RANGE_KEY,
                            'AttributeType': 'S'
                        }
                    ],
                    'KeySchema': [
                        {
                            'AttributeName': session_permissions_constants.SESSION_PERMISSIONS_DB_HASH_KEY,
                            'KeyType': 'HASH'
                        },
                        {
                            'AttributeName': session_permissions_constants.SESSION_PERMISSIONS_DB_RANGE_KEY,
                            'KeyType': 'RANGE'
                        }
                    ],
                    'BillingMode': 'PAY_PER_REQUEST'
                },
                wait=True
            )

    def get_index_name(self) -> str:
        return f"{self.context.config().get_string('virtual-desktop-controller.opensearch.session_permission.alias', required=True)}-{self.context.session_permission_template_version}"

    def get_default_sort(self) -> SocaSortBy:
        return SocaSortBy(
            key=session_permissions_constants.SESSION_PERMISSIONS_FILTER_SESSION_CREATED_ON_KEY,
            order=SocaSortOrder.ASC
        )

    @staticmethod
    def convert_db_dict_to_session_permission_object(db_entry: Dict) -> Optional[VirtualDesktopSessionPermission]:
        return VirtualDesktopSessionPermission(
            idea_session_id=Utils.get_value_as_string(session_permissions_constants.SESSION_PERMISSIONS_DB_HASH_KEY, db_entry, ''),
            idea_session_owner=Utils.get_value_as_string(session_permissions_constants.SESSION_PERMISSIONS_DB_IDEA_SESSION_OWNER_KEY, db_entry, ''),
            idea_session_instance_type=Utils.get_value_as_string(session_permissions_constants.SESSION_PERMISSIONS_DB_IDEA_SESSION_INSTANCE_TYPE_KEY, db_entry, ''),
            idea_session_base_os=VirtualDesktopBaseOS(Utils.get_value_as_string(session_permissions_constants.SESSION_PERMISSIONS_DB_IDEA_SESSION_BASE_OS_KEY, db_entry, '')),
            idea_session_name=Utils.get_value_as_string(session_permissions_constants.SESSION_PERMISSIONS_DB_IDEA_SESSION_NAME_KEY, db_entry, ''),
            idea_session_state=VirtualDesktopSessionState(Utils.get_value_as_string(session_permissions_constants.SESSION_PERMISSIONS_DB_IDEA_SESSION_STATE_KEY, db_entry, '')),
            idea_session_created_on=Utils.to_datetime(Utils.get_value_as_int(session_permissions_constants.SESSION_PERMISSIONS_DB_IDEA_SESSION_CREATED_ON_KEY, db_entry)),
            idea_session_hibernation_enabled=Utils.get_value_as_bool(session_permissions_constants.SESSION_PERMISSIONS_DB_IDEA_SESSION_HIBERNATION_KEY, db_entry, False),
            idea_session_type=VirtualDesktopSessionType[Utils.get_value_as_string(session_permissions_constants.SESSION_PERMISSIONS_DB_IDEA_SESSION_TYPE_KEY, db_entry)],
            permission_profile=VirtualDesktopPermissionProfile(
                profile_id=Utils.get_value_as_string(session_permissions_constants.SESSION_PERMISSIONS_DB_PERMISSION_PROFILE_ID_KEY, db_entry, '')
            ),
            actor_type=VirtualDesktopSessionPermissionActorType(Utils.get_value_as_string(session_permissions_constants.SESSION_PERMISSIONS_DB_ACTOR_TYPE_KEY, db_entry, '')),
            actor_name=Utils.get_value_as_string(session_permissions_constants.SESSION_PERMISSIONS_DB_RANGE_KEY, db_entry, ''),
            created_on=Utils.to_datetime(Utils.get_value_as_int(session_permissions_constants.SESSION_PERMISSIONS_DB_CREATED_ON_KEY, db_entry)),
            updated_on=Utils.to_datetime(Utils.get_value_as_int(session_permissions_constants.SESSION_PERMISSIONS_DB_UPDATED_ON_KEY, db_entry)),
            expiry_date=Utils.to_datetime(Utils.get_value_as_int(session_permissions_constants.SESSION_PERMISSIONS_DB_EXPIRY_DATE_KEY, db_entry))
        )

    @staticmethod
    def convert_session_permission_object_to_db_dict(session_permission: VirtualDesktopSessionPermission) -> Dict:
        if Utils.is_empty(session_permission):
            return {}

        return {
            session_permissions_constants.SESSION_PERMISSIONS_DB_HASH_KEY: session_permission.idea_session_id,
            session_permissions_constants.SESSION_PERMISSIONS_DB_RANGE_KEY: session_permission.actor_name,
            session_permissions_constants.SESSION_PERMISSIONS_DB_IDEA_SESSION_OWNER_KEY: session_permission.idea_session_owner,
            session_permissions_constants.SESSION_PERMISSIONS_DB_IDEA_SESSION_BASE_OS_KEY: session_permission.idea_session_base_os,
            session_permissions_constants.SESSION_PERMISSIONS_DB_IDEA_SESSION_INSTANCE_TYPE_KEY: session_permission.idea_session_instance_type,
            session_permissions_constants.SESSION_PERMISSIONS_DB_IDEA_SESSION_STATE_KEY: session_permission.idea_session_state,
            session_permissions_constants.SESSION_PERMISSIONS_DB_IDEA_SESSION_NAME_KEY: session_permission.idea_session_name,
            session_permissions_constants.SESSION_PERMISSIONS_DB_IDEA_SESSION_CREATED_ON_KEY: Utils.to_milliseconds(session_permission.idea_session_created_on),
            session_permissions_constants.SESSION_PERMISSIONS_DB_IDEA_SESSION_TYPE_KEY: session_permission.idea_session_type,
            session_permissions_constants.SESSION_PERMISSIONS_DB_IDEA_SESSION_HIBERNATION_KEY: False if Utils.is_empty(session_permission.idea_session_hibernation_enabled) else session_permission.idea_session_hibernation_enabled,
            session_permissions_constants.SESSION_PERMISSIONS_DB_PERMISSION_PROFILE_ID_KEY: session_permission.permission_profile.profile_id,
            session_permissions_constants.SESSION_PERMISSIONS_DB_ACTOR_TYPE_KEY: session_permission.actor_type,
            session_permissions_constants.SESSION_PERMISSIONS_DB_EXPIRY_DATE_KEY: Utils.to_milliseconds(session_permission.expiry_date),
            session_permissions_constants.SESSION_PERMISSIONS_DB_CREATED_ON_KEY: Utils.to_milliseconds(session_permission.created_on),
            session_permissions_constants.SESSION_PERMISSIONS_DB_UPDATED_ON_KEY: Utils.to_milliseconds(session_permission.updated_on)
        }

    def create(self, session_permission: VirtualDesktopSessionPermission) -> VirtualDesktopSessionPermission:
        db_entry = self.convert_session_permission_object_to_db_dict(session_permission)
        db_entry[session_permissions_constants.SESSION_PERMISSIONS_DB_CREATED_ON_KEY] = Utils.current_time_ms()
        db_entry[session_permissions_constants.SESSION_PERMISSIONS_DB_UPDATED_ON_KEY] = Utils.current_time_ms()
        self._table.put_item(
            Item=db_entry
        )
        self.trigger_create_event(db_entry[session_permissions_constants.SESSION_PERMISSIONS_DB_HASH_KEY], db_entry[session_permissions_constants.SESSION_PERMISSIONS_DB_RANGE_KEY], new_entry=db_entry)
        return self.convert_db_dict_to_session_permission_object(db_entry)

    def update(self, session_permission: VirtualDesktopSessionPermission) -> VirtualDesktopSessionPermission:
        db_entry = self.convert_session_permission_object_to_db_dict(session_permission)
        db_entry[session_permissions_constants.SESSION_PERMISSIONS_DB_UPDATED_ON_KEY] = Utils.current_time_ms()
        update_expression_tokens = []
        expression_attr_names = {}
        expression_attr_values = {}

        for key, value in db_entry.items():
            if key in {session_permissions_constants.SESSION_PERMISSIONS_DB_HASH_KEY, session_permissions_constants.SESSION_PERMISSIONS_DB_RANGE_KEY, session_permissions_constants.SESSION_PERMISSIONS_DB_CREATED_ON_KEY}:
                continue
            update_expression_tokens.append(f'#{key} = :{key}')
            expression_attr_names[f'#{key}'] = key
            expression_attr_values[f':{key}'] = value

        result = self._table.update_item(
            Key={
                session_permissions_constants.SESSION_PERMISSIONS_DB_HASH_KEY: db_entry[session_permissions_constants.SESSION_PERMISSIONS_DB_HASH_KEY],
                session_permissions_constants.SESSION_PERMISSIONS_DB_RANGE_KEY: db_entry[session_permissions_constants.SESSION_PERMISSIONS_DB_RANGE_KEY],
            },
            UpdateExpression='SET ' + ', '.join(update_expression_tokens),
            ExpressionAttributeNames=expression_attr_names,
            ExpressionAttributeValues=expression_attr_values,
            ReturnValues='ALL_OLD'
        )

        old_db_entry = Utils.get_value_as_dict('Attributes', result, {})
        self.trigger_update_event(db_entry[session_permissions_constants.SESSION_PERMISSIONS_DB_HASH_KEY], db_entry[session_permissions_constants.SESSION_PERMISSIONS_DB_RANGE_KEY], old_entry=old_db_entry, new_entry=db_entry)
        return self.convert_db_dict_to_session_permission_object(db_entry)

    def delete(self, session_permission: VirtualDesktopSessionPermission):
        if Utils.is_empty(session_permission.idea_session_id) or Utils.is_empty(session_permission.actor_name):
            raise exceptions.invalid_params('idea_session_id and actor_name is required')

        result = self._table.delete_item(
            Key={
                session_permissions_constants.SESSION_PERMISSIONS_DB_HASH_KEY: session_permission.idea_session_id,
                session_permissions_constants.SESSION_PERMISSIONS_DB_RANGE_KEY: session_permission.actor_name
            },
            ReturnValues='ALL_OLD'
        )
        old_db_entry = Utils.get_value_as_dict('Attributes', result, {})
        self.trigger_delete_event(old_db_entry[session_permissions_constants.SESSION_PERMISSIONS_DB_HASH_KEY], old_db_entry[session_permissions_constants.SESSION_PERMISSIONS_DB_RANGE_KEY], deleted_entry=old_db_entry)

    def get_for_session(self, idea_session_id: str) -> List[VirtualDesktopSessionPermission]:
        if Utils.is_empty(idea_session_id):
            self._logger.error(f'idea_session_id: {idea_session_id} is invalid')
            return []

        session_permissions: List[VirtualDesktopSessionPermission] = []
        try:
            result = self._table.query(
                KeyConditionExpression=Key(session_permissions_constants.SESSION_PERMISSIONS_DB_HASH_KEY).eq(idea_session_id)
            )
            db_entry_list = Utils.get_value_as_list('Items', result, [])
            for db_entry in db_entry_list:
                session_permissions.append(self.convert_db_dict_to_session_permission_object(db_entry))
        except Exception as e:
            self._logger.error(e)
            return []
        return session_permissions

    def get(self, idea_session_id: str, actor: str) -> Optional[VirtualDesktopSessionPermission]:
        if Utils.is_any_empty(actor, idea_session_id):
            self._logger.error(f'actor: {actor} and/or idea_session_id: {idea_session_id} is invalid')
            return None

        try:
            result = self._table.get_item(
                Key={
                    session_permissions_constants.SESSION_PERMISSIONS_DB_HASH_KEY: idea_session_id,
                    session_permissions_constants.SESSION_PERMISSIONS_DB_RANGE_KEY: actor
                }
            )
            db_entry = Utils.get_value_as_dict('Item', result)
        except self._ddb_client.exceptions.ResourceNotFoundException as _:
            # in this case we simply need to return None since the resource was not found
            return None
        except Exception as e:
            self._logger.exception(e)
            raise e

        return self.convert_db_dict_to_session_permission_object(db_entry)

    def list_all_from_db(self, cursor: str) -> (List[VirtualDesktopSessionPermission], Optional[str]):
        scan_request = {}
        if Utils.is_not_empty(cursor):
            scan_request = {
                'ExclusiveStartKey': Utils.from_json(Utils.base64_decode(cursor))
            }

        permissions: List[VirtualDesktopSessionPermission] = []
        response_cursor = None
        try:
            result = self._table.scan(**scan_request)
            db_entries = Utils.get_value_as_list('Items', result, [])

            for db_entry in db_entries:
                permissions.append(self.convert_db_dict_to_session_permission_object(db_entry))

            last_evaluated_key = Utils.get_value_as_dict('LastEvaluatedKey', result)
            if Utils.is_not_empty(last_evaluated_key):
                response_cursor = Utils.base64_encode(Utils.to_json(last_evaluated_key))

        except Exception as e:
            self._logger.error(e)
        finally:
            return permissions, response_cursor

    def list_from_index(self, options: ListPermissionsRequest) -> ListPermissionsResponse:
        response = self.list_from_opensearch(options)
        permissions: List[VirtualDesktopSessionPermission] = []
        permissions_response = Utils.get_value_as_list('hits', Utils.get_value_as_dict('hits', response, default={}), default=[])
        for permission in permissions_response:
            index_object = Utils.get_value_as_dict('_source', permission, default={})
            permissions.append(self.convert_db_dict_to_session_permission_object(index_object))

        return ListPermissionsResponse(
            listing=permissions,
            paginator={},
            filters=options.filters,
            date_range=options.date_range,
            sort_by=options.sort_by
        )
