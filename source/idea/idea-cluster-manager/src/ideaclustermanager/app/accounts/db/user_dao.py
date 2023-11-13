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
import logging

from ideasdk.utils import Utils
from ideadatamodel import ListUsersRequest, ListUsersResult, SocaPaginator, User
from ideasdk.context import SocaContext

from ideaclustermanager.app.accounts.auth_utils import AuthUtils
from ideaclustermanager.app.accounts.cognito_user_pool import CognitoUserPool

from typing import Optional, Dict
from boto3.dynamodb.conditions import Attr


class UserDAO:

    def __init__(self, context: SocaContext, user_pool: CognitoUserPool, logger=None):
        self.context = context
        if logger is not None:
            self.logger = logger
        else:
            self.logger = context.logger('user-dao')
        self.user_pool = user_pool
        self.table = None

    def get_table_name(self) -> str:
        return f'{self.context.cluster_name()}.accounts.users'

    def initialize(self):
        self.context.aws_util().dynamodb_create_table(
            create_table_request={
                'TableName': self.get_table_name(),
                'AttributeDefinitions': [
                    {
                        'AttributeName': 'username',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'role',
                        'AttributeType': 'S'
                    }
                ],
                'KeySchema': [
                    {
                        'AttributeName': 'username',
                        'KeyType': 'HASH'
                    }
                ],
                "GlobalSecondaryIndexes": [
                    {
                        "IndexName": "role-index",
                        "KeySchema": [
                            {
                                "AttributeName": "role",
                                "KeyType": "HASH"
                            }
                        ],
                        "Projection": {
                            "ProjectionType": "INCLUDE",
                            "NonKeyAttributes": [
                                "additional_groups",
                                "username"
                            ]
                        },
                    }
                ],
                'BillingMode': 'PAY_PER_REQUEST'
            },
            wait=True
        )
        self.table = self.context.aws().dynamodb_table().Table(self.get_table_name())

    def convert_from_db(self, user: Dict) -> User:
        user_entry = User(
            **{
                'username': Utils.get_value_as_string('username', user),
                'email': Utils.get_value_as_string('email', user),
                'uid': Utils.get_value_as_int('uid', user),
                'gid': Utils.get_value_as_int('gid', user),
                'group_name': Utils.get_value_as_string('group_name', user),
                'login_shell': Utils.get_value_as_string('login_shell', user),
                'home_dir': Utils.get_value_as_string('home_dir', user),
                'sudo': Utils.get_value_as_bool('sudo', user),
                'enabled': Utils.get_value_as_bool('enabled', user),
                'password_last_set': Utils.get_value_as_int('password_last_set', user),
                'password_max_age': Utils.get_value_as_int('password_max_age', user),
                'additional_groups': Utils.get_value_as_list('additional_groups', user),
                'created_on': Utils.get_value_as_int('created_on', user),
                'updated_on': Utils.get_value_as_int('updated_on', user),
                'role': user['role'] if 'role' in user else None,
                'synced_on': int(user['synced_on']) if 'synced_on' in user else None,
                'is_active': user['is_active'] if 'is_active' in user else None
            }
        )

        # The Cognito status lookup was removed for performance considerations
        # over multiple/looped API calls for bulk users. This takes place on
        # singleton lookups/get_user.

        return user_entry

    @staticmethod
    def convert_to_db(user: User) -> Dict:
        db_user = {
            'username': user.username
        }
        if user.email is not None:
            db_user['email'] = user.email
        if user.uid is not None:
            db_user['uid'] = user.uid
        if user.gid is not None:
            db_user['gid'] = user.gid
        if user.group_name is not None:
            db_user['group_name'] = user.group_name
        if user.login_shell is not None:
            db_user['login_shell'] = user.login_shell
        if user.home_dir is not None:
            db_user['home_dir'] = user.home_dir
        if user.sudo is not None:
            db_user['sudo'] = user.sudo
        if user.role is not None:
            db_user['role'] = user.role
        if user.is_active is not None:
            db_user['is_active'] = user.is_active
        if user.enabled is not None:
            db_user['enabled'] = user.enabled
        if user.password_last_set is not None:
            db_user['password_last_set'] = int(user.password_last_set.timestamp() * 1000)
        if user.password_max_age is not None:
            db_user['password_max_age'] = int(user.password_max_age)
        if user.additional_groups is not None:
            db_user['additional_groups'] = user.additional_groups

        return db_user

    def create_user(self, user: Dict) -> Dict:

        username = Utils.get_value_as_string('username', user)
        username = AuthUtils.sanitize_username(username)

        created_user = {
            **user,
            'username': username,
            'created_on': Utils.current_time_ms(),
            'updated_on': Utils.current_time_ms(),
            'synced_on': Utils.current_time_ms()
        }

        self.table.put_item(
            Item=created_user,
            ConditionExpression=Attr('username').not_exists()
        )
        return created_user

    def get_user(self, username: str) -> Optional[Dict]:
        username = AuthUtils.sanitize_username(username)
        _lu_start = Utils.current_time_ms()
        result = self.table.get_item(
            Key={
                'username': username
            }
        )
        _lu_stop = Utils.current_time_ms()
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"user_lookup: {result} - {_lu_stop - _lu_start}ms")
        return Utils.get_value_as_dict('Item', result)


    def update_user(self, user: Dict) -> Dict:
        username = Utils.get_value_as_string('username', user)
        username = AuthUtils.sanitize_username(username)
        user['updated_on'] = Utils.current_time_ms()

        update_expression_tokens = []
        expression_attr_names = {}
        expression_attr_values = {}

        for key, value in user.items():
            if key in ('username', 'created_on'):
                continue
            update_expression_tokens.append(f'#{key} = :{key}')
            expression_attr_names[f'#{key}'] = key
            expression_attr_values[f':{key}'] = value

        result = self.table.update_item(
            Key={
                'username': username
            },
            ConditionExpression=Attr('username').eq(username),
            UpdateExpression='SET ' + ', '.join(update_expression_tokens),
            ExpressionAttributeNames=expression_attr_names,
            ExpressionAttributeValues=expression_attr_values,
            ReturnValues='ALL_NEW'
        )

        updated_user = result['Attributes']
        updated_user['username'] = username
        return updated_user

    def delete_user(self, username: str):

        username = AuthUtils.sanitize_username(username)
        self.table.delete_item(
            Key={
                'username': username
            }
        )

    def list_users(self, request: ListUsersRequest) -> ListUsersResult:

        scan_request = {}

        cursor = request.cursor
        last_evaluated_key = None
        if Utils.is_not_empty(cursor):
            last_evaluated_key = Utils.from_json(Utils.base64_decode(cursor))
        if last_evaluated_key is not None:
            scan_request['LastEvaluatedKey'] = last_evaluated_key

        scan_filter = None
        if Utils.is_not_empty(request.filters):
            scan_filter = {}
            for filter_ in request.filters:
                if filter_.eq is not None:
                    scan_filter[filter_.key] = {
                        'AttributeValueList': [filter_.eq],
                        'ComparisonOperator': 'EQ'
                    }
                if filter_.like is not None:
                    scan_filter[filter_.key] = {
                        'AttributeValueList': [filter_.like],
                        'ComparisonOperator': 'CONTAINS'
                    }
        if scan_filter is not None:
            scan_request['ScanFilter'] = scan_filter

        _scan_start = Utils.current_time_ms()
        scan_result = self.table.scan(**scan_request)
        _scan_end = Utils.current_time_ms()

        db_users = Utils.get_value_as_list('Items', scan_result, [])

        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"DDB Table scan took {_scan_end - _scan_start}ms for {len(db_users)} users")

        users = []

        _idp_start = Utils.current_time_ms()
        for db_user in db_users:
            user = self.convert_from_db(db_user)
            users.append(user)
        _idp_end = Utils.current_time_ms()

        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"User status took {_idp_end - _idp_start}ms for {len(users)} users")

        response_cursor = None
        last_evaluated_key = Utils.get_any_value('LastEvaluatedKey', scan_result)
        if last_evaluated_key is not None:
            response_cursor = Utils.base64_encode(Utils.to_json(last_evaluated_key))

        return ListUsersResult(
            listing=users,
            paginator=SocaPaginator(
                cursor=response_cursor
            )
        )
