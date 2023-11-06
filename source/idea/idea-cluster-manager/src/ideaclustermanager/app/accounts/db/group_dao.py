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
from ideadatamodel import exceptions, ListGroupsRequest, ListGroupsResult, Group, SocaPaginator
from ideasdk.context import SocaContext

from typing import Optional, Dict
from boto3.dynamodb.conditions import Attr


class GroupDAO:

    def __init__(self, context: SocaContext, logger=None):
        self.context = context
        if logger is not None:
            self.logger = logger
        else:
            self.logger = context.logger('group-dao')
        self.table = None

    def get_table_name(self) -> str:
        return f'{self.context.cluster_name()}.accounts.groups'

    def initialize(self):
        self.context.aws_util().dynamodb_create_table(
            create_table_request={
                'TableName': self.get_table_name(),
                'AttributeDefinitions': [
                    {
                        'AttributeName': 'group_name',
                        'AttributeType': 'S'
                    }
                ],
                'KeySchema': [
                    {
                        'AttributeName': 'group_name',
                        'KeyType': 'HASH'
                    }
                ],
                'BillingMode': 'PAY_PER_REQUEST'
            },
            wait=True
        )
        self.table = self.context.aws().dynamodb_table().Table(self.get_table_name())

    @staticmethod
    def convert_from_db(group: Dict) -> Group:
        return Group(
            **{
                'name': Utils.get_value_as_string('group_name', group),
                'ds_name': Utils.get_value_as_string('ds_name', group),
                'gid': Utils.get_value_as_int('gid', group),
                'title': Utils.get_value_as_string('title', group),
                'description': Utils.get_value_as_string('description', group),
                'enabled': Utils.get_value_as_bool('enabled', group),
                'group_type': Utils.get_value_as_string('group_type', group),
                'type': Utils.get_value_as_string('type', group),
                'role': Utils.get_value_as_string('role', group),
                'created_on': Utils.get_value_as_int('created_on', group),
                'updated_on': Utils.get_value_as_int('updated_on', group),
                'synced_on': Utils.get_value_as_int('synced_on', group)
            }
        )

    @staticmethod
    def convert_to_db(group: Group) -> Dict:
        db_group = {
            'group_name': group.name,
        }
        if group.name is not None:
            db_group['group_name'] = group.name
        if group.gid is not None:
            db_group['gid'] = group.gid
        if group.title is not None:
            db_group['title'] = group.title
        if group.description is not None:
            db_group['description'] = group.description
        if group.enabled is not None:
            db_group['enabled'] = group.enabled
        if group.group_type is not None:
            db_group['group_type'] = group.group_type
        if group.type is not None:
            db_group['type'] = group.type
        if group.role is not None:
            db_group['role'] = group.role
        if group.ref is not None:
            db_group['ref'] = group.ref
        if group.ds_name is not None:
            db_group['ds_name'] = group.ds_name
        return db_group

    def create_group(self, group: Dict) -> Dict:

        group_name = Utils.get_value_as_string('group_name', group)
        if Utils.is_empty(group_name):
            raise exceptions.invalid_params('group_name is required')

        created_group = {
            **group,
            'created_on': Utils.current_time_ms(),
            'updated_on': Utils.current_time_ms()
        }
        self.table.put_item(
            Item=created_group,
            ConditionExpression=Attr('group_name').not_exists()
        )
        return created_group

    def get_group(self, group_name: str) -> Optional[Dict]:
        if Utils.is_empty(group_name):
            raise exceptions.invalid_params('group_name is required')
        result = self.table.get_item(
            Key={
                'group_name': group_name
            }
        )
        return Utils.get_value_as_dict('Item', result)

    def update_group(self, group: Dict) -> Optional[Dict]:
        group_name = Utils.get_value_as_string('group_name', group)
        if Utils.is_empty(group_name):
            raise exceptions.invalid_params('group_name is required')

        group['updated_on'] = Utils.current_time_ms()

        update_expression_tokens = []
        expression_attr_names = {}
        expression_attr_values = {}

        for key, value in group.items():
            if key in ('group_name', 'created_on'):
                continue
            update_expression_tokens.append(f'#{key} = :{key}')
            expression_attr_names[f'#{key}'] = key
            expression_attr_values[f':{key}'] = value

        result = self.table.update_item(
            Key={
                'group_name': group_name
            },
            ConditionExpression=Attr('group_name').eq(group_name),
            UpdateExpression='SET ' + ', '.join(update_expression_tokens),
            ExpressionAttributeNames=expression_attr_names,
            ExpressionAttributeValues=expression_attr_values,
            ReturnValues='ALL_NEW'
        )

        updated_user = result['Attributes']
        return updated_user

    def delete_group(self, group_name: str):
        if Utils.is_empty(group_name):
            raise exceptions.invalid_params('group_name is required')
        self.table.delete_item(
            Key={
                'group_name': group_name
            }
        )

    def list_groups(self, request: ListGroupsRequest) -> ListGroupsResult:

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

        scan_result = self.table.scan(**scan_request)

        db_groups = Utils.get_value_as_list('Items', scan_result, [])
        groups = []
        for db_group in db_groups:
            group = self.convert_from_db(db_group)
            groups.append(group)

        response_cursor = None
        last_evaluated_key = Utils.get_any_value('LastEvaluatedKey', scan_result)
        if last_evaluated_key is not None:
            response_cursor = Utils.base64_encode(Utils.to_json(last_evaluated_key))

        return ListGroupsResult(
            listing=groups,
            paginator=SocaPaginator(
                cursor=response_cursor
            )
        )
