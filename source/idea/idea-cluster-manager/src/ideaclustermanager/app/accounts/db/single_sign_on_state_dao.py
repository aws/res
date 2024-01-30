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
from ideadatamodel import exceptions, AuthResult
from ideasdk.context import SocaContext

from typing import Optional, Dict
from boto3.dynamodb.conditions import Attr


class SingleSignOnStateDAO:

    def __init__(self, context: SocaContext, logger=None):
        self.context = context
        if logger is not None:
            self.logger = logger
        else:
            self.logger = context.logger('single-sign-on-state-dao')
        self.table = None

    def get_table_name(self) -> str:
        return f'{self.context.cluster_name()}.accounts.sso-state'

    def initialize(self):
        self.context.aws_util().dynamodb_create_table(
            create_table_request={
                'TableName': self.get_table_name(),
                'AttributeDefinitions': [
                    {
                        'AttributeName': 'state',
                        'AttributeType': 'S'
                    }
                ],
                'KeySchema': [
                    {
                        'AttributeName': 'state',
                        'KeyType': 'HASH'
                    }
                ],
                'BillingMode': 'PAY_PER_REQUEST'
            },
            wait=True,
            ttl=True,
            ttl_attribute_name='ttl'
        )
        self.table = self.context.aws().dynamodb_table().Table(self.get_table_name())

    def create_sso_state(self, sso_state: Dict) -> Dict:

        state = Utils.get_value_as_string('state', sso_state)
        if Utils.is_empty(state):
            raise exceptions.invalid_params('state is required')

        created_state = {
            **sso_state,
            'ttl': Utils.current_time_ms() + (10 * 60 * 1000),  # 10 minutes
            'created_on': Utils.current_time_ms(),
            'updated_on': Utils.current_time_ms(),
        }
        self.table.put_item(
            Item=created_state,
            ConditionExpression=Attr('state').not_exists()
        )
        return created_state

    def update_sso_state(self, sso_state: Dict) -> Dict:

        state = Utils.get_value_as_string('state', sso_state)
        if Utils.is_empty(state):
            raise exceptions.invalid_params('state is required')

        sso_state['updated_on'] = Utils.current_time_ms()

        update_expression_tokens = []
        expression_attr_names = {}
        expression_attr_values = {}

        for key, value in sso_state.items():
            if key in ('state', 'created_on'):
                continue
            update_expression_tokens.append(f'#{key} = :{key}')
            expression_attr_names[f'#{key}'] = key
            expression_attr_values[f':{key}'] = value

        result = self.table.update_item(
            Key={
                'state': state
            },
            ConditionExpression=Attr('state').eq(state),
            UpdateExpression='SET ' + ', '.join(update_expression_tokens),
            ExpressionAttributeNames=expression_attr_names,
            ExpressionAttributeValues=expression_attr_values,
            ReturnValues='ALL_NEW'
        )

        updated_sso_state = result['Attributes']
        updated_sso_state['state'] = state
        return updated_sso_state

    def get_sso_state(self, state: str) -> Optional[Dict]:
        if Utils.is_empty(state):
            raise exceptions.invalid_params('state is required')
        result = self.table.get_item(
            Key={
                'state': state
            }
        )
        return Utils.get_value_as_dict('Item', result)

    def delete_sso_state(self, state: str):
        if Utils.is_empty(state):
            raise exceptions.invalid_params('state is required')
        self.table.delete_item(
            Key={
                'state': state
            }
        )
