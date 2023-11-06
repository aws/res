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

from ideasdk.utils import Utils
from ideadatamodel import exceptions, ListUsersInGroupRequest, ListUsersInGroupResult, SocaPaginator
from ideasdk.context import SocaContext

from ideaclustermanager.app.accounts.auth_utils import AuthUtils
from ideaclustermanager.app.accounts.db.user_dao import UserDAO

from typing import List
from boto3.dynamodb.conditions import Key


class GroupMembersDAO:

    def __init__(self, context: SocaContext, user_dao: UserDAO, logger=None):
        self.context = context
        self.user_dao = user_dao
        if logger is not None:
            self.logger = logger
        else:
            self.logger = context.logger('group-members-dao')
        self.table = None

    def get_table_name(self) -> str:
        return f'{self.context.cluster_name()}.accounts.group-members'

    def initialize(self):
        self.context.aws_util().dynamodb_create_table(
            create_table_request={
                'TableName': self.get_table_name(),
                'AttributeDefinitions': [
                    {
                        'AttributeName': 'group_name',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'username',
                        'AttributeType': 'S'
                    }
                ],
                'KeySchema': [
                    {
                        'AttributeName': 'group_name',
                        'KeyType': 'HASH'
                    },
                    {
                        'AttributeName': 'username',
                        'KeyType': 'RANGE'
                    }
                ],
                'BillingMode': 'PAY_PER_REQUEST'
            },
            wait=True
        )
        self.table = self.context.aws().dynamodb_table().Table(self.get_table_name())

    def create_membership(self, group_name: str, username: str):
        username = AuthUtils.sanitize_username(username)
        if Utils.is_empty(group_name):
            raise exceptions.invalid_params('group_name is required')

        self.table.put_item(
            Item={
                'group_name': group_name,
                'username': username
            }
        )

    def delete_membership(self, group_name: str, username: str):
        username = AuthUtils.sanitize_username(username)
        if Utils.is_empty(group_name):
            raise exceptions.invalid_params('group_name is required')

        self.table.delete_item(
            Key={
                'group_name': group_name,
                'username': username
            }
        )

    def has_users_in_group(self, group_name: str) -> bool:
        query_result = self.table.query(
            Limit=1,
            KeyConditions={
                'group_name': {
                    'AttributeValueList': [group_name],
                    'ComparisonOperator': 'EQ'
                }
            }
        )
        memberships = Utils.get_value_as_list('Items', query_result, [])
        return len(memberships) > 0

    def get_usernames_in_group(self, group_name: str) -> List[str]:
        if Utils.is_empty(group_name):
            raise exceptions.invalid_params('group_name is required')

        usernames = []

        exclusive_start_key = None
        while True:
            if exclusive_start_key is not None:
                query_result = self.table.query(
                    ExclusiveStartKey=exclusive_start_key,
                    KeyConditionExpression=Key('group_name').eq(group_name)
                )
            else:
                query_result = self.table.query(
                    KeyConditionExpression=Key('group_name').eq(group_name)
                )

            db_user_groups = Utils.get_value_as_list('Items', query_result, [])
            for db_user_group in db_user_groups:
                usernames.append(db_user_group['username'])

            exclusive_start_key = Utils.get_any_value('LastEvaluatedKey', query_result)
            if exclusive_start_key is None:
                break

        return usernames

    def list_users_in_group(self, request: ListUsersInGroupRequest) -> ListUsersInGroupResult:
        group_names = request.group_names
        if Utils.is_empty(group_names):
            raise exceptions.invalid_params('group_names are required')

        cursor = request.cursor
        exclusive_start_keys = None
        last_evaluated_keys = {}
        username_set = set()
        users = []

        if Utils.is_not_empty(cursor):
            exclusive_start_keys = Utils.from_json(Utils.base64_decode(cursor))

        for group_name in group_names:
            exclusive_start_key = Utils.get_value_as_dict(group_name, exclusive_start_keys, {})
            if Utils.is_not_empty(exclusive_start_key):
                query_result = self.table.query(
                    Limit=request.page_size,
                    ExclusiveStartKey=exclusive_start_key,
                    KeyConditionExpression=Key('group_name').eq(group_name)
                )
            else:
                query_result = self.table.query(
                    Limit=request.page_size,
                    KeyConditionExpression=Key('group_name').eq(group_name)
                )

            db_user_groups = Utils.get_value_as_list('Items', query_result, [])
            for db_user_group in db_user_groups:
                db_username = db_user_group['username']
                if db_username in username_set:
                    continue
                username_set.add(db_username)
                db_user = self.user_dao.get_user(db_username)
                if db_user is None:
                    continue
                user = self.user_dao.convert_from_db(db_user)
                users.append(user)

            last_evaluated_key = Utils.get_any_value('LastEvaluatedKey', query_result)
            if Utils.is_not_empty(last_evaluated_key):
                last_evaluated_keys[group_name] = last_evaluated_key

        response_cursor = None
        if Utils.is_not_empty(last_evaluated_keys):
            response_cursor = Utils.base64_encode(Utils.to_json(last_evaluated_keys))

        return ListUsersInGroupResult(
            listing=users,
            paginator=SocaPaginator(
                page_size=request.page_size,
                cursor=response_cursor
            )
        )
