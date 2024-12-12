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
from ideadatamodel import exceptions, ListUsersInGroupRequest, ListUsersInGroupResult, SocaPaginator, constants
from ideasdk.context import SocaContext

from ideaclustermanager.app.accounts.db.user_dao import UserDAO

from boto3.dynamodb.conditions import Key
from res.resources import accounts


class GroupMembersDAO:

    def __init__(self, context: SocaContext, logger=None):
        self.context = context
        if logger is not None:
            self.logger = logger
        else:
            self.logger = context.logger('group-members-dao')
        self.table = None

    def get_table_name(self) -> str:
        return f'{self.context.cluster_name()}.accounts.group-members'

    def initialize(self):
        self.table = self.context.aws().dynamodb_table().Table(self.get_table_name())

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
                db_user = accounts.get_user(db_username)
                if db_user is None:
                    continue
                user = UserDAO.convert_from_db(db_user)
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
