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
from ideadatamodel import (exceptions, EmailTemplate, ListEmailTemplatesRequest, ListEmailTemplatesResult, SocaPaginator)
from ideasdk.context import SocaContext

from typing import Dict, Optional
from boto3.dynamodb.conditions import Attr
import arrow


class EmailTemplatesDAO:

    def __init__(self, context: SocaContext, logger=None):
        self.context = context
        if logger is not None:
            self.logger = logger
        else:
            self.logger = context.logger('email-templates-dao')
        self.table = None

    def get_table_name(self) -> str:
        return f'{self.context.cluster_name()}.email-templates'

    def initialize(self):
        self.context.aws_util().dynamodb_create_table(
            create_table_request={
                'TableName': self.get_table_name(),
                'AttributeDefinitions': [
                    {
                        'AttributeName': 'name',
                        'AttributeType': 'S'
                    }
                ],
                'KeySchema': [
                    {
                        'AttributeName': 'name',
                        'KeyType': 'HASH'
                    }
                ],
                'BillingMode': 'PAY_PER_REQUEST'
            },
            wait=True
        )
        self.table = self.context.aws().dynamodb_table().Table(self.get_table_name())

    @staticmethod
    def convert_from_db(email_template: Dict) -> EmailTemplate:
        name = Utils.get_value_as_string('name', email_template)
        title = Utils.get_value_as_string('title', email_template)
        template_type = Utils.get_value_as_string('template_type', email_template)
        subject = Utils.get_value_as_string('subject', email_template)
        body = Utils.get_value_as_string('body', email_template)
        created_on = Utils.get_value_as_int('created_on', email_template)
        updated_on = Utils.get_value_as_int('updated_on', email_template)
        return EmailTemplate(
            name=name,
            title=title,
            template_type=template_type,
            subject=subject,
            body=body,
            created_on=arrow.get(created_on).datetime,
            updated_on=arrow.get(updated_on).datetime
        )

    @staticmethod
    def convert_to_db(email_template: EmailTemplate) -> Dict:
        db_email_template = {
            'name': email_template.name
        }

        if email_template.title is not None:
            db_email_template['title'] = email_template.title

        if email_template.template_type is not None:
            db_email_template['template_type'] = email_template.template_type

        if email_template.subject is not None:
            db_email_template['subject'] = email_template.subject

        if email_template.body is not None:
            db_email_template['body'] = email_template.body

        return db_email_template

    def create_email_template(self, email_template: Dict) -> Dict:

        name = Utils.get_value_as_string('name', email_template)
        if Utils.is_empty(name):
            raise exceptions.invalid_params('name is required')

        created_email_template = {
            **email_template,
            'created_on': Utils.current_time_ms(),
            'updated_on': Utils.current_time_ms()
        }
        self.table.put_item(
            Item=created_email_template
        )

        return created_email_template

    def get_email_template(self, name: str) -> Optional[Dict]:

        if Utils.is_empty(name):
            raise exceptions.invalid_params('name is required')

        result = self.table.get_item(
            Key={
                'name': name
            }
        )
        return Utils.get_value_as_dict('Item', result)

    def update_email_template(self, email_template: Dict):

        name = Utils.get_value_as_string('name', email_template)
        if Utils.is_empty(name):
            raise exceptions.invalid_params('name is required')

        email_template['updated_on'] = Utils.current_time_ms()

        update_expression_tokens = []
        expression_attr_names = {}
        expression_attr_values = {}

        for key, value in email_template.items():
            if key in ('name', 'created_on'):
                continue
            update_expression_tokens.append(f'#{key} = :{key}')
            expression_attr_names[f'#{key}'] = key
            expression_attr_values[f':{key}'] = value

        result = self.table.update_item(
            Key={
                'name': name
            },
            ConditionExpression=Attr('name').eq(name),
            UpdateExpression='SET ' + ', '.join(update_expression_tokens),
            ExpressionAttributeNames=expression_attr_names,
            ExpressionAttributeValues=expression_attr_values,
            ReturnValues='ALL_NEW'
        )

        updated_email_template = result['Attributes']
        updated_email_template['name'] = name

        return updated_email_template

    def delete_email_template(self, name: str):

        if Utils.is_empty(name):
            raise exceptions.invalid_params('name is required')

        self.table.delete_item(
            Key={
                'name': name
            }
        )

    def list_email_templates(self, request: ListEmailTemplatesRequest) -> ListEmailTemplatesResult:
        scan_request = {}

        cursor = request.cursor
        last_evaluated_key = None
        if Utils.is_not_empty(cursor):
            last_evaluated_key = Utils.from_json(Utils.base64_decode(cursor))
        if last_evaluated_key is not None:
            scan_request['ExclusiveStartKey'] = last_evaluated_key

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

        db_email_templates = Utils.get_value_as_list('Items', scan_result, [])
        email_templates = []
        for db_email_template in db_email_templates:
            email_template = self.convert_from_db(db_email_template)
            email_templates.append(email_template)

        response_cursor = None
        last_evaluated_key = Utils.get_any_value('LastEvaluatedKey', scan_result)
        if last_evaluated_key is not None:
            response_cursor = Utils.base64_encode(Utils.to_json(last_evaluated_key))

        return ListEmailTemplatesResult(
            listing=email_templates,
            paginator=SocaPaginator(
                cursor=response_cursor
            )
        )
